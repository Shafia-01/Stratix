<div align="center">
  <img src="assets/keylytics_icon.png" width="100" style="margin-bottom: -35px;">
  <h1><strong>KeyLytics: AI-Powered SEO Keyword Intelligence System</strong></h1>
  <p>
    <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
    <img src="https://img.shields.io/badge/Streamlit-UI-red?logo=streamlit" alt="Streamlit">
    <img src="https://img.shields.io/badge/FastAPI-API-green?logo=fastapi" alt="FastAPI">
    <img src="https://img.shields.io/badge/LangGraph-Agentic-purple" alt="LangGraph">
    <img src="https://img.shields.io/badge/Gemini-2.5_Flash-orange?logo=google" alt="Gemini">
  </p>
</div>

KeyLytics is a production-grade SEO keyword intelligence platform that combines real-time data APIs, AI-powered analysis, and an autonomous multi-agent research pipeline to deliver comprehensive keyword strategy at scale.

---

## 🆕 Phase 3 — Autonomous Agent Mode (LangGraph)

The latest release adds a **fully autonomous, human-in-the-loop research pipeline** powered by LangGraph:

- 🧠 **AI Research Planner** — Gemini 2.5 Flash generates a structured research plan from any seed keyword
- 🔬 **ReAct Research Agent** — Executes all 6 SEO tools autonomously in the correct order
- ✅ **Human-in-the-Loop Checkpoints** — You review & approve the plan before research runs, and the report before saving
- 📊 **Strategy Synthesis** — LLM synthesises all findings into an executive summary + 5 actionable recommendations
- 🔍 **LangSmith Tracing** — Every run is traced end-to-end for observability
- 🌐 **FastAPI Routes** — `POST /agent/run`, `POST /agent/resume`, `GET /agent/status/{run_id}`

Access via **🤖 Agent Mode** in the sidebar.

---

## ✨ Features

### 1. 🤖 Agent Mode *(Phase 3 — New)*
**Autonomous Multi-Agent SEO Research Pipeline**

Run a complete end-to-end SEO intelligence workflow with just a seed keyword:
- **Research Planning**: AI generates a structured plan with objectives, modules, and keyword targets
- **Plan Approval**: Human-in-the-loop checkpoint — approve, edit, or cancel the plan
- **Autonomous Research**: ReAct agent calls all 6 tools in the optimal order
- **Aggregation**: Deterministic aggregator builds `IntelligenceFindings` + per-tool confidence scores
- **Strategy Synthesis**: LLM synthesises findings into a full `StrategyReport`
- **Report Approval**: Second HITL checkpoint — approve, request regeneration with notes, or reject
- **Database Persistence**: Approved keywords automatically saved to the database

**Use Cases**: Comprehensive keyword strategy, autonomous research at scale, auditable AI-powered SEO analysis

---

### 2. 🔍 Keyword Discovery
**AI-Powered Keyword Research with Real-Time Metrics**

- **Multi-Source Intelligence**: Combines DataForSEO API (real-time) with Gemini AI fallback
- **Intelligent Metrics**: Search volume, competition, CPC, and trend scores
- **Scalable Analysis**: Quick (5 keywords) or Comprehensive (50+ keywords)
- **Smart Scoring**: AI-powered opportunity scoring
- **Database Integration**: Automatically saves discovered keywords

**Use Cases**: Initial research, long-tail opportunities, trending keyword discovery

---

### 3. 📊 SERP Analysis
**Deep Dive into Search Engine Results Pages**

- **Snippet Analysis**: Title tags, meta descriptions, featured snippets
- **People Also Ask**: Extracts PAA questions to identify content gaps
- **Top Ranking Analysis**: Patterns, content structure, ranking factors
- **Optimization Suggestions**: AI-generated recommendations

**Use Cases**: Content optimization, featured snippet opportunities, competitor strategies

---

