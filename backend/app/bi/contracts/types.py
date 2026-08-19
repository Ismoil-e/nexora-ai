from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class KPICategory(str, Enum):
    FINANCE = "finance"
    OPERATIONS = "operations"
    HR = "hr"
    DOCUMENTS = "documents"
    AI = "ai"
    CUSTOM = "custom"


class KPIStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class SeverityLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class TrendDirection(str, Enum):
    GROWING = "growing"
    DECLINING = "declining"
    STABLE = "stable"
    VOLATILE = "volatile"


class TargetRole(str, Enum):
    CEO = "CEO"
    CFO = "CFO"
    COO = "COO"
    HR_DIRECTOR = "HR_Director"
    PROJECT_MANAGER = "Project_Manager"


@dataclass
class KPICalculationResult:
    code: str
    name: str
    category: str
    current_value: float
    previous_value: Optional[float]
    change_pct: Optional[float]
    status: str
    unit: str
    target_value: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    meta_data: Optional[Dict[str, Any]] = None


@dataclass
class InsightData:
    title: str
    category: str
    severity: str
    summary: str
    explanation: str
    recommended_actions: List[str] = field(default_factory=list)
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None


@dataclass
class ForecastData:
    metric_name: str
    target_period: str
    predicted_value: float
    confidence_score: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    methodology: str = "linear_trend"
    historical_points_count: int = 0
    meta_data: Optional[Dict[str, Any]] = None


@dataclass
class RiskAlertData:
    category: str
    risk_level: str
    title: str
    description: str
    impact: str
    mitigation_step: str
    source_entity: Optional[str] = None
