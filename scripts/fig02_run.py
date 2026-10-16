import matplotlib
matplotlib.use("Agg")

import pandas as pd
import numpy as np
import math

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

grouped_ifmha = ifmha_subset_stat.dropna(subset=["gage_height_va"]).groupby("site_no")

LAT, LON = "dec_lat_va", "dec_long_va"

pop = pd.read_csv("data/processed/screening_cache/population_screening.csv", converters={"site_no": str})
print(f"Loaded cached pop screening: {pop.shape}")

TARGET_SITES_UNIQUE = [
    '3611500', '7258000', '3301500', '6905500',
    '5404000', '5422000', '8330000',
    '5481650', '7381482', '5488500', '6810000', '5597000'
]

print("Rendering Fig. 2 gallery (cell 44)...")
exec(open("scripts/fig02_observed_rating_curves_gallery.py", encoding="utf-8").read())

print("DONE")
