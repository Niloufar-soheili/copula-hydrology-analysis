"""
Builds two publication-ready composite figures for the case-studies section.

Fig A (site_summary_panel.png): merges Table 1's catchment attributes with a plain
box-plot view of the discharge/stage distributions — replaces Table 1 + the
avg/min/max columns with one self-contained figure. (Originally a raincloud-style
half-violin + boxplot; simplified to box plots only after review -- the KDE clouds
didn't read well for a Journal of Hydrology figure.)

Fig B (rating_curve_qq_grid.png): a true 3x3 composite (not glued images) — one row per
site, columns = [rating curve, discharge Q-Q, stage Q-Q]. Styled and sized to match the
paper's existing 12-site preprocessing grid figure (fig_selected_sites_clean.png):
same rcParams (serif/Times, light solid grid, hidden top/right spines, inward ticks,
sparse MaxNLocator ticks), same per-panel size convention, and a single figure-level
legend in the same position/style.
"""
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.gridspec import GridSpec
from copulas.univariate import GammaUnivariate, TruncatedGaussian, GaussianUnivariate, StudentTUnivariate

# Run this script from the REPO ROOT.
DATA_DIR = "data/processed/case_study_sites"   # per-site inputs, under DATA_DIR/<site>/...
OUT_DIR = "figures"                             # sfig-01 / sfig-02 outputs

BLUE = "#1565C0"
RED = "#E53935"
GRID_GRAY = "#bbbbbb"

# rcParams matched to fig_selected_sites_clean.png (the 12-site preprocessing grid)
plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times New Roman", "DejaVu Serif"],
    "font.size":           16,
    "axes.titlesize":      15,
    "axes.labelsize":      17,
    "xtick.labelsize":     15,
    "ytick.labelsize":     15,
    "legend.fontsize":     14,
    "xtick.major.width":   1.2,
    "ytick.major.width":   1.2,
    "xtick.direction":     "in",
    "ytick.direction":     "in",
    "xtick.major.size":    6,
    "ytick.major.size":    6,
    "xtick.top":           True,
    "ytick.right":         True,
    "figure.dpi":          150,
    "savefig.dpi":         300,
    "savefig.bbox":        "tight",
    "figure.facecolor":    "white",
    "axes.facecolor":      "white",
    "axes.grid":           True,
    "grid.color":          "#D5D8DC",
    "grid.linestyle":      "-",
    "grid.linewidth":      0.6,
    "grid.alpha":          0.6,
    "axes.linewidth":      0.5,
    "axes.edgecolor":      "#BFC9CA",
    "axes.spines.top":     False,
    "axes.spines.right":   False,
})

DIST_MAP = {
    "GammaUnivariate": GammaUnivariate,
    "TruncatedGaussian": TruncatedGaussian,
    "GaussianUnivariate": GaussianUnivariate,
    "StudentTUnivariate": StudentTUnivariate,
}

SITE_ORDER = ["6606600", "5481650", "8096500"]

SITE_META = {
    "6606600": dict(river="Little Sioux River", place="at Correctionville", st="IA",
                     usgs="06606600", order=6, area="6,475.0"),
    "5481650": dict(river="Des Moines River", place="near Saylorville", st="IA",
                     usgs="05481650", order=6, area="15,128.2"),
    "8096500": dict(river="Brazos River", place="at Waco", st="TX",
                     usgs="08096500", order=7, area="76,557.8"),
}

# one accent color per site, used consistently across its row in Fig A
SITE_COLOR = {
    "6606600": "#1565C0",  # blue
    "5481650": "#00838F",  # teal
    "8096500": "#6A1B9A",  # purple
}


def rating_curve_model(H, C, n, H0):
    return C * np.clip(H - H0, 1e-9, None) ** n


