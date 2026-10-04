"""Under which terms each claim may be reused, recorded in the serving tables (ADR 0005, ADR 0013).

Claims in the repository are project-curated data under CC BY 4.0. Claims the build makes from the Allen Mouse Brain
Connectivity Atlas (ADR 0010) keep the Allen Institute's terms: shown and served with their citation, never dumped.
"""

ALLEN = "allen-institute"
PROJECT = "cc-by-4.0"


def terms_of(claim: dict) -> str:
    return ALLEN if "allen.experiment" in (claim.get("extra") or {}) else PROJECT
