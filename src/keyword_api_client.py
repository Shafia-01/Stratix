import os
import requests
import json
import base64
from dotenv import load_dotenv
from src.gemini_client import generate_keywords
from src.data_quality import DataSource
from src.logger_config import get_logger

logger = get_logger(__name__)

load_dotenv()

# ------------------------------------------------------------
# API CONFIGURATION
# ------------------------------------------------------------
DATAFORSEO_USERNAME = os.getenv("DATAFORSEO_USERNAME")
DATAFORSEO_PASSWORD = os.getenv("DATAFORSEO_PASSWORD")
LIVE_API_URL = "https://api.dataforseo.com/v3"
SANDBOX_URL = "https://sandbox.dataforseo.com/v3"

# Credit Preservation Settings
# Set DEMO_MODE=true to use sandbox/cached data (preserves credits)
# Set PRESERVE_CREDITS=true to auto-switch to sandbox when balance is low
# Set LOW_BALANCE_THRESHOLD=0.50 to switch to sandbox when balance < $0.50
DEMO_MODE = os.getenv("DATAFORSEO_DEMO_MODE", "false").lower() == "true"
PRESERVE_CREDITS = os.getenv("DATAFORSEO_PRESERVE_CREDITS", "true").lower() == "true"
LOW_BALANCE_THRESHOLD = float(os.getenv("DATAFORSEO_LOW_BALANCE_THRESHOLD", "0.50"))
FORCE_SANDBOX = os.getenv("DATAFORSEO_FORCE_SANDBOX", "false").lower() == "true"

