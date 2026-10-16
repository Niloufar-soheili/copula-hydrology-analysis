# ==============================================================================
# CONUS MAP — stage variability at fixed discharge, full IFMHA population
# ==============================================================================
# For every gauge: bin its Q readings into deciles, measure the IQR of stage
# within each bin (spread among readings taken at nearly the same discharge),
# average across bins. No site is excluded for being high or low variability —
# only for lacking enough data to compute the metric (< 50 valid obs) or for
# missing/out-of-CONUS coordinates. Color = that metric, in meters.

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import matplotlib.pyplot as plt
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

MIN_OBS_POP = 50
N_BINS      = 10
MIN_PER_BIN = 4
LAT, LON    = 'dec_lat_va', 'dec_long_va'

# Same 12 figure sites / 3 case-study sites used throughout this notebook.
# site_no in this dataset is NOT zero-padded (e.g. "3611500", not "03611500").
TARGET_12 = globals().get("TARGET_SITES_UNIQUE", [
    '3611500', '7258000', '3301500', '6905500',
    '5404000', '5422000', '8330000',
    '5481650', '7381482', '5488500', '6810000', '5597000'
])
TARGET_12 = [str(s).lstrip('0') for s in TARGET_12]
CASE_3 = ['6606600', '5481650', '8096500']


def stochasticity_metrics(Q, H, n_bins=N_BINS, min_per_bin=MIN_PER_BIN):
    Q = np.asarray(Q, float)
    H = np.asarray(H, float)
    if len(Q) < MIN_OBS_POP:
        return None
    edges = np.unique(np.quantile(Q, np.linspace(0, 1, n_bins + 1)))
    if len(edges) < 4:
        return None
    b = np.digitize(Q, edges[1:-1])
    keep = np.zeros(len(H), bool)
    for u in np.unique(b):
        if np.sum(b == u) >= min_per_bin:
            keep |= (b == u)
    Hk, Qk, bk = H[keep], Q[keep], b[keep]
    if len(Hk) < MIN_OBS_POP:
        return None
    grand = Hk.mean()
    sst = np.sum((Hk - grand) ** 2)
    if sst <= 0:
        return None
    ssb = sum(np.sum(bk == u) * (Hk[bk == u].mean() - grand) ** 2
              for u in np.unique(bk))
    eta2 = ssb / sst
    iqrs = [np.percentile(Hk[bk == u], 75) - np.percentile(Hk[bk == u], 25)
            for u in np.unique(bk)]
    rho, _ = spearmanr(Qk, Hk)
    return dict(n_obs=int(len(Hk)), stoch=float(1 - eta2),
                mean_iqr=float(np.mean(iqrs)),
                rho=float(rho) if not np.isnan(rho) else np.nan)


print("Screening full population (no outcome gates)...")
pop_records, n_seen = [], 0
for sn, grp in grouped_ifmha:
    n_seen += 1
    df_s = grp[['discharge_m3s', 'stage_m']].dropna()
    df_s = df_s[(df_s['discharge_m3s'] > 0) & (df_s['stage_m'] > 0) &
                (df_s['stage_m'] < 20)]
    if len(df_s) < MIN_OBS_POP:
        continue
    Q, H = df_s['discharge_m3s'].values, df_s['stage_m'].values
    q_lo, q_hi = np.percentile(Q, 1), np.percentile(Q, 99)
    h_lo, h_hi = np.percentile(H, 1), np.percentile(H, 99)
    m = (Q >= q_lo) & (Q <= q_hi) & (H >= h_lo) & (H <= h_hi)
    Q, H = Q[m], H[m]
    if len(Q) < MIN_OBS_POP:
        continue
    met = stochasticity_metrics(Q, H)
    if met is None:
        continue
    met['site_no'] = sn
    pop_records.append(met)

pop = pd.DataFrame(pop_records)
print(f"Sites examined:                 {n_seen}")
print(f"Sites with >= {MIN_OBS_POP} valid obs:     {len(pop)}")

meta = (ifmha_subset_stat.groupby('site_no')[[LAT, LON]]
        .median(numeric_only=True).reset_index())
pop = pop.merge(meta, on='site_no', how='left').dropna(subset=[LAT, LON])
pop = pop[(pop[LAT].between(24, 50)) & (pop[LON].between(-125, -66))].copy()
print(f"Sites with valid CONUS coordinates: {len(pop)}")

