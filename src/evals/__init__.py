"""
Keylytics LLM-as-judge evaluation framework.

Exports:
  KeylyticsEvaluator — evaluates plan quality, report quality, tool reliability.
  EvalResult         — Pydantic model for evaluation output (re-exported from schemas).
"""
from src.evals.evaluator import KeylyticsEvaluator  # noqa: F401
