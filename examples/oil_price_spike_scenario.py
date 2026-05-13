"""Scenario builder for an oil-price spike with a retail price cap.

This module does not solve the model by itself. It builds a reform
specification dictionary that can be passed to `Specifications.update_specifications`
in a baseline/reform workflow like `examples/run_og_eth.py`.
"""

from __future__ import annotations

import json
import os
import sys
from importlib.resources import files

import pandas as pd

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CUR_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)


def estimate_subsidy_share_of_gdp(
    sam_path: str,
    price_spike: float = 0.40,
    commodity_code: str = "cchem",
    row_total_col: str = "total",
) -> float:
    """Estimate annual subsidy cost as share of GDP from SAM data.

    The policy interpretation is a full retail price cap at the pre-spike
    level for the selected commodity. If world/market-clearing price rises by
    `price_spike`, government pays the wedge.

    Args:
        sam_path: Path to the ETH SAM CSV file.
        price_spike: Proportional market price shock (0.40 means +40%).
        commodity_code: SAM row code to proxy oil/fuel consumption.
        row_total_col: Column containing row totals in SAM.

    Returns:
        Estimated subsidy expenditure as share of GDP (model ratio units).
    """
    sam = pd.read_csv(sam_path)
    idx = sam["Code"] == commodity_code
    if idx.sum() != 1:
        raise ValueError(
            f"Could not uniquely identify commodity code '{commodity_code}' in SAM."
        )

    commodity_row = sam.loc[idx].iloc[0]
    commodity_uses = float(commodity_row[row_total_col])

    gov_row = sam.loc[sam["Code"] == "gov"]
    if gov_row.empty:
        raise ValueError("Could not find government row ('gov') in SAM.")
    gdp_proxy = float(gov_row.iloc[0][row_total_col])

    share_in_gdp = commodity_uses / gdp_proxy
    subsidy_share = share_in_gdp * price_spike
    return subsidy_share


def build_oil_spike_reform(
    subsidy_share: float,
    duration_years: int = 1,
    alpha_g_baseline: float | None = None,
) -> dict:
    """Build reform dict for a temporary subsidy financed by higher deficit.

    Strategy:
    * raise `alpha_G` temporarily by `subsidy_share`
    * keep transfers and baseline closure multipliers unchanged
    * allow debt to absorb the one-year fiscal shock
    """
    with files("ogeth").joinpath("ogeth_default_parameters.json").open("r") as f:
        defaults = json.load(f)

    if alpha_g_baseline is None:
        alpha_g_baseline = float(defaults["alpha_G"][0])

    alpha_g_reform = [alpha_g_baseline + subsidy_share] * duration_years + [alpha_g_baseline]

    return {
        "alpha_G": alpha_g_reform,
        "baseline_spending": False,
    }


if __name__ == "__main__":
    sam_path = files("ogeth").joinpath("data", "IFPRI_SAM_ETH_2022_SAM.csv")
    subsidy_share = estimate_subsidy_share_of_gdp(str(sam_path), price_spike=0.40)
    reform = build_oil_spike_reform(subsidy_share=subsidy_share, duration_years=1)
    print("Estimated subsidy share of GDP:", round(subsidy_share, 4))
    print("Reform dictionary:", reform)
