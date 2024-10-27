from typing import Callable
import pandas as pd
from typing import Dict, List, Iterable

EXPERIMENTS_SHEET_NAME = "experiments"
RESULTS_SHEET_NAME = "results"


def run_scenarios(
    input_filename: str,
    output_filename: str,
    simulate: Callable,
    num_replications=10,
    reproducible=True,
    start_seed=0,
) -> pd.DataFrame:
    scenarios = read_scenarios_excel(input_filename)
    replications = make_replications(
        scenarios, num_replications, reproducible, start_seed
    )
    results = run_simulations(replications, simulate)
    write_results_excel(results, output_filename)
    return results


def read_scenarios_excel(
    filepath: str, sheet_name: str = EXPERIMENTS_SHEET_NAME
) -> List[Dict]:
    """Read scenarios from Excel file and return as list of dictionaries."""
    df_scenarios = pd.read_excel(filepath, sheet_name)
    if animation == True:
        df_scenarios = df_scenarios.head(1)
    return df_scenarios.to_dict("records")


def make_replications(
    scenarios: Iterable[Dict], n_replications: int = 10, reproducible=True, start_seed=0
) -> List[Dict]:
    return [
        {**params, "replication_nr": n, "random_seed": (seed if reproducible else "*")}
        for params in scenarios
        for n, seed in enumerate(range(start_seed, start_seed + n_replications))
    ]


def run_simulations(
    params_seq: Iterable[Dict], simulate: Callable, animate=False, chatty=False
) -> pd.DataFrame:
    """Run a simulation for each parameter se (dict) in sequence and return a dataframe with the results."""
    run = lambda params: run_model_params_dict(params, simulate, animate, chatty)
    return pd.DataFrame(map(run, params_seq))


def run_model_params_dict(
    params_dict: Dict, simulate: Callable, animate=False, chatty=False
) -> dict:
    if chatty:
        scenario = params_dict["scenario"]
        replication_nr = params_dict["replication_nr"]
        seed = params_dict["random_seed"]
        print(f"scenario {scenario} \t replication {replication_nr} \t seed {seed}")
    return simulate(animate=animate, **params_dict)


def write_results_excel(
    df: pd.DataFrame, filepath: str, sheet_name: str = RESULTS_SHEET_NAME
) -> None:
    """Write results to Excel file."""
    df.to_excel(filepath, sheet_name, index=False)


if __name__ == "__main__":
    import chem_simulation as simulation
    from helpers import transform_timeseries

    # if animation == True: Run only 1 scenario with animation
    # if animation == False: Run all scenarios without animation -> choose number of replications
    # the input file is the file with the scenarios and should be in the same folder as the sim_runner.py
    animation = False # auf false stellen wen mehrere experimente (gleichzeitig oder hintereinander) durchgeführt werden
    num_replications = 5

    input_filename = "experiments_4.xlsx"
    output_filename = "output.xlsx"

    if animation == False:
        df = run_scenarios(
            input_filename,
            output_filename,
            simulation.simulate,
            num_replications=num_replications,
        )
        write_results_excel(df, "output.xlsx", "results")
    else:
        output_filename = "output_animate.xlsx"
        scenarios = read_scenarios_excel(input_filename)
        scenario = {**scenarios[0], "random_seed": 0, "replication_nr": 0}
        results = simulation.simulate(animate=animation, **scenario)
        df = pd.DataFrame([results])
        write_results_excel(df, "output_animate.xlsx", "results")

    transform_timeseries(
        output_filename, "results", "queue_reaction_length", "q_react_length"
    )
