import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import math
from scipy.stats import kendalltau, rankdata
from scipy.stats import norm, multivariate_normal
from scipy.optimize import curve_fit
from copulas.univariate import (
    GammaUnivariate, TruncatedGaussian,
    GaussianUnivariate, StudentTUnivariate
)
from copulas.bivariate import Clayton, Frank, Gumbel
try:
    from tqdm.notebook import tqdm
    _HAS_TQDM = True
except Exception:
    _HAS_TQDM = False

warnings.filterwarnings('ignore')

EPS         = 1e-12
MIN_GAP     = 3
MIN_N       = 60
N_TOPFLOW   = 360
TAIL_TRIM   = 1        # trim top X% of sparse high-flow tail before copula fit
SEED        = 42
np.random.seed(SEED)

# Sites that MUST use Gaussian copula regardless of BIC (5 of the 12
# screening sites; see PROJECT_METHODOLOGY.md Section 5, Step 10)
GAUSSIAN_OVERRIDE = {
    '06905500', '05404000', '05422000', '08330000', '03301500'
}
# Sites that use the top 75% (Q >= 25th percentile) instead of top-N (3 of
# the 12 screening sites)
TOP_75_OVERRIDE = {
    '06810000', '07258000', '03611500'
}
# ==============================================================
# HELPERS
# ==============================================================

def rating_curve_model(H, C, n, H0):
    return C * np.maximum(H - H0, 0) ** n

def predict_stage_from_discharge(Q, C, n, H0):
    return (np.maximum(np.asarray(Q, float), 1e-9) / C) ** (1.0 / n) + H0

class GaussianCopulaCompat:
    def __init__(self): self.rho = None
    @property
    def theta(self): return self.rho
    def fit(self, UV):
        tau = kendalltau(UV[:, 0], UV[:, 1]).correlation
        if tau is None or np.isnan(tau): tau = 0.0
        self.rho = float(np.sin(np.pi * tau / 2))
    def log_probability_density(self, UV):
        Z   = norm.ppf(np.clip(UV, EPS, 1 - EPS))
        r   = self.rho if self.rho is not None else 0.0
        cov = np.array([[1.0, r], [r, 1.0]])
        mv  = multivariate_normal(mean=[0.0, 0.0], cov=cov, allow_singular=True)
        lp  = mv.logpdf(Z) - norm.logpdf(Z[:, 0]) - norm.logpdf(Z[:, 1])
        return np.where(np.isfinite(lp), lp, -700.0)
    def sample(self, n):
        r   = self.rho if self.rho else 0.0
        cov = np.array([[1.0, r], [r, 1.0]])
        Z   = np.random.multivariate_normal([0, 0], cov, n)
        return norm.cdf(Z)

def fit_marginals(data):
    candidates = [
        GammaUnivariate(), TruncatedGaussian(),
        GaussianUnivariate(), StudentTUnivariate()
    ]
    best, best_bic = None, np.inf
    for m in candidates:
        try:
            m.fit(data)
            ll  = np.sum(np.log(np.maximum(m.pdf(data), 1e-300)))
            bic = 2 * np.log(len(data)) - 2 * ll
            if bic < best_bic:
                best_bic, best = bic, m
        except Exception:
            continue
    return best

def fit_copulas(UV):
    models = {
        'gaussian': GaussianCopulaCompat(),
        'gumbel':   Gumbel(),
        'frank':    Frank(),
        'clayton':  Clayton(),
    }
    scores = []
    for name, m in models.items():
        try:
            m.fit(UV)
            lp  = m.log_probability_density(UV)
            ll  = np.sum(np.where(np.isfinite(lp), lp, -700.0))
            bic = np.log(len(UV)) - 2 * ll
            scores.append({'family': name, 'BIC': bic, 'model': m})
        except Exception:
            continue
    scores.sort(key=lambda x: x['BIC'])
    return scores

