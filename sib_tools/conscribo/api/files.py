from pathlib import Path

import requests

from sib_tools.conscribo.auth import get_conscribo_session_id
from sib_tools.conscribo.constants import api_url


def _fpcdn_base_url() -> str:
    return api_url.replace("https://api.secure.conscribo.nl/", "https://fpcdn.secure.conscribo.nl/")


def download_file(file_id: int | str, save_to: str | None = None) -> bytes:
    """GET /download/{fileId}/ against the FPCDN endpoint.

    Returns file bytes and optionally writes them to ``save_to``.
    """
    response = requests.get(
        f"{_fpcdn_base_url()}/download/{file_id}/",
        headers={
            "X-Conscribo-SessionId": get_conscribo_session_id(),
            "X-Conscribo-API-Version": "1.20240610",
        },
        allow_redirects=True,
    )
    response.raise_for_status()
    payload = response.content

    if save_to:
        output_path = Path(save_to)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)

    return payload
