from backend.app.src.get_decline_rate import get_decline_rate
from backend.app.src.get_hit_rate import get_hit_rate
from backend.app.src.get_quote_rate import get_quote_rate


from typing import Literal


def get_yield_rate(naics_code: int, unit: Literal["cld", "ml"]) -> float:
    """Returns the yield rate based on the NAICS code and unit."""
    decline_rate = get_decline_rate(naics_code, unit)
    quote_rate = get_quote_rate(naics_code, unit)
    hit_rate = get_hit_rate(naics_code, unit)

    return (1 - decline_rate) * quote_rate * hit_rate