from typing import NotRequired, TypedDict

from .types_common import ConscriboResponseMessages


class ConscriboStartSessionRequest(TypedDict):
    userName: str
    passPhrase: str
    twoFaCode: NotRequired[int]


class ConscriboSessionResponse(TypedDict):
    sessionId: str
    userDisplayName: str
    status: int
    responseMessages: NotRequired[ConscriboResponseMessages]


class ConscriboSessionStatusResponse(TypedDict):
    secsToLogout: int
    status: int
    responseMessages: NotRequired[ConscriboResponseMessages]
