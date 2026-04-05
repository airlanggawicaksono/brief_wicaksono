from enum import StrEnum


class Stage(StrEnum):
    RECEIVED_INPUT = "received_input"
    INTENT_DETECTED = "intent_detected"
    AGENT_STARTED = "agent_started"
    TOOL_STARTED = "tool_started"
    TOOL_FINISHED = "tool_finished"
    QUERY_EXECUTED = "query_executed"
    DIRECT_RESPONSE = "direct_response"
    RESPONSE_READY = "response_ready"
    FAILED = "failed"


class EventType(StrEnum):
    PROCESS = "process"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    MESSAGE = "message"
    EXTRACTION = "extraction"
    ERROR = "error"
