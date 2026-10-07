from app.src.get_naics_description import get_naics_description
from app.src.get_naics_subdescription import get_naics_subdescription
from app.src.naics_code.src.neural_metrics_naics_code import (
    get_neural_metrics_naics_code,
)
from app.src.naics_code.src.relativity6_naics_code import (
    get_relativity6_naics_code,
)
from dataclasses import dataclass

# Will look for NAICS codes in this order, returning the first one found, or missing code if none are found
NAICS_CODE_HIERARCHY = [
    "agent_entered_code",
    "nm_naics_code",
    "r6_naics_code",
]


@dataclass
class NaicsCodeContext:
    """Dataclass holding all relevant information for determining the NAICS code for a company, including
    the company name, address, and any NAICS codes that have been found from various sources.
    """

    name: str
    address: str

    _missing_code: int = 999999

    _naics_code: int = -1

    _agent_entered_code: int = -1
    _nm_naics_code: int = -1
    _rel6_naics_code: int = -1

    def get_naics_code(self) -> int:
        """Returns the NAICS code for the company, or the missing code if not found.

        Uses the hierarchy of NAICS code sources to determine the most reliable code to return. The order of preference is:
        1. Agent-entered code
        2. Neural Metrics code
        3. Relativity6 code
        """

        for code_type in NAICS_CODE_HIERARCHY:
            code = getattr(self, code_type)
            if code != -1:
                return code

        return self._missing_code

    def is_missing(self) -> bool:
        """Returns True if the NAICS code is missing, False otherwise."""
        return self._naics_code == -1

    @property
    def agent_entered_code(self) -> int:
        """Returns the agent-entered NAICS code for the company, or -1 if not found."""
        return self._agent_entered_code

    @agent_entered_code.setter
    def agent_entered_code(self, value: int):
        """Sets the agent-entered NAICS code for the company."""
        self._agent_entered_code = value

    @property
    def nm_naics_code(self) -> int:
        """Returns the Neural Metrics NAICS code for the company, or -1 if not found."""
        if self._nm_naics_code == -1:
            self._nm_naics_code = get_neural_metrics_naics_code(self.name, self.address)
        return self._nm_naics_code

    @property
    def r6_naics_code(self) -> int:
        """Returns the Relativity6 NAICS code for the company, or -1 if not found."""
        if self._rel6_naics_code == -1:
            self._rel6_naics_code = get_relativity6_naics_code(self.name, self.address)
        return self._rel6_naics_code

    @property
    def naics_code(self) -> int:
        """Returns the NAICS code for the company, or -1 if not found."""
        if self.is_missing():
            return 999_999
        return self._naics_code

    @property
    def naics2_code(self) -> int:
        """Returns the 2-digit NAICS code for the company, or -1 if not found."""
        return int(str(self.naics_code)[:2])

    @property
    def naics4_code(self) -> int:
        """Returns the 4-digit NAICS code for the company, or -1 if not found."""
        if self.is_missing():
            return 9999
        return int(str(self.naics_code)[:4])

    @property
    def naics_desc(self) -> str:
        """Returns the description of the NAICS code for the company, or 'Unknown' if not found."""
        if self.is_missing():
            return "Unknown"
        return get_naics_description(self.naics_code)

    @property
    def naics_subdesc(self) -> str:
        """Returns the sub-description of the NAICS code for the company, or 'Unknown' if not found."""
        if self.is_missing():
            return "Unknown"
        return get_naics_subdescription(self.naics_code)
