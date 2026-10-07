def get_product(normalized_product_name: str, unit: str) -> str:
    """Returns the product based on the normalized product name and unit.

    Adapted from the original workbook function:
    ```excel
    =IF(AN3="Work Comp","Work Comp",IF(AND(AG3="SB",AN3<>"Work Comp"),"BOP",IF(AND(AG3="CLD",AN3<>"Work Comp"),"Package/All Other","")))
    ```
    where AN3 is the normalized product name input and AG3 is the unit input.
    The function returns:
        - "Work Comp" for "Work Comp" normalized product name
        - "BOP" for "SB" unit and not "Work Comp" normalized product name
        - "Package/All Other" for anything else (not "Work Comp" normalized product name and not "SB" unit)
    """

    if normalized_product_name.lower() == "work comp":
        return "Work Comp"
    if unit.lower() == "sb" and normalized_product_name.lower() != "work comp":
        return "BOP"
    if unit.lower() == "cld" and normalized_product_name.lower() != "work comp":
        return "Package/All Other"
    raise ValueError(
        f"Unknown combination of normalized product name: {normalized_product_name} and unit: {unit}"
    )