# ======================================================================================
# Fig A — Site summary panel: catchment attributes + discharge/stage box plots.
# Simplified per review: dropped the raincloud-style KDE clouds (looked out of place for
# a Journal of Hydrology figure) -- clean box plots only, same information otherwise.
# Re-applied to the paper's canonical style (PAPER_STYLE_GUIDE.md ss3/ss4/ss5): 7.0in
# canonical width, 12pt title/labels, 10pt ticks, same grid/spine/tick convention as
# Fig. 1/Fig. 2 -- this panel had still been on the old oversized/hidden-spine style.
plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times New Roman", "DejaVu Serif"],

    "font.size":           12,
    "axes.titlesize":      12,
    "axes.labelsize":      12,
    "xtick.labelsize":     10,
    "ytick.labelsize":     10,
    "legend.fontsize":     11,

    "xtick.major.width":   0.8,
    "ytick.major.width":   0.8,
    "xtick.major.size":    4.0,
    "ytick.major.size":    4.0,
    "xtick.direction":     "in",
    "ytick.direction":     "in",
    "xtick.top":           True,
    "ytick.right":         True,

    "axes.grid":           True,
    "grid.color":          "#D5D8DC",
    "grid.linestyle":      "-",
    "grid.linewidth":      0.4,
    "grid.alpha":          0.5,

    "axes.linewidth":      0.5,
    "axes.edgecolor":      "#555555",
    "axes.spines.top":     True,
    "axes.spines.right":   True,

    "figure.dpi":          150,
    "savefig.dpi":         600,
    "savefig.bbox":        "tight",
    "figure.facecolor":    "white",
    "axes.facecolor":      "white",
})

BOX_BLUE = "#004080"   # same accent color used in the paper's other site-grid figures

FIG_WIDTH = 7.0
ROW_HEIGHT = 1.05
fig, (ax_d, ax_s) = plt.subplots(
    1, 2, figsize=(FIG_WIDTH, len(SITE_ORDER) * ROW_HEIGHT + 0.5))

y_positions = np.arange(len(SITE_ORDER))[::-1]  # first site on top

for ax, var, log, xlim, xlabel, panel_letter in [
    (ax_d, "discharge_m3s", True, (1e-1, 3e3),
     "Discharge, $Q$ (m$^3$ s$^{-1}$)", "(a)"),
    (ax_s, "stage_m", False, (0, 9), "Stage, $H$ (m)", "(b)"),
]:
    for y, site in zip(y_positions, SITE_ORDER):
        full = pd.read_csv(f"{DATA_DIR}/{site}/full_record_{site}.csv")
        full = full[full["stage_m"] < 20]
        values = full[var].values

        ax.boxplot(values, positions=[y], vert=False, widths=0.55,
                   showfliers=False, patch_artist=True, zorder=3,
                   medianprops=dict(color="#C0392B", linewidth=1.4),
                   boxprops=dict(facecolor="white", edgecolor=BOX_BLUE, linewidth=1.1),
                   whiskerprops=dict(color=BOX_BLUE, linewidth=1.0),
                   capprops=dict(color=BOX_BLUE, linewidth=1.0))

    if log:
        ax.set_xscale("log")
    ax.set_xlim(*xlim)
    ax.set_ylim(-0.6, len(SITE_ORDER) - 1 + 0.6)
    ax.set_yticks([])
    ax.set_xlabel(xlabel)
    ax.tick_params(labelsize=10, length=2.5, width=0.6, pad=1.5)
    # via set_title so it pulls from axes.titlesize (12pt) automatically, instead of a
    # hand-picked size that has to be kept in sync with the title category by hand
    ax.set_title(panel_letter, loc="left", fontweight="bold", pad=8)

# two-line row labels (river/station, then stream order & area) on the left panel only
for y, site in zip(y_positions, SITE_ORDER):
    meta = SITE_META[site]
    ax_d.text(-0.03, y + 0.16, f"{meta['river']} (USGS {meta['usgs']})",
               transform=ax_d.get_yaxis_transform(), ha="right", va="center",
               fontsize=11, color="black")
    ax_d.text(-0.03, y - 0.16,
               f"Stream order {meta['order']}, Area {meta['area']} km$^2$",
               transform=ax_d.get_yaxis_transform(), ha="right", va="center",
               fontsize=10, color="black")

