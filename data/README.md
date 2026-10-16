# Data

## What's committed vs. what you need to obtain

| Path | Committed? | Size | What |
|---|---|---|---|
| `data/processed/` | **Yes** | ~2 MB total | Small cached intermediates (per-site rating-curve fits, screening results, copula fit cache, probabilistic-prediction grids) that the figure scripts read directly, so you don't have to re-run the full pipeline from raw data just to regenerate a figure. |
| `data/raw/ifmha_subset_stat.csv` | **No** | ~760 MB | A ~6,323-gauge CONUS subset of the IFMHA dataset (paired discharge/stage field measurements). Required only for `scripts/fig01_run.py`, `fig02_run.py`, `fig03_run.py`, and for re-running the three case-study notebooks from scratch. |
| `data/raw/Bankfull_Meanflow_CONUS.txt` | **No** | ~216 MB | Bankfull channel geometry per NHDPlus V2.1 reach (Zarrabi et al., 2025). Required only if you re-run the case-study notebooks' bankfull-threshold step. |

## How to obtain the raw files

Both raw files are too large for version control and are not redistributed in this repository.

**`ifmha_subset_stat.csv`** is a filtered subset (the ~6,323 CONUS gauges with usable paired discharge/stage measurements) of the IFMHA dataset:

> Erfani, S.M.H., Erfani, M., Cohen, S., Downey, A.R.J., Goharian, E. (2024). A large dataset of fluvial hydraulic and geometry attributes derived from USGS field measurement records. *Environmental Modelling & Software*, 180, 106136. https://doi.org/10.1016/j.envsoft.2024.106136

The full dataset (~2.8 million field measurements, 10,050 USGS gauges, 1845–2022) is hosted at [github.com/smhassanerfani/ifmha](https://github.com/smhassanerfani/ifmha) via Git LFS:

```bash
git lfs install
git clone https://github.com/smhassanerfani/ifmha.git
cd ifmha/dataset
git lfs pull
```

(If you hit the repo's LFS bandwidth limit, the same page links a Google Drive mirror.) Once you have it, filter it down to the CONUS subset with valid paired discharge/stage/lat-lon this project uses (see `docs/PROJECT_METHODOLOGY.md` Section 3), and save the result as `data/raw/ifmha_subset_stat.csv`.

**`Bankfull_Meanflow_CONUS.txt`** (bankfull channel geometry per NHDPlus V2.1 reach) is from:

> Zarrabi, R., McDermott, R., Erfani, S.M.H., Cohen, S. (2025). Bankfull and Mean-Flow Channel Geometry Estimation Through Machine Learning Algorithms Across the CONtiguous United States (CONUS). *Water Resources Research*, 61(2). https://doi.org/10.1029/2024wr037997

Data: "Bankfull and Mean-flow Channel Geometry Dataset across the CONtiguous United States (CONUS)," HydroShare, DOI: [10.4211/hs.63ae139ccd2445959470d0e5a2ebf6a5](https://doi.org/10.4211/hs.63ae139ccd2445959470d0e5a2ebf6a5) (CC BY 4.0). That page notes a newer version may have replaced it since — check HydroShare for the current one. Records are linked to NHDPlus V2.1 reaches by COMID.

Place both files at:

```
data/raw/ifmha_subset_stat.csv
data/raw/Bankfull_Meanflow_CONUS.txt
```

All scripts in `scripts/` expect these exact paths when run from the repo root.

## `data/processed/` contents

- `screening_cache/population_screening.csv` — cached output of the CONUS-wide 6,323-gauge screen (the per-gauge stage-IQR variability metric behind fig-01). Reused rather than recomputed by fig-02 and fig-03's scripts.
- `screening_cache/copula_results_cache.pkl` — cached copula fits for the 12 fig-02/fig-03 screening sites.
- `case_study_sites/<site>/` — per-site cached inputs for the three case-study gauges (06606600, 05481650, 08096500): full daily record, observed rating-curve points, fitted rating-curve parameters, marginal-distribution fit info, and the probabilistic (copula) prediction grid used by fig-04, sfig-01, sfig-02, and the FIM combined figures.
- `fim_maps/` — the ArcGIS Pro-rendered HAND-FIM inundation extent rasters (PNG). These are **not reproducible from a script in this repo** — see `docs/REPRODUCIBILITY_NOTES.md`.

## Why this split

`data/processed/` is small enough to version-control directly and lets anyone regenerate every final figure/table without first assembling the 1 GB of raw inputs. The raw files are only needed if you want to re-verify the pipeline from the original field measurements.
