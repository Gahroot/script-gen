from enum import Enum

from pydantic import BaseModel, EmailStr


class PainPointSolution(BaseModel):
    pain_point: str
    solution: str


class IntakeData(BaseModel):
    business_name: str
    target_audience: str
    pain_points_solutions: list[PainPointSolution]
    offer: str
    risk_reversal: str = ""
    guarantees: str = ""
    limited_availability: str = ""
    discounts: str = ""
    lead_magnet: str = ""
    top_stats: list[str]
    website_url: str = ""
    landing_page_url: str = ""
    city: str = ""
    service_area: str = ""

    # Contact info for delivery
    contact_name: str
    contact_email: EmailStr
    contact_phone: str = ""


class VerificationResult(BaseModel):
    passed: bool
    failed_hooks: list[int] = []
    failed_meats: list[int] = []
    failed_ctas: list[int] = []
    reasons: list[str] = []


class GeneratedScripts(BaseModel):
    hooks: list[str]
    meats: list[str]
    ctas: list[str]


class PipelineResponse(BaseModel):
    success: bool
    markdown: str
    contact_name: str
    contact_email: str
    contact_phone: str
    business_name: str


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus
    status_url: str
    business_name: str
    email_delivery: bool


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    business_name: str
    contact_email: str
    created_at: float
    completed_at: float | None = None
    duration_seconds: float | None = None
    email_sent: bool = False
    markdown: str | None = None
    error: str | None = None
