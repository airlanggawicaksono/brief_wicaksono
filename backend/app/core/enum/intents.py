from enum import StrEnum


class Intent(StrEnum):
    DATA_QUERY = "data_query"
    GENERAL = "general"
    CLARIFICATION = "clarification"
