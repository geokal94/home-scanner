"""Observability utilities (Sentry, structlog already in home_scanner.logging)."""
from .sentry import init_sentry

__all__ = ["init_sentry"]
