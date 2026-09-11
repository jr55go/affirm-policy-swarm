def is_production_eligible(finding: dict) -> bool:
    """
    Phase 0: Enforce strict production eligibility.
    Rejects any finding with fallback markers, synthetic data, or missing locators.
    """
    # 1. Require canonical locator
    if not finding.get("url"):
        return False

    # 2. Reject if validation was bypassed or not explicitly approved
    if str(finding.get("validation_status", "")).strip().lower() != "approved":
        return False

    # 3. Reject any known fallback markers
    fallback_flags = [
        "is_fallback", "used_fallback", "fallback_mode",
        "triage_fallback", "compression_fallback", "impact_fallback",
        "entity_fallback", "risk_fallback", "validation_fallback",
        "is_mock", "is_simulated"
    ]
    if any(finding.get(flag) for flag in fallback_flags):
        return False

    return True
