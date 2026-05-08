"""Notifier: scrape → diff → dispatch."""
from .diff import compute_alerts_to_send

__all__ = ["compute_alerts_to_send"]
