"""Local-only evaluation helpers for the Stage-4 dry-run harness.

This package deliberately has no dependency on generation modules or paid APIs.
"""

from .auto_repair_harness import run_harness

__all__ = ["run_harness"]
