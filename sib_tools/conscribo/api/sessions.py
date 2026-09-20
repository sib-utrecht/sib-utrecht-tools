from typing import Any

from sib_tools.conscribo.auth import conscribo_get, conscribo_post
from sib_tools.conscribo.types import (
    ConscriboSessionResponse,
    ConscriboSessionStatusResponse,
    ConscriboStartSessionRequest,
)


def start_session(payload: ConscriboStartSessionRequest) -> ConscriboSessionResponse:
    """POST /sessions/"""
    return conscribo_post("/sessions/", json=payload, return_type=ConscriboSessionResponse)


def get_session_information() -> ConscriboSessionStatusResponse:
    """GET /sessions/"""
    return conscribo_get("/sessions/", return_type=ConscriboSessionStatusResponse)