def predict_conditional_pdf(q_val, ux, uy, copula, n_points=600):
    u_q    = float(np.clip(ux.cdf(np.array([q_val])), EPS, 1 - EPS).item())
    h_min  = float(uy.ppf(0.001))
    h_max  = float(uy.ppf(0.999))
    h_grid = np.linspace(h_min, h_max, n_points)
    v_grid = np.clip(uy.cdf(h_grid), EPS, 1 - EPS)
    uv     = np.column_stack([np.full(n_points, u_q), v_grid])
    lp     = copula.log_probability_density(uv)
    c_dens = np.exp(np.where(np.isfinite(lp), lp, -700.0))
    f_h    = np.maximum(uy.pdf(h_grid), 0.0)
    pdf    = np.maximum(c_dens * f_h, 0.0)
    total  = (np.trapezoid if hasattr(np, "trapezoid") else np.trapz)(pdf, h_grid)
    if total > 1e-12:
        pdf /= total
    return h_grid, pdf

def quantiles_from_pdf(h_grid, pdf, qs=(0.05, 0.25, 0.50, 0.75, 0.95)):
    cdf = np.cumsum(pdf) * (h_grid[1] - h_grid[0])
    cdf /= cdf[-1]
    return np.array([h_grid[np.searchsorted(cdf, q)] for q in qs])

# ==============================================================
# MAIN LOOP  (verbatim from notebook cell 23 — the real pipeline)
# ==============================================================
results = {}

