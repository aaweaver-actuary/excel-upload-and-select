from typing import Literal


def get_target_system(unit: Literal["cld", "sb"]) -> str:
    """Returns the target system based on the unit.

    Adapted from the original workbook function:
    ```excel
    =IF(AG5="SB","Cinergy",IF(AG5="CLD","eclas",""))
    ```

    where AG5 is the unit input. The function returns "Cinergy" for "SB", "eclas" for "CLD", and raises a ValueError for any other input.
    """
    if unit.lower() == "cld":
        return "eclas"
    if unit.lower() == "sb":
        return "Cinergy"

    raise ValueError(f"Unknown unit: {unit}")
