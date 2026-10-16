"""
Generates FIGURE_3x3_copula_vs_gpr.png / .pdf (case-study comparison: copula
vs. standard GPR, 2 rows x 3 sites) per PAPER_STYLE_GUIDE.md. The
heteroscedastic GPR variant/row has been dropped per request (2026-08-24) -
the paper now compares only against the standard GPR baseline. Filename is
unchanged (still "3x3") to avoid touching the LaTeX \includegraphics/label;
rename both if a "2x3"-accurate filename is preferred later.

Styling (2026-09-24 restyle): rewritten to match prob_rating_curves_row.png
(_make_prob_rc_row.py) element-for-element -- same rcParams, same band/line/
point colors, alphas, line widths, and draw-order zorder stack, same square
per-panel aspect via box_aspect(1) at the same 7.0in figure width (so a
single panel is the same physical size in both figures), same per-panel
axes-start-at-0 convention, same (a)/(b)/(c) two-line title format, same
tick locators, and the same legend wording/formatting. The GPR row reuses
the identical band-alpha/line-width/point-style "vocabulary" as the copula
row, just in the existing blue hue family, so the two methods are drawn
consistently and are directly comparable panel-to-panel.

Data sources (re-run this file any time the figure needs regenerating -
no re-fitting happens here, it only reads cached results):
- _3x3_data_{site}.npz (project root): Q_hf, H_hf, q_grid, cop_preds, H_rc,
  gpr_std_preds, gpr_het_preds, best_name - per-site copula/GPR quantile
  predictions on the verified, consistent 10August-pipeline high-flow subset
  (Gumbel / Gumbel / Frank winners for 5481650 / 6606600 / 8096500).
- data/processed/case_study_sites/<site>/prob_rc_{site}.npz: all_discharge/all_stage (the full
  daily record, for the gray background layer only).
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# Run this script from the REPO ROOT.
BASE = "."
DATA_DIR = "data/processed/case_study_sites"

# --- canonical rcParams block, verbatim from _make_prob_rc_row.py -----------
plt.rcParams.update({
    'font.family':        'serif',
    'font.serif':         ['Times New Roman', 'DejaVu Serif'],

    'font.size':          12,
    'axes.titlesize':     12,
    'axes.labelsize':     12,
    'xtick.labelsize':    10,
    'ytick.labelsize':    10,
    'legend.fontsize':    11,

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

    'figure.dpi':         150,
    'savefig.dpi':        600,
    'figure.facecolor':   'white',
    'axes.facecolor':     'white',
})

# Site order / column content is unchanged; only the (a)/(b)/(c) + river-name
# title format is new, matching prob_rating_curves_row.png's SITES list.
SITE_ORDER = ["5481650", "6606600", "8096500"]
SITE_TITLES = {
    "5481650": "(a) Des Moines River\nUSGS 05481650",
    "6606600": "(b) Little Sioux River\nUSGS 06606600",
    "8096500": "(c) Brazos River\nUSGS 08096500",
}

# (data_key, row_label, median_color, band90_color, band50_color) -- the
# reference (_make_prob_rc_row.py) uses two DIFFERENT colors for the 50% and
# 90% bands within one hue family (not one color at two opacities). Copula
# keeps the reference's exact salmon pair; GPR reuses the identical
# alpha/zorder/width "vocabulary" in the equivalent two-tone blue pair so
# the two rows are directly comparable.
ROW_KEYS = [
    ("cop_preds",     "Copula",       "#C0392B", "#FADADD", "#F4A79D"),
    ("gpr_std_preds", "Standard GPR", "#1565C0", "#BBDEFB", "#64B5F6"),
]
POINT_COLOR = "#004080"

FIG_WIDTH = 7.0
N_COLS, N_ROWS = 3, 2
# FIG_HEIGHT=6.15 is tuned, not a guess: with box_aspect(1) + tight_layout,
# a 2-row grid is height-constrained (panels shrink well below the
# reference's 1.82in squares) unless given enough vertical room that the
# SAME 7.0in width / 3-column / w_pad=1.3 budget that produces
# prob_rating_curves_row.png's 1.82in squares becomes the binding
# constraint again. 6.15in is the smallest height at which that holds:
# panels come out at 1.809in (vs. reference 1.817in, <0.5% off) and both
# the horizontal AND vertical gaps between panels land at ~0.44-0.45in,
# matching the reference's own inter-panel gap almost exactly. Verified by
# measuring ax.get_position() directly (see PR/commit notes) -- don't
# shrink this back down without re-checking panel size stays put.
FIG_HEIGHT = 6.15
fig, axes = plt.subplots(N_ROWS, N_COLS, figsize=(FIG_WIDTH, FIG_HEIGHT))
for ax in axes.flat:
    ax.set_box_aspect(1)   # literal square panels, same size as prob_rating_curves_row.png

data = {s: dict(np.load(f"{DATA_DIR}/{s}/_3x3_data_{s}.npz", allow_pickle=True)) for s in SITE_ORDER}

# Full daily record (gray background layer), same cache + same style as
# prob_rating_curves_row.png.
all_record = {}
for s in SITE_ORDER:
    pr = np.load(f"{DATA_DIR}/{s}/prob_rc_{s}.npz")
    all_record[s] = (pr["all_discharge"], pr["all_stage"])

for col, site in enumerate(SITE_ORDER):
    d = data[site]
    q_grid, H_rc = d["q_grid"], d["H_rc"]
    Q_hf, H_hf = d["Q_hf"], d["H_hf"]
    Q_all, H_all = all_record[site]

    for row, (key, row_label, line_c, band90_c, band50_c) in enumerate(ROW_KEYS):
        ax = axes[row, col]
        preds = d[key]

        # Draw order, matching _make_prob_rc_row.py exactly: gray background
        # (z1) -> 90% band (z2) -> 50% band (z3) -> rating curve (z4) ->
        # observed points (z5) -> median, drawn last / highest (z6).
        ax.scatter(Q_all, H_all, s=3, alpha=0.25, color='#888888',
                   edgecolors='none', zorder=1, rasterized=True)

        ax.fill_between(q_grid, preds[:, 0], preds[:, 4], color=band90_c,
                         alpha=0.7, zorder=2)
        ax.fill_between(q_grid, preds[:, 1], preds[:, 3], color=band50_c,
                         alpha=0.65, zorder=3)

        ax.plot(q_grid, H_rc, color='#2E7D32', ls='--', lw=1.2, zorder=4)

        ax.scatter(Q_hf, H_hf, s=10, alpha=0.85, color=POINT_COLOR,
                   edgecolors='w', linewidths=0.3, zorder=5, rasterized=True)

        ax.plot(q_grid, preds[:, 2], color=line_c, lw=1.3, zorder=6)

        # Start both axes at 0, exactly like prob_rating_curves_row.png, so
        # the gray full-record cloud reads as context leading up to the
        # zoomed high-flow band instead of being clipped off.
        y_max = np.nanmax([np.nanmax(preds[:, 4]), np.nanmax(H_hf), np.nanmax(H_rc)])
        x_max = np.nanmax([q_grid.max(), Q_hf.max()])
        ax.set_ylim(0, y_max * 1.05)
        ax.set_xlim(0, x_max * 1.02)

        ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=4, prune='lower'))
        ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=5))

        if row == 0:
            ax.set_title(SITE_TITLES[site], pad=4)
        if row == N_ROWS - 1:
            ax.set_xlabel(r'Discharge, $Q$ (m$^3$ s$^{-1}$)')
        if col == 0:
            ax.set_ylabel(f'{row_label}\nStage, $H$ (m)')

# --- single shared legend at the bottom, same wording/format as the reference,
# extended with the GPR row using the same phrasing pattern -----------------
legend_items = [
    Line2D([], [], marker='o', ls='none', ms=3.6, mfc='#888888', mec='none',
           label='All observed data'),
    Line2D([], [], marker='o', ls='none', ms=5.0, mfc=POINT_COLOR, mec='w', mew=0.4,
           label='Observed high-flow data'),
    Line2D([], [], color='#2E7D32', lw=1.6, ls='--', label='Deterministic rating curve'),
    Line2D([], [], color='#C0392B', lw=1.6, ls='-', label='Copula median stage estimate (P50)'),
    Patch(facecolor='#F4A79D', alpha=0.65, label='Copula 50% predictive interval (P25\u2013P75)'),
    Patch(facecolor='#FADADD', alpha=0.7, label='Copula 90% predictive interval (P5\u2013P95)'),
    Line2D([], [], color='#1565C0', lw=1.6, ls='-', label='Standard GPR median stage estimate (P50)'),
    Patch(facecolor='#64B5F6', alpha=0.65, label='Standard GPR 50% predictive interval (P25\u2013P75)'),
    Patch(facecolor='#BBDEFB', alpha=0.7, label='Standard GPR 90% predictive interval (P5\u2013P95)'),
]
fig.legend(handles=legend_items, loc='lower center', ncol=2,
           bbox_to_anchor=(0.5, -0.09), bbox_transform=fig.transFigure,
           frameon=True, framealpha=0.92, edgecolor='#bbbbbb', fontsize=11,
           borderpad=0.6, handletextpad=0.6, columnspacing=1.4)

plt.tight_layout(pad=0.4, h_pad=0.4, w_pad=1.3, rect=[0, 0.12, 1, 1])
plt.savefig("figures/fig-04_copula_vs_gpr_comparison.png", bbox_inches='tight', facecolor='white')
plt.savefig("figures/fig-04_copula_vs_gpr_comparison.pdf", bbox_inches='tight', facecolor='white')
print("Saved figures/fig-04_copula_vs_gpr_comparison.png / .pdf")
