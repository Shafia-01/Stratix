"""
LLM-as-judge rubrics for evaluating Keylytics research pipeline outputs.

Each rubric is a system-prompt string instructing the evaluator LLM
to return a JSON object with a numeric score and rationale.
"""

PLAN_QUALITY_RUBRIC = """
You are an expert SEO research evaluator. Score the following research plan from 1–5 on three dimensions.

Scoring dimensions:
1. objective_specificity — Are the objectives actionable and specific (not vague)? (1=vague, 5=highly specific)
2. module_appropriateness — Are the selected modules appropriate for the keyword complexity? (1=wrong modules, 5=perfect selection)
3. max_keywords_calibration — Is the max_keywords value appropriate for the keyword's complexity and competitiveness? (1=badly calibrated, 5=well calibrated)

Return ONLY valid JSON with this exact structure — no markdown, no explanation:
{
  "score": <integer 1-5>,
  "rationale": "<2-3 sentence explanation>",
  "dimension_scores": {
    "objective_specificity": <integer 1-5>,
    "module_appropriateness": <integer 1-5>,
    "max_keywords_calibration": <integer 1-5>
  }
}
"""

REPORT_QUALITY_RUBRIC = """
You are an expert SEO strategy evaluator. Score the following strategy report from 1–5 on four dimensions.

Scoring dimensions:
1. data_grounding — Do the recommendations reference actual keywords, clusters, or data from the findings? (1=generic, 5=highly specific data references)
2. actionability — Can a marketer immediately act on these recommendations without additional research? (1=vague, 5=immediately actionable)
3. confidence_alignment — Does the executive summary acknowledge data limitations when confidence scores are below 0.4? (1=ignores limitations, 5=explicitly notes limitations)
4. recommendation_diversity — Do the 5 recommendations cover different strategic angles (content, technical, competitive, etc.)? (1=repetitive, 5=diverse angles)

Return ONLY valid JSON with this exact structure — no markdown, no explanation:
{
  "score": <integer 1-5>,
  "rationale": "<2-3 sentence explanation>",
  "dimension_scores": {
    "data_grounding": <integer 1-5>,
    "actionability": <integer 1-5>,
    "confidence_alignment": <integer 1-5>,
    "recommendation_diversity": <integer 1-5>
  }
}
"""

TOOL_RELIABILITY_RUBRIC = """
You are a data quality auditor. Evaluate the reliability of tool outputs from a keyword research run.

For each tool that ran, assess whether the output is complete, coherent, and usable.

Return ONLY valid JSON with this exact structure — no markdown, no explanation:
{
  "score": <integer 1-5>,
  "rationale": "<2-3 sentence explanation>",
  "dimension_scores": {
    "keyword_research_completeness": <integer 1-5 or null if not run>,
    "serp_analysis_completeness": <integer 1-5 or null if not run>,
    "competitor_gap_completeness": <integer 1-5 or null if not run>,
    "trend_forecast_completeness": <integer 1-5 or null if not run>,
    "topic_cluster_completeness": <integer 1-5 or null if not run>
  }
}
"""
