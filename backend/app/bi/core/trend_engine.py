import math
from typing import Dict, List, Optional, Tuple

from app.bi.contracts.types import TrendDirection


class TrendEngine:
    """Detects trends, growth/decline patterns, seasonality, and anomalies in time-series data."""

    def analyze_series(
        self,
        values: List[float],
        labels: List[str],
        granularity: str = "daily",
        anomaly_threshold_std: float = 2.0,
    ) -> Dict:
        """Analyzes numeric time series data and computes trend velocity, growth rate, and anomalies."""
        if not values or len(values) == 0:
            return {
                "trend_direction": TrendDirection.STABLE.value,
                "average_value": 0.0,
                "growth_rate_pct": 0.0,
                "anomalies_detected": 0,
                "series": [],
            }

        n = len(values)
        avg = sum(values) / n

        # Standard deviation for anomaly detection
        variance = sum((x - avg) ** 2 for x in values) / (n if n == 1 else (n - 1))
        std_dev = math.sqrt(variance)

        # Calculate period-over-period changes and flag anomalies
        series_points = []
        anomalies_count = 0

        for i, val in enumerate(values):
            prev_val = values[i - 1] if i > 0 else None
            change_pct = None
            if prev_val is not None and prev_val != 0:
                change_pct = round(((val - prev_val) / abs(prev_val)) * 100.0, 2)

            is_anomaly = False
            if std_dev > 0 and abs(val - avg) > (anomaly_threshold_std * std_dev):
                is_anomaly = True
                anomalies_count += 1

            label = labels[i] if i < len(labels) else f"P{i+1}"
            series_points.append({
                "period": label,
                "value": round(val, 2),
                "change_pct": change_pct,
                "is_anomaly": is_anomaly,
            })

        # Calculate overall growth rate
        growth_rate_pct = 0.0
        first_val = values[0]
        last_val = values[-1]
        if first_val != 0:
            growth_rate_pct = round(((last_val - first_val) / abs(first_val)) * 100.0, 2)

        # Determine trend direction
        if n >= 2:
            # Simple slope via least-squares
            x_mean = (n - 1) / 2.0
            numerator = sum((i - x_mean) * (values[i] - avg) for i in range(n))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            slope = (numerator / denominator) if denominator != 0 else 0.0

            if abs(slope) < 0.05 * (avg if avg != 0 else 1.0):
                direction = TrendDirection.STABLE.value
            elif slope > 0:
                direction = TrendDirection.GROWING.value
            else:
                direction = TrendDirection.DECLINING.value
        else:
            direction = TrendDirection.STABLE.value

        return {
            "trend_direction": direction,
            "average_value": round(avg, 2),
            "growth_rate_pct": growth_rate_pct,
            "anomalies_detected": anomalies_count,
            "series": series_points,
        }


trend_engine = TrendEngine()
