"""Future clinician-facing reading-report layer.

Keep this separate from the validated signal-processing core.
"""

from .analysis import QEEGResult

def descriptive_findings(result: QEEGResult) -> list[str]:
    return []
