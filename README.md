# Stochastic Rating Curves for Flood Inundation Mapping

A USGS rating curve normally treats stage-to-discharge as a single fixed
curve. In reality, the same discharge can correspond to a range of stages —
backwater, hysteresis, channel change, measurement error. This project fits
a copula to the field-measurement record at each site instead, so a
discharge maps to a full predictive distribution of stage rather than one
number, and then carries that uncertainty through HAND-FIM to see what it
does to flood extent at three case-study rivers.

`docs/PROJECT_METHODOLOGY.md` walks through the whole thing end to end —
why a copula, how each site's fit is built, how it's checked against a
Gaussian Process Regression baseline, and how it feeds into the flood maps.
Start there if you're new to this.

This work isn't published yet, so this repo is deliberately scoped to code,
data, and figures — no manuscript text, no title, no citation details that
would pre-empt publication. A `CITATION.cff` with those fields will go up
once there's something to cite.

## Layout

```
notebooks/    the 3 case-study per-site copula fits, plus their GPR-baseline comparisons
scripts/      everything that generates a figure
figures/      the figures themselves
data/
  README.md     how to get the raw IFMHA data (not committed — see below)
  processed/    small cached intermediates the scripts read directly (committed)
docs/
  PROJECT_METHODOLOGY.md    the full write-up
  PAPER_STYLE_GUIDE.md      figure styling conventions
  REPRODUCIBILITY_NOTES.md  known gaps — read before assuming everything here reruns cleanly
requirements.txt
LICENSE
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

`cartopy` (only needed for the CONUS map) has non-Python dependencies
(GEOS, PROJ) that pip doesn't always resolve. If it fails to build, use
conda instead: `conda install -c conda-forge cartopy`.

## Data

Two raw files (~1 GB combined) are needed to rerun the pipeline from
scratch, and neither is committed here — see `data/README.md` for what they
are and where to get them. You don't need either one just to regenerate a
figure: the fitted intermediates each figure script actually reads live in
`data/processed/` and are committed directly (a few MB total).

## How it fits together

1. **CONUS screening.** Every USGS gauge with 50+ field measurements gets
   checked for stage-at-fixed-discharge scatter, so the three case studies
   aren't cherry-picked — the scatter shows up across the whole population.
   `scripts/fig01_step1_conus_screening.py` → `fig01_step2_conus_map_plot.py`.
2. **Twelve-site gallery.** A spread of sites across that screening range
   get both their observed and copula-probabilistic rating curves fit and
   plotted. `fig02_observed_rating_curves_gallery.py`,
   `fig03_probabilistic_rating_curves_gallery.py`.
3. **Three case studies.** Little Sioux (06606600), Des Moines (05481650),
   and Brazos (08096500) go through the full pipeline — temporal thinning,
   physical-plausibility filtering, rating-curve fit, high-flow subsetting,
   marginal and copula fitting — in `notebooks/casestudy_<site>_copula.ipynb`.
4. **GPR comparison.** Each site's high-flow data also gets a standard and
   heteroscedastic Gaussian Process Regression fit, in
   `casestudy_<site>_gpr_comparison.ipynb`, to show what a symmetric
   predictive distribution structurally can't capture that the copula can.
5. **Flood inundation mapping.** The copula's stage percentiles are run
   through HAND, and the resulting extents are finalized as maps in ArcGIS
   Pro — that part isn't scripted, the maps are included as finished images
   (see `docs/REPRODUCIBILITY_NOTES.md`). Each map is then paired with the
   site's rating curve into one combined figure. Only Little Sioux is done
   so far.

## Figures

| Figure | What it shows | Built by |
|---|---|---|
| fig-01 | Stage-discharge variability across 6,323 USGS gauges | `scripts/fig01_run.py` |
| fig-02 | Observed rating curves, 12 sites | `scripts/fig02_run.py` |
| fig-03 | Copula-probabilistic rating curves, same 12 sites | `scripts/fig03_run.py` |
| fig-04 | Copula vs. GPR, 3 case-study sites | `scripts/fig04_copula_vs_gpr_comparison.py` |
| sfig-01 | Case-study discharge/stage distributions | `scripts/sfig01_sfig02_case_study_composites.py` |
| sfig-02 | Rating curves + Q-Q plots, 3 sites | `scripts/sfig01_sfig02_case_study_composites.py` |
| FIM-06606600 | Rating curve + HAND-FIM map, Little Sioux | `scripts/fim_06606600_combined_figure.py` |
| FIM-05481650, FIM-08096500 | Same, Des Moines / Brazos | not built yet |

Run any `scripts/*.py` from the repo root — they all assume that as the
working directory and only touch paths under `data/` and `figures/`.