fig.tight_layout(w_pad=2.2)
# The module-level 'savefig.bbox': 'tight' rcParam auto-crops to content, which drifts
# the ACTUAL saved width away from the nominal 7.0in canonical width by a different
# amount per figure (measured: fig1_conus_map.png 6.78in, fig2 gallery 7.08in,
# rating_curve_qq_grid.png 8.06in) -- since \includegraphics[width=\textwidth] rescales
# the whole raster, that drift changes the effective printed point size differently per
# figure even though the rcParams all match (PAPER_STYLE_GUIDE.md ss5's physical-size
# warning, one level deeper). Passing bbox_inches=None here does NOT disable it --
# that just falls back to the rcParam, which IS 'tight'. Have to override the rcParam
# itself in a scoped context to actually get the untrimmed, exact-figsize save.
with plt.rc_context({"savefig.bbox": None}):
    fig.savefig(f"{OUT_DIR}/sfig-01_case_study_site_distributions.png", facecolor="white")
    fig.savefig(f"{OUT_DIR}/sfig-01_case_study_site_distributions.pdf", facecolor="white")
plt.close(fig)
print("Saved site_summary_panel.png")


# ======================================================================================
# Fig B — 3x3 composite: rating curve | discharge Q-Q | stage Q-Q, one row per site
# ======================================================================================
# Re-applied to the paper's canonical figure style (PAPER_STYLE_GUIDE.md ss3/ss5):
# title/label 12pt, ticks 10pt, legend 11pt, dpi 600, same grid/spine/tick
# convention as Fig. 1/Fig. 2. This intentionally overrides the oversized,
# fig_selected_sites_clean.png-matched rcParams set at module level above,
# which only applies to Fig A (already saved by this point).
plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times New Roman", "DejaVu Serif"],

    "font.size":           12,
    "axes.titlesize":      12,
    "axes.labelsize":      12,
    "xtick.labelsize":     10,
    "ytick.labelsize":     10,
    "legend.fontsize":     11,

    "xtick.major.width":   0.8,
    "ytick.major.width":   0.8,
    "xtick.major.size":    4.0,
    "ytick.major.size":    4.0,
    "xtick.direction":     "in",
    "ytick.direction":     "in",
    "xtick.top":           True,
    "ytick.right":         True,

    "axes.grid":           True,
    "grid.color":          "#D5D8DC",
    "grid.linestyle":      "-",
    "grid.linewidth":      0.4,
    "grid.alpha":          0.5,

    "axes.linewidth":      0.5,
    "axes.edgecolor":      "#555555",
    "axes.spines.top":     True,
    "axes.spines.right":   True,

    "figure.dpi":          150,
    "savefig.dpi":         600,
    "savefig.bbox":        "tight",
    "figure.facecolor":    "white",
    "axes.facecolor":      "white",
})

# Colors matched to the rest of the paper: observed points navy (same as the
# Fig. 2 rating-curve gallery), reference/fit line the same red used for the
# P99 marker there.
BLUE = "#004080"
RED = "#FF0000"

N_COLS = 3
n_rows = 3
# Canonical 7.0in source width (PAPER_STYLE_GUIDE.md ss4 -- same width Fig. 1/Fig. 2 are
# built at). LEFT_MARGIN_IN = row-label text width (1.50in, measured at 12pt bold) + a
# small gap (0.1in) + column 1's own y-axis-label/tick overhang (~0.4in, measured via
# get_tightbbox -- axes.get_position() only covers the data area, NOT the ylabel/tick
# text outside it, which is exactly what this margin was too narrow to include the first
# time). NOT an arbitrary scaled-down ratio -- with savefig.bbox='tight' now disabled for
# this figure (see the rc_context lower in this block), nothing outside the nominal
# canvas survives the save, so the margin has to genuinely fit everything in it.
# Width and height are decoupled on purpose: only the WIDTH is canonically constrained
# to 7.0in (PAPER_STYLE_GUIDE.md ss4). Squeezing COL_WIDTH_IN to fit LEFT_MARGIN_IN
# within that fixed budget left too little vertical room for column headers + per-panel
# titles to both fit without colliding -- fixed by giving ROW_HEIGHT_IN its own,
# taller value; the figure is simply not square anymore, which is fine.
_CANON_WIDTH_IN = 7.0
LEFT_MARGIN_IN = 2.2   # 2.0 left the row label touching the y-axis label with zero gap
COL_WIDTH_IN = (_CANON_WIDTH_IN - LEFT_MARGIN_IN) / N_COLS
ROW_HEIGHT_IN = 2.0
fig_width = N_COLS * COL_WIDTH_IN + LEFT_MARGIN_IN
fig_height = n_rows * ROW_HEIGHT_IN
fig, axes = plt.subplots(n_rows, N_COLS, figsize=(fig_width, fig_height))

col_titles = ["Rating Curve", "Discharge Q–Q Plot", "Stage Q–Q Plot"]

for i, site in enumerate(SITE_ORDER):
    meta = SITE_META[site]

    # --- Column 1: rating curve ---
    ax = axes[i, 0]
    obs = np.loadtxt(f"{DATA_DIR}/{site}/rc_obs_{site}.csv", delimiter=",", skiprows=1)
    Q_obs, H_obs = obs[:, 0], obs[:, 1]
    with open(f"{DATA_DIR}/{site}/rc_params_{site}.json") as f:
        p = json.load(f)
    H_grid = np.linspace(H_obs.min(), H_obs.max(), 300)
    Q_fit = rating_curve_model(H_grid, p["C"], p["n"], p["H0"])

    # s=6 matches the Fig. 2 gallery's marker size for a similarly-sized
    # (~2 in) panel -- s=20 (tuned for the old 13.6 in canvas) made points
    # overlap into a blob here and flattened the visible scatter spread.
    # Points drawn on top of the fit line (zorder 4 > 3) -- otherwise the
    # line paints over any point that sits close to it, which is most of
    # them wherever the fit is good.
    # marker/tick styling matched to fig_copula_sites_clean_v2.png's
    # "high-flow data" layer (s=7, edgecolors='w', linewidths=0.2) and its
    # tick convention (nbins=3, prune='lower', length=2.5/width=0.6/pad=1.5)
    ax.plot(Q_fit, H_grid, color=RED, linewidth=1.6, zorder=3, label="Rating Curve")
    ax.scatter(Q_obs, H_obs, s=7, alpha=0.85, color=BLUE,
               edgecolors="w", linewidth=0.2, zorder=4, rasterized=True,
               label="Observed Field Data")
    ax.set_xlabel("Discharge, $Q$ (m$^3$ s$^{-1}$)")
    ax.set_ylabel("Stage, $H$ (m)")
    ax.set_title(f"USGS {meta['usgs']}", pad=4)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=3, prune="lower"))
    ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=3, prune="lower"))
    ax.tick_params(labelsize=10, length=2.5, width=0.6, pad=1.5)
    ax.set_xlim(left=0)

    # --- Columns 2-3: Q-Q plots ---
    with open(f"{DATA_DIR}/{site}/marginal_info_{site}.json") as f:
        info = json.load(f)
    data = pd.read_csv(f"{DATA_DIR}/{site}/marginal_data_{site}.csv")

    for j, (var, col) in enumerate([("discharge", "x"), ("stage", "y")], start=1):
        ax = axes[i, j]
        dist_name = info[f"{var}_dist"]
        DistCls = DIST_MAP[dist_name]
        u = DistCls()
        vals = data[col].values
        u.fit(vals)
        n = len(vals)
        pp = (np.arange(1, n + 1) - 0.5) / n
        theo_q = u.percent_point(pp)
        emp_q = np.sort(vals)

        # Q-Q points sit almost exactly on the 1:1 line for a good fit, so
        # they need to draw on top of it (zorder 4 > 3). No white edge here
        # (unlike the RC panel) -- a right-skewed marginal (Gamma) compresses
        # many points into a narrow low-quantile range, and overlapping
        # white-ringed circles there blend into a pale haze instead of a
        # solid cluster. fig_copula_sites_clean_v2.png avoids this the same
        # way for its dense layer: no marker edge.
        lo, hi = min(theo_q.min(), emp_q.min()), max(theo_q.max(), emp_q.max())
        ax.plot([lo, hi], [lo, hi], color=RED, lw=1.4, zorder=3)
        ax.scatter(theo_q, emp_q, s=8, alpha=0.8, color=BLUE,
                   edgecolors="none", zorder=4, rasterized=True)
        # Just the fitted marginal's name -- "Theoretical quantiles (...)"
        # is explained once in the caption instead of repeated on all 6
        # panels, and it sidesteps the 2-line-wrap/collision fight entirely.
        ax.set_xlabel(dist_name.replace("Univariate", ""))
        ax.set_ylabel("Empirical quantiles")
        ax.set_title(f"USGS {meta['usgs']}", pad=4)
        ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=3, prune="lower"))
        ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=3, prune="lower"))
        ax.tick_params(labelsize=10, length=2.5, width=0.6, pad=1.5)

