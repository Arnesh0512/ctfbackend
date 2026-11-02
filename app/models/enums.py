from enum import StrEnum

from sqlalchemy import Enum


class QuestionStatus(StrEnum):
    ACTIVE = "active"
    SOLVED = "solved"
    SKIPPED = "skipped"


class QuestionEvent(StrEnum):
    VIEW = "view"
    ANSWER_CORRECT = "answer_correct"
    ANSWER_WRONG = "answer_wrong"
    RETRY_PURCHASED = "retry_purchased"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    UNBLOCKED = "unblocked"
    H1_PURCHASED = "h1_purchased"
    H2_PURCHASED = "h2_purchased"
    H12_PURCHASED = "h12_purchased"
    START = "start"
    LEFT = "left"
    WAIT = "wait"
    NO_WAIT = "no_wait"
    END = "end"


def str_enum(enum_cls: type[StrEnum]) -> Enum:
    return Enum(
        enum_cls,
        native_enum=False,
        length=32,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )
