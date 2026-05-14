"""Run a steady-state-only oil spike subsidy experiment.

Use this when you have SS results (or only want SS solves) and do not have TPI.
This script runs baseline and reform with `time_path=False` and reports
steady-state GDP effects.
"""

import copy
import json
import os
from importlib.resources import files

from distributed import Client
from ogcore.execute import runner
from ogcore.parameters import Specifications
from ogcore.utils import safe_read_pickle

from ogeth.calibrate import Calibration
from ogeth.utils import is_connected

from oil_price_spike_scenario import (
    build_oil_spike_reform,
    estimate_subsidy_share_of_gdp,
)


def main():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    save_dir = os.path.join(cur_dir, "OG-ETH-OilSpike-SS")
    base_dir = os.path.join(save_dir, "OUTPUT_BASELINE")
    reform_dir = os.path.join(save_dir, "OUTPUT_REFORM")

    client = Client(n_workers=1, threads_per_worker=1)

    p = Specifications(
        baseline=True,
        num_workers=1,
        baseline_dir=base_dir,
        output_base=base_dir,
    )

    with files("ogeth").joinpath("ogeth_default_parameters.json").open("r") as f:
        defaults = json.load(f)
    p.update_specifications(defaults)

    if is_connected():
        c = Calibration(p, update_from_api=True)
        p.update_specifications(c.get_dict())

    runner(p, time_path=False, client=client)

    sam_path = files("ogeth").joinpath("data", "IFPRI_SAM_ETH_2022_SAM.csv")
    subsidy_share = estimate_subsidy_share_of_gdp(str(sam_path), price_spike=0.40)
    reform_dict = build_oil_spike_reform(subsidy_share=subsidy_share, duration_years=1)

    p2 = copy.deepcopy(p)
    p2.baseline = False
    p2.output_base = reform_dir
    p2.update_specifications(reform_dict)

    runner(p2, time_path=False, client=client)
    client.close()

    base_ss = safe_read_pickle(os.path.join(base_dir, "SS", "SS_vars.pkl"))
    reform_ss = safe_read_pickle(os.path.join(reform_dir, "SS", "SS_vars.pkl"))

    y_base = float(base_ss["Yss"])
    y_reform = float(reform_ss["Yss"])
    pct_diff = 100 * (y_reform / y_base - 1)

    print(f"Estimated subsidy share of GDP: {subsidy_share:.4f}")
    print(f"Steady-state GDP percent difference (reform vs baseline): {pct_diff:.3f}%")


if __name__ == "__main__":
    main()
