"""Edit this file to change the import schema and matching/import defaults."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    aliases: tuple[str, ...] = ()
    required: bool = False


FIELDS = (
    Field("firstName", "First Name", ("firstname", "given name", "fname", "first")),
    Field("lastName", "Last Name", ("lastname", "surname", "lname", "family name", "familyname")),
    Field("email", "Email", ("e-mail", "email address", "e-mail address")),
    Field("phone", "Phone", ("telephone", "mobile", "cell", "phone number", "cell phone")),
    Field("company", "Company", ("organization", "org", "employer", "business")),
    Field("state", "State", ("province", "region", "location state", "state/province")),
)


@dataclass(frozen=True)
class Settings:
    suggestion_threshold: float = 80
    candidate_limit: int = 3
    max_rows: int = 50_000
    max_file_bytes: int = 20 * 1024 * 1024
    max_request_bytes: int = 64 * 1024 * 1024
    preview_rows: int = 10


SETTINGS = Settings()
