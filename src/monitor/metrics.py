"""System-wide latency and health monitoring."""

import time
from dataclasses import dataclass, field
from collections import deque


@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: float
    labels: dict = field(default_factory=dict)


@dataclass
class SystemMonitor:
    """Collects and reports on system-wide metrics."""

    _metrics: dict[str, deque] = field(default_factory=dict, repr=False)
    _start_time: float = field(default_factory=time.time)

    def record(self, name: str, value: float, labels: dict | None = None):
        if name not in self._metrics:
            self._metrics[name] = deque(maxlen=1000)
        self._metrics[name].append(
            MetricPoint(name=name, value=value, timestamp=time.time(), labels=labels or {})
        )

    def get_series(self, name: str, last_n: int = 100) -> list[dict]:
        points = self._metrics.get(name, [])
        return [
            {"value": p.value, "timestamp": p.timestamp, "labels": p.labels}
            for p in list(points)[-last_n:]
        ]

    def get_percentiles(self, name: str) -> dict:
        points = self._metrics.get(name, [])
        if not points:
            return {"p50": 0, "p95": 0, "p99": 0, "min": 0, "max": 0, "count": 0}
        values = sorted(p.value for p in points)
        n = len(values)
        return {
            "p50": values[int(n * 0.50)],
            "p95": values[min(int(n * 0.95), n - 1)],
            "p99": values[min(int(n * 0.99), n - 1)],
            "min": values[0],
            "max": values[-1],
            "count": n,
        }

    def get_dashboard_snapshot(self) -> dict:
        uptime = time.time() - self._start_time
        return {
            "uptime_seconds": round(uptime, 1),
            "metrics": {
                name: {
                    "latest": list(points)[-1].value if points else 0,
                    "count": len(points),
                    **self.get_percentiles(name),
                }
                for name, points in self._metrics.items()
            },
        }
