from backend.app.src.lookup_rt_unit import lookup_rt_unit


def get_unit(naics_code: int, department: str) -> str:
    """Returns the unit based on the NAICS code and department.

    Adapted from the original workbook function:
    ```excel
    =IF(AF8="sales",VLOOKUP(O8,elig!$A$2:$J$1494,10,FALSE),"")
    ```

    where AF8 is the department input, O8 is the NAICS code input, and the VLOOKUP function retrieves the RT unit from a lookup table.
    The function returns the RT unit for "sales" department, and raises a ValueError for any other input.
    """
    if department.lower() == "sales":
        return lookup_rt_unit(naics_code)
    raise ValueError(f"Unknown department: {department}")