### 4. 🧩 Competitor Gap Analysis
**Find Keywords Your Competitors Rank For (But You Don't)**

- **Competitor Identification**: Automatically identifies top competitors
- **Keyword Gap Detection**: Finds keywords where competitors rank top 20 but you don't
- **Gap Scoring**: Opportunity scores based on rankings and traffic potential
- **Strategic Recommendations**: Prioritized opportunities by feasibility

**Use Cases**: Competitive intelligence, easy wins, outranking competitors

---

### 5. 📝 Content Optimization
**AI-Powered Content Analysis and Optimization**

- **Meta Title & Description Suggestions**: 3 SEO-optimized options
- **Missing Topics Identification**: Comprehensive content gap analysis
- **Content Structure Improvements**: Headings, readability, keyword placement

**Use Cases**: Improving existing content, optimizing before publishing

---

### 6. 🎯 Search Intent Classification
**Understand What Users Really Want**

- **Intent Types**: Informational, Commercial, Transactional, Navigational
- **Hybrid Classification**: Rule-based + Gemini AI for accuracy
- **Intent Caching**: Avoids redundant analysis

**Use Cases**: Content strategy, aligning content with funnel stages

---

### 7. 💰 Conversion Mapping
**Rank Keywords by ROI Potential**

- **ROI Calculation**: `Score / (CPC + 0.01)`
- **Buyer Intent Ranking**: Conversion potential and commercial value
- **Visual ROI Charts**: Interactive Plotly charts

**Use Cases**: PPC campaign planning, budget allocation

---

### 8. 🧠 Topic Clustering
**Group Keywords into Semantic Topic Clusters**

- **Semantic Clustering**: AI groups keywords by semantic similarity
- **Cluster Scoring**: Opportunity potential ranking
- **Content Strategy Mapping**: Maps clusters to pillar pages

**Use Cases**: Content pillar planning, semantic SEO, content calendar creation

---

### 9. 🌐 Industry Focus
**Industry-Specific Keyword Intelligence**

- **Industry Selection**: 15+ industries (Technology, Healthcare, Finance, E-commerce, etc.)
- **Industry-Specific Keywords**: 20+ tailored high-value keywords
- **Trend Awareness**: Current industry-specific opportunities

**Use Cases**: Niche keyword discovery, industry trend analysis

---

### 10. 📈 Trend Forecasting
**Predict Keyword Trends with Seasonal Analysis**

- **6-Month Forecasts**: Confidence-scored predictions
- **Seasonal Pattern Analysis**: Optimal content timing
- **Market Opportunity Identification**: Trending keywords before they peak

**Use Cases**: Content calendar planning, seasonal content strategy

---

### 11. 🧩 Full Strategy
**Comprehensive SEO Strategy in One Analysis**

- **Unified Analysis**: Keyword Discovery + Competitor Gap + Topic Clustering + Trend Forecasting + SERP
- **Executive Summary**: High-level overview of all analyses
- **Strategic Recommendations**: Based on all combined analyses

**Use Cases**: Comprehensive SEO audits, new market entry, client reporting

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd keylytics

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Start Streamlit UI  (http://localhost:8501)
streamlit run app.py

# Start FastAPI server  (http://localhost:8000)
uvicorn api.main:app --reload --port 8000
```

Both services run simultaneously and share the same SQLite database (`keylytics.db`).

---

## 📋 Prerequisites

- **Python 3.10+**
- **SQLite** (standard Python library — auto-configured)
- **API Keys**:
  - **Required**: Google Gemini API key (`GEMINI_API_KEY`)
  - **Required**: SerpAPI key (`SERPAPI_KEY`)
  - **Optional**: DataForSEO credentials (enhanced keyword research)
  - **Optional**: LangSmith API key (`LANGCHAIN_API_KEY`) — for Phase 3 tracing

---

## 🔧 Configuration

### Environment Variables
Create a `.env` file from the example:

```bash
cp .env.example .env
```

Key variables:

```bash
# ── Core APIs (required) ──────────────────────────────────────────────────
GEMINI_API_KEY=your_gemini_api_key
SERPAPI_KEY=your_serpapi_key

# ── DataForSEO (optional — enhanced keyword data) ─────────────────────────
DATAFORSEO_USERNAME=your_dataforseo_username
DATAFORSEO_PASSWORD=your_dataforseo_password
DATAFORSEO_DEMO_MODE=true          # true = sandbox (saves credits), false = live
DATAFORSEO_PRESERVE_CREDITS=true   # auto-switch to sandbox on low balance

# ── LangSmith (optional — Phase 3 observability) ──────────────────────────
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=keylytics-phase3
KEYLYTICS_ENV=development
```

### Credit Preservation (DataForSEO)

| Mode | Setting | Use When |
|---|---|---|
| Demo/Sandbox | `DATAFORSEO_DEMO_MODE=true` | Testing / development |
| Force Sandbox | `DATAFORSEO_FORCE_SANDBOX=true` | Presentations |
| Auto-Preserve | `DATAFORSEO_PRESERVE_CREDITS=true` + `DATAFORSEO_LOW_BALANCE_THRESHOLD=0.50` | Production |
| Live | both flags `false` | Actual usage |

---

## 🌐 FastAPI Endpoints

The FastAPI server runs at `http://localhost:8000`. Interactive docs at `/docs`.

### Core Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check + API status |
| POST | `/keywords/research` | Keyword research |
| POST | `/intelligence/run` | Full intelligence run |

### Phase 3 — Agent Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/agent/run` | Start a new autonomous research run |
| POST | `/agent/resume` | Resume a paused run with human feedback |
| GET | `/agent/status/{run_id}` | Poll current run state |

#### Agent Run Flow

```bash
# 1. Start a run — graph pauses at plan_approval checkpoint
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{"seed_keyword": "AI SEO tools"}'
# Returns: {run_id, status: "awaiting_approval", checkpoint_data.research_plan}

# 2. Approve the plan — research runs, pauses at report_approval
curl -X POST http://localhost:8000/agent/resume \
  -H "Content-Type: application/json" \
  -d '{"run_id": "<run_id>", "human_feedback": {"approved": true}}'
# Returns: {status: "awaiting_approval", checkpoint_data.strategy_report}

# 3. Approve the report — saves to DB, run completes
curl -X POST http://localhost:8000/agent/resume \
  -H "Content-Type: application/json" \
  -d '{"run_id": "<run_id>", "human_feedback": {"approved": true}}'
# Returns: {status: "completed"}
```

---

## 📁 Project Structure

```
keylytics/
├── app.py                          # Streamlit application entry point
├── api/                            # FastAPI application
│   ├── main.py                     # App factory, middleware, global error handlers
│   └── routes/
│       ├── health.py               # GET /health
│       ├── keywords.py             # POST /keywords/research
│       ├── intelligence.py         # POST /intelligence/run
│       └── agent.py                # POST /agent/run, /agent/resume, GET /agent/status
├── src/                            # Shared source modules
│   ├── graph/                      # ── Phase 3: LangGraph pipeline ──
│   │   ├── __init__.py             # Package: exports build_graph, get_compiled_graph
│   │   ├── state.py                # AgentState TypedDict (LangGraph-checkpointable)
│   │   ├── tracing.py              # LangSmith run configs + metadata helpers
│   │   ├── nodes.py                # 5 node functions + 3 routing helpers
│   │   └── graph.py                # StateGraph builder + MemorySaver checkpointer
│   ├── tools/                      # ── Phase 2C: LangChain tool adapters ──
│   │   ├── registry.py             # Tool registry: all 6 tools registered
│   │   └── langchain_adapters.py   # StructuredTool wrappers for LangGraph
│   ├── schemas.py                  # Pydantic models (ResearchPlan, StrategyReport, etc.)
│   ├── agent.py                    # Keyword discovery agent
│   ├── lightweight_agent.py        # Quick analysis agent
│   ├── competitor_gap_analyzer.py  # Competitor keyword gap analysis
│   ├── serp_analyzer.py            # SERP analysis
│   ├── topic_clusterer.py          # Semantic topic clustering
│   ├── trend_forecaster.py         # 6-month trend forecasting
│   ├── intent_classifier.py        # Search intent classification
│   ├── keyword_api_client.py       # DataForSEO API client
│   ├── gemini_client.py            # Gemini AI client wrapper
│   ├── db_client.py                # Database operations (SQLite/SQLAlchemy)
│   ├── scoring.py                  # Keyword scoring algorithms
│   ├── logger_config.py            # Structured logging
│   └── ui/                         # Streamlit page components
│       ├── agent_mode.py           # 🤖 Agent Mode HITL interface (Phase 3)
│       ├── keyword_discovery.py
│       ├── serp_analysis.py
│       ├── competitor_gap.py
│       ├── topic_clustering.py
│       ├── trend_forecasting.py
│       ├── full_strategy.py
│       ├── sidebar.py
│       └── theme.py
├── tests/                          # Test suite (132 tests)
│   ├── api_routes/                 # FastAPI route tests (incl. agent endpoints)
│   ├── unit/                       # Unit tests (graph nodes, schemas, tools)
│   ├── integration/                # Integration tests (pipeline, DB)
│   └── conftest.py
├── requirements.txt                # Python dependencies
├── pytest.ini                      # Test configuration
└── .env.example                    # Environment variable template
```

---

## 📦 Dependencies

Key packages — see [`requirements.txt`](requirements.txt) for full list:

| Package | Purpose |
|---|---|
| `streamlit` | Web UI framework |
| `fastapi>=0.137.1` | REST API server |
| `langgraph>=0.2.0` | Agentic pipeline (Phase 3) |
| `langchain-core>=0.2.0` | LangChain StructuredTool adapters |
| `langchain-google-genai>=1.0.0` | Gemini LLM for LangGraph nodes |
| `langsmith>=0.1.0` | Run tracing + observability |
| `google-generativeai` | Direct Gemini API access |
| `pydantic>=2.0.0` | Schema validation |
| `SQLAlchemy` | Database ORM |
| `pytrends` | Google Trends data |
| `plotly` | Interactive visualizations |
| `tenacity` | Retry logic |

---

## 🧪 Testing

```bash
# Run the full test suite
python -m pytest tests/ -q

# Run only unit tests
python -m pytest tests/unit/ -q

# Run Phase 3 graph tests
python -m pytest tests/unit/test_graph.py -v

# Run agent API route tests
python -m pytest tests/api_routes/test_agent.py -v

# With coverage
python -m pytest tests/ --cov=src --cov=api --cov-report=term-missing
```

Current status: **132 passed** ✅

---

## 🔁 LangGraph Pipeline Architecture

```
START
  └─► planner_node           (Gemini LLM → ResearchPlan)
        └─► [INTERRUPT: plan_approval]  ◄── Human reviews plan
              ├─► research_agent_node   (ReAct agent → 6 tools)
              │     └─► aggregator_node (Deterministic → IntelligenceFindings + confidence scores)
              │             └─► strategy_agent_node (Gemini LLM → StrategyReport)
              │                   └─► [INTERRUPT: report_approval]  ◄── Human reviews report
              │                         ├─► persist_node (→ DB save) → END
              │                         └─► strategy_agent_node (regenerate, max 1 retry)
              ├─► planner_node (edited plan, max 2 retries)
              └─► END (rejected)
```

**State checkpointing**: `MemorySaver` stores state after every node — runs survive restarts.

**LangSmith tracing**: Every `graph.invoke()` call is tagged with `seed_keyword`, `run_id`, `version: phase3`.

---

## 🚨 Troubleshooting

### Common Issues

| Issue | Fix |
|---|---|
| `GEMINI_API_KEY not found` | Add key to `.env` and restart |
| FastAPI won't start | Ensure `fastapi>=0.137.1` is installed (`pip install -r requirements.txt`) |
| Agent Mode returns connection error | Start the FastAPI server first: `uvicorn api.main:app --reload --port 8000` |
| DataForSEO errors | Set `DATAFORSEO_DEMO_MODE=true` in `.env` to use sandbox |
| Database errors | Delete `keylytics.db` and restart — it will be recreated |
| `Module import errors` | Run `pip install -r requirements.txt` |
| Test collection errors | Ensure `tests/unit/__init__.py` exists (included in repo) |

### Logs

```bash
# Streamlit debug logs
streamlit run app.py --logger.level debug

# FastAPI with verbose logging
uvicorn api.main:app --reload --log-level debug
```

---

## 📈 Performance Optimization

- **Streamlit caching**: `@st.cache_data` on expensive API calls
- **API response caching**: SQLite-backed cache for keyword data
- **Batch processing**: Parallel processing for large keyword sets
- **LangGraph checkpointing**: Runs resume from last checkpoint on failure

---

## 🔐 Security

- API keys stored in `.env` (never committed)
- `src/security_utils.py` redacts keys from error messages and logs
- CORS configured for localhost dev origins only
- Input validation via Pydantic schemas on all API endpoints

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for new functionality
4. Ensure all tests pass (`python -m pytest tests/ -q`)
5. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License — see the LICENSE file for details.
