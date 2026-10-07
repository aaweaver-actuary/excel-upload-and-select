"""Recreation of a current process to submit company name and address to Neural Metrics API to retrieve NAICS code.
This script is intended for use in a Python environment with access to the necessary libraries and credentials.

Neural Metrics API requires an API key and a PEM file for secure communication.
The API key should be stored in an environment variable named `NEURALMETRICS_API_KEY`,
and the PEM file path should be specified in the `PEM_PATH` variable.
"""

from hashlib import sha256
import json
import pandas as pd
import httpx
from datetime import datetime, date
from pathlib import Path
from dataclasses import dataclass, field
import os
from dotenv import load_dotenv

load_dotenv()


def get_neural_metrics_naics_code(name: str, address: str) -> int:
    """Returns the NAICS code for the company based on its name and address."""
    # Placeholder implementation; replace with actual logic to retrieve NAICS code
    return 123456


def ts() -> str:
    """Returns a string representing the current date in the format MMDDYYYY."""
    now = datetime.now()
    return f"{now.month}{now.day}{now.year}"


def get_book(name: str) -> pd.DataFrame:
    INPUT_FOLDER = Path(
        r"O:\\PARM\\Small Business\\Causey\\Third party data\\Refresh\\relativity6\\one_off\\input"
    )
    input_filename = name + "_In.xlsx"
    return pd.read_excel(INPUT_FOLDER / input_filename, dtype=str).fillna("")


@dataclass(slots=True)
class NmApiDetails:
    """Represents the details required to connect to the Neural Metrics API. This class holds the API key and the path to the PEM file for secure communication."""

    key: str = os.getenv("NEURALMETRICS_API_KEY", "")
    pem_path: Path = Path(os.getenv("PEM_PATH", ""))


@dataclass(slots=True)
class NmSession:
    """Represents a session with the Neural Metrics API. This class handles the connection to the API and manages the session token."""

    is_async: bool = False

    _api_detail: NmApiDetails = field(default_factory=NmApiDetails)

    _endpoint: str = "https://api.smartratio.neuralmetrics.ai/smb/api/v1/getSession"

    _session: httpx.Client | httpx.AsyncClient | None = None
    _session_token: str | None = None

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Key {self._api_detail.key}",
            "Content-Type": "application/json",
        }

    @property
    def is_connected(self) -> bool:
        return self._session_token is not None

    @property
    def session(self) -> httpx.Client | httpx.AsyncClient:
        if self._session is None:
            self.connect()
        return self._session

    def connect(self) -> None:
        """Establishes a connection to the Neural Metrics API and retrieves a session token."""
        if self.is_async:
            self._session = httpx.AsyncClient()
        else:
            self._session = httpx.Client()

        response = self._session.post(
            url=self._endpoint, headers=self.headers, verify=self._api_detail.pem_path
        )
        response.raise_for_status()
        self._session_token = response.json().get("sessionToken")


@dataclass
class Submission:
    """Represents a submission to the Neural Metrics API. This class holds the details of the company being submitted, including its name, address, and other relevant information."""

    _name: str | None = None
    _address: str | None = None

    _country: str = "US"
    _lean_crawling: bool = False
    _force_recrawl: bool = False
    _force_content_cache_refresh: bool = False
    _lro_submission: bool = False
    _property_details: bool = False

    @property
    def name(self) -> str:
        return self._name if self._name is not None else ""

    @property
    def address(self) -> str:
        return self._address if self._address is not None else ""

    @property
    def key(self) -> str:
        return sha256(f"{self.name}{self.address}".encode("utf-8")).hexdigest()

    @property
    def payload(self) -> dict:
        return {
            "companyData": [
                {
                    "companyName": self.name,
                    "companyAddress": self.address,
                    "country": self._country,
                    "id": self.key,
                    "leanCrawling": self._lean_crawling,
                    "forceRecrawl": self._force_recrawl,
                    "forceContentCacheRefresh": self._force_content_cache_refresh,
                    "lroSubmission": self._lro_submission,
                    "propertyDetails": self._property_details,
                }
            ]
        }


@dataclass
class NmBatchSubmission:
    """Represents the details required for a batch submission to the Neural Metrics API. This class manages the session and API details."""

    _session: NmSession = field(default_factory=NmSession)
    _api_detail: NmApiDetails = field(default_factory=NmApiDetails)

    _endpoint: str = (
        "https://api.smartratio.neuralmetrics.ai/smb/api/v2/company/submit/batch"
    )

    @property
    def session_token(self) -> str:
        if not self._session.is_connected:
            self._session.connect()
        if self._session._session_token is None:
            token = "ERR"
        else:
            token = self._session._session_token
        return token

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Session {self.session_token}",
            "Content-Type": "application/json",
            "RequestSource": "API",
        }

    def _build_submission(self, name: str | None, address: str | None) -> Submission:
        return Submission(_name=name, _address=address)

    def _submission_payload(self, name: str | None, address: str | None) -> dict:
        submission = self._build_submission(name, address)
        return submission.payload


s = NmSession()
# s.connect()
# sessionToken = s._session_token
# submission_head = {
#     "Content-Type": "application/json",
#     "Authorization": "Session " + sessionToken,
#     "RequestSource": "API",
# }
details_head = {
    "Content-Type": "application/json",
    "Authorization": "Session " + sessionToken,
    "RequestSource": "API",
    "enableViolation": "true",
}

counter = 0


# date_part = '1292026'

rownum = pd.Series(range(1, len(Book) + 1), index=Book.index)

# Book['Lookup'] = date_part + rownum.astype(str) + '-1'


# Book["Address"] = (
#     Book["Address"].fillna("")
#     + " "
#     + Book["City"].fillna("")
#     + ", "
#     + Book["State"].fillna("")
#     + " "
#     + Book["Zip"].fillna("")
# ).str.strip()

for index, row in Book.iterrows():
    counter += 1
    print(counter)

    rsub = httpx.post(
        url=NmBatchSubmission._endpoint,
        headers=submission_head,
        data=payload,
        verify=s._api_detail.pem_path,
    )

    try:
        json.dump(
            rsub.json(),
            open(
                f"O:\\PARM\\Small Business\\Causey\\Third party data\\Refresh\\neuralmetrics\\one_off\\submission_json_out\\{row['Lookup']}_submission_{date.today()}.json",
                "w",
            ),
            indent=2,
        )
    except Exception:
        json.dump(
            {},
            open(
                f"O:\\PARM\\Small Business\\Causey\\Third party data\\Refresh\\neuralmetrics\\one_off\\submission_json_out\\{row['Lookup']}_submission_{date.today()}.json",
                "w",
            ),
            indent=2,
        )
print("Done")
