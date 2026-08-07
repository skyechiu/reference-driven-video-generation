"""
pipeline.policies — Mode A reusable policy layer.

Side-effect-free policy modules distilled from the street-run repair. They
DOCUMENT and STRUCTURE the fixes as general Mode A logic; they do not change
the current production scripts and importing them runs no API and touches no
state. See docs/MODE_A_REUSABLE_POLICIES.md for how to fold them in.
"""
from . import reference_policy, motion_policy, evaluation_policy, backend_limits

__all__ = ["reference_policy", "motion_policy", "evaluation_policy", "backend_limits"]
