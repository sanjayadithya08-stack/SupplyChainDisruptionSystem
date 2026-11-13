from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class PredictionResponse(BaseModel):
    label: str
    confidence: float
    disruption_type: str
    affected_regions: List[str]
    estimated_duration_days: int
    error: Optional[str] = None

class PreventionPlan(BaseModel):
    immediate_actions: List[str]
    short_term_actions: List[str]
    long_term_actions: List[str]
    rerouting_options: List[Dict[str, Any]] = Field(default_factory=list)
    supplier_alternatives: List[Dict[str, Any]] = Field(default_factory=list)
    inventory_recommendations: List[str] = Field(default_factory=list)
    estimated_cost_impact: str
    priority: str

class FullAnalysisResponse(BaseModel):
    prediction: PredictionResponse
    plan: PreventionPlan
    context: Optional[str] = None

class CombinedInput(BaseModel):
    news: str
    weather: str
    geo: str

class BatchInput(BaseModel):
    texts: List[str]

class AlertRequest(BaseModel):
    level: str
    message: str

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    uptime_seconds: float
    artefacts: Dict[str, bool]
    system_metrics: Dict[str, Any] = Field(default_factory=dict)
    channels: Dict[str, bool] = Field(default_factory=dict)
    version: str = "2.1.0"
