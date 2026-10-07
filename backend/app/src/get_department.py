def get_department(likely_unit: str, classified_department: str) -> str:
    """Returns the department based on the likely unit and classified department.

    Adapted from the original workbook function:
    ```excel
    =IF(Y4="CSU", "E&S", AL4)
    ```

    where Y4 is the likely unit input and AL4 is the classified department input. The function returns "E&S" if the likely unit is "CSU", otherwise it returns the classified department.
    """
    if likely_unit.lower() == "csu":
        return "E&S"
    return classified_department