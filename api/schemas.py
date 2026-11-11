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

class OrderRequest(BaseModel):
    supplier_id: str = Field(min_length=1, max_length=64)
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(gt=0, le=1_000_000)
    unit_price: float = Field(gt=0)
    reason: str = Field(default="Manual replenishment", max_length=250)
    shipment_id: Optional[str] = Field(default=None, max_length=64)

class AutomationRequest(BaseModel):
    shipment_id: str = Field(min_length=1, max_length=64)
    disruption_type: str = Field(min_length=1, max_length=64)
    risk_level: str = Field(min_length=1, max_length=16)

class ShipmentImportRequest(BaseModel):
    shipments: List[Dict[str, Any]] = Field(min_length=1, max_length=10000)
    replace_existing: bool = True

class DisruptionResolutionRequest(BaseModel):
    action_taken: str = Field(min_length=3, max_length=500)

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    uptime_seconds: float
    artefacts: Dict[str, bool]
    system_metrics: Dict[str, Any] = Field(default_factory=dict)
    version: str = "2.0.0"
