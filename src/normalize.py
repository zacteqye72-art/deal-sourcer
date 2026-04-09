import re
from typing import Optional


def parse_price(price_str: Optional[str]) -> Optional[float]:
    """Parse a price string like '$45,000' or '45000' into a float."""
    if not price_str:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(price_str))
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def calc_multiple(asking_price: Optional[float], annual_profit: Optional[float]) -> Optional[float]:
    """Calculate price multiple = asking_price / annual_profit."""
    if not asking_price or not annual_profit or annual_profit <= 0:
        return None
    return round(asking_price / annual_profit, 2)
