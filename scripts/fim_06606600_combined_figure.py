"""
Builds fim_6606600_combined.png: the Little Sioux (06606600) probabilistic
rating-curve panel placed beside its HAND-FIM inundation-extent map, as a
single image file for submission (previously two separate minipage figures
in LaTeX, at 0.40\\textwidth / 0.57\\textwidth).

Right panel (data/processed/fim_maps/06606600_FIM_final.png) is an ArcGIS Pro render
-- no generating script exists for it in this project (checked: nothing in
scripts/ or any notebook references it) -- so it is used completely
untouched, at its native resolution.

Left panel is REGENERATED from the same source data/logic as
scripts/_make_src_added_figs.py's site="6606600" case (not a resize of the
existing GUMBEL-6606600-SRC-Added-2.png), at a figure size chosen so its
native rendered height equals the FIM map's native height exactly -- so the
two panels sit at the same height with zero raster scaling of either one.

Why a separate script instead of editing _make_src_added_figs.py: that
script's figsize/legend layout (single-column legend, rect=0.27) is shared
by all three sites' STANDALONE SRC-added figures, which are still used at
their original size elsewhere in the paper. Forcing the same shrink used
here onto all three would break those. This script only ever touches the
combined-figure-specific output.

Layout note: fitting the full title + annotated callouts + legend into a
canvas as short as the FIM map (2.9in tall) genuinely does not fit with the
original single-column, 11pt legend -- the legend's own absolute height
(~1.19in at 11pt) plus the title and x-axis leave too little for the axes
box itself, and things visibly overlap. The legend below is switched to 2
columns at a slightly smaller (9.5pt) size purely to fit that height without
overlap; every other element (title, axis label, tick, annotation font
sizes, line weights, colors) is identical to _make_src_added_figs.py. This
does make the regenerated panel wider than the original 40:57 LaTeX ratio
implied (see the printed report at the end) -- that's a real consequence of
"no squashing + matches the map's height + nothing overlaps", not a bug.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

# Run this script from the REPO ROOT.
DATA_DIR = "data/processed/case_study_sites/6606600"
FIM_DIR = "data/processed/fim_maps"
OUT_DIR = "figures"

RIGHT_PATH = f"{FIM_DIR}/06606600_FIM_final.png"
OUT_PATH = f"{OUT_DIR}/FIM-06606600_littlesioux_combined.png"

# ---------------------------------------------------------------------------
# 1) Load the untouched map first -- its native height sets the target for
#    the regenerated left panel.
# ---------------------------------------------------------------------------
right = Image.open(RIGHT_PATH)
right_dpi = right.info.get("dpi", (700, 700))
TARGET_H_PX = right.size[1]
TARGET_DPI = right_dpi[0]
TARGET_H_IN = TARGET_H_PX / TARGET_DPI
print(f"Right panel (untouched): {right.size} px @ {right_dpi} dpi "
      f"-> target left-panel height = {TARGET_H_IN:.4f} in")

# ---------------------------------------------------------------------------
# 2) Regenerate the left panel at that exact height. figsize/dpi below were
#    tuned by rendering + measuring actual pixel output (matplotlib's
#    bbox_inches='tight' expands beyond the nominal figsize to fit the
#    legend/title, so the nominal numbers here are reverse-engineered to
#    land on TARGET_H_PX exactly, not a guess).
# ---------------------------------------------------------------------------
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
    'savefig.dpi':        TARGET_DPI,
    'figure.facecolor':   'white',
    'axes.facecolor':     'white',
})

site = "6606600"
cfg = dict(title="Little Sioux River at Correctionville\nUSGS Site 06606600",
           Q_target=400, p95_yoff=1.7)

SRC_TABLE = """1.352337 0.3048
4.859541 0.6096
10.26505 0.9144
17.46265 1.2192
26.26562 1.524
36.85817 1.8288
48.86376 2.1336
62.43736 2.4384
77.69509 2.7432
93.30218 3.048
106.9859 3.3528
114.9087 3.6576
120.4087 3.9624
106.0238 4.2672
114.6553 4.572
160.8202 4.8768
237.2388 5.1816
333.8784 5.4864
446.8134 5.7912
577.5016 6.096
717.5469 6.4008
875.0098 6.7056
1041.264 7.0104
1221.822 7.3152
1416.775 7.62
1632.342 7.9248
1874.489 8.2296
2127.055 8.5344
2391.368 8.8392
2662.203 9.144
2929.902 9.4488
3177.191 9.7536
3465.597 10.0584"""

data = np.load(f"{DATA_DIR}/prob_rc_{site}.npz")
discharge_grid = data["discharge_grid"]
preds = data["preds"]
discharge_data = data["discharge_data"]
stage_data = data["stage_data"]

src_arr = np.array([row.split() for row in SRC_TABLE.strip().split("\n")], dtype=float)
src_q, src_h = src_arr[:, 0], src_arr[:, 1]
mono = np.concatenate([[True], np.diff(src_q) > 0])
src_q, src_h = src_q[mono], src_h[mono]

x_lo, x_hi = discharge_grid.min(), discharge_grid.max()
src_lo, src_hi = max(x_lo, src_q.min()), min(x_hi, src_q.max())
src_q_plot = np.linspace(src_lo, src_hi, 200)
src_h_plot = np.interp(src_q_plot, src_q, src_h)

Q_target = cfg["Q_target"]
p05 = np.interp(Q_target, discharge_grid, preds[:, 0])
p95 = np.interp(Q_target, discharge_grid, preds[:, 4])

FIGSIZE_W, FIGSIZE_H = 2.0, 2.77   # tuned -- see module docstring

fig, ax = plt.subplots(figsize=(FIGSIZE_W, FIGSIZE_H))

ax.fill_between(discharge_grid, preds[:, 0], preds[:, 4], color='#FADADD', alpha=0.7,
                 label='90% Predictive Uncertainty (P5\u2013P95)')
ax.fill_between(discharge_grid, preds[:, 1], preds[:, 3], color='#F4A79D', alpha=0.65,
                 label='50% Predictive Uncertainty (P25\u2013P75)')
ax.plot(discharge_grid, preds[:, 2], color='#C0392B', lw=1.6, label='Median Stage Estimate (P50)')
ax.plot(src_q_plot, src_h_plot, color='#2E7D32', lw=1.6, ls='--', label='HAND-FIM SRC')
ax.scatter(discharge_data, stage_data, s=16, alpha=0.9, color='#004080',
           edgecolors='w', linewidths=0.4, label='Observed High-Flow Data', zorder=5)

y_min = np.nanmin([preds[:, 0].min(), stage_data.min(), src_h_plot.min()])
y_max = np.nanmax([preds[:, 4].max(), stage_data.max(), src_h_plot.max()])
y_pad = 0.25 * (y_max - y_min)
ax.set_ylim(y_min - y_pad, y_max + y_pad)
ax.set_xlim(discharge_grid.min(), discharge_grid.max())

x_left = discharge_grid.min()
ax.axvline(x=Q_target, color='black', lw=1.0, ls=':', zorder=4)
ax.text(Q_target, ax.get_ylim()[1] * 0.98, f'$Q$={Q_target} m$^3$ s$^{{-1}}$',
        fontsize=8.5, color='black', ha='center', va='top', zorder=10,
        bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.85))

for stage, label, y_offset in zip([p05, p95], ['$H_{{P05}}$={:.2f} m', '$H_{{P95}}$={:.2f} m'],
                                   [-0.45, cfg["p95_yoff"]]):
    ax.plot([x_left, Q_target], [stage, stage], color='black', lw=0.9, ls='--', alpha=0.7, zorder=5)
    ax.plot(Q_target, stage, 'o', color='black', ms=4.5, zorder=9,
             markeredgecolor='white', markeredgewidth=0.5)
    ax.annotate(label.format(stage), xy=(Q_target, stage),
                xytext=(Q_target + discharge_grid.max() * 0.03, stage + y_offset),
                fontsize=8, color='black', va='center', zorder=10,
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='black', linewidth=0.5, alpha=0.97),
                arrowprops=dict(arrowstyle='-', color='black', lw=0.7, alpha=0.6))

ax.set_xlabel(r'Discharge, $Q$ (m$^3$ s$^{-1}$)')
ax.set_ylabel(r'Stage, $H$ (m)')
ax.set_title(cfg["title"], pad=6)

# 2-column, slightly smaller legend -- the only design change from
# _make_src_added_figs.py, needed to fit this height (see docstring).
legend_handles, legend_labels = ax.get_legend_handles_labels()
leg = fig.legend(legend_handles, legend_labels, loc='lower center', ncol=2,
                  bbox_to_anchor=(0.5, -0.02), bbox_transform=fig.transFigure,
                  frameon=True, framealpha=0.92, edgecolor='#bbbbbb', fontsize=9.5,
                  borderpad=0.6, handletextpad=0.5, columnspacing=1.0)

# Reserve exactly the legend's own measured height (font-driven, not
# figsize-driven) instead of a fraction tuned for a different canvas size.
fig.canvas.draw()
legend_h_in = leg.get_window_extent().transformed(fig.dpi_scale_trans.inverted()).height
rect_bottom = (legend_h_in + 0.06) / FIGSIZE_H

plt.tight_layout(pad=0.3, rect=[0, rect_bottom, 1, 1])

left_tmp_path = f"{OUT_DIR}/_left_panel_6606600_regenerated.png"
fig.savefig(left_tmp_path, dpi=TARGET_DPI, bbox_inches='tight', facecolor='white')
plt.close(fig)

left = Image.open(left_tmp_path)
print(f"Left panel (regenerated): {left.size} px @ {left.info.get('dpi')} dpi")

if left.size[1] != TARGET_H_PX:
    print(f"WARNING: regenerated left panel height ({left.size[1]}px) does not "
          f"exactly match the target ({TARGET_H_PX}px) -- off by {left.size[1]-TARGET_H_PX}px. "
          "Combining anyway at native sizes (no rescale), padding to align.")

# ---------------------------------------------------------------------------
# 3) Combine at native pixel sizes -- NO resizing of either panel. If the
#    regenerated left panel's height is off by a few px from the target
#    (matplotlib's tight bbox can round to the pixel), pad the shorter one
#    with white rather than stretch anything.
# ---------------------------------------------------------------------------
gap = 20
combined_h = max(left.size[1], right.size[1])
canvas = Image.new("RGBA", (left.size[0] + gap + right.size[0], combined_h), (255, 255, 255, 255))
canvas.paste(left, (0, (combined_h - left.size[1]) // 2), left if left.mode == "RGBA" else None)
canvas.paste(right, (left.size[0] + gap, (combined_h - right.size[1]) // 2),
             right if right.mode == "RGBA" else None)
canvas = canvas.convert("RGB")
canvas.save(OUT_PATH, dpi=(TARGET_DPI, TARGET_DPI))

left_frac = left.size[0] / (left.size[0] + right.size[0]) * 100
right_frac = 100 - left_frac
print(f"\nSaved: {OUT_PATH}")
print(f"Final size (px): {canvas.size}")
print(f"Final dpi: ({TARGET_DPI}, {TARGET_DPI})")
print(f"Final size (in): {canvas.size[0]/TARGET_DPI:.3f} x {canvas.size[1]/TARGET_DPI:.3f}")
print(f"Width split: left {left_frac:.1f}% : right {right_frac:.1f}%  "
      f"(originally 40:57 in LaTeX; wider left panel here is the direct "
      f"cost of fitting all content without overlap at this height -- see docstring)")

import os
os.remove(left_tmp_path)  # intermediate only, not a deliverable
