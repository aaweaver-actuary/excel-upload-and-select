def get_potential_wp(premium: float, yield_rate: float) -> float:
    """Returns the potential WP based on the premium and yield rate.

    Adapted from the original workbook function:
    ```excel
    =J2*U2
    ```

    where J2 is the premium input and U2 is the yield rate input. The function returns the potential WP by multiplying the premium and yield rate.

    This might be more accurately called "expected premium", since it is essentially a probability weighted premium.
    The potential WP is the expected premium based on the yield rate, which represents the probability of converting a quote into a sale.
    """
    return premium * yield_rate