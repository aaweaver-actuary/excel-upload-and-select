from app.par.src.lookup_prior_insurer_fct import lookup_prior_insurer_fct
from app.par.src.lookup_agency_par_fct import lookup_agency_par_fct
from app.par.src.lookup_naics4_par_fct import lookup_naics4_par_fct
from app.par.src.lookup_state_par_fct import lookup_state_par_fct


def calculate_par(prior_insurer: str, agency: str, naics4: int, state: str) -> float:
    """Calculates the PAR based on the provided inputs."""
    prior_insurer_par = lookup_prior_insurer_fct(prior_insurer)
    agency_par = lookup_agency_par_fct(agency)
    naics4_par = lookup_naics4_par_fct(naics4)
    state_par = lookup_state_par_fct(state)

    # Combine the individual PAR values to calculate the final PAR.
    # The factor lookups are placeholders, but this is the real calculation of the PAR based on the individual factors:
    return prior_insurer_par * agency_par * naics4_par * state_par