for sn_raw in TARGET_SITES_UNIQUE:
    sn = sn_raw.zfill(8)
    print(f"\nProcessing site {sn}...")

    # --- 1. Extract raw data ---
    try:
        site_raw = ifmha_subset_stat[
            ifmha_subset_stat['site_no'] == sn
        ].copy()
        if site_raw.empty:
            site_raw = ifmha_subset_stat[
                ifmha_subset_stat['site_no'] == sn.lstrip('0')
            ].copy()
        if site_raw.empty:
            print(f"  Site {sn} not found — skipping")
            continue
    except Exception as e:
        print(f"  Error extracting {sn}: {e}")
        continue

    # --- 2. Daily aggregation + 3-day gap filter ---
    site_raw['measurement_dt'] = pd.to_datetime(
        site_raw['measurement_dt'], errors='coerce'
    )
    site_raw = site_raw.dropna(
        subset=['measurement_dt', 'discharge_m3s', 'stage_m']
    ).copy()
    site_raw['date'] = site_raw['measurement_dt'].dt.floor('D')

    daily = (
        site_raw.groupby(['site_no', 'date'], as_index=False)
        .agg(discharge_m3s=('discharge_m3s', 'mean'),
             stage_m=('stage_m', 'mean'),
             COMID=('COMID', 'first'))
        .sort_values('date')
        .reset_index(drop=True)
    )

    kept, last_date = [], None
    for _, row in daily.iterrows():
        if last_date is None or (row['date'] - last_date).days >= MIN_GAP:
            kept.append(row)
            last_date = row['date']
    df_s = pd.DataFrame(kept).reset_index(drop=True)
    df_s = df_s[
        (df_s['discharge_m3s'] > 0) &
        (df_s['stage_m'] > 0) &
        (df_s['stage_m'] < 20)
    ].copy()

    # ALL observed data for plotting (full record)
    Q_all_plot = df_s['discharge_m3s'].values
    H_all_plot = df_s['stage_m'].values

    if len(df_s) < MIN_N:
        print(f"  Too few observations ({len(df_s)}) — skipping")
        continue

    # --- 3. Fit rating curve ---
    H_all = df_s['stage_m'].values
    Q_all = df_s['discharge_m3s'].values
    try:
        H0g = H_all.min() * 0.9
        Cg  = Q_all.mean() / max((H_all.mean() - H0g) ** 2, 1e-6)
        (C_fit, n_fit, H0_fit), _ = curve_fit(
            rating_curve_model, H_all, Q_all,
            p0=[Cg, 2.0, H0g],
            bounds=([0, 0.1, H_all.min() - 5], [np.inf, 5, H_all.min() + 0.5]),
            maxfev=8000
        )
    except Exception as e:
        print(f"  RC fit failed: {e} — skipping")
        continue

    # --- 4. High-flow subset (top-N or top-75%) ---
    if sn in TOP_75_OVERRIDE:
        threshold = float(np.percentile(df_s['discharge_m3s'].values, 25))
        hf = df_s[df_s['discharge_m3s'] >= threshold].copy()
        print(f"  Top-75% subset: {len(hf)} pts (Q >= {threshold:.1f})")
    else:
        threshold = df_s['discharge_m3s'].nlargest(N_TOPFLOW).iloc[-1]
        hf = df_s[df_s['discharge_m3s'] >= threshold].copy()
        print(f"  Top-{N_TOPFLOW} subset: {len(hf)} pts (Q >= {threshold:.1f})")

    # --- 5. Outlier removal (3-sigma on stage residuals) ---
    pred_H = predict_stage_from_discharge(
        hf['discharge_m3s'].values, C_fit, n_fit, H0_fit
    )
    resid = np.abs(hf['stage_m'].values - pred_H)
    thr   = resid.mean() + 3 * resid.std()
    hf    = hf[resid <= thr].copy()
    print(f"  After outlier removal: {len(hf)} pts")

    # --- 6. Trim sparse high-flow tail (top TAIL_TRIM% of Q) ---
    q_cap_trim = np.percentile(hf['discharge_m3s'].values, 100 - TAIL_TRIM)
    hf_clean   = hf[hf['discharge_m3s'] <= q_cap_trim].copy()
    print(f"  After tail trim (top {TAIL_TRIM}%): {len(hf_clean)} pts "
          f"(Q <= {q_cap_trim:.1f})")

    if len(hf_clean) < MIN_N:
        print(f"  Too few after trimming — skipping")
        continue

    Q_hf = hf_clean['discharge_m3s'].values
    H_hf = hf_clean['stage_m'].values

    # --- 7. Fit marginals and select best copula (respecting GAUSSIAN_OVERRIDE) ---
    try:
        ux = fit_marginals(Q_hf)
        uy = fit_marginals(H_hf)
        if ux is None or uy is None:
            print("  Marginal fit failed — skipping")
            continue

        u  = rankdata(Q_hf) / (len(Q_hf) + 1)
        v  = rankdata(H_hf) / (len(H_hf) + 1)
        UV = np.column_stack([u, v])

        if sn in GAUSSIAN_OVERRIDE:
            best_model = GaussianCopulaCompat()
            best_model.fit(UV)
            best_name  = 'gaussian (forced)'
            print(f"  -> Gaussian forced (rho = {best_model.rho:.3f})")
        else:
            scores = fit_copulas(UV)
            if not scores:
                print("  Copula fit failed — skipping")
                continue
            best_model = scores[0]['model']
            best_name  = scores[0]['family']
            print(f"  Best copula by BIC: {best_name} (BIC = {scores[0]['BIC']:.1f})")
    except Exception as e:
        print(f"  Modelling error: {e} — skipping")
        continue

    # --- 8. Prediction bands (reduced extrapolation pad) ---
    q_min  = Q_hf.min()
    q_max  = Q_hf.max()
    q_pad  = (q_max - q_min) * 0.10
    q_grid = np.linspace(q_min, q_max + q_pad, 80)

    preds = np.full((len(q_grid), 5), np.nan)
    for i, qv in enumerate(q_grid):
        try:
            h_g, pdf = predict_conditional_pdf(qv, ux, uy, best_model)
            preds[i] = quantiles_from_pdf(h_g, pdf)
        except Exception:
            continue

    H_rc  = np.linspace(H_hf.min(), H_hf.max() * 1.1, 200)
    Q_rc  = rating_curve_model(H_rc, C_fit, n_fit, H0_fit)

    lat_row = pop.loc[pop["site_no"] == sn.lstrip("0"), LAT]
    lat = float(lat_row.iloc[0]) if len(lat_row) else np.nan

    results[sn] = {
        'Q_all':   Q_all_plot,
        'H_all':   H_all_plot,
        'Q_hf':    Q_hf,
        'H_hf':    H_hf,
        'q_grid':  q_grid,
        'preds':   preds,
        'Q_rc':    Q_rc,
        'H_rc':    H_rc,
        'copula':  best_name,
        'n':       len(Q_hf),
        'lat':     lat,
    }
    print(f"  Done — copula: {best_name}, N={len(Q_hf)}")

