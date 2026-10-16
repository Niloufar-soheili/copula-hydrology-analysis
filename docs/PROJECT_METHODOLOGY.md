# Stochastic Rating Curves for Flood Inundation Mapping — Project Methodology

This document explains the whole project from the ground up: the motivation,
every analysis step, what each step proves, and where the code lives. It is
written to be read top to bottom by someone new to the project (e.g. an
undergraduate joining it), but the section headers also work as a reference.

---

## 1. The 60-second summary

Every stream gauge converts a measured **water level** into a **flow rate**
using a single fixed curve called a *rating curve*. That curve is treated as
exact. In reality, at high flows the same flow rate can correspond to a
*range* of water levels — because of flood-wave physics, backwater, channel
change, ice, vegetation, and measurement error. This project replaces the
single rating curve with a **probability distribution**: for any discharge, it
predicts a full distribution of plausible stages, using a statistical tool
called a **copula**. It then shows what that stage uncertainty does to a
**flood inundation map** — the map of which land gets wet in a flood.

Two headline results:

1. The copula captures a **skewed, discharge-dependent** stage uncertainty
   that the standard alternative (Gaussian Process Regression) *structurally
   cannot* represent.
2. When the stage uncertainty is pushed through a flood model (HAND-FIM), a
   1.5–3.5 m spread in plausible stage at a single discharge produces
   **substantially different flood extents**, and the deterministic rating
   curve used in operational practice sits at roughly the 20th–40th percentile
   of that range — i.e. on the optimistic side.

---

## 2. Background: the concepts you need

### 2.1 Stage and discharge

- **Discharge** (`Q`, units m³/s): the volume of water passing a cross-section
  per second. This is what hydrologists actually care about, but it is hard to
  measure — it requires sending a technician out with a current meter or an
  acoustic Doppler profiler (ADCP) to physically measure velocity across the
  channel.
- **Stage** (`H`, units m): the height of the water surface above a fixed
  reference level (datum). This is *easy* to measure — a pressure sensor or
  float in a stilling well records it continuously, every 15 minutes, forever,
  with no technician needed.

### 2.2 The rating curve

Because stage is cheap and discharge is expensive, every USGS gauge uses a
**rating curve**: a function `Q = f(H)` fitted once from a set of paired
field measurements (technician goes out, measures `Q` directly, notes the
`H` at that moment). After that, the continuous stage record is pushed
through the rating curve to produce a continuous discharge record. The
standard form is a **power law**:

```
Q = C · (H − H0)^n
```

- `C` — a scale coefficient
- `n` — an exponent (≈ 2 for many natural channels)
- `H0` — the stage at which flow would be zero (the bottom of the control
  section)

These three parameters are fitted by least squares (`scipy.optimize.curve_fit`
in this project).

### 2.3 The problem this project addresses

If you plot every field-measured `(Q, H)` pair for a gauge, they do **not**
fall exactly on one curve. They *scatter*, and the scatter is usually
**worst at high flows** — exactly the flows that matter for flooding. Known
physical causes:

| Cause | Effect on the Q–H relationship |
|---|---|
| **Hysteresis (loop rating)** | During a flood wave, the water-surface slope is steeper while the flood is *rising* than while it is *falling*. Steeper slope → more flow at the same depth. So at a given `Q`, stage is **lower on the rising limb, higher on the falling limb**. |
| **Backwater** | A downstream obstruction (confluence, dam, ice jam, vegetation) raises stage without raising discharge. |
| **Channel change (scour/fill)** | The bed erodes during big floods and refills afterward, moving `H0` around. |
| **Measurement error** | High-flow discharge measurements are hard and often use indirect methods (from a bridge, a cableway, a boat), which are less accurate. |

Standard practice ignores all of this and reports one discharge per stage.
This project asks: **what if we model the scatter explicitly, as a
probability distribution, and see what difference it makes?**

### 2.4 Why a copula

We want the conditional distribution `f(H | Q)` — "given this discharge, how
is stage distributed?". A **copula** is a function that lets you build a joint
distribution of two variables by specifying:

1. the **marginal** distribution of each variable *separately* (the
   distribution of `Q` on its own, and of `H` on its own), and
2. the **dependence structure** linking them — captured entirely by the copula.

Sklar's theorem guarantees any joint distribution can be written this way.
The practical payoff: the copula's dependence structure is free to be
**asymmetric and skewed**. A simpler assumption (jointly Gaussian `Q` and
`H`) forces the dependence to be symmetric, which — as this project shows —
is wrong for high-flow hydraulics.

Five bivariate copula families are candidates in this project:

| Family | Tail behaviour |
|---|---|
| **Gaussian** | symmetric, no tail dependence |
| **Student-t** | symmetric, but with tail dependence (both tails) |
| **Clayton** | lower-tail dependence |
| **Gumbel** | **upper-tail dependence** — physically the expected family for floods (extremes in `Q` and `H` occur together) |
| **Frank** | symmetric, no tail dependence |

---

## 3. The data: the IFMHA dataset

- **File:** `ifmha_subset_stat.csv` (~760 MB, in the project root; on Colab it
  lives at `/content/drive/MyDrive/IFMHA/ifmha_subset_stat.csv`).
