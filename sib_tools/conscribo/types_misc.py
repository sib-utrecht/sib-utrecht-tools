from typing import Any, NotRequired, TypedDict

from .types_common import ConscriboResponseMessages


class ConscriboMultiRequestItem(TypedDict, total=False):
    method: str
    endpoint: str
    params: dict[str, Any]
    body: dict[str, Any]


class ConscriboMultiRequestRequest(TypedDict):
    requests: list[ConscriboMultiRequestItem]


class ConscriboMultiRequestItemResponse(TypedDict, total=False):
    status: int
    responseMessages: ConscriboResponseMessages
    body: dict[str, Any]


class ConscriboMultiRequestResponse(TypedDict):
    responses: list[ConscriboMultiRequestItemResponse]
    status: NotRequired[int]
    responseMessages: NotRequired[ConscriboResponseMessages]


class ConscriboFileErrorResponse(TypedDict, total=False):
    status: int
    responseMessages: ConscriboResponseMessages
    body: str