print(f"\nSuccessfully processed {len(results)} sites.")

import pickle
with open("data/processed/screening_cache/copula_results_cache.pkl", "wb") as _f:
    pickle.dump(results, _f)
print("Cached results -> data/processed/screening_cache/copula_results_cache.pkl")

# ==============================================================
# PLOT — rebuilt per PAPER_STYLE_GUIDE.md to match Fig. 2 / the
# preprocessing figure: canonical 12/10/11pt rcParams, 4x3 grid,
# "N. Site XXXXXXXX" titles numbered north -> south (same lat sort
# as Fig. 2 and the preprocessing figure, so site N is site N in all
# three), bottom shared legend with the guide's standard style params.
# ==============================================================
plt.rcParams.update({
    'font.family':        'serif',
    'font.serif':         ['Times New Roman', 'DejaVu Serif'],

    'font.size':          12,
    'axes.titlesize':     12,
    'axes.labelsize':     12,
    'xtick.labelsize':    10,
    'ytick.labelsize':    10,
    'legend.fontsize':    11,   # guide §5

    'xtick.major.width':  0.8,
    'ytick.major.width':  0.8,
    'xtick.major.size':   4.0,
    'ytick.major.size':   4.0,
    'xtick.direction':    'in',
    'ytick.direction':    'in',
    'xtick.top':          True,
    'ytick.right':        True,

    'axes.grid':          True,
    'grid.color':         '#D5D8DC',
    'grid.linestyle':     '-',
    'grid.linewidth':     0.4,
    'grid.alpha':         0.5,

    'axes.linewidth':     0.5,
    'axes.edgecolor':     '#555555',
    'axes.spines.top':    True,
    'axes.spines.right':  True,

    'figure.dpi':         150,
    'savefig.dpi':        600,
    'figure.facecolor':   'white',
    'axes.facecolor':     'white',
})

# number sites north -> south by the same latitude sort as Fig. 2 / the
# preprocessing figure, so site N here is site N everywhere else
site_keys = list(results.keys())
site_keys.sort(key=lambda sn: -results[sn]['lat'] if np.isfinite(results[sn]['lat']) else 0)
site_num = {sn: i + 1 for i, sn in enumerate(site_keys)}

N_COLS     = 4
FIG_WIDTH  = 7.0
ROW_HEIGHT = 1.7           # matches Fig. 2 / the preprocessing figure exactly
n_rows     = math.ceil(len(site_keys) / N_COLS)

fig, axes = plt.subplots(
    nrows=n_rows, ncols=N_COLS,
    figsize=(FIG_WIDTH, n_rows * ROW_HEIGHT)
)
axes_flat = np.atleast_1d(axes).flatten()

from matplotlib.lines import Line2D
from matplotlib.patches import Patch

