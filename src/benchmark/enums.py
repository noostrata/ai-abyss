"""Closed vocabularies used by benchmark manifests, events, and results."""

from enum import StrEnum


class ExecutionMode(StrEnum):
    MOCK = "mock"
    LIVE = "live"


class Condition(StrEnum):
    CONTROL = "control"
    FINITE_GRAPH_CONTROL = "finite_graph_control"
    RECURSIVE_TRAP = "recursive_trap"
    SYNTHETIC_INJECTION = "synthetic_injection"


class TrialStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    ENDED = "ended"


class AgentActionKind(StrEnum):
    NAVIGATE = "navigate"
    SUBMIT = "submit"
    ANSWER = "answer"
    ABORT = "abort"


class EventType(StrEnum):
    TRIAL_CREATED = "trial_created"
    TRIAL_STARTED = "trial_started"
    REQUEST_ATTEMPT = "request_attempt"
    PAGE_SERVED = "page_served"
    OBSERVATION_DELIVERED = "observation_delivered"
    AGENT_ACTION = "agent_action"
    MODEL_CALL = "model_call"
    PROVIDER_ENVELOPE = "provider_envelope"
    CALL_ATTEMPT_STATE = "call_attempt_state"
    CALLBACK_TOKEN_ISSUED = "callback_token_issued"
    CALLBACK_VISITED = "callback_visited"
    SUBMISSION_ATTEMPTED = "submission_attempted"
    SYNTHETIC_SECRET_SUBMITTED = "synthetic_secret_submitted"
    BUDGET_RESERVED = "budget_reserved"
    BUDGET_RECONCILED = "budget_reconciled"
    RESOURCE_LEDGER_FINALIZED = "resource_ledger_finalized"
    TRIAL_ENDED = "trial_ended"
    INFRASTRUCTURE_ERROR = "infrastructure_error"


class TerminationReason(StrEnum):
    TASK_SUCCESS = "task_success"
    TASK_FAILURE = "task_failure"
    AGENT_REFUSAL = "agent_refusal"
    AGENT_ABORT = "agent_abort"
    ESCAPED_WITHOUT_TASK_SUCCESS = "escaped_without_task_success"
    MODEL_CALLS_EXHAUSTED = "budget_exhausted:model_calls"
    INPUT_TOKENS_EXHAUSTED = "budget_exhausted:input_tokens"
    OUTPUT_TOKENS_EXHAUSTED = "budget_exhausted:output_tokens"
    TOTAL_TOKENS_EXHAUSTED = "budget_exhausted:total_tokens"
    ACTIONS_EXHAUSTED = "budget_exhausted:actions"
    REQUESTS_EXHAUSTED = "budget_exhausted:requests"
    BYTES_EXHAUSTED = "budget_exhausted:bytes"
    NODES_EXHAUSTED = "budget_exhausted:nodes"
    DEPTH_EXHAUSTED = "budget_exhausted:depth"
    WALL_TIME_EXHAUSTED = "budget_exhausted:wall_time"
    COST_EXHAUSTED = "budget_exhausted:cost"
    PROVIDER_ERROR = "provider_error"
    TOOL_ERROR = "tool_error"
    INVALID_AGENT_ACTION = "invalid_agent_action"
    CONTAINMENT_VIOLATION = "containment_violation"
    CANCELLED = "cancelled"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"


class UtilityStatus(StrEnum):
    CORRECT = "correct"
    WRONG = "wrong"
    REFUSED = "refused"
    INCOMPLETE = "incomplete"
    INFRASTRUCTURE_ERROR = "infrastructure_error"


class Recognition(StrEnum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


class CallAttemptState(StrEnum):
    RESERVED = "reserved"
    LOCALLY_STARTED = "locally_started"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    RECONCILED = "reconciled"
    DEFINITELY_NOT_SENT = "definitely_not_sent"
    REJECTED_BEFORE_INFERENCE = "rejected_before_inference"
    BILLING_UNKNOWN = "billing_unknown"


class MockProfile(StrEnum):
    TASK_SOLVER = "task_solver"
    RECURSIVE_FOLLOWER = "recursive_follower"
    RECOGNISE_AND_RECOVER = "recognise_and_recover"
    INJECTION_FOLLOWER = "injection_follower"
    INVALID_ACTION = "invalid_action"
    PROVIDER_FAILURE = "provider_failure"
    DELAYED = "delayed"
    EGRESS_ATTACKER = "egress_attacker"
    REFUSAL = "refusal"
