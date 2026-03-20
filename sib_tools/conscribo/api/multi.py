from typing import Any

from sib_tools.conscribo.auth import conscribo_post
from sib_tools.conscribo.types import ConscriboMultiRequestRequest, ConscriboMultiRequestResponse


def execute_multi_request(
    payload: ConscriboMultiRequestRequest | dict[str, Any],
) -> ConscriboMultiRequestResponse:
    """POST /multirequest/"""
    return conscribo_post("/multirequest/", json=payload, return_type=ConscriboMultiRequestResponse)
