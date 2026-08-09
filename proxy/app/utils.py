"""Logging and utility functions."""

import logging
import sys

# Configure standard logger
logger = logging.getLogger("enterprise_ai_proxy")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def log_request_metrics(
    request_id: str,
    endpoint: str,
    model: str,
    status_code: int,
    latency_ms: float,
) -> None:
    """Logs structured metrics for API requests.

    Guarantees no authorization tokens, API keys, or image payloads are included.
    """
    logger.info(
        f"RequestID={request_id} | Endpoint={endpoint} | Model={model} | "
        f"Status={status_code} | Latency={latency_ms:.2f}ms"
    )
