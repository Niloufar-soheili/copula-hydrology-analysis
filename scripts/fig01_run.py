import matplotlib
matplotlib.use("Agg")

import pandas as pd
import numpy as np
import math

# ---- cell 1: data loading (local path instead of Colab Drive path) --------
# Run this script from the REPO ROOT. See data/README.md for how to obtain
# the raw IFMHA CSV (not committed -- 760MB).
INPUT_FILE_PATH = "data/raw/ifmha_subset_stat.csv"
CFS_TO_M3S = 0.028316832
FT_TO_M = 0.3048

print("Loading IFMHA subset (this is a 760MB CSV, may take a bit)...")
ifmha_subset_stat = pd.read_csv(
    INPUT_FILE_PATH,
    converters={"site_no": str},
    low_memory=False,
)
print(f"DataFrame Shape: {ifmha_subset_stat.shape}")

ifmha_subset_stat["discharge_m3s"] = ifmha_subset_stat["discharge_va"] * CFS_TO_M3S
ifmha_subset_stat["stage_m"] = ifmha_subset_stat["gage_height_va"] * FT_TO_M

# ---- cell 2 (relevant line only): grouped_ifmha ----------------------------
grouped_ifmha = ifmha_subset_stat.dropna(subset=["gage_height_va"]).groupby("site_no")

# ---- TARGET_SITES_UNIQUE (final list, cell 14/21) --------------------------
TARGET_SITES_UNIQUE = [
    '3611500', '7258000', '3301500', '6905500',
    '5404000', '5422000', '8330000',
    '5481650', '7381482', '5488500', '6810000', '5597000'
]

print("Running population screening...")
exec(open("scripts/fig01_step1_conus_screening.py", encoding="utf-8").read().split("# --- figure")[0])

print("Rendering Fig. 1 (CONUS variability map)...")
exec(open("scripts/fig01_step2_conus_map_plot.py", encoding="utf-8").read())

print("DONE")
