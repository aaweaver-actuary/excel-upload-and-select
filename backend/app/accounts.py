"""Authoritative schema for batch accounts; source values live in the workbook."""
from pydantic import Field as PydanticField
from pydantic.dataclasses import dataclass

from .columns import Field
from .models import Model

@dataclass(slots=True)
class Address:
    

class CanonicalAccount(Model):
    source_row_number: int = PydanticField(ge=2)
    account_id: str | None = None
    business_name: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    naics: str | None = None


ALIASES = {
    "account_id": ("account number", "account id", "insured id"),
    "business_name": ("Insured Name", "Account", "Business Name", "Applicant", "company"),
    "address_line_1": ("street address", "address", "street"),
    "address_line_2": ("suite", "address 2"),
    "postal_code": ("zip", "zip code", "postal"),
    "naics": ("Industry Code", "NAICS Code"),
}
ACCOUNT_FIELDS = tuple(
    Field(key, key.replace("_", " ").title(), ALIASES.get(key, ()), key == "business_name")
    for key in CanonicalAccount.model_fields if key != "source_row_number"
)


def normalize(value, field: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip() or None
    if text is None:
        return None
    if field == "state":
        return text.upper()
    if field == "naics" and text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    if field == "postal_code" and text.isdigit() and len(text) < 5:
        return text.zfill(5)
    return text


def validate_account(account: CanonicalAccount) -> list[str]:
    issues = []
    if not account.business_name:
        issues.append("MISSING_BUSINESS_NAME")
    if account.postal_code and not (
        len(account.postal_code) == 5 and account.postal_code.isdigit()
        or len(account.postal_code) == 10 and account.postal_code[5] == "-"
        and account.postal_code[:5].isdigit() and account.postal_code[6:].isdigit()
    ):
        issues.append("INVALID_POSTAL_CODE")
    return issues
