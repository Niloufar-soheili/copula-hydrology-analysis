# ==============================================================================
# FIG. 2 — rating-curve gallery, the paper's 12 sites only
# ==============================================================================
# Same 12 sites as TARGET_SITES_UNIQUE used throughout this notebook (includes
# 05481650, which is also one of the 3 case-study sites — its RC belongs here
# either way since it is one of the paper's original 12). The 2 case-study-only
# sites (06606600, 08096500) are NOT plotted here; their rating curves are
# shown separately in the case-study section. Numbered north -> south, same
# order as the map above, so a reader can cross-reference by number or by
# site. Same rcParams, same median/99th-percentile lines, same style as the
# paper's other RC figures.
# Depends on `pop`, `grouped_ifmha`, `LAT` from the cell above.

import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D
from scipy.optimize import curve_fit


def rating_curve_model(H, C, n, H0):
    return C * np.maximum(H - H0, 0) ** n

plt.rcParams.update({
    'font.family':        'serif',
    'font.serif':         ['Times New Roman', 'DejaVu Serif'],

    'font.size':          12,
    'axes.titlesize':     12,
    'axes.labelsize':     12,
    'xtick.labelsize':    10,
    'ytick.labelsize':    10,
    'legend.fontsize':    10,

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

TARGET_SITES_UNIQUE = globals().get("TARGET_SITES_UNIQUE", [
    '3611500', '7258000', '3301500', '6905500',
    '5404000', '5422000', '8330000',
    '5481650', '7381482', '5488500', '6810000', '5597000'
])
TARGET_SITES_PADDED = [s.zfill(8) for s in TARGET_SITES_UNIQUE]

gallery = []
for sn in TARGET_SITES_PADDED:
    try:
        grp = grouped_ifmha.get_group(sn)
    except KeyError:
        try:
            grp = grouped_ifmha.get_group(sn.lstrip('0'))
        except KeyError:
            print(f"Site {sn} not found")
            continue
    df_s = grp[['discharge_m3s', 'stage_m']].dropna()
    df_s = df_s[(df_s['discharge_m3s'] > 0) & (df_s['stage_m'] > 0) & (df_s['stage_m'] < 20)]
    if df_s.empty:
        continue
    Q, H = df_s['discharge_m3s'].values, df_s['stage_m'].values
    q_lo, q_hi = np.percentile(Q, [1, 95])
    h_lo, h_hi = np.percentile(H, [1, 99])
    m = (Q >= q_lo) & (Q <= q_hi) & (H >= h_lo) & (H <= h_hi)
    Q, H = Q[m], H[m]
    if len(Q) < 30:
        continue
    lat_row = pop.loc[pop['site_no'] == sn.lstrip('0'), LAT]
    lat = float(lat_row.iloc[0]) if len(lat_row) else np.nan
    gallery.append({'site_no': sn, 'Q': Q, 'H': H, 'lat': lat})

gallery.sort(key=lambda s: -s['lat'] if np.isfinite(s['lat']) else 0)
for i, s in enumerate(gallery):
    s['num'] = i + 1
print(f"Gallery: {len(gallery)} sites")

N_COLS = 4
FIG_WIDTH = 7.0
# 4 columns x 3 rows: wide enough per panel (7.0/4 = 1.75 in) to render
# title/tick/legend text at the same sizes used in the other figures.
# Height is scaled to keep roughly the same per-panel aspect.
ROW_HEIGHT = 1.7
n_rows = math.ceil(len(gallery) / N_COLS)  # 3 rows for 12 sites at 4 cols

fig2, axes = plt.subplots(nrows=n_rows, ncols=N_COLS,
                         figsize=(FIG_WIDTH, n_rows * ROW_HEIGHT))
axes_flat = axes.flatten()

for idx, site in enumerate(gallery):
    axp = axes_flat[idx]
    Q, H, sn = site['Q'], site['H'], site['site_no']

    axp.scatter(Q, H, s=6, alpha=0.85, color='#004080',
               edgecolors='w', linewidths=0.15, zorder=3, rasterized=True)

    # Fitted deterministic rating curve Q = C*(H-H0)^n, same model/bounds used
    # everywhere else in the paper. Drawn at zorder=5, ABOVE the observed
    # points (zorder=3) and the reference lines (zorder=4), so it stays
    # visible through the dense point cloud instead of being buried under it.
    try:
        H0_guess = H.min() * 0.95
        C_guess = Q.mean() / max((H.mean() - H0_guess) ** 2.0, 1e-8)
        (C_fit, n_fit, H0_fit), _ = curve_fit(
            rating_curve_model, H, Q,
            p0=[C_guess, 2.0, H0_guess],
            bounds=([0.0, 0.1, H.min() - 5.0], [np.inf, 5.0, H.min() + 0.5]),
            maxfev=20000,
        )
        H_grid = np.linspace(H.min(), H.max(), 200)
        Q_rc = rating_curve_model(H_grid, C_fit, n_fit, H0_fit)
        axp.plot(Q_rc, H_grid, color='#FF0000', lw=1.2, ls='-',
                 zorder=5, label='Rating curve')
    except Exception as e:
        print(f"  Site {sn}: rating-curve fit failed ({e}) -- panel left without an RC line")

    med_q = np.percentile(Q, 50)
    axp.axvline(med_q, color='#388E3C', lw=0.8, ls='--', alpha=1.0,
               zorder=4, label='P50')
    p99_q = np.percentile(Q, 99)
    axp.axvline(p99_q, color='#2E7D32', lw=0.8, ls='-', alpha=1.0,
               zorder=4, label='P99')

    # Title, tick, and legend sizes match the global rcParams above
    # (and the other figures in the paper): title 12pt, ticks 10pt,
    # legend 11pt.
    axp.set_title(f"{site['num']}. Site {sn}", pad=2, fontsize=12)
    axp.set_xlim(left=0)
    axp.set_ylim(bottom=0)
    axp.xaxis.set_major_locator(ticker.MaxNLocator(nbins=3, prune='lower'))
    axp.yaxis.set_major_locator(ticker.MaxNLocator(nbins=3, prune='lower'))
    axp.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f'{y:g}' if y >= 0 else ''))
    axp.tick_params(labelsize=10, length=2.5, width=0.6, pad=1.5)

