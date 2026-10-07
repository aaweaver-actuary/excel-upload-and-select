"""
This module provides a function to get the description of a NAICS code. It reads the code from a lookup 
table and returns the corresponding description. If the code is not found, it returns 'Unknown'.

The lookup table comes from RDM and is a mapping of NAICS codes to their descriptions. 
"""

def get_naics_description(naics_code: int) -> str:
    """Returns the description of the NAICS code, or 'Unknown' if not found."""
    naics_descriptions = {
        123456: "Example Neural Metrics NAICS Description",
        987654: "Example Relativity6 NAICS Description",
        111111: "Example Agent-Entered NAICS Description",
    }
    return naics_descriptions.get(naics_code, "Unknown")
