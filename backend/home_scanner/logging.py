"""structlog configuration with correlation IDs."""
from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar

import structlog

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def new_correlation_id() -> str:
    cid = uuid.uuid4().hex[:8]
    _correlation_id.set(cid)
    return cid


def _add_correlation_id(_, __, event_dict):
    event_dict["cid"] = _correlation_id.get()
    return event_dict


def configure(level: str = "INFO") -> None:
    logging.basicConfig(stream=sys.stdout, level=getattr(logging, level.upper()))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_correlation_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
    )
