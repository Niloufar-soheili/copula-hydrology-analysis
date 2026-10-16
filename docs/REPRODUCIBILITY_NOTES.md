# Reproducibility notes

Honest caveats about this repo's reproducibility chain, written at the time
of packaging (2026-10-15). Two things are worth knowing before you assume
"run every script top to bottom" reproduces every figure bit-for-bit.

## 1. `fig-04`'s input cache (`_3x3_data_<site>.npz`) has no generating script

`scripts/fig04_copula_vs_gpr_comparison.py` only *reads*
`data/processed/case_study_sites/<site>/_3x3_data_<site>.npz` (the per-site
copula/GPR quantile predictions it plots). Nowhere in the original project
is there a script that *writes* this file -- it was produced by manually
running cells from `notebooks/casestudy_<site>_gpr_comparison.ipynb` and
saving the result, and that save step itself was never captured as code.

Practically: the cached `.npz` files are committed in `data/processed/`, so
`fig04_copula_vs_gpr_comparison.py` runs and reproduces fig-04 as-is. What's
missing is a script that regenerates those `.npz` files
*from* the GPR comparison notebooks, should the underlying copula or GPR
fits ever change. If you need that, the quantities to extract from each
notebook are documented in `fig04_copula_vs_gpr_comparison.py`'s own
docstring (`Q_hf, H_hf, q_grid, cop_preds, H_rc, gpr_std_preds,
gpr_het_preds, best_name`).

## 2. The three case-study notebooks and their GPR-comparison notebooks were not re-run together

The three `casestudy_<site>_copula.ipynb` notebooks in this repo reflect one
specific, deliberate pipeline fix made late in development: the Brazos
(08096500) notebook's undocumented `MAX_DISCHARGE_THRESHOLD = 900 m3/s`
discharge cap and an unjustified `START_YEAR = 1940` pre-filter were removed,
and the physical-plausibility filter was unified across all three sites to
`Q > 0, H > 0, H < 20 m`. This is the current, final version of that pipeline.

The companion `casestudy_<site>_gpr_comparison.ipynb` notebooks (and
therefore `fig-04`'s cached `_3x3_data_8096500.npz`) were built from the
copula fit **before** that fix. They were not re-executed afterward. In
practice this means: if you re-run `casestudy_08096500_brazos_copula.ipynb`
and `casestudy_08096500_brazos_gpr_comparison.ipynb` back-to-back today,
the copula numbers from the first notebook and the GPR-comparison numbers
from the second will not agree with each other for Brazos, because the
second was never regenerated against the first's current state.

fig-04 itself is still correct as committed — it was built from the GPR
comparison as it existed at the time, same as the cached `.npz` here.
Flagging this so nobody is confused later about why re-running both
notebooks doesn't reproduce fig-04 numerically from scratch.

## 3. FIM combined figures: only 06606600 exists so far

`scripts/fim_06606600_combined_figure.py` regenerates the Little Sioux
probabilistic-rating-curve panel at a figure size matched to its paired
HAND-FIM map's native resolution, then combines the two into a single file
with no rescaling of either panel. The equivalent combined figures for
05481650 (Des Moines) and 08096500 (Brazos) are not yet in this repo and
will be added separately. The ingredients for both already exist in
`data/processed/case_study_sites/<site>/` and
`data/processed/fim_maps/<site>_FIM_final.png`; the same script's approach
(regenerate the rating-curve panel to match the map's native pixel height,
combine without rescaling) applies directly.

## 4. The HAND-FIM map rasters are not reproducible from this repo

`data/processed/fim_maps/*_FIM_final.png` were produced by running HAND
with the copula's stage percentiles as input, then finalizing the resulting
extents as maps in ArcGIS Pro. No script in this repo reproduces that step
-- they're committed as finished images, the same way a satellite image or
a scanned figure would be. This repo's scope is the statistical
rating-curve pipeline and the figures/tables derived from it; the HAND run
and ArcGIS Pro styling happen upstream of it.