for i in range(len(gallery), len(axes_flat)):
    axes_flat[i].axis('off')

legend_items = [
    Line2D([], [], color='#FF0000', lw=1.4, ls='-', label='Rating curve'),
    Line2D([], [], color='#388E3C', lw=1.4, ls='--', label='P50'),
    Line2D([], [], color='#2E7D32', lw=1.4, ls='-', label='P99'),
]
fig2.legend(handles=legend_items, loc='center right', ncol=3,
            bbox_to_anchor=(0.99, 0.06), bbox_transform=fig2.transFigure,
            frameon=True, framealpha=0.92, edgecolor='#bbbbbb', fontsize=11,
            borderpad=0.6, handletextpad=0.6, columnspacing=1.4)

fig2.supxlabel(r'Discharge, $Q$ (m$^3$ s$^{-1}$)', fontsize=12, y=0.06, x=0.42)
fig2.supylabel(r'Stage, $H$ (m)', fontsize=12, x=0.01)

plt.tight_layout(pad=0.3, h_pad=0.5, w_pad=0.3, rect=[0.02, 0.09, 1, 1])
plt.savefig('figures/fig-02_observed_rating_curves_gallery.png', dpi=600, bbox_inches='tight', facecolor='white')
plt.savefig('figures/fig-02_observed_rating_curves_gallery.pdf', dpi=600, bbox_inches='tight', facecolor='white')
print("Saved fig2_rc_gallery.png / .pdf")
plt.show()
