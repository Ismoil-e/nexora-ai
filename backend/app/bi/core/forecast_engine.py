import math
from typing import Dict, List, Optional

from app.bi.contracts.types import ForecastData


class ForecastEngine:
    """Statistical and predictive forecasting engine for business metrics."""

    def forecast_metric(
        self,
        metric_name: str,
        historical_values: List[float],
        periods_ahead: int = 3,
        methodology: str = "linear_trend",
        period_prefix: str = "P+",
    ) -> List[ForecastData]:
        """Generates future forecast points with lower/upper confidence bounds."""
        if not historical_values or len(historical_values) == 0:
            # Default fallback when no historical data is provided
            return [
                ForecastData(
                    metric_name=metric_name,
                    target_period=f"{period_prefix}{i+1}",
                    predicted_value=10.0,
                    confidence_score=0.5,
                    lower_bound=5.0,
                    upper_bound=15.0,
                    methodology=methodology,
                    historical_points_count=0,
                )
                for i in range(periods_ahead)
            ]

        n = len(historical_values)
        avg = sum(historical_values) / n

        # Estimate variance and confidence
        if n > 1:
            variance = sum((x - avg) ** 2 for x in historical_values) / (n - 1)
            std_err = math.sqrt(variance / n)
            confidence_score = min(0.95, max(0.60, 0.5 + (0.05 * min(n, 8))))
        else:
            variance = 0.0
            std_err = avg * 0.1
            confidence_score = 0.55

        results: List[ForecastData] = []

        if methodology == "moving_avg" or n < 3:
            # Weighted Moving Average
            weights = [i + 1 for i in range(n)]
            weight_sum = sum(weights)
            wma = sum(w * val for w, val in zip(weights, historical_values)) / weight_sum

            for step in range(1, periods_ahead + 1):
                margin = (std_err if std_err > 0 else (wma * 0.15)) * (1.0 + 0.1 * step)
                pred = max(0.0, round(wma, 2))
                results.append(
                    ForecastData(
                        metric_name=metric_name,
                        target_period=f"{period_prefix}{step}",
                        predicted_value=pred,
                        confidence_score=round(confidence_score * (1.0 - 0.05 * step), 2),
                        lower_bound=max(0.0, round(pred - margin, 2)),
                        upper_bound=round(pred + margin, 2),
                        methodology="moving_avg",
                        historical_points_count=n,
                    )
                )
        else:
            # Linear Regression projection: y = a + b*x
            x_vals = list(range(n))
            x_mean = sum(x_vals) / n
            y_mean = avg

            num = sum((x_vals[i] - x_mean) * (historical_values[i] - y_mean) for i in range(n))
            denom = sum((x_vals[i] - x_mean) ** 2 for i in range(n))

            slope = (num / denom) if denom != 0 else 0.0
            intercept = y_mean - slope * x_mean

            for step in range(1, periods_ahead + 1):
                target_x = (n - 1) + step
                raw_pred = intercept + slope * target_x
                pred = max(0.0, round(raw_pred, 2))
                margin = (std_err if std_err > 0 else (pred * 0.12)) * (1.0 + 0.15 * step)

                results.append(
                    ForecastData(
                        metric_name=metric_name,
                        target_period=f"{period_prefix}{step}",
                        predicted_value=pred,
                        confidence_score=round(confidence_score * (1.0 - 0.04 * step), 2),
                        lower_bound=max(0.0, round(pred - margin, 2)),
                        upper_bound=round(pred + margin, 2),
                        methodology="linear_trend",
                        historical_points_count=n,
                    )
                )

        return results


forecast_engine = ForecastEngine()
