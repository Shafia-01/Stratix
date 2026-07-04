"""
Thread-safe in-memory Prometheus-compatible metrics collector for Keylytics.

Metrics are stored in-process and exposed via GET /metrics in Prometheus text format.
Designed to be imported as a singleton via get_metrics().

Metric types:
  - Counter  (increment)    — monotonically increasing counts
  - Histogram (observe)     — distribution of observed values
  - Gauge     (gauge)       — current point-in-time value

Usage:
    from src.metrics import get_metrics
    m = get_metrics()
    m.increment("keylytics_tool_calls_total", {"tool_name": "keyword_research", "status": "success"})
    m.observe("keylytics_plan_eval_score", 0.85)
    m.gauge("keylytics_monitoring_jobs_active", 3.0)
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict, List, Optional

from src.logger_config import get_logger

logger = get_logger(__name__)

# Global singleton
_metrics_instance: Optional["KeylyticsMetrics"] = None
_metrics_lock = threading.Lock()


def get_metrics() -> "KeylyticsMetrics":
    """Return the process-wide KeylyticsMetrics singleton."""
    global _metrics_instance
    if _metrics_instance is None:
        with _metrics_lock:
            if _metrics_instance is None:
                _metrics_instance = KeylyticsMetrics()
    return _metrics_instance


def _label_key(labels: Optional[Dict[str, str]]) -> str:
    """Serialise a label dict into a sorted string key."""
    if not labels:
        return ""
    return ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))


def _format_labels(labels: Optional[Dict[str, str]]) -> str:
    """Format labels for Prometheus text output."""
    if not labels:
        return ""
    parts = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    return f"{{{parts}}}"


class KeylyticsMetrics:
    """
    Thread-safe in-memory metrics store.

    Stores:
      _counters:    {metric_name: {label_key: float}}
      _histograms:  {metric_name: {label_key: List[float]}}
      _gauges:      {metric_name: {label_key: float}}
    """

    # Canonical histogram bucket boundaries
    _EVAL_BUCKETS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    _COUNT_BUCKETS = [1, 5, 10, 20, 50, 100, 200, 500]

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._histograms: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._gauges: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        # Label map for reconstruction
        self._label_map: Dict[str, Dict[str, Dict[str, str]]] = defaultdict(lambda: defaultdict(dict))

    def increment(self, name: str, labels: Optional[Dict[str, str]] = None, amount: float = 1.0) -> None:
        """Increment a counter metric."""
        names = [name]
        if name.startswith("keylytics_"):
            names.append(name.replace("keylytics_", "stratix_", 1))
        elif name.startswith("stratix_"):
            names.append(name.replace("stratix_", "keylytics_", 1))
        for n in names:
            key = _label_key(labels)
            with self._lock:
                self._counters[n][key] += amount
                if labels:
                    self._label_map["counter"][n + key] = labels

    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram observation."""
        names = [name]
        if name.startswith("keylytics_"):
            names.append(name.replace("keylytics_", "stratix_", 1))
        elif name.startswith("stratix_"):
            names.append(name.replace("stratix_", "keylytics_", 1))
        for n in names:
            key = _label_key(labels)
            with self._lock:
                self._histograms[n][key].append(value)
                if labels:
                    self._label_map["histogram"][n + key] = labels

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric to an absolute value."""
        names = [name]
        if name.startswith("keylytics_"):
            names.append(name.replace("keylytics_", "stratix_", 1))
        elif name.startswith("stratix_"):
            names.append(name.replace("stratix_", "keylytics_", 1))
        for n in names:
            key = _label_key(labels)
            with self._lock:
                self._gauges[n][key] = value
                if labels:
                    self._label_map["gauge"][n + key] = labels

    # ── Prometheus text format ─────────────────────────────────────────────

    def to_prometheus_text(self) -> str:
        """Serialise all metrics to Prometheus exposition format."""
        lines: List[str] = []

        with self._lock:
            counters = {k: dict(v) for k, v in self._counters.items()}
            histograms = {k: {lk: list(lv) for lk, lv in v.items()} for k, v in self._histograms.items()}
            gauges = {k: dict(v) for k, v in self._gauges.items()}
            label_map = {
                scope: {mk: dict(mv) for mk, mv in m.items()}
                for scope, m in self._label_map.items()
            }

        # Counters
        for name, series in sorted(counters.items()):
            lines.append(f"# HELP {name} Keylytics counter metric")
            lines.append(f"# TYPE {name} counter")
            for lkey, value in series.items():
                stored_labels = label_map.get("counter", {}).get(name + lkey)
                lstr = _format_labels(stored_labels)
                lines.append(f"{name}{lstr} {value}")

        # Histograms
        for name, series in sorted(histograms.items()):
            lines.append(f"# HELP {name} Keylytics histogram metric")
            lines.append(f"# TYPE {name} histogram")
            buckets = (
                self._EVAL_BUCKETS
                if "eval" in name or "score" in name
                else self._COUNT_BUCKETS
            )
            for lkey, values in series.items():
                stored_labels = label_map.get("histogram", {}).get(name + lkey)

                # Build base label string without closing brace
                if stored_labels:
                    base_label_parts = ",".join(f'{k}="{v}"' for k, v in sorted(stored_labels.items()))
                else:
                    base_label_parts = ""

                for bucket in buckets:
                    count = sum(1 for v in values if v <= bucket)
                    if base_label_parts:
                        bucket_labels = f'{{{base_label_parts},le="{bucket}"}}'
                    else:
                        bucket_labels = f'{{le="{bucket}"}}'
                    lines.append(f"{name}_bucket{bucket_labels} {count}")

                # +Inf bucket
                inf_labels = f'{{{base_label_parts},le="+Inf"}}' if base_label_parts else '{le="+Inf"}'
                lines.append(f"{name}_bucket{inf_labels} {len(values)}")

                # Count and sum with full label set
                full_labels = f'{{{base_label_parts}}}' if base_label_parts else ""
                lines.append(f"{name}_count{full_labels} {len(values)}")
                lines.append(f"{name}_sum{full_labels} {sum(values):.4f}")

        # Gauges
        for name, series in sorted(gauges.items()):
            lines.append(f"# HELP {name} Keylytics gauge metric")
            lines.append(f"# TYPE {name} gauge")
            for lkey, value in series.items():
                stored_labels = label_map.get("gauge", {}).get(name + lkey)
                lstr = _format_labels(stored_labels)
                lines.append(f"{name}{lstr} {value}")

        return "\n".join(lines) + "\n"

    def get_summary(self) -> dict:
        """Return a Python dict summary for the /health/detailed endpoint."""
        with self._lock:
            return {
                "counters": {
                    name: {lk: v for lk, v in series.items()}
                    for name, series in self._counters.items()
                },
                "histograms": {
                    name: {
                        lk: {
                            "count": len(vals),
                            "sum": sum(vals),
                            "mean": sum(vals) / len(vals) if vals else 0.0,
                        }
                        for lk, vals in series.items()
                    }
                    for name, series in self._histograms.items()
                },
                "gauges": {
                    name: {lk: v for lk, v in series.items()}
                    for name, series in self._gauges.items()
                },
            }
