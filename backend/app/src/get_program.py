def get_program(department: str) -> str:
    """Returns the program based on the department.

    Adapted from the original workbook function:
    ```excel
    =IF(AF3="sales","Commercial Lines","")
    ```

    where AF3 is the department input. The function returns "Commercial Lines" for "sales", and raises a ValueError for any other input.
    """
    if department.lower() == "sales":
        return "Commercial Lines"

    raise ValueError(f"Unknown department: {department}")