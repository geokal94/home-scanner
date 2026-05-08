"""Notifier: scrape → diff → dispatch."""
from .diff import compute_alerts_to_send
from .dispatch import dispatch_alerts

__all__ = ["compute_alerts_to_send", "dispatch_alerts"]