rect_left = LEFT_MARGIN_IN / fig_width
# bottom margin is a FRACTION of fig_height, which shrank along with the
# rest of the canvas when it was rescaled to the 7.0 in canonical width —
# the same absolute inches of text now need a bigger fraction, or the
# bottom-row x-axis labels collide with the shared legend below them.
fig.subplots_adjust(left=rect_left, right=0.97, top=0.85, bottom=0.18,
                     wspace=0.95, hspace=0.85)

# Row labels + column titles, placed using the FINALIZED axes positions (figure-fraction
# coordinates, via get_position() -- only valid after subplots_adjust) instead of the
# previous axes-fraction offset (xy=(-0.42, 0.5), xycoords="axes fraction"). That offset
# scales with the axes' own width, which shrank along with everything else when this
# figure was rescaled to 7.0in -- with savefig.bbox='tight' now disabled (see the
# rc_context lower down), auto-crop-expansion no longer bails this out, so it clipped the
# row labels ("(b) Des Moines River" etc. were cut off). Figure-fraction placement is
# decoupled from axes size entirely, and LEFT_MARGIN_IN above is sized to the actual
# measured text width (1.50in at 12pt bold) plus padding, so it now genuinely fits.
ROW_LABEL_X = 0.012
for i, site in enumerate(SITE_ORDER):
    meta = SITE_META[site]
    row_letter = "(a)" if i == 0 else "(b)" if i == 1 else "(c)"
    pos = axes[i, 0].get_position()
    y_center = (pos.y0 + pos.y1) / 2
    fig.text(ROW_LABEL_X, y_center + 0.022, f"{row_letter} {meta['river']}",
             ha="left", va="center", fontsize=12, fontweight="bold", color="black")
    fig.text(ROW_LABEL_X, y_center - 0.022, f"USGS {meta['usgs']}",
             ha="left", va="center", fontsize=12, fontweight="bold", color="black")

for j, t in enumerate(col_titles):
    pos = axes[0, j].get_position()
    fig.text((pos.x0 + pos.x1) / 2, pos.y1 + 0.025, t,
             ha="center", va="bottom", fontsize=12, fontweight="bold")

# Shared legend at the bottom of the figure (same placement/style rule as
# Fig. 1/Fig. 2 — PAPER_STYLE_GUIDE.md ss6), not tucked inside one panel.
# y=0.012 (just inside the canvas, not below it like the old y=-0.02) -- this figure's
# width is now pinned to the exact 7.0in nominal figsize (see the rc_context below), so
# nothing outside [0, 1] in figure-fraction space is currently able to survive the save.
handles, labels = axes[0, 0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=2,
           bbox_to_anchor=(0.5 * (1 + rect_left), 0.012), bbox_transform=fig.transFigure,
           fontsize=11, frameon=True, framealpha=0.92, edgecolor="#bbbbbb",
           borderpad=0.6, handletextpad=0.6, columnspacing=1.4)

# Pin the ACTUAL saved width to the nominal 7.0in canonical width (PAPER_STYLE_GUIDE.md
# ss5's savefig.bbox note) -- 'savefig.bbox': 'tight' (set module-level, top of file)
# otherwise crops to content afterward and the saved width drifts (this figure measured
# at 8.06in actual vs. 7.0in nominal before this fix). bbox_inches=None passed directly
# to savefig does NOT disable it -- that just falls back to the rcParam, which IS
# 'tight' -- so the rcParam itself has to be overridden in a scoped context.
with plt.rc_context({"savefig.bbox": None}):
    fig.savefig(f"{OUT_DIR}/sfig-02_rating_curve_qq_grid.png", facecolor="white")
    fig.savefig(f"{OUT_DIR}/sfig-02_rating_curve_qq_grid.pdf", facecolor="white")
plt.close(fig)
print("Saved rating_curve_qq_grid.png")