for idx, sn in enumerate(site_keys):
    ax  = axes_flat[idx]
    res = results[sn]

    # clip q_grid to where the band is still varying (avoid a long flat
    # extrapolated tail dominating the panel)
    band_width = res['preds'][:, 4] - res['preds'][:, 0]
    dw         = np.abs(np.diff(band_width))
    last_valid = np.where(dw > 1e-3)[0]
    cut = (last_valid[-1] + 2) if len(last_valid) > 0 else len(res['q_grid'])
    cut = min(cut, len(res['q_grid']))
    q_grid_c = res['q_grid'][:cut]
    preds_c  = res['preds'][:cut]
    q_max_plot = float(q_grid_c[-1])

    ax.scatter(res['Q_all'], res['H_all'],
               s=3, alpha=0.25, color='#888888',
               edgecolors='none', zorder=1, rasterized=True)

    ax.fill_between(q_grid_c, preds_c[:, 0], preds_c[:, 4],
                     color='#FADADD', alpha=0.80, zorder=2)
    ax.fill_between(q_grid_c, preds_c[:, 1], preds_c[:, 3],
                     color='#F4A79D', alpha=0.75, zorder=3)

    mask_rc = res['Q_rc'] <= q_max_plot
    ax.plot(res['Q_rc'][mask_rc], res['H_rc'][mask_rc],
            color='#2E7D32', lw=0.9, ls='--', zorder=4)

    ax.scatter(res['Q_hf'], res['H_hf'],
               s=7, alpha=0.85, color='#004080',
               edgecolors='w', linewidths=0.2, zorder=5, rasterized=True)

    # drawn last / highest zorder so it isn't hidden under the (often nearly
    # coincident) deterministic rating curve or the high-flow point cloud
    ax.plot(q_grid_c, preds_c[:, 2], color='#C0392B', lw=1.1, zorder=6)

    ax.set_title(f"{site_num[sn]}. Site {sn}", pad=2, fontsize=12)
    ax.set_xlim(0, q_max_plot * 1.02)
    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=3, prune='lower'))
    ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=3, prune='lower'))
    ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda y, _: f'{y:g}' if y >= 0 else ''))
    ax.tick_params(labelsize=10, length=2.5, width=0.6, pad=1.5)

for i in range(len(site_keys), len(axes_flat)):
    axes_flat[i].axis('off')

legend_items = [
    Line2D([], [], marker='o', ls='none', ms=3.6, mfc='#888888', mec='none',
           label='All observed data'),
    Line2D([], [], marker='o', ls='none', ms=5.0, mfc='#004080', mec='w', mew=0.4,
           label='High-flow data (used for copula fit)'),
    Line2D([], [], color='#C0392B', lw=1.4, ls='-', label='Copula median (P50)'),
    Line2D([], [], color='#2E7D32', lw=1.4, ls='--', label='Deterministic rating curve'),
    Patch(facecolor='#F4A79D', alpha=0.75, label='50% predictive interval (P25–P75)'),
    Patch(facecolor='#FADADD', alpha=0.80, label='90% predictive interval (P5–P95)'),
]
fig.legend(handles=legend_items,
           loc='lower center', ncol=2,
           bbox_to_anchor=(0.52, 0.005), bbox_transform=fig.transFigure,
           frameon=True, framealpha=0.92, edgecolor='#bbbbbb', fontsize=11,
           borderpad=0.6, handletextpad=0.6, columnspacing=1.4)

fig.supxlabel(r'Discharge, $Q$ (m$^3$ s$^{-1}$)', fontsize=12, y=0.195, x=0.42)
fig.supylabel(r'Stage, $H$ (m)',                   fontsize=12, x=0.01)

plt.tight_layout(pad=0.3, h_pad=0.5, w_pad=0.3, rect=[0.02, 0.225, 1, 1])

PNG_OUT = 'figures/fig-03_probabilistic_rating_curves_gallery.png'
PDF_OUT = 'figures/fig-03_probabilistic_rating_curves_gallery.pdf'
plt.savefig(PNG_OUT, dpi=600, bbox_inches='tight', facecolor='white')
plt.savefig(PDF_OUT, dpi=600, bbox_inches='tight', facecolor='white')

import os
for _f in (PNG_OUT, PDF_OUT):
    print(f"Saved {_f}  ({os.path.getsize(_f)/1e6:.1f} MB)")
