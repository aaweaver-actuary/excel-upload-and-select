def get_naics_subdescription(naics_code: int) -> str:
    """Returns the sub-description of the NAICS code, or 'Unknown' if not found."""
    naics_subdescriptions = {
        123456: "Example Neural Metrics NAICS Sub-Description",
        987654: "Example Relativity6 NAICS Sub-Description",
        111111: "Example Agent-Entered NAICS Sub-Description",
    }
    return naics_subdescriptions.get(naics_code, "Unknown")
