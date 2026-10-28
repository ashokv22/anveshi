# Correlation limits
DEFAULT_MAX_CORRELATION_DEPTH = 2
DEFAULT_MAX_CORRELATED_EVENTS = 500
SAFE_CORRELATION_IDENTIFIER_KEYS = frozenset(
    {"transaction_id", "request_id", "trace_id"}
)

# Investigation limits
DEFAULT_INVESTIGATION_WINDOW_MINUTES = 15
