from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal

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

class ThreatResponseRequest(BaseModel):
    mode: Optional[Literal["immediate", "short_term", "long_term", "ai"]] = None
    responses: Dict[str, Literal["immediate", "short_term", "long_term", "ai"]] = Field(default_factory=dict)

class ActionOutcomeRequest(BaseModel):
    outcome: Literal["in_progress", "completed", "rejected"]
    note: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    uptime_seconds: float
    artefacts: Dict[str, bool]
    system_metrics: Dict[str, Any] = Field(default_factory=dict)
    channels: Dict[str, Any] = Field(default_factory=dict)
    version: str = "2.1.0"