class KeywordAPIClient:
    """
    Hybrid keyword client with intelligent fallback:
    1. Try DataForSEO Live API (real-time data)
    2. Auto-switch to Sandbox if account limited/balance=0
    3. Fallback to Gemini if DataForSEO completely unreachable
    """

    def __init__(self):
        self.session = requests.Session()
        self.using_sandbox = False
        self.account_limited = False
        self.balance_zero = False
        self.credits_preserved = False
        
        # Credit preservation modes
        if FORCE_SANDBOX:
            logger.info(f"🔒 FORCE_SANDBOX mode enabled - Using sandbox only (preserves credits)")
            self.base_url = SANDBOX_URL
            self.using_sandbox = True
            self.credits_preserved = True
        elif DEMO_MODE:
            logger.info(f"🎭 DEMO_MODE enabled - Using sandbox/cached data (preserves credits)")
            self.base_url = SANDBOX_URL
            self.using_sandbox = True
            self.credits_preserved = True
        else:
            self.base_url = LIVE_API_URL  # Start with live API
        
        if DATAFORSEO_USERNAME and DATAFORSEO_PASSWORD:
            credentials = f"{DATAFORSEO_USERNAME}:{DATAFORSEO_PASSWORD}"
            encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
            self.session.headers.update({
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json"
            })
            
            # Check balance if preserve credits is enabled and not in demo/sandbox mode
            if PRESERVE_CREDITS and not self.using_sandbox:
                balance = self._check_balance()
                if balance is not None and balance < LOW_BALANCE_THRESHOLD:
                    logger.info(f"💰 Low balance detected (${balance:.3f} < ${LOW_BALANCE_THRESHOLD})")
                    logger.info(f"🔒 Auto-switching to sandbox mode to preserve credits")
                    self._switch_to_sandbox()
                    self.credits_preserved = True
        else:
            logger.warning(f"Missing DataForSEO credentials. Will use Gemini fallback only.")
    
    def _check_balance(self):
        """
        Check DataForSEO account balance.
        Returns balance as float or None if unavailable.
        """
        try:
            # DataForSEO User endpoint to get account info
            url = f"{LIVE_API_URL}/user"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Try to extract balance from response
                # Note: Actual endpoint structure may vary
                if "balance" in data:
                    return float(data["balance"])
                elif "data" in data and "balance" in data["data"]:
                    return float(data["data"]["balance"])
            
            # If balance check fails, return None (will proceed with caution)
            return None
        except Exception as e:
            # If we can't check balance, return None
            logger.warning(f"Could not check balance: {e}")
            return None

    def _is_account_limited_error(self, status_code, response_data):
        """
        Detect if account is limited, balance is zero, or rate limited.
        Returns: (is_limited, error_type)
        """
        # HTTP Status Code checks
        if status_code == 402:
            # Payment Required - balance is zero
            return True, "balance_zero"
        elif status_code == 429:
            # Rate Limited - too many requests
            return True, "rate_limited"
        elif status_code == 401:
            # Unauthorized - invalid credentials
            return True, "unauthorized"
        
        # DataForSEO Response Status Code checks
        if response_data:
            df_status = response_data.get("status_code")
            status_message = response_data.get("status_message", "").lower()
            error_message = str(response_data).lower()
            
            # Check for balance/credit related errors
            if df_status and df_status != 20000:
                # Status codes that indicate account issues
                if df_status in [40001, 40002, 40003]:  # Invalid parameters
                    return False, None
                elif df_status in [40100, 40101, 40102]:  # Authentication errors
                    return True, "unauthorized"
                elif df_status in [40200, 40201]:  # Payment/balance errors
                    return True, "balance_zero"
                elif df_status in [42900, 42901]:  # Rate limit errors
                    return True, "rate_limited"
            
            # Check error messages for balance/limit keywords
            balance_keywords = ["balance", "credit", "payment", "insufficient", "zero balance", 
                              "account limit", "quota exceeded", "no credits"]
            if any(keyword in error_message or keyword in status_message for keyword in balance_keywords):
                return True, "balance_zero"
            
            limit_keywords = ["rate limit", "too many requests", "throttled", "limit exceeded"]
            if any(keyword in error_message or keyword in status_message for keyword in limit_keywords):
                return True, "rate_limited"
        
        return False, None

    def _switch_to_sandbox(self):
        """Switch client to Sandbox environment for testing/mock data."""
        if not self.using_sandbox:
            logger.info(f"🧩 Switching to DataForSEO Sandbox mode (mock results)...")
            self.base_url = SANDBOX_URL
            self.using_sandbox = True
            self.credits_preserved = True

    def _should_use_sandbox(self, status_code, response_data):
        """
        Determine if we should switch to sandbox based on error.
        Returns True if account is limited or balance is zero.
        """
        is_limited, error_type = self._is_account_limited_error(status_code, response_data)
        
        if is_limited:
            if error_type == "balance_zero":
                self.balance_zero = True
                logger.info(f"💳 Account balance is zero. Switching to Sandbox...")
                return True
            elif error_type == "rate_limited":
                self.account_limited = True
                logger.info(f"⏱️ Account rate limited. Switching to Sandbox...")
                return True
            elif error_type == "unauthorized":
                logger.info(f"🔐 Authentication failed. Check your credentials.")
                return False  # Don't use sandbox for auth errors
        
        return False

    # ------------------------------------------------------------
    # MAIN FUNCTION: Keyword Suggestions
    # ------------------------------------------------------------
    def get_keyword_suggestions(self, seed_keyword, max_keywords=50, location_code=2840, language_code="en"):
        """
        Get keyword suggestions with intelligent fallback:
        1. Try DataForSEO Live API
        2. Auto-switch to Sandbox if account limited/balance=0
        3. Fallback to Gemini if DataForSEO unreachable
        """
        # Skip DataForSEO if no credentials
        if not DATAFORSEO_USERNAME or not DATAFORSEO_PASSWORD:
            logger.warning(f"No DataForSEO credentials. Using Gemini fallback...")
            return self._fallback_to_gemini(seed_keyword, max_keywords)

        # Don't reset if in preserve credits mode
        if self.credits_preserved or self.using_sandbox:
            logger.info(f"💾 Credits preservation mode active - Using {'sandbox' if self.using_sandbox else 'cached'} data")
        
        # Reset state for new request (unless we know account is limited or preserving credits)
        if not self.balance_zero and not self.account_limited and not self.credits_preserved:
            # Only reset if not in demo/sandbox mode
            if not FORCE_SANDBOX and not DEMO_MODE:
                self.base_url = LIVE_API_URL
                self.using_sandbox = False

        try:
            logger.info(f"Fetching keywords for: '{seed_keyword}'")
            mode_indicator = "🔒 SANDBOX (Credits Preserved)" if self.credits_preserved else "🌐 Live DataForSEO"
            logger.info(f"{mode_indicator}: {'Sandbox' if self.using_sandbox else 'Live API'}")
            
            # Step 1: Get keyword suggestions
            suggestions, error_info = self._get_dataforseo_suggestions(
                seed_keyword, location_code, language_code
            )
            
            # Check if we should switch to sandbox
            if error_info and not self.using_sandbox:
                status_code, response_data = error_info
                if self._should_use_sandbox(status_code, response_data):
                    self._switch_to_sandbox()
                    # Retry with sandbox
                    suggestions, _ = self._get_dataforseo_suggestions(
                        seed_keyword, location_code, language_code
                    )

            # Validate suggestions are relevant to seed keyword
            if suggestions:
                # Filter out suggestions that are completely unrelated
                seed_words = set(seed_keyword.lower().split())
                relevant_suggestions = []
                for sug in suggestions:
                    sug_lower = sug.lower()
                    sug_words = set(sug_lower.split())
                    # Check if suggestion shares at least one word with seed keyword
                    # or if seed keyword appears in suggestion
                    if (seed_words & sug_words) or any(word in sug_lower for word in seed_words if len(word) > 3):
                        relevant_suggestions.append(sug)
                    else:
                        logger.warning(f"Filtered out irrelevant suggestion: '{sug}' (not related to '{seed_keyword}')")
                
                if len(relevant_suggestions) < max_keywords * 0.3:  # If less than 30% are relevant, likely bad data
                    logger.warning(f"Only {len(relevant_suggestions)}/{len(suggestions)} suggestions are relevant to '{seed_keyword}'")
                    logger.warning(f"DataForSEO may be returning irrelevant data. Falling back to Gemini...")
                    suggestions = []  # Force fallback to Gemini
                else:
                    suggestions = relevant_suggestions[:max_keywords * 2]  # Keep more for metrics filtering
                    logger.info(f"Filtered to {len(suggestions)} relevant suggestions")
            
            # If still no suggestions, try Gemini
            if not suggestions or len(suggestions) == 0:
                logger.warning(f"No relevant suggestions from DataForSEO. Falling back to Gemini...")
                return self._fallback_to_gemini(seed_keyword, max_keywords)

            # Step 2: Get keyword metrics (volume, CPC, competition)
            metrics_data, metrics_error = self._get_keyword_metrics_batch(
                suggestions, location_code, language_code
            )
            
            # Check if metrics call failed and we should switch to sandbox
            if (not metrics_data or len(metrics_data) == 0) and metrics_error and not self.using_sandbox:
                status_code, response_data = metrics_error
                if self._should_use_sandbox(status_code, response_data):
                    self._switch_to_sandbox()
                    # Retry metrics with sandbox
                    metrics_data, _ = self._get_keyword_metrics_batch(
                        suggestions, location_code, language_code
                    )

            # If no metrics but we have suggestions, use suggestions with unavailable metrics
            if not metrics_data or len(metrics_data) == 0:
                logger.warning(f"No metrics from DataForSEO, but we have {len(suggestions)} suggestions. Setting unavailable metrics...")
                metrics_data = []
                for kw in suggestions:
                    metrics_data.append({
                        "keyword": kw,
                        "search_volume": 0,
                        "competition": None,
                        "cpc": None,
                        "data_source": DataSource.UNAVAILABLE.value
                    })

            # Step 3: Sort by opportunity score
            sorted_keywords = self._sort_keywords_by_opportunity(metrics_data, max_keywords)
            
            # Ensure we have at least the requested number of keywords
            # If we have fewer, try to pad with Gemini-generated keywords
            if len(sorted_keywords) < max_keywords:
                logger.warning(f"DataForSEO returned {len(sorted_keywords)} keywords, but {max_keywords} requested.")
                logger.info(f"💡 Generating additional keywords with Gemini...")
                
                # Try to get more from Gemini for the missing ones
                existing_keywords = {item.get("keyword", "").lower() for item in sorted_keywords}
                additional_needed = max_keywords - len(sorted_keywords)
                additional_keywords = self._fallback_to_gemini(seed_keyword, additional_needed)
                
                # Filter out duplicates and add to sorted_keywords
                for item in additional_keywords:
                    kw = item.get("keyword", "")
                    if kw and kw.lower() not in existing_keywords:
                        # Convert Gemini format to DataForSEO format
                        sorted_keywords.append({
                            "keyword": kw,
                            "search_volume": item.get("volume", 0),
                            "competition": item.get("competition"),
                            "cpc": item.get("cpc"),
                            "opportunity_score": item.get("opportunity_score", 0.0),
                            "data_source": item.get("data_source", DataSource.UNAVAILABLE.value)
                        })
                        existing_keywords.add(kw.lower())
                        if len(sorted_keywords) >= max_keywords:
                            break
                
                # Re-sort after adding new keywords
                sorted_keywords = self._sort_keywords_by_opportunity(sorted_keywords, max_keywords)
            
            # Format response to match expected structure
            formatted_keywords = []
            for i, item in enumerate(sorted_keywords[:max_keywords], 1):
                formatted_keywords.append({
                    "rank": i,
                    "keyword": item.get("keyword", ""),
                    "volume": item.get("search_volume", 0),
                    "competition": item.get("competition"),
                    "cpc": item.get("cpc"),
                    "opportunity_score": item.get("opportunity_score", 0.0),
                    "data_source": item.get("data_source", DataSource.LIVE.value)
                })
            
            logger.info(f"Successfully retrieved {len(formatted_keywords)} keywords (requested {max_keywords})")
            return formatted_keywords

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error connecting to DataForSEO: {e}")
            logger.info(f"⚙️ Falling back to Gemini...")
            return self._fallback_to_gemini(seed_keyword, max_keywords)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.info(f"⚙️ Falling back to Gemini...")
            return self._fallback_to_gemini(seed_keyword, max_keywords)

    # ------------------------------------------------------------
    # INTERNAL FUNCTIONS
    # ------------------------------------------------------------
    def _get_dataforseo_suggestions(self, seed_keyword, location_code, language_code):
        """
        Fetch keyword suggestions from DataForSEO.
        Returns: (suggestions_list, error_info_tuple)
        """
        endpoints = [
            "dataforseo_labs/google/keywords_for_keywords/live",
            "dataforseo_labs/google/keyword_ideas/live"
        ]

        for endpoint in endpoints:
            url = f"{self.base_url}/{endpoint}"
            logger.info(f"🔎 Trying endpoint: {endpoint}")
            
            payload = [{
                "keywords": [seed_keyword],
                "location_code": location_code,
                "language_code": language_code,
                "limit": 100
            }]

            try:
                response = self.session.post(url, json=payload, timeout=30)
                status_code = response.status_code
                logger.info(f"📡 Response status: {status_code}")

                # Handle different status codes
                if status_code == 404:
                    logger.warning(f"Endpoint not found: {endpoint}")
                    continue  # Try next endpoint

                # Parse response
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response: {response.text[:200]}")
                    return [], (status_code, {"error": "invalid_json"})

                # Check for account/balance errors
                error_info = (status_code, data)
                is_limited, error_type = self._is_account_limited_error(status_code, data)
                
                if is_limited and error_type in ["balance_zero", "rate_limited"]:
                    logger.warning(f"Account issue detected: {error_type}")
                    return [], error_info

                # Check for successful response
                if status_code == 200 and data.get("status_code") == 20000:
                    if data.get("tasks") and len(data["tasks"]) > 0:
                        task = data["tasks"][0]
                        if task.get("result") and len(task["result"]) > 0:
                            items = task["result"][0].get("items", [])
                            suggestions = [
                                item["keyword"] 
                                for item in items 
                                if "keyword" in item and item.get("keyword")
                            ]
                            if suggestions:
                                logger.info(f"Found {len(suggestions)} suggestions")
                                return suggestions[:100], None
                
                # If we get here, there was an error but not account-limited
                if status_code != 200:
                    logger.warning(f"API error (status {status_code}): {response.text[:200]}")
                    continue

            except requests.exceptions.Timeout:
                logger.info(f"⏱️ Timeout connecting to {endpoint}")
                continue
            except requests.exceptions.ConnectionError:
                logger.info(f"🔌 Connection error to {endpoint}")
                return [], (0, {"error": "connection_error"})
            except Exception as e:
                logger.warning(f"Error with {endpoint}: {e}")
                continue

        return [], None

    def _get_keyword_metrics_batch(self, keywords, location_code, language_code):
        """
        Get search volume, CPC, and competition metrics.
        Returns: (metrics_list, error_info_tuple)
        """
        url = f"{self.base_url}/keywords_data/google_ads/search_volume/live"
        payload = [{
            "keywords": keywords[:100],  # Limit to 100 keywords per request
            "location_code": location_code,
            "language_code": language_code
        }]

        try:
            response = self.session.post(url, json=payload, timeout=30)
            status_code = response.status_code
            logger.info(f"📊 Metrics API status: {status_code}")

            # Parse response
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in metrics response: {response.text[:200]}")
                return [], (status_code, {"error": "invalid_json"})
            
            # Debug: Save raw response if in debug mode (optional)
            if os.getenv("DATAFORSEO_DEBUG") == "true":
                with open("dataforseo_metrics_response.json", "w") as f:
                    json.dump(data, f, indent=2)
                logger.info(f"🔍 Debug: Saved raw response to dataforseo_metrics_response.json")

            # Check for account/balance errors
            error_info = (status_code, data)
            is_limited, error_type = self._is_account_limited_error(status_code, data)
            
            if is_limited and error_type in ["balance_zero", "rate_limited"]:
                logger.warning(f"Account issue in metrics API: {error_type}")
                return [], error_info

            # Debug: Log response structure for troubleshooting
            if status_code == 200:
                df_status = data.get("status_code")
                logger.info(f"🔍 DataForSEO status_code: {df_status}")
                
                # Process successful response
                if df_status == 20000:
                    tasks = data.get("tasks", [])
                    if tasks and len(tasks) > 0:
                        task = tasks[0]
                        task_status = task.get("status_code")
                        task_message = task.get("status_message", "")
                        logger.info(f"🔍 Task status_code: {task_status}, message: {task_message}")
                        
                        # Check if task has results - try multiple structures
                        result = task.get("result", [])
                        
                        # Also check if result is None (task might not be complete)
                        if result is None:
                            logger.warning(f"Task result is None. Task might still be processing.")
                            logger.info(f"🔍 Task status: {task_status}, message: {task_message}")
                            # Check if we need to wait and retry (for async APIs)
                            if task_status and task_status != 20000:
                                logger.warning(f"Task not completed. Status: {task_status}")
                            return [], None
                        
                        if result and len(result) > 0:
                            metrics = []
                            
                            # Method 1: Try standard structure (result is list of dicts with items)
                            for result_item in result:
                                items_to_process = []
                                
                                # Check if result_item is a list
                                if isinstance(result_item, list):
                                    items_to_process = result_item
                                # Check if result_item is a dict with items
                                elif isinstance(result_item, dict):
                                    # Try getting items from various possible keys
                                    items_to_process = (
                                        result_item.get("items", []) or
                                        result_item.get("data", []) or
                                        result_item.get("results", [])
                                    )
                                    # If no items key, check if the dict itself is an item
                                    if not items_to_process and "keyword" in result_item:
                                        items_to_process = [result_item]
                                else:
                                    continue
                                
                                # Process items
                                for item in items_to_process:
                                    if isinstance(item, dict):
                                        # Try to extract keyword - check multiple possible keys
                                        keyword = (
                                            item.get("keyword") or
                                            item.get("key") or
                                            item.get("search_term") or
                                            item.get("query")
                                        )
                                        
                                        if keyword:
                                            # Try multiple field names for metrics
                                            search_volume = (
                                                item.get("search_volume") or
                                                item.get("volume") or
                                                item.get("search_volume_monthly") or
                                                item.get("monthly_searches") or
                                                0
                                            )
                                            
                                            competition = (
                                                item.get("competition") or
                                                item.get("competition_index") or
                                                item.get("competition_level") or
                                                item.get("competition_value") or
                                                0.5
                                            )
                                            
                                            cpc = (
                                                item.get("cpc") or
                                                item.get("bid") or
                                                item.get("cost_per_click") or
                                                item.get("cpc_value") or
                                                0.0
                                            )
                                            
                                            # Normalize competition (might be 0-1, 0-100, or 0-1.0)
                                            if isinstance(competition, (int, float)):
                                                if competition > 1 and competition <= 100:
                                                    competition = competition / 100.0
                                                elif competition > 100:
                                                    competition = min(competition / 1000.0, 1.0)
                                            else:
                                                competition = 0.5
                                            
                                            metrics.append({
                                                "keyword": str(keyword),
                                                "search_volume": int(search_volume) if search_volume else 0,
                                                "competition": float(competition) if competition is not None else None,
                                                "cpc": float(cpc) if cpc is not None else None,
                                                "data_source": DataSource.LIVE.value
                                            })
                            
                            if metrics:
                                logger.info(f"Retrieved metrics for {len(metrics)} keywords")
                                return metrics, None
                            else:
                                # Log the actual structure for debugging
                                logger.warning(f"No metrics parsed. Trying to understand response structure...")
                                logger.info(f"🔍 Result type: {type(result)}, length: {len(result) if result else 0}")
                                if result and len(result) > 0:
                                    logger.info(f"🔍 First result_item type: {type(result[0])}")
                                    if isinstance(result[0], dict):
                                        logger.info(f"🔍 First result_item keys: {list(result[0].keys())[:10]}")
                                        # Try to print a sample
                                        logger.info(f"🔍 Sample result_item: {str(result[0])[:300]}")
                        else:
                            logger.warning(f"Task result is empty or invalid.")
                            logger.info(f"🔍 Task keys: {list(task.keys())}")
                            logger.info(f"🔍 Task status_code: {task.get('status_code')}")
                            logger.info(f"🔍 Task status_message: {task.get('status_message', 'N/A')}")
                            # Check if there's error info
                            if task.get("status_code") != 20000:
                                logger.warning(f"Task failed with status: {task.get('status_code')}")
                    else:
                        logger.warning(f"No tasks in response. Data keys: {list(data.keys())}")
                else:
                    # Log the error status
                    status_message = data.get("status_message", "Unknown error")
                    logger.warning(f"DataForSEO API returned status_code {df_status}: {status_message}")
                    # Check if it's a balance/limit error
                    if self._should_use_sandbox(status_code, data):
                        return [], (status_code, data)
                    # Log response for debugging
                    logger.info(f"🔍 Response preview: {str(data)[:500]}")

            # Error but not account-limited
            if status_code != 200:
                logger.warning(f"Metrics API HTTP error {status_code}: {response.text[:500]}")
                return [], error_info

        except requests.exceptions.Timeout:
            logger.info(f"⏱️ Metrics API timeout")
            return [], (0, {"error": "timeout"})
        except requests.exceptions.ConnectionError:
            logger.info(f"🔌 Metrics API connection error")
            return [], (0, {"error": "connection_error"})
        except Exception as e:
            logger.warning(f"Metrics fetch error: {e}")
            import traceback
            logger.info(f"🔍 Traceback: {traceback.format_exc()}")
            return [], (0, {"error": str(e)})

        # If we get here, response was 200 but we didn't parse metrics
        logger.warning(f"Could not parse metrics from response. Status: {status_code}")
        return [], None

    def _sort_keywords_by_opportunity(self, metrics_data, max_keywords):
        """Rank keywords by opportunity score (volume high, competition low)."""
        for item in metrics_data:
            vol = max(item.get("search_volume", 0) or 0, 0)
            comp = item.get("competition")
            if comp is None:
                comp = 0.5  # neutral assumption
            comp = min(max(comp, 0.0), 1.0)
            
            # Normalize volume (assume max 100k for scoring)
            normalized_volume = min(vol / 100000, 1.0)
            
            # Opportunity score: higher volume + lower competition = better
            item["opportunity_score"] = round(
                (0.7 * normalized_volume) + (0.3 * (1 - comp)), 
                3
            )
        
        # Sort by opportunity score (descending)
        sorted_data = sorted(
            metrics_data, 
            key=lambda x: x.get("opportunity_score", 0), 
            reverse=True
        )
        
        return sorted_data[:max_keywords]

    def _fallback_to_gemini(self, seed_keyword, max_keywords):
        """Use Gemini for backup keyword generation when DataForSEO fails."""
        logger.info(f"💡 Using Gemini AI fallback for: '{seed_keyword}'")
        logger.info(f"📝 Generating {max_keywords} relevant keywords related to '{seed_keyword}' with AI...")
        
        try:
            # Pass max_keywords to ensure we get enough keywords
            # Make sure Gemini understands we need keywords RELATED to the seed keyword
            keywords = generate_keywords(seed_keyword, max_keywords)
            
            # Validate keywords are actually related to seed keyword
            if keywords:
                seed_words = set(seed_keyword.lower().split())
                validated_keywords = []
                for kw in keywords:
                    kw_lower = kw.lower()
                    kw_words = set(kw_lower.split())
                    # Check relevance - must share at least one significant word or contain seed keyword
                    if (seed_words & kw_words) or any(word in kw_lower for word in seed_words if len(word) > 2):
                        validated_keywords.append(kw)
                    else:
                        logger.warning(f"Filtered out irrelevant Gemini keyword: '{kw}'")
                
                if len(validated_keywords) < max_keywords * 0.5:  # If less than 50% are relevant, regenerate
                    logger.warning(f"Only {len(validated_keywords)}/{len(keywords)} Gemini keywords are relevant. Regenerating...")
                    keywords = generate_keywords(seed_keyword, max_keywords * 2)  # Generate more to filter
                    # Re-validate
                    validated_keywords = []
                    for kw in keywords:
                        kw_lower = kw.lower()
                        kw_words = set(kw_lower.split())
                        if (seed_words & kw_words) or any(word in kw_lower for word in seed_words if len(word) > 2):
                            validated_keywords.append(kw)
                
                keywords = validated_keywords[:max_keywords]
            
            if not keywords or len(keywords) < max_keywords:
                logger.warning(f"Gemini returned {len(keywords) if keywords else 0} keywords, expected {max_keywords}. Generating variations...")
                # Generate more variations to reach max_keywords
                base_variations = [
                    f"{seed_keyword} guide", f"{seed_keyword} tips", f"best {seed_keyword}",
                    f"{seed_keyword} tutorial", f"how to {seed_keyword}", f"{seed_keyword} review",
                    f"{seed_keyword} comparison", f"{seed_keyword} tools", f"{seed_keyword} software",
                    f"{seed_keyword} services", f"buy {seed_keyword}", f"{seed_keyword} price",
                    f"{seed_keyword} examples", f"{seed_keyword} benefits", f"{seed_keyword} features",
                    f"{seed_keyword} alternatives", f"{seed_keyword} vs", f"free {seed_keyword}",
                    f"{seed_keyword} online", f"{seed_keyword} course", f"{seed_keyword} training",
                    f"{seed_keyword} strategy", f"{seed_keyword} ideas", f"{seed_keyword} solutions",
                    f"top {seed_keyword}", f"{seed_keyword} list", f"{seed_keyword} checklist",
                    f"{seed_keyword} template", f"{seed_keyword} framework", f"{seed_keyword} methodology"
                ]
                
                if not keywords:
                    keywords = []
                
                # Add variations that aren't already in the list
                existing_lower = {kw.lower() for kw in keywords}
                for var in base_variations:
                    if var.lower() not in existing_lower and len(keywords) < max_keywords:
                        keywords.append(var)
                        existing_lower.add(var.lower())
            
            # Ensure we have at least max_keywords (or as many as possible)
            keywords = keywords[:max_keywords] if len(keywords) > max_keywords else keywords
            
            formatted = []
            for i, kw in enumerate(keywords, 1):
                formatted.append({
                    "rank": i,
                    "keyword": kw,
                    "volume": 0,
                    "competition": None,
                    "cpc": None,
                    "opportunity_score": 0.0,
                    "data_source": DataSource.UNAVAILABLE.value
                })
            
            logger.info(f"Gemini generated {len(formatted)} keywords (requested {max_keywords})")
            return formatted
            
        except Exception as e:
            logger.error(f"Gemini fallback error: {e}")
            # Emergency fallback
            return [{
                "rank": 1,
                "keyword": seed_keyword,
                "volume": 0,
                "competition": None,
                "cpc": None,
                "opportunity_score": 0.0,
                "data_source": DataSource.UNAVAILABLE.value
            }]

    def get_keyword_metrics(self, keyword, location_code=2840, language_code="en"):
        """
        Get metrics for a single keyword.
        Used by agent.py for individual keyword processing.
        """
        metrics_data, error_info = self._get_keyword_metrics_batch(
            [keyword], location_code, language_code
        )
        
        if metrics_data and len(metrics_data) > 0:
            metric = metrics_data[0]
            return {
                "volume": metric.get("search_volume", 0),
                "competition": metric.get("competition"),
                "cpc": metric.get("cpc"),
                "data_source": DataSource.LIVE.value
            }
        
        # Fallback: return default metrics
        return {
            "volume": 0,
            "competition": None,
            "cpc": None,
            "data_source": DataSource.UNAVAILABLE.value
        }


# ------------------------------------------------------------
# PUBLIC FUNCTIONS
# ------------------------------------------------------------
keyword_api_client = KeywordAPIClient()

def get_enhanced_keywords(seed_keyword, max_keywords=50):
    """
    Get enhanced keywords with DataForSEO integration and fallback.
    """
    return keyword_api_client.get_keyword_suggestions(seed_keyword, max_keywords)

def get_keyword_metrics_enhanced(keyword):
    """
    Get metrics for a single keyword.
    Used by agent.py for processing individual keywords.
    """
    return keyword_api_client.get_keyword_metrics(keyword)
