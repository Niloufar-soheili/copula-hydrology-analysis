# Paper Style Guide — Fonts, Figures, Tables, Legends

This file is the single source of truth for formatting decisions in this
project's figures and tables. Anyone — in one session or a parallel one —
editing text, tables, or regenerating a figure should read this first and
keep it updated when a new convention is agreed on. If you change a
convention, edit this file in the same session so things don't drift.

Status legend used below: ✅ decided and applied · 🔲 decided, not yet
applied everywhere · ❓ not yet decided.

---

## 1. Document-level typography

- **Body text: 12pt**, `\documentclass[preprint,authoryear,review,12pt]{elsarticle}`.
  This is correct as-is — do not change. 12pt + `review` (double-spaced,
  single column, line numbers) is the standard combination for a
  reviewer-facing Elsevier manuscript. ✅
- Section/subsection headings: default `elsarticle` sizes, no manual
  override. ✅

## 2. Tables

- **Table text: `\small` (≈10.95pt at the 12pt document base)**, not
  `\resizebox{\textwidth}{!}{...}`. (Note: LaTeX's standard size ladder at
  12pt base is `\normalsize`=12 → `\small`=10.95 → `\footnotesize`=10 →
  `\scriptsize`=8 — `\small` is *not* exactly 10pt, that's `\footnotesize`.)
  `\resizebox` scales font size differently per table depending on content,
  which produces inconsistent, uncontrolled sizes across the paper. Use
  `tabularx` / `booktabs` (already loaded) for width control instead. 🔲 —
  decided, but existing tables in the manuscript still use `\resizebox` and
  need to be converted one at a time.
- Table footnotes (superscript notes below a table): `\footnotesize` (10pt). ✅
- Table captions: default caption style, no override. ✅

## 3. Figures — canonical `rcParams` block

Every figure-generating cell should start from this block (copy verbatim,
only add to it if a figure needs something extra — don't remove or shrink
any of these):

```python
plt.rcParams.update({
    'font.family':        'serif',
    'font.serif':         ['Times New Roman', 'DejaVu Serif'],

    'font.size':          12,
    'axes.titlesize':     12,
    'axes.labelsize':     12,
    'xtick.labelsize':    10,
    'ytick.labelsize':    10,
    'legend.fontsize':    11,   # see §5 — bumped from the old default of 10

    'figure.dpi':         150,
    'savefig.dpi':        600,
    'figure.facecolor':   'white',
    'axes.facecolor':     'white',
})
```

Multi-panel rating-curve style figures also add this grid/tick block
(see Fig. 2 gallery, cell 44, for the full version):

```python
'xtick.direction': 'in', 'ytick.direction': 'in',
'xtick.top': True, 'ytick.right': True,
'axes.grid': True, 'grid.color': '#D5D8DC', 'grid.linestyle': '-',
'grid.linewidth': 0.4, 'grid.alpha': 0.5,
'axes.linewidth': 0.5, 'axes.edgecolor': '#555555',
```

## 4. Figure widths

- Single full figure: `\includegraphics[width=\textwidth]{...}`, source
  figure built at **7.0 in** wide in matplotlib (`FIG_WIDTH = 7.0`). ✅
- Side-by-side subfigures: `0.49\textwidth` each in LaTeX. ✅
- Multi-panel galleries (e.g. Fig. 2's 12-site rating-curve grid): keep
  panels **wide enough to hit the sizes in §5 without any override**. If a
  layout forces per-panel text below 10pt, widen the grid (fewer columns,
  more rows) rather than shrinking fonts — this is exactly what happened
  going from 6×2 → 4×3 in Fig. 2. ✅ (established convention, applied to
  Fig. 2; apply to any future gallery-style figure)

## 5. Figure text size categories (the actual decision)

These are **categories**, not per-figure choices — the same category should
render at the same size in every figure, full stop.

| Category | Size | Notes |
|---|---|---|
| Panel/axes title | **12pt** | matches `axes.titlesize` |
| Axis labels (incl. shared `supxlabel`/`supylabel`) | **12pt** | matches `axes.labelsize` |
| Tick labels | **10pt** | matches `xtick`/`ytick.labelsize` |
| Legend text | **11pt** | see §6 — set explicitly on the legend call, don't rely on the `legend.fontsize` rcParam alone for older figures still at 10 |
| Colorbar label | **11.5pt** | one exception: a vertical colorbar is narrow, 11.5 is the largest that doesn't crowd the bar (see Fig. 1) |
| Colorbar ticks | **10pt** | matches tick-label category |
| Small-space labels (e.g. numbered site badges on a map) | as small as needed, **6pt minimum working value used so far** | **only** when literal physical collision is unavoidable — this is not a category, it's an explicitly-flagged exception. Never shrink a *category* to solve a one-off collision; shrink only that one element and say so in a code comment |

Do not introduce new one-off sizes (e.g. 8.5, 7, 6.5) for title/tick/legend
text the way the original Fig. 2 code did — that was the exact problem this
guide exists to prevent.

**Point size alone is not enough — physical figure size matters just as
much.** `\includegraphics[width=\textwidth]` rescales the *entire* source
image, text included, to fit the page. A figure built wider than the
canonical 7.0in (§4) gets shrunk on insertion, and its "12pt" title prints
smaller than a 12pt title in a figure that was actually built at 7.0in. This
is exactly what happened with `rating_curve_qq_grid.png`: it was built at
13.6in wide, so even after matching every rcParam to Fig. 1/Fig. 2 it still
rendered visibly smaller once placed in the paper. Fix: **always build the
source figure at the canonical 7.0in width**, not just the canonical point
sizes — see cell/script comments at the point sizes are meaningless without
also matching the physical scale. Rescaling a figure down to 7.0in will
usually also require re-tuning `wspace`/`hspace` and any long axis-label
strings (wrap onto 2 lines rather than widen the panel) — same-size text in
a narrower panel needs more relative room, not less.

**Second layer of the same trap: `savefig.bbox: 'tight'` silently un-does the
7.0in you set.** Setting `figsize=(7.0, ...)` controls the *nominal* figure
size, but `bbox_inches='tight'` (set as a module-level rcParam in
`_make_composite_figs.py`, and used the same way for Fig. 1/Fig. 2) crops
the saved raster to its actual content bounding box afterward — and that
box drifts by a different amount per figure depending on how far labels/
legends overhang the axes. Measured on this project's own figures, all
nominally 7.0in: `fig1_conus_map.png` saved at 6.78in, the Fig. 2 gallery at
7.08in, `rating_curve_qq_grid.png` at **8.06in**. Since `\includegraphics
[width=\textwidth]` rescales the whole raster to the page width regardless
of its native size, this drift changes the effective printed point size
differently per figure even when every rcParam matches exactly — the same
consequence as §5's first physical-size warning, one level further down the
pipeline where it's easy to miss because the *code* still says `figsize=
(7.0, ...)`.

Fix, if a figure's saved width needs to be pinned exactly (verify with
`PIL.Image.open(path).size` and its `dpi` — `width_px / dpi_x` gives the
actual inches): override the rcParam in a scoped context around that
figure's `savefig` call only —

```python
with plt.rc_context({"savefig.bbox": None}):
    fig.savefig(path, facecolor="white")
```

(`bbox_inches=None` passed directly to `savefig` does **not** work — that
argument's default *is* "use the rcParam," so passing `None` just falls
back to whatever the rcParam already says, i.e. still `'tight'`.) Applied
to `site_summary_panel.png`, now pinned at exactly 7.000in. **Not yet
applied to Fig. 1, the Fig. 2 gallery, or `rating_curve_qq_grid.png`** —
their widths still drift as measured above; revisit if their effective font
size ever looks off relative to a figure that has been pinned.

## 5b. Dense-scatter marker edges (avoiding the "faded" look)

A colored marker with a white edge (`edgecolors='w'`) looks fine in
isolation, but where many points overlap tightly — e.g. the low-quantile
end of a Q-Q plot for a right-skewed marginal, which compresses points into
a narrow x-range — the overlapping white rings blend into a pale haze. It
reads as "the data faded," but it's really borders piling up, not a change
in the data or its color. `fig_copula_sites_clean_v2.png` (the canonical
polished reference — `scripts/_cell_copula_plot_only.py`) avoids this by
using **no edge** (`edgecolors='none'`) for its dense/background point
layer, while keeping a white edge for its sparser foreground layer. Rule:
if a scatter layer is dense enough that points regularly overlap, drop the
white edge; keep it only for layers sparse enough that the edge stays
crisp. (Applied to the Q-Q columns in `rating_curve_qq_grid.png`; the RC
column's points are sparser and keep the white edge, matching
`fig_copula_sites_clean_v2.png`'s own high-flow layer: `s=7, alpha=0.85,
edgecolors='w', linewidth=0.2`.)

## 6. Legends — placement and style

**Decision: legends go at the bottom of the figure**, not tucked inside a
corner of one panel. Two accepted placements:

1. **Multi-panel grid figures** (e.g. Fig. 2 gallery): one shared legend
   for the whole figure, bottom-right, sitting on the same row as the
   x-axis `supxlabel`. Do **not** put a separate legend inside any
   individual panel.
2. **Single-axes figures** (e.g. Fig. 1 map): legend inside the plot area,
   bottom-left (or wherever there's genuinely empty space — for Fig. 1 that
   was the map's blank interior).

Standard legend style (match these params everywhere):

```python
frameon=True, framealpha=0.92, edgecolor='#bbbbbb', fontsize=11,
borderpad=0.6, handletextpad=0.6
```

For a shared bottom-right legend built from proxy handles (`Line2D`), see
Fig. 2 gallery cell 44 for the working pattern:

```python
from matplotlib.lines import Line2D
legend_items = [Line2D([], [], color=..., lw=1.4, ls='--', label='...'), ...]
fig.legend(handles=legend_items, loc='center right', ncol=2,
           bbox_to_anchor=(0.99, 0.06), bbox_transform=fig.transFigure,
           frameon=True, framealpha=0.92, edgecolor='#bbbbbb', fontsize=11,
           borderpad=0.6, handletextpad=0.6, columnspacing=1.4)
```

Status: ✅ applied to Fig. 1 (map, bottom-left-in-axes) and Fig. 2 (gallery,
bottom-right shared). 🔲 not yet applied to any figure beyond these two —
apply this same rule when we get to each remaining Results figure.

## 6b. Scatter marker size

**Marker size (`s` in `ax.scatter`) must scale with panel size, the same
way font size does.** A marker tuned for a large panel (e.g. `s=20` on a
3.9in-wide panel) will overlap into an illegible blob once the panel is
rescaled down to the canonical width, flattening exactly the visual spread
a scatter plot exists to show. **Decision: `s=6`**, `edgecolors='w'`,
`linewidth=0.15` for scatter points in any panel around the Fig. 2 gallery's
~1.75–2in size (established value, copied directly from Fig. 2). Re-check
this any time a panel's physical size changes for any reason (see §5's note
on physical figure size) — it's coupled to panel size, not a fixed global
constant.

**Draw order matters as much as marker size.** Data points must have a
higher `zorder` than any fit/reference line drawn through or near them —
otherwise the line paints over points that sit close to it, which for a
good-fitting Q-Q or rating-curve line is most of them. This is easy to miss
because it looks like "the dots got smaller" when actually they're being
hidden, not shrunk (this happened in `rating_curve_qq_grid.png`: line was
`zorder=4`, points `zorder=3` — swapped to fix). Points: `zorder=4`;
fit/reference lines: `zorder=3`, in every figure.

## 6c. Repeated axis-label text (Q-Q style plots)

When the same explanatory phrase would otherwise repeat across every panel
of a multi-panel figure (e.g. "Theoretical quantiles (Gamma)" on 6 different
Q-Q panels), prefer a short per-panel label (just the distribution name,
e.g. "Gamma") plus one sentence in the caption explaining what the axis
represents, over cramming the full phrase into every panel. This also
sidesteps line-wrapping/collision fights in narrow panels — see
`rating_curve_qq_grid.png`'s Q-Q columns.

## 7. Panel title wording

For numbered multi-site figures, panel titles read **`"N. Site XXXXXXXX"`**
(number, period, space, "Site", space, USGS site number) — not bare
`"N. XXXXXXXX"`. Applied to Fig. 2. Apply the same wording to any other
numbered per-site panel figure (e.g. the probabilistic rating-curve gallery,
if one gets rebuilt in this style).

## 8. Color conventions established so far

| Element | Color | Used in |
|---|---|---|
| Observed data points (rating-curve scatter) | `#004080` (navy) | Fig. 2 |
| P50 / median discharge line | `#388E3C` (green), dashed | Fig. 1 caption reference, Fig. 2 |
| P99 discharge line | `#FF0000` (red), solid | Fig. 1 caption reference, Fig. 2 |
| Site variability colormap (CONUS map) | `YlOrRd` | Fig. 1 |
| Numbered site badge markers | white fill, `#1A237E` (dark indigo) edge/text | Fig. 1, Fig. 2 legend swatches |

Not yet standardized: predictive-interval band colors/opacity, deterministic
vs. copula-median line colors in the probabilistic rating curve figures
(Figs. 3–4 in the manuscript numbering, not yet revisited this session).

## 9. Figure regeneration workflow (for parallel sessions)

- Figures 1 and 2 (CONUS map, RC gallery) are generated from
  `final_abnormal_sites_12may.ipynb`, cells 40/42 (map) and 44 (gallery).
- The notebook was written for Google Colab (`INPUT_FILE_PATH =
  '/content/drive/...'`, `google.colab.drive.mount(...)`). Locally, the
  same data lives at `ifmha_subset_stat.csv` (760MB) in the project root —
  swap the path, skip the Drive mount, everything else runs unchanged.
- `population_screening.csv` (written by cell 40) is a cached copy of the
  full 6,323-site population screening (`pop` dataframe). **Reuse this file**
  instead of re-running the ~6,500-site screening loop when only Fig. 2 (or
  anything else downstream of `pop`) needs regenerating — see
  `scripts/_run_fig2.py` for the pattern (load CSV → rebuild
  `grouped_ifmha` → `pd.read_csv('population_screening.csv')` instead of
  recomputing `pop`).
- `scripts/_run_fig1.py` / `_run_fig2.py` are standalone drivers that
  extract the relevant notebook cell(s) via `json.load` + `exec(...)` and
  run them outside Jupyter (Windows `python.exe` in `.venv`). Edit the
  notebook cell first (that's the source of truth), then re-extract and
  re-run — don't hand-edit the driver scripts' embedded logic.
- `fig2_rc_2.png`/`.pdf` is the filename actually referenced by the
  manuscript's `\includegraphics`; the notebook cell saves to
  `fig2_rc_gallery.png`/`.pdf`. **Always copy the gallery output over
  `fig2_rc_2.*` after regenerating** — the two must stay byte-identical.

## 10. Table conversion example (§2 applied)

`tab:variability_factors` (the geomorphic/hydraulic/network-scale/data-quality
factors table) was converted from `\resizebox{\textwidth}{!}{...}` to
`\small` + `tabularx`, per §2. Use this as the template for converting the
paper's other remaining `\resizebox` tables — same pattern: drop
`\resizebox`, add `\small`, switch the tabular environment to `tabularx`
with a single `X` (auto-wrapping) column for the longest/prose-heavy column,
and pull `\arraystretch` down from 1.4 to 1.15 to stop the table from
running tall. Requires `\usepackage{tabularx}`, already loaded.

```latex
\begin{table}[H]
\centering
\small
\caption{Factors examined from the IFMHA dataset and their relationship to
site-level stage--discharge variability.}
\label{tab:variability_factors}
\renewcommand{\arraystretch}{1.15}
\begin{tabularx}{\textwidth}{@{}
  >{\raggedright\arraybackslash}p{0.16\textwidth}
  >{\raggedright\arraybackslash}p{0.22\textwidth}
  X @{}}
\toprule
\textbf{Category} & \textbf{Factor} & \textbf{Relationship to variability} \\
\midrule
\multirow{2}{0.16\textwidth}{Geomorphic control}
  & Channel material\textsuperscript{a}
  & Fine, mobile substrate (silt, sand) $\rightarrow$ more variable \\
  & Channel bed stability
  & Soft, mobile bed $\rightarrow$ more variable \\
\cmidrule(l){1-3}
Hydraulic control
  & Channel slope
  & Lower gradient $\rightarrow$ more variable \\
\cmidrule(l){1-3}
\multirow{2}{0.16\textwidth}{Network-scale control}
  & Drainage area
  & Larger drainage area $\rightarrow$ more variable \\
  & Stream order
  & Higher stream order $\rightarrow$ more variable \\
\cmidrule(l){1-3}
Data quality
  & High-flow measurement method
  & Greater reliance on indirect methods (cableway, bridge, boat) $\rightarrow$ more variable \\
\bottomrule
\end{tabularx}

\vspace{2pt}
{\footnotesize \textsuperscript{a}Silt, sand, gravel, cobble, boulder.}
\end{table}
```

Why this is more compact than the original: `\resizebox{\textwidth}{!}`
forces the table to span the *entire* text width regardless of how little
text it holds, which is what was making it tall (the auto-scale grows row
height along with everything else). The plain `l l X` version fixed the
sizing but still let the two label columns claim their full natural
single-line width ("Network-scale control", "High-flow measurement method"),
crowding the prose column. Giving Category/Factor **fixed, narrower**
widths (`p{0.16\textwidth}`, `p{0.22\textwidth}`) instead lets the longer
labels wrap onto 2 lines in their own cell — shorter overall, and it hands
the majority of the row back to the "Relationship" column, so that text
wraps less aggressively too. Same information, at `\small` (10pt) matching
every other table, in noticeably less vertical space than either earlier
version.

## 11. Per-figure status log

| Figure (manuscript label) | Source | Status |
|---|---|---|
| Fig. 1 — CONUS map (`fig:broad_variability`) | notebook cell 42 | ✅ font sizes + colorbar label wording fixed |
| Fig. 2 — 12-site RC gallery (`fig:site_rcs`) | `scripts/_cell44.py`, run via `scripts/_run_fig2.py` | ✅ font sizes, layout (4×3), legend placement, title wording all fixed. **2026-09-11: added the missing fitted rating curve** (`Q = C(H-H0)^n`, same model/bounds as everywhere else in the paper) — the panels previously showed only the raw scatter + P50/P99 discharge reference lines, no fitted curve at all. Legend widened to 3 columns ("Rating curve", "P50", "P99"). **Revised same day**: RC recolored red `#FF0000` and drawn at `zorder=5` (above both the `zorder=3` points and the `zorder=4` reference lines — a deliberate exception to §6b's "points above fit lines" default, needed here so the RC stays visible through the dense point cloud); P99 recolored to the green `#2E7D32` freed up by that swap (P50 stays the slightly different green `#388E3C`, dashed, so the two remain distinguishable by both shade and style). Re-copied over `fig2_rc_2.png`/`.pdf` per the byte-identical convention below. |
| `rating_curve_qq_grid.png` (case-study RC + Q-Q composite, ss3.3.1) | `_make_composite_figs.py`, "Fig B" section | ✅ font sizes, colors, grid/spine style, legend placement fixed; rescaled the source canvas from 13.6in to canonical 7.0in; **also** pinned the *actual saved* width to exactly 7.000in (was drifting to 8.06in under `bbox_inches='tight'`, see §5's `savefig.bbox` note) — required decoupling column width from row height (only width is canonically constrained), moving row labels from axes-fraction to figure-fraction placement, and sizing `LEFT_MARGIN_IN` (2.2in) to the row labels' actual measured text width + the y-axis label/tick overhang (measured via `get_tightbbox`, not guessed) + real buffer. Verified: exact 7.000in width, zero content touching any canvas edge, no inter-element overlaps |
| `site_summary_panel.png` (case-study catchment/distribution panel, ss3.3.1) | `_make_composite_figs.py`, "Fig A" section | ✅ simplified from a raincloud (KDE + box) plot to plain box plots per review (KDE clouds didn't read well for JoH); font sizes, grid/spine style brought in line with Fig. 1/Fig. 2; also the first figure with its *actual saved width* pinned to exactly 7.000in (see ss5's `savefig.bbox` note) rather than left to drift under `bbox_inches='tight'` |
| `FIGURE_3x3_copula_vs_gpr.png` (copula vs. standard/heteroscedastic GPR, 3 case-study sites) | **`_make_3x3_copula_vs_gpr.py`** (project root) - re-run this file to regenerate; it reads cached `_3x3_data_{site}.npz` + `case_study_figs/prob_rc_{site}.npz`, no re-fitting. (Previously this figure had no source script anywhere on disk - it had to be reverse-engineered from the npz caches once; this script is now the permanent source, so that never has to happen again.) | ✅ rescaled from 11.1in to canonical 7.0in, rcParams/grid/tick block matched to §3, dots matched to §6b/§8 (`s=6`, `#004080`, `zorder=4` above lines), legend moved to shared bottom placement per §6, column titles switched to `"USGS XXXXXXXX"` to match `rating_curve_qq_grid.png`, gray full-record background layer added matching `prob_rating_curves_row.png` (axis limits explicitly locked so this layer only adds context, doesn't change the crop) |
| Remaining Results figures (preprocessing scatter, FIM maps) | various | ❓ not yet reviewed this pass |

Update this table as each figure gets its consistency pass.