pop['group'] = 'all'
pop.loc[pop['site_no'].astype(str).isin(TARGET_12), 'group'] = 'figure_12'
pop.loc[pop['site_no'].astype(str).isin(CASE_3),   'group'] = 'case_study'

N = len(pop)
print()
for thresh in [0.10, 0.20, 0.30, 0.50]:
    frac = (pop['mean_iqr'] > thresh).mean()
    print(f"  mean within-bin stage IQR > {thresh:.2f} m : "
          f"{frac*100:5.1f}%  ({int(frac*N)} sites)")
print(f"\n  median across all {N:,} sites: {pop['mean_iqr'].median():.2f} m")

print("\nPercentile rank of the paper's sites within the full population:")
for sn in TARGET_12 + CASE_3:
    row = pop[pop['site_no'].astype(str) == sn]
    if row.empty:
        print(f"  {sn}: not found"); continue
    pct = (pop['mean_iqr'] < row['mean_iqr'].iloc[0]).mean() * 100
    print(f"  {sn}: mean_iqr={row['mean_iqr'].iloc[0]:.2f} m "
          f"({pct:.0f}th percentile)  group={row['group'].iloc[0]}")

pop.to_csv('data/processed/screening_cache/population_screening.csv', index=False)

# --- figure -------------------------------------------------------------------
# Extent given a bit more margin than the strict CONUS box (24-50N, 125-66W)
# so the southern border (Texas/Gulf Coast) has breathing room and doesn't
# sit flush against the legend box.
fig = plt.figure(figsize=(7.0, 4.3))
ax = fig.add_axes([0.03, 0.05, 0.80, 0.90], projection=ccrs.AlbersEqualArea(
    central_longitude=-96, standard_parallels=(29.5, 45.5)))
ax.set_extent([-127, -64, 22, 51], crs=ccrs.PlateCarree())
ax.add_feature(cfeature.LAND, facecolor='#FBFBFA', zorder=0)
ax.add_feature(cfeature.OCEAN, facecolor='#EAF2F6', zorder=0)
ax.add_feature(cfeature.LAKES.with_scale('50m'), facecolor='#EAF2F6',
               edgecolor='none', zorder=1)
ax.add_feature(cfeature.STATES.with_scale('50m'),
               linewidth=0.35, edgecolor='#9AA0A6', zorder=2)
ax.add_feature(cfeature.COASTLINE.with_scale('50m'),
               linewidth=0.5, edgecolor='#5F6368', zorder=2)

base = pop[pop['group'] == 'all']
vmax = pop['mean_iqr'].quantile(0.95)
sc = ax.scatter(base[LON], base[LAT], c=base['mean_iqr'], s=6,
                cmap='YlOrRd', vmin=0, vmax=vmax,
                alpha=0.55, linewidths=0, edgecolors='none',
                transform=ccrs.PlateCarree(), zorder=3)

f12_only = pop[pop['group'] == 'figure_12']
ax.scatter(f12_only[LON], f12_only[LAT], marker='o', s=55,
           facecolors='white', edgecolors='#1A237E', linewidths=1.4,
           transform=ccrs.PlateCarree(), zorder=4,
           label='Sites shown in Fig. 1 (n=12)')

c3 = pop[pop['group'] == 'case_study']
ax.scatter(c3[LON], c3[LAT], marker='o', s=100,
           facecolors='#1A237E', edgecolors='white', linewidths=1.1,
           transform=ccrs.PlateCarree(), zorder=5,
           label='Case-study sites (n=3)')

ax.legend(loc='lower left', frameon=True, framealpha=0.92,
          fontsize=10, borderpad=0.6, handletextpad=0.6)

cax = fig.add_axes([0.85, 0.10, 0.025, 0.80])
cb = fig.colorbar(sc, cax=cax, extend='max')
cb.set_label('Mean within-bin stage IQR (m)', fontsize=12)
cb.ax.tick_params(labelsize=10)

plt.savefig('fig_conus_stage_variability.png', dpi=600, bbox_inches='tight',
            facecolor='white')
plt.savefig('fig_conus_stage_variability.pdf', dpi=600, bbox_inches='tight',
            facecolor='white')
print("\nSaved fig_conus_stage_variability.png / .pdf")
plt.show()
