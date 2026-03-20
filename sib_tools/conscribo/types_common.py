from typing import NotRequired, TypedDict


class ConscriboUserMessage(TypedDict):
    message: str
    code: str
    hint: NotRequired[str]


class ConscriboResponseMessages(TypedDict):
    error: list[ConscriboUserMessage]
    warning: list[ConscriboUserMessage]
    info: list[ConscriboUserMessage]


class ConscriboMessageResponse(TypedDict, total=False):
    status: int
    responseMessages: ConscriboResponseMessages


class ConscriboFileField(TypedDict, total=False):
    fileId: int
    fileName: str
    contents: str


class ConscriboBankAccountField(TypedDict, total=False):
    iban: str
    bic: str
    name: str