- **Contents:** paired **field measurements** of discharge (`discharge_va`,
  in cubic feet per second) and gage height (`gage_height_va`, in feet) for
  **~6,323 USGS stream gauges** across the contiguous United States (CONUS),
  each with a `site_no`, an `NHDPlus COMID` (reach identifier), a date, a
  measurement method, and lat/lon.
- **Unit conversion** (done in every notebook's first cell):
  `discharge_m3s = discharge_va × 0.028316832`,
  `stage_m = gage_height_va × 0.3048`.
- **Important:** these are the *discrete field measurements* (technician
  visits), **not** the continuous 15-minute record. Median spacing between
  visits is roughly 40 days — long enough that a flood has fully risen and
  fallen between two consecutive visits. That fact matters later (Section 8).
- **Supporting file:** `Bankfull_Meanflow_CONUS.txt` — machine-learning
  estimates of bankfull channel geometry (`bnk_depth`) for every NHDPlus V2.1
  reach, from Zarrabi et al. (2025). Used to define a physically meaningful
  "flood threshold" per site.

---

## 4. Part I — CONUS-wide screening: how common is rating-curve scatter?

**Goal:** show that stage-at-fixed-discharge scatter is not a quirk of a few
weird gauges but a widespread, spatially patterned phenomenon.

**Code:** `scripts/_cell40.py` (the metric + the map data), `scripts/_cell42.py`
(the final Figure 1 map). Both are extracted from
`final_abnormal_sites_12may.ipynb` cells 40/42.

### 4.1 The variability metric

For every gauge with at least 50 valid measurements:

1. Sort its discharge measurements and split them into **10 deciles** (bins of
   roughly equal count).
2. In each bin, all the measurements have *nearly the same discharge*. Compute
   the **interquartile range (IQR) of stage** within that bin — i.e. the
   spread of water levels observed at essentially the same flow.
3. Average that within-bin stage IQR across all 10 bins.

The result — **"mean within-bin stage IQR"**, in meters — is a single number
per gauge. Near **0** means discharge and stage are in near-deterministic
lock-step (a single rating curve is fine). **Larger** means a real range of
stages occurs at the same discharge (a single rating curve is hiding
information).

No gauge is excluded for being high- or low-variability — only for having too
little data (< 50 obs) or missing/out-of-CONUS coordinates. So the map is an
**unbiased population screen**, not a cherry-pick.

### 4.2 What the map shows (Figure 1)

- The metric's distribution across the ~6,323 gauges is **strongly
  right-skewed**: most gauges are low, a long tail is high.
- **Spatially:** high values concentrate in the **Great Plains**, the **lower
  Mississippi–Missouri–Arkansas–Red River alluvial corridor**, and the **Gulf
  coastal plain**. Low values cluster in the **Appalachians / New England**
  and the **Rocky Mountains / Cascades**.
- Interpretation: low-gradient, fine-sediment, large-drainage-area rivers
  (mobile beds, backwater-prone, gentle slopes) scatter more; steep bedrock
  streams scatter less. This matches the physical causes in Section 2.3.

### 4.3 The 12 representative sites (Figure 2)

Twelve gauges spanning the full range of the metric are selected for a
detailed look. Their observed rating curves — with the deterministic
power-law fit and the copula's predictive bands overlaid — are Figure 2 of
the paper (a 4×3 grid, `fig_copula_sites_clean_v2.png`, built by
`scripts/_cell_copula_v2.py`). The 12 sites, numbered north → south:

```
03611500  07258000  03301500  06905500  05404000  05422000
08330000  05481650  07381482  05488500  06810000  05597000
```

A cached table of the full 6,323-site screen is saved as
`population_screening.csv` so downstream figures don't re-run the whole loop.

---

## 5. Part II — The copula model, step by step

This is the statistical core of the paper. Two implementations exist and are
*almost* identical:

- **`scripts/_cell_copula_v2.py`** — the batch version that fits all 12
  screening sites and makes Figure 2.
- **`10Agust6606600_ipynb.ipynb`**, **`10August5481650_ipynb.ipynb`**,
  **`10August8096500_ipynb.ipynb`** — the per-site notebooks for the three
  detailed case-study sites. **These three are the canonical/authoritative
  source for the case-study numbers** (see `memory/canonical_site_notebooks.md`
  — there is an older `copula_analysis_<site>_cleaned.ipynb` family that
  disagrees for Brazos, and must not be used).

The two implementations differ in two small ways, noted inline below.

### Step 1 — Extract one site, aggregate to daily

Pull all rows for the target `site_no`. Convert timestamps, drop rows missing
`Q`, `H`, or date. **Collapse sub-daily measurements to one value per calendar
day** (mean of `Q` and mean of `H` for that day). This removes the handful of
cases where a technician logged two measurements hours apart.

### Step 2 — Temporal thinning (reduce autocorrelation)

Copula fitting assumes the input pairs are approximately **independent**.
Consecutive measurements close in time are not (the river "remembers" its
state). Fix: a greedy scan keeps a day **only if it is at least 3 days after
the previously kept day** (`MIN_GAP = 3`). Everything closer is dropped.

### Step 3 — Physical plausibility filter

Keep only rows with `Q > 0`, `H > 0`, and `H < 20 m`. (A 20 m stage would be
a data error for these rivers.) Dropped counts are still reported so nothing
is hidden. This filter is now applied identically in all three canonical
notebooks (06606600 previously had no explicit filter cell, 05481650 used a
25 m threshold, and 08096500 additionally applied an undocumented
`MAX_DISCHARGE_THRESHOLD = 900 m³/s` cap and an unjustified `START_YEAR =
1940` pre-filter — all three have been unified to this one rule; see the
Section 6 correction note for the resulting Brazos change).

### Step 4 — Fit the deterministic rating curve

Fit `Q = C·(H − H0)^n` by non-linear least squares
(`scipy.optimize.curve_fit`, bounded: `C > 0`, `0 < n < 5`, `H0` near the
minimum observed stage). This curve is used two ways: (a) as the "outlier
detector" in Step 6, and (b) as the **deterministic baseline** that the
probabilistic curve is compared against in every figure.

### Step 5 — Select the high-flow subset

The copula is fitted **only on high flows** — the flows relevant to flooding,
where the interesting scatter lives. Two selection rules are used:

- **Batch script (`_cell_copula_v2.py`):** take the **top 360** discharge
  values (`N_TOPFLOW = 360`); for a few very flashy sites, take instead all
  flows above the 25th percentile (`TOP_75_OVERRIDE`).
- **Case-study notebooks:** compute a **bankfull discharge** `Q_bf` (look up
  `bnk_depth` for the site's COMID in `Bankfull_Meanflow_CONUS.txt`, treat it
  as bankfull stage, run it through the fitted rating curve). Then take the
  **top ~200–220 measurements** (`N_POINTS_DESIRED`) to guarantee enough data
  for a stable fit. So the notebooks report a bankfull threshold as the
  *physical* motivation, but the *operational* cut is a fixed sample size of
  ~200 points. (The paper text describes this as "pairs at or above bankfull,
  minimum 100"; the code enforces the fixed-N version.)

### Step 6 — Outlier removal

Using the fitted rating curve, predict the stage each high-flow discharge
"should" have. Compute the absolute residual `|H_observed − H_predicted|`.
Drop any point where the residual exceeds `mean + 3·standard deviation`.
Typically removes 1–10 points per site.

### Step 7 — Trim the sparse upper tail

Drop the top 1% of discharge values (`TAIL_TRIM = 1`). The very highest few
flows are so sparsely sampled that they destabilise the marginal fit without
adding real information.

### Step 8 — Fit the marginal distributions

For `Q` and for `H` **separately**, fit four candidate families —
**Gamma, Truncated Gaussian, Gaussian, Student-t** — by maximum likelihood,
and select the one with the **lowest BIC**:

```
BIC = k·ln(n) − 2·ln(L̂)
```

where `k` = number of parameters, `n` = sample size, `L̂` = maximised
likelihood. BIC rewards fit (`L̂`) and penalises complexity (`k·ln(n)`), so it
avoids overfitting. In practice **Gamma wins for discharge at all three
case-study sites**, and Gamma or Truncated Gaussian wins for stage.

### Step 9 — Transform to "uniform space" (the PIT)

The copula operates on variables that are uniform on [0, 1]. Transform each
observation via the **probability integral transform (PIT)**:

- **Case-study notebooks:** `u = F_Q(Q)`, `v = F_H(H)` using the *fitted
  marginal CDFs* from Step 8.
- **Batch script:** `u = rank(Q)/(n+1)`, `v = rank(H)/(n+1)` using *empirical
  ranks*. (Rank-based PIT is more robust to a mis-specified marginal — see
  Section 9 for why that distinction turned out to matter.)

### Step 10 — Fit the copula and select the family

Fit each of Gaussian, (Student-t), Clayton, Frank, Gumbel to the `(u, v)`
pairs by maximum likelihood. Score each by BIC (with the correct parameter
count: Gaussian and the Archimedean families have 1 parameter, Student-t has
2). **Pick the lowest BIC.**

- Little Sioux (06606600): **Gumbel** wins
- Des Moines (05481650): **Gumbel** wins
- Brazos (08096500): **Gumbel** wins (`n = 199`, BIC ≈ −267). *(Updated —
  see the correction note at the end of Section 6. Brazos previously showed
  Frank winning at `n = 200`, BIC ≈ −386, but that result depended on an
  undocumented `MAX_DISCHARGE_THRESHOLD = 900 m³/s` cap and an unjustified
  `START_YEAR = 1940` pre-filter in the notebook, both since removed.)*

The batch script additionally has a `GAUSSIAN_OVERRIDE` list — 5 of the 12
screening sites are *forced* to use the Gaussian copula regardless of BIC,
because their tail-dependence copula fits were numerically unstable on the
smaller/noisier screening samples. The three case-study sites are **not** on
that list — their family is chosen freely by BIC.

### Step 11 — Build the conditional distribution `f(H | Q)`

For a query discharge `q`:

```
f(h | q) = c( F_Q(q), F_H(h) ) · f_H(h)
```

- `c(·,·)` is the fitted copula **density**
- `f_H(h)` is the fitted stage marginal **density**
- Evaluate on a fine grid of `h` values, then normalise so it integrates to 1.

### Step 12 — Extract the probabilistic rating curve

Sweep `q` across a grid spanning the observed high-flow range. At each `q`,
take the **5th, 25th, 50th, 75th, and 95th percentiles** of `f(H | q)`. Plot:

- **P50** = the "most probable" rating curve (the probabilistic analogue of
  the deterministic curve)
- **P25–P75 band** = 50% predictive interval
- **P05–P95 band** = 90% predictive interval

That shaded, fanning band *is* the stochastic rating curve. It is the paper's
central object.

---

## 6. Part III — The three case-study sites and how the model is scored

| Site | River | Copula | High-flow `n` | Notes |
|---|---|---|---|---|
| **06606600** | Little Sioux River at Correctionville, IA | Gumbel | 221 | unregulated |
| **05481650** | Des Moines River near Saylorville, IA | Gumbel | 217 | just below Saylorville Dam (regulated) |
| **08096500** | Brazos River at Waco, TX | Gumbel | 199 | urbanised, channelised |

### Performance metrics (all computed in-sample)

Three numbers summarise how good the probabilistic curve is. They are
**complementary** — a good model needs all three.

1. **NSE (Nash–Sutcliffe Efficiency)** — accuracy of the *point* prediction.
   Compares the **median (P50)** prediction to the observations:

   ```
   NSE = 1 − Σ(H_obs − H_P50)² / Σ(H_obs − mean(H_obs))²
   ```

   NSE = 1 is perfect; NSE = 0 means "no better than predicting the mean".
   All three sites: **NSE ≈ 0.80–0.91**. (NSE is mathematically identical to
   R² here.) NSE says *nothing* about the uncertainty band — only the centre
   line.

2. **95% coverage** — is the uncertainty band *honest*? The fraction of
   observations that actually fall inside the predicted **[P2.5, P97.5]**
   interval:

   ```
   Coverage = (1/n) · Σ  1[ H_P2.5 ≤ H_obs ≤ H_P97.5 ]
   ```

   A well-calibrated model gives coverage ≈ 0.95. Under 0.95 → band too
   narrow (overconfident). Over 0.95 → band too wide (underconfident).

3. **95% spread (sharpness)** — how *tight* is the band? The mean width of the
   [P2.5, P97.5] interval, in meters:

   ```
   Spread = (1/n) · Σ ( H_P97.5 − H_P2.5 )
   ```

   Smaller is better **only if coverage is still ≈ 0.95** — otherwise you
   could "win" on spread with a uselessly narrow interval. Coverage and
   spread must always be read as a pair.

**Case-study values** (`SUMMARY_gpr_vs_copula_metrics.csv`; Brazos row below
is the corrected in-repo value — the CSV file itself still holds the
pre-correction number, see the note below):

| Site | Copula coverage | Copula spread (m) | Copula NSE |
|---|---|---|---|
| 06606600 | 95.5% | 2.20 | 0.812 |
| 05481650 | 99.1% | 1.84 | 0.812 |
| 08096500 | 94.0% | 1.73 | 0.928 |

> **Correction (pipeline fix, see also Section 5 Step 10 above):** the
> 08096500 (Brazos) notebook previously applied an undocumented
> `MAX_DISCHARGE_THRESHOLD = 900 m³/s` discharge cap and an unjustified
> `START_YEAR = 1940` pre-filter before selecting its high-flow subset. Both
> have been removed from `10August8096500_ipynb.ipynb` (no site now applies a
> discharge cap, and the physical-plausibility filter is unified across all
> three sites to `Q>0, H>0, H<20 m`, matching Step 3 above). Removing the cap
> lets genuinely large historical floods back into the high-flow subset
> (discharge range widens from 75–895 m³/s to 87–2050 m³/s), which flips the
> BIC-selected copula family from **Frank to Gumbel** — the physically
> expected upper-tail-dependence family, and the same family the three sites
> now share. NSE improves (0.908→0.928), spread narrows (1.94→1.73 m), and
> coverage drops marginally but stays near nominal (94.5%→94.0%). This is the
> same Frank→Gumbel flip previously found via a completely different route in
> Section 9 (semiparametric margins) — two independent fixes now agree that
> Frank was an artifact of the truncated/capped Brazos high-flow tail, not
> the genuine dependence structure.
>
> **Not yet propagated:** `SUMMARY_gpr_vs_copula_metrics.csv`,
> `SUMMARY_copula_asymmetry.csv`, the Section 7 GPR/CRPS comparison, and the
> Section 9 `MarginalFix_8096500.ipynb` experiment were all built against the
> old (capped) Brazos data and have **not** been re-run against this fix.
> Their Brazos-related numbers should be treated as stale until those
> notebooks are re-executed. The Little Sioux and Des Moines rows above are
> confirmed unaffected by this fix.

---

## 7. Part IV — Comparison against Gaussian Process Regression (GPR)

**Goal:** show the copula is doing something a standard machine-learning
regressor cannot.

**Code:** `GPR_cells_to_paste.ipynb` (the canonical copy of the added cells);
results pooled by `scripts/make_summary_figures.py` into
`SUMMARY_gpr_vs_copula_metrics.csv`. Reproduction steps in
`REPRODUCE_GPR_RESULTS.md`.

### The two GPR baselines

1. **Standard (homoscedastic) GPR** — an RBF kernel + a white-noise term.
   Assumes the scatter around the trend is **constant** in size and
   **Gaussian** (symmetric).
2. **Heteroscedastic GP** — a second GP is fitted to model how the noise
   *variance* changes with discharge (using 5-fold out-of-sample residuals to
   avoid an optimistic feedback loop), plus a post-hoc scale calibration so
   its 95% coverage hits exactly 95%. This relaxes the "constant noise"
   assumption but **keeps the symmetric-Gaussian assumption**.

### Scoring

Same in-sample protocol as Section 6, plus one extra metric:

- **CRPS (Continuous Ranked Probability Score)** — a *proper scoring rule*
  that rewards a predictive distribution for being both well-calibrated *and*
  sharp, in a single number. Lower is better. Closed form for Gaussians
  (Gneiting & Raftery 2007); numerical integration for the copula's arbitrary
  PDF.

### The aggregate result (honest version)

On CRPS and coverage, the **GPR baselines slightly edge the copula** at all
three sites:

| Site | Copula CRPS | GPR-std CRPS | GPR-het CRPS |
|---|---|---|---|
| 06606600 | 0.326 | 0.297 | 0.300 |
| 05481650 | 0.274 | 0.264 | 0.260 |
| 08096500 | 0.245 | 0.213 | 0.213 |

So the copula is **not** the more accurate model by aggregate calibration
scores, as fitted here. Section 9 shows part of this gap is a fixable
modelling artefact.

### The structural result (the robust point)

A Gaussian predictive distribution is **symmetric by construction**. For *any*
GPR, with *any* kernel and *any* tuning:

```
(P95 − P50) / (P50 − P05)  =  1.000   exactly
conditional skewness        =  0.000   exactly
```

The copula's conditional distribution is free to be skewed. Measured
(`SUMMARY_copula_asymmetry.csv`):

| Site | asymmetry ratio at **low** Q | at **high** Q | skew at low Q | skew at high Q |
|---|---|---|---|---|
| 06606600 | 1.58 | 0.81 | +1.00 | −0.47 |
| 05481650 | 1.27 | 0.79 | +0.52 | −0.58 |
| 08096500 | 1.66 | 0.63 | +1.10 | −0.67 |

Read this as: at **low discharge** the upper tail of `f(H|Q)` is longer
(stage is more likely to jump *up* than *down* relative to the median); at
**high discharge** the lower tail is longer, and the **skew reverses sign**.
No symmetric model can represent either the asymmetry or its reversal. This
is the structural justification for using a copula, and it does not depend on
how the aggregate scores come out.

---

## 8. Part V — A physical mechanism and a decision-relevant metric

**Code:** `scripts/analysis_hysteresis_and_loss.py`. Needs the continuous
daily discharge record, fetched separately by `scripts/fetch_daily_discharge.py`
into `daily_discharge_<site>.csv`.

### 8.1 Hysteresis as the mechanism (Part A)

The skew reversal in Section 7 is a *statistical* observation. Loop rating
(hysteresis) is the standard *hydraulic* explanation: on a flood's rising
limb the water-surface slope is steeper → more conveyance → **lower stage at
a given discharge**; on the falling limb, the reverse. If the high-flow
measurements are a **mixture** of rising-limb points (shifted low) and
falling-limb points (shifted high), then `f(H|Q)` is a mixture of two offset
sub-populations — which is skewed, and un-representable by one Gaussian.

The test (`SUMMARY_hysteresis.csv`):

1. Label each field measurement **rising / falling / steady** using the
   *continuous daily record* around that date. (The ~40-day-spaced field
   visits themselves cannot tell you the limb — a flood rises and falls in
   days.)
2. Test whether stage residuals differ by limb in the hysteresis-predicted
   direction (Mann–Whitney U).
3. Check whether the rising/falling mix shifts with discharge (the candidate
   driver of the skew reversal).

**Status: suggestive, not confirmed.** The predicted direction holds at 2 of
3 sites (Des Moines, Brazos) but not Little Sioux, and none of the
differences are statistically significant at these sample sizes. Report it as
a plausible mechanism, not a proven one.

### 8.2 Asymmetric loss: what symmetry costs a decision-maker (Part B)

In flood design, **under-predicting stage is worse than over-predicting** — a
missed evacuation versus an unnecessary one. Under a linear asymmetric
("lin-lin" / quantile) loss with cost ratio `r = cost_under / cost_over`, the
loss-minimising prediction is **not the median** — it is the predictive
**quantile at level `τ* = r / (1 + r)`**.

Because the copula's `f(H|Q)` is skewed and the Gaussian's is not, the two
models recommend **different design stages at the same `r`**
(`SUMMARY_design_stage_gap.csv`). The gap grows with `r` and is largest at
Brazos: **≈ 0.26–0.31 m** at `r = 20`. Quantile loss is a proper scoring rule
for quantiles, so this is a fair comparison, not a metric picked to flatter
one model.

(`SUMMARY_asymmetric_loss.csv` also scores the *realised* mean loss of each
method against the observed stages. As fitted here, the copula's mean loss is
slightly *higher* than GPR's — consistent with Section 7's aggregate result,
and again partly addressed by Section 9.)

---

## 9. Side experiment — does the marginal specification explain the copula's underperformance?

**Code:** `MarginalFix_8096500.ipynb`. Full write-up:
`MARGINAL_FIX_RESULTS.md`. Run on **Brazos (08096500) only**, because it had
the largest copula-vs-GPR deficit and therefore the most headroom to test.

**Diagnosis:** the culprit was the **discharge marginal**, not the stage
marginal or the copula. The fitted parametric Gamma for discharge
over-extended its upper tail (fitted out to ~2413 m³/s when the data max is
~895 m³/s), so high discharges were mapped onto wrong `u` values, **mis-locating**
the conditional distribution at exactly the high flows that matter.

**Fix (standard copula practice):** replace only the margins —

- fit the copula on **rank pseudo-observations** `r_i/(n+1)` (uniform by
  construction, immune to marginal misspecification), and
- use **kernel density estimates** for `f_H`, `F_Q`, `F_H` instead of assumed
  parametric families.

**Result:**

- CRPS **−6.9%**; asymmetric loss at `r = 10` **−29.7%**, at `r = 20`
  **−35.1%**.
- The copula-vs-GPR gap at `r = 20` falls from **58% worse to 3% worse**.
- **Side effect:** on rank pseudo-observations the BIC-selected family flips
  **Frank → Gumbel**. Frank has *no* upper-tail dependence; Gumbel does, and
  is the physically expected family for floods. So the parametric margins
  were corrupting the *dependence conclusion* too, not just the spread.

**Honest limitations:** coverage now over-covers (94.5% → 98.0%, likely KDE
over-smoothing); GPR still edges it slightly on CRPS; **one site only** — this
does not yet prove marginal specification is the general culprit.

---

## 10. Part VI — Flood inundation mapping (the "so what")

This is where stage uncertainty becomes a map of wet land. The flood model is
**OWP HAND-FIM**, run through the `fimserve` Python package (Colab).

### 10.1 How HAND-FIM works

**HAND = Height Above Nearest Drainage.** For every terrain cell, precompute
the vertical distance between that cell and the nearest stream cell it drains
to. Then, given a **water-surface height** `h` for a reach, every cell whose
HAND value is `< h` is flooded (to depth `h − HAND`). So HAND-FIM needs
exactly one input per reach: a stage.

Operationally, that stage comes from a **Synthetic Rating Curve (SRC)** —
Manning's equation applied to the terrain-derived channel cross-section
geometry, giving one stage per discharge. This is a purely deterministic,
geometry-based estimate.

### 10.2 Part 1 — Probabilistic flood-extent maps (2 natural sites)

**Code:** `FIM_2sites_percentile_overlay.ipynb`, built by
`scripts/build_fim_2sites_notebook.py` from
`scripts/extract_2site_copula_percentiles.py`. Full log:
`FIM_2sites_NOTES.md`.

**Sites** (chosen for being genuinely unregulated *and* having the widest
copula predictive spread — a narrow band gives near-identical maps):

| Site | River | Copula | Chosen `Q` (m³/s) | Stage P05 → P95 | Spread |
|---|---|---|---|---|---|
| 05597000 | Big Muddy River, Plumfield IL | Gumbel | 149.6 | 4.46 → 8.00 m | 3.54 m (55% of median) |
| 03301500 | Rolling Fork, Boston KY | Gaussian | 330.0 | 8.18 → 11.58 m | 3.40 m (34% of median) |

**Procedure, per site:**

1. From the cached copula fit (`scripts/_copula_results_cache.pkl`), find the
   discharge where the P95 − P05 stage spread is widest.
2. Take the 5 percentile stages there (P05, P25, P50, P75, P95).
3. Convert each stage to an equivalent discharge using **that reach's HAND
   SRC** (from HAND's `hydrotable.csv`). *(This step hit two real bugs — a
   single reach can map to several HAND sub-catchments, and HAND-sub-catchment
   IDs are not unique across the model's "branches" — both fixed by a spatial
   point-in-polygon lookup against the gauge coordinates. See
   `FIM_2sites_NOTES.md`.)*
4. Run each discharge through HAND-FIM → 5 inundation rasters.
5. **Overlay them as nested extents.** Because a higher stage floods
   everything a lower stage floods plus more, `P05 ⊂ P25 ⊂ P50 ⊂ P75 ⊂ P95`.
   Drawn on one map with a graded colour ramp, this shows a **core** flooded
   under nearly every plausible stage and an **outer edge** flooded only under
   the most extreme stage.

### 10.3 Part 2 — Where does the deterministic SRC fall in the range? (3 case-study sites)

**Figures:** `case_study_figs/*_FIM_final.png` (the maps),
`case_study_figs/{GUMBEL,FRANK}-*-SRC-Added-2.png` (the rating curves).

For each of the three original case-study sites, generate flood extents at
**P05**, **P95**, and the **deterministic SRC** stage, and locate the SRC
within the copula's range:

| Site | `Q` (m³/s) | P05 | P25 | P50 | P75 | P95 | SRC | SRC's percentile |
|---|---|---|---|---|---|---|---|---|
| Little Sioux 06606600 | 400 | 5.02 | 5.80 | 6.22 | 6.61 | 7.23 | 5.66 | **≈ 21st** (between P05–P25) |
| Des Moines 05481650 | 600 | 4.47 | 5.02 | 5.31 | 5.58 | 5.99 | 5.17 | **≈ 38th** (between P25–P50) |
| Brazos 08096500 | 600 | 4.36 | 5.06 | 5.56 | 6.08 | 6.70 | 5.29 | **≈ 37th** (between P25–P50) |

**Findings:**

1. The SRC falls **below the copula median at all three sites** (≈ 21st–38th
   percentile). This is not a claim that the SRC is "unreliable" — a single
   hydraulic estimate is, by definition, one point in a range — but its
   position within that range **is not knowable from the deterministic
   estimate alone**, and it varied by site (closer to the low end at
   unregulated Little Sioux than at regulated Des Moines / urban Brazos).
   With three sites this is an observation, not a generalisation.
2. **Separately:** at Brazos, the largest stage spread of the three (2.34 m)
   produced only a *small* change in flood extent, because the confined
   floodplain limits how far the water can spread. So local terrain shapes
   both where the SRC sits *and* how much a given stage spread matters on the
   ground.
3. **Methodological caveat:** HAND assigns inundation by elevation threshold
   alone, with no check that a flooded cell is hydraulically connected to the
   channel. Disconnected wet patches over low-lying fields (visible at Des
   Moines) should be read with caution, not as confirmed flood risk.

### 10.4 Skill assessment against a satellite benchmark (site 06606600 only)

**Code:** `FIMin3steps_6606600.ipynb` (generates the maps) →
`FIMeval_6606600.ipynb` (scores them). Run order in `FIM_RUN_ORDER.md`.

The 5 copula-percentile inundation maps for the June 2024 Little Sioux flood
are compared against a **PlanetScope satellite** flood map (the FIMbench
Tier-2 benchmark), scoring CSI / POD / FAR / F1 / MCC per percentile, with
scoring restricted to an AOI buffered around the target reach's flowline. The
question it answers: **which percentile of the copula's predictive
distribution best reproduces the observed flood extent, and does the observed
extent fall inside the P05–P95 band at all?**

---

## 11. Glossary

| Term | Meaning |
|---|---|
| **Stage (`H`)** | water-surface height above a datum, in m. Cheap to measure continuously. |
| **Discharge (`Q`)** | volumetric flow rate, in m³/s. Expensive to measure. |
| **Rating curve** | the function converting stage to discharge at a gauge; standard form `Q = C(H−H0)^n`. |
| **Marginal distribution** | the distribution of one variable on its own (e.g. of `Q`, ignoring `H`). |
| **Copula** | a function that joins marginals into a joint distribution, carrying all the dependence information. |
| **PIT (probability integral transform)** | mapping a variable to [0, 1] via its CDF (or its empirical rank). |
| **Conditional distribution `f(H\|Q)`** | the distribution of stage for one fixed discharge — the paper's central object. |
| **BIC** | Bayesian Information Criterion; model-selection score balancing fit against parameter count; lower is better. |
| **NSE** | Nash–Sutcliffe Efficiency; skill of the point (median) prediction; 1 = perfect, 0 = no better than the mean. |
| **Coverage** | fraction of observations inside the predicted 95% interval; should be ≈ 0.95. |
| **Spread / sharpness** | mean width of the predicted 95% interval; smaller is better *given* good coverage. |
| **CRPS** | Continuous Ranked Probability Score; proper scoring rule combining calibration and sharpness; lower is better. |
| **Hysteresis / loop rating** | the flood-wave effect making stage lower on the rising limb and higher on the falling limb at the same discharge. |
| **Asymmetric (lin-lin / quantile) loss** | a loss where under- and over-prediction cost differently; minimised by the `τ* = r/(1+r)` quantile. |
| **GPR** | Gaussian Process Regression; the ML baseline; its predictive distribution is symmetric by construction. |
| **HAND** | Height Above Nearest Drainage; the terrain index behind the flood model. |
| **SRC (Synthetic Rating Curve)** | HAND-FIM's deterministic stage estimate from Manning's equation on terrain geometry. |
| **Bankfull discharge** | the flow that just fills the channel to the top of its banks; used as a physical "flood threshold". |
| **COMID** | NHDPlus reach identifier; links a gauge to external reach datasets. |
| **IFMHA** | the name of the ~6,323-gauge field-measurement dataset used throughout. |

---

## 12. File map — where everything lives

### Data
| File | What |
|---|---|
| `ifmha_subset_stat.csv` | the main dataset (~760 MB): paired `Q`/`H` field measurements for ~6,323 CONUS gauges |
| `Bankfull_Meanflow_CONUS.txt` | bankfull channel geometry per NHDPlus reach (Zarrabi et al. 2025) |
| `population_screening.csv` | cached output of the 6,323-site CONUS screen (reuse, don't re-run) |
| `daily_discharge_<site>.csv` | continuous daily discharge for the 3 case-study sites (for the hysteresis test) |
| `scripts/_copula_results_cache.pkl` | cached copula fits for the 12 screening sites (reuse, don't re-fit) |

### Copula model
| File | What |
|---|---|
| `10Agust6606600_ipynb.ipynb` | **canonical** per-site notebook — Little Sioux |
| `10August5481650_ipynb.ipynb` | **canonical** per-site notebook — Des Moines |
| `10August8096500_ipynb.ipynb` | **canonical** per-site notebook — Brazos |
| `backup_final_notebooks/` | untouched copies of the three above |
| `scripts/_cell_copula_v2.py` | batch copula fit for the 12 screening sites → Figure 2 |
| `scripts/_cell40.py`, `_cell42.py` | CONUS variability metric + Figure 1 map |
| `scripts/_cell_preprocessing_v2.py` | the "what QC removes per site" figure |
| `copula_analysis_<site>_cleaned.ipynb` | **do NOT use** — older pipeline, disagrees on Brazos |

### GPR comparison and downstream analyses
| File | What |
|---|---|
| `GPR_cells_to_paste.ipynb` | canonical copy of the GPR-baseline + asymmetry cells |
| `GPRcomparison_<site>.ipynb` | the executed per-site notebooks (built by `scripts/build_gpr_notebooks.py`) |
| `scripts/make_summary_figures.py` | pools per-site CSVs → `SUMMARY_gpr_vs_copula_metrics.csv`, figures |
| `scripts/analysis_hysteresis_and_loss.py` | hysteresis test + asymmetric-loss / design-stage-gap analysis |
| `scripts/fetch_daily_discharge.py` | pulls the continuous daily record needed for the limb labelling |
| `MarginalFix_8096500.ipynb` + `MARGINAL_FIX_RESULTS.md` | the semiparametric-margins experiment (Brazos only) |
| `scripts/validate_palette.py` | computational colour-blindness check for figure palettes |

### Flood inundation mapping
| File | What |
|---|---|
| `FIM_2sites_percentile_overlay.ipynb` | 5-percentile nested flood maps, Big Muddy + Rolling Fork |
| `scripts/build_fim_2sites_notebook.py`, `extract_2site_copula_percentiles.py` | build the above from cached copula fits |
| `FIM_2sites_NOTES.md` | full log incl. the two HAND sub-catchment bugs and their fixes |
| `FIMin3steps_6606600.ipynb` | generates the P05/SRC/P95 maps for Little Sioux |
| `FIMeval_6606600.ipynb` | scores them against the PlanetScope satellite benchmark |
| `FIM_RUN_ORDER.md` | what to run, in what order, for the FIM chain |
| `case_study_figs/` | all the case-study figure PNGs + the executed notebooks that made them |

### Manuscript
| File | What |
|---|---|
| `PAPER_STYLE_GUIDE.md` | **single source of truth** for fonts, figure sizes, tables, legends, colours |
| `case_study_figs/case_studies_section.tex` | draft LaTeX for the case-studies subsection |

---

## 13. Honest status of the findings (as of this write-up)

| Claim | Status |
|---|---|
| Stage-at-fixed-discharge scatter is widespread and spatially patterned across CONUS | **Solid** — unbiased 6,323-site screen |
| The copula produces a coherent, reasonably calibrated `f(H\|Q)` (coverage ≈ 0.95, NSE ≈ 0.8–0.9) at the case-study sites | **Solid** |
| The copula's `f(H\|Q)` is skewed, and the skew reverses sign with discharge | **Solid** — measured directly; structurally impossible for any GPR |
| The copula beats GPR on aggregate calibration scores (CRPS, coverage) | **False as fitted** — GPR slightly edges it at all 3 sites. *Brazos GPR/CRPS numbers pre-date the Section 6 pipeline fix (undocumented discharge cap removed) and have not been recomputed against the corrected data — treat the Brazos row as stale pending a re-run.* |
| The copula's underperformance is partly a fixable marginal-specification artefact | **Suggestive** — demonstrated at 1 site (Brazos): CRPS −7%, asymmetric loss −30–35%, and the family flips to the physically-expected Gumbel. Needs replication at the other 2 sites. *A second, independent fix (removing an undocumented discharge cap, Section 6) also flips Brazos from Frank to Gumbel — two unrelated corrections now agree the original Frank result was a data-pipeline artifact, not a genuine finding.* |
| Hysteresis is the mechanism behind the skew | **Suggestive, not confirmed** — right direction at 2 of 3 sites, none significant |
| Copula vs. Gaussian recommend materially different design stages under asymmetric loss | **Solid** — up to ~0.3 m at `r = 20`, largest at Brazos |
| A 1.5–3.5 m stage spread at one discharge produces substantially different flood extents | **Solid** — shown directly with HAND-FIM |
| The deterministic HAND-FIM SRC sits below the copula median (≈ 20th–40th percentile) | **Solid for the 3 sites shown**; not generalised beyond them |
| How much stage spread translates to *area* spread depends on local floodplain geometry | **Solid** — Brazos (big stage spread, small area change) is the clear example |
