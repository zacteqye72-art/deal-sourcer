from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Listing:
    source: str
    source_id: str
    title: str
    url: str
    asking_price: Optional[float] = None
    mrr: Optional[float] = None
    annual_profit: Optional[float] = None
    multiple: Optional[float] = None
    monetization_type: Optional[str] = None
    platform: Optional[str] = None
    business_age_months: Optional[int] = None
    description: Optional[str] = None
    raw_data: Optional[str] = None  # JSON string
    is_pet_related: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
