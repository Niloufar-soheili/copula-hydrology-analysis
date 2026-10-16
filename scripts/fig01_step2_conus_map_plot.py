# ==============================================================================
# FIG. 1 — CONUS map (standalone)
# ==============================================================================
# Same full-population background as computed above (all 6,323 gauges,
# unbiased). Colorbar is a standalone vertical bar outside the map frame, to
# the right, so it never overlaps the map. Only the 12 Fig. 2 sites are
# shown, numbered north -> south to match the panel numbers in Fig. 2
# exactly, so a reviewer can trace a dot straight to its rating curve.
# Case-study sites are not shown here.
# Depends on `pop`, `grouped_ifmha`, `LAT`, `LON` from the cell above.

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import cartopy.crs as ccrs
import cartopy.feature as cfeature

plt.rcParams.update({
    'font.family':        'serif',
    'font.serif':         ['Times New Roman', 'DejaVu Serif'],
    'font.size':          12,
    'axes.titlesize':     12,
    'axes.labelsize':     12,
    'xtick.labelsize':    10,
    'ytick.labelsize':    10,
    'legend.fontsize':    10,
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

# --- the 12 Fig. 2 sites, numbered north -> south, same order as Fig. 2 -----
fig2_rows = pop[pop['site_no'].astype(str).isin(TARGET_SITES_UNIQUE)].drop_duplicates(subset='site_no')
fig2_rows = fig2_rows.sort_values(LAT, ascending=False).reset_index(drop=True)
fig2_rows['num'] = fig2_rows.index + 1

fig1 = plt.figure(figsize=(7.0, 4.3))
# Map axes occupy nearly the full figure; a slim strip on the right is left
# free (outside this rect) for a standalone colorbar so it never overlaps
# the map. Tighter extent than before (was [-127,-64,22,51]) so CONUS fills
# the freed space instead of leaving a wide ocean/Canada/Mexico margin.
ax = fig1.add_axes([0.005, 0.02, 0.855, 0.96], projection=ccrs.AlbersEqualArea(
    central_longitude=-96, standard_parallels=(29.5, 45.5)))
ax.set_extent([-124.5, -66.5, 24.0, 49.7], crs=ccrs.PlateCarree())

# Shaded-relief terrain (Natural Earth low-res raster), muted with a
# translucent white wash so the data overlay stays legible — gives the map
# real geographic texture (mountains vs. plains) instead of a flat tint,
# and the relief itself echoes the slope argument made in the text.
ax.stock_img()
ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                       facecolor='white', alpha=0.55, zorder=0.5))

ax.add_feature(cfeature.OCEAN.with_scale('50m'), facecolor='#DCEAF2', zorder=1)
ax.add_feature(cfeature.LAKES.with_scale('50m'), facecolor='#DCEAF2',
               edgecolor='#8FB4C6', linewidth=0.3, zorder=1)
ax.add_feature(cfeature.RIVERS.with_scale('50m'), edgecolor='#6FA8C7',
               linewidth=0.45, alpha=0.75, zorder=2)
ax.add_feature(cfeature.STATES.with_scale('10m'),
               linewidth=0.35, edgecolor='#8A8A8A', zorder=3)
ax.add_feature(cfeature.COASTLINE.with_scale('10m'),
               linewidth=0.55, edgecolor='#555555', zorder=3)
ax.add_feature(cfeature.BORDERS.with_scale('10m'),
               linewidth=0.55, edgecolor='#555555', zorder=3)
for spine in ax.spines.values():
    spine.set_edgecolor('#333333')
    spine.set_linewidth(0.8)

base = pop[pop['group'] == 'all']
vmax = pop['mean_iqr'].quantile(0.95)
sc = ax.scatter(base[LON], base[LAT], c=base['mean_iqr'], s=6, cmap='YlOrRd',
                vmin=0, vmax=vmax, alpha=0.62, linewidths=0, edgecolors='none',
                transform=ccrs.PlateCarree(), zorder=5)

# The 12 Fig. 2 sites: hollow, numbered 1-12 to match the panels below. Two
# pairs sit close enough (05481650/05488500 in Iowa, ~0.9 deg apart;
# 05597000/03611500 in southern Illinois, ~0.8 deg apart) that their badges
# touch at a legible size. Nudge each pair apart symmetrically along the axis
# connecting them by a small, fixed amount — enough to clear, not enough to
# reach any other site.
MARKER_S = 95
NUDGE_DEG = {   # (d_lon, d_lat), degrees — small, along the pair's own axis
    '5481650': (-0.32, 0.16),
    '5488500': (0.32, -0.16),
    '5597000': (-0.21, 0.53),
    '3611500': (0.21, -0.53),
}
for _, r in fig2_rows.iterrows():
    sn = str(r['site_no'])
    dlon, dlat = NUDGE_DEG.get(sn, (0.0, 0.0))
    lx, ly = r[LON] + dlon, r[LAT] + dlat
    ax.scatter([lx], [ly], marker='o', s=MARKER_S, facecolors='white',
               edgecolors='#1A237E', linewidths=1.2,
               transform=ccrs.PlateCarree(), zorder=7)
    ax.text(lx, ly, str(int(r['num'])), transform=ccrs.PlateCarree(),
            ha='center', va='center', fontsize=6, fontweight='bold',
            color='#1A237E', zorder=8)

# Colorbar as a standalone axes outside the map frame, to the right, with a
# visible gap so it never overlaps the map (map rect ends at x=0.86).
cax = fig1.add_axes([0.90, 0.10, 0.028, 0.80])
cb = fig1.colorbar(sc, cax=cax, extend='max')
cb.set_label('Stage IQR per discharge decile (m)', fontsize=11.5)
cb.ax.tick_params(labelsize=10)
cb.outline.set_linewidth(0.5)

plt.savefig('figures/fig-01_conus_variability_map.png', bbox_inches='tight', facecolor='white')
plt.savefig('figures/fig-01_conus_variability_map.pdf', bbox_inches='tight', facecolor='white')
print("Saved fig1_conus_map.png / .pdf")
plt.show()
