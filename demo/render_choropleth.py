"""
demo/render_choropleth.py

a harvested choropleth, drawn to be read ~ the picture of a map that
`rewilding map` writes as geojson

  python demo/render_choropleth.py plots/maine/harvest/map_cii_broadband.geojson

drawn in Maine's own projected frame so the state keeps its true shape, on a
fixed 0 to 100 scale for percentiles so the colours mean the same thing on
every map, with each county named and valued in place, a legend that says what
the number is, and a caption that says what it cannot say.

it refuses to draw if two units share one geometry. that is GEO-1, which
turned sixteen counties into sixteen copies of the state, and a handsome
picture of that would be worse than no picture. ♡
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python demo/render_choropleth.py")
    ap.add_argument("geojson")
    ap.add_argument("--out", help="png path (default: beside the geojson)")
    ap.add_argument("--title", default="Households with broadband, among the nation's counties")
    ap.add_argument("--subtitle", default="ACS 2020-2024, recomputed in rewildingCities; agrees with CII 2026 in all 16 counties")
    ap.add_argument("--label-field", default="COUNTY")
    ap.add_argument("--crs", default="EPSG:26983", help="frame to draw in (default Maine East)")
    a = ap.parse_args(argv)

    import geopandas as gpd
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable

    path = Path(a.geojson)
    meta = json.loads(path.read_text()).get("rewilding:map", {})
    col = meta.get("color_by") or "percentile"
    g = gpd.read_file(path)
    if col not in g.columns:
        print(f"refused: no '{col}' column to colour by. columns: {', '.join(g.columns)}", file=sys.stderr)
        return 1

    m = g.to_crs(a.crs)
    areas = m.geometry.area.round()
    if len(m) > 1 and areas.nunique() < len(m):
        print(f"refused: {len(m) - areas.nunique()} unit(s) share a geometry with another (GEO-1). "
              f"rerun the boundary chain with the fixed dissolve before drawing.", file=sys.stderr)
        return 1

    pct = col == "percentile"
    vals = m[col].astype(float)
    norm = Normalize(0, 100) if pct else Normalize(vals.min(), vals.max())
    cmap = plt.get_cmap("YlGnBu")

    fig, ax = plt.subplots(figsize=(7.2, 9.6))
    present = vals.notna()
    m[present].plot(ax=ax, color=[cmap(norm(v)) for v in vals[present]],
                    edgecolor="white", linewidth=0.9)
    if (~present).any():
        m[~present].plot(ax=ax, color="#e6e6e6", edgecolor="white", linewidth=0.9, hatch="///")

    halo = [pe.withStroke(linewidth=2.6, foreground="white")]
    for _, r in m.iterrows():
        p = r.geometry.representative_point()
        v = r[col]
        value = "no value" if v != v or v is None else (f"{v:.0f}" if pct else f"{v:.1f}")
        name = str(r.get(a.label_field, "")).replace(" County", "")
        ax.annotate(f"{name}\n{value}", (p.x, p.y), ha="center", va="center",
                    fontsize=7.2, color="#1f2a30", path_effects=halo)

    sm = ScalarMappable(norm=norm, cmap=cmap)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.01, shrink=0.55)
    cbar.set_label("national percentile (0 to 100)" if pct else col, fontsize=8)
    cbar.ax.tick_params(labelsize=7)
    cbar.outline.set_visible(False)

    ax.set_title(f"{a.title}\n", fontsize=12, loc="left", fontweight="bold", color="#1f2a30")
    ax.text(0, 1.0, a.subtitle, transform=ax.transAxes, fontsize=8, color="#55606a", va="bottom")
    caption = ("A percentile says how a county compares with the nation's 3,144, never whether its "
               "broadband is enough." if pct else "")
    unjoined = meta.get("unjoined_rows")
    prov = (f"{len(m)} counties drawn; joined on {meta.get('join_on', '?')} by derivation"
            + (f"; {unjoined} rows of the national result fall outside this plot" if unjoined else ""))
    fig.text(0.06, 0.035, caption, fontsize=7.5, color="#55606a", style="italic")
    fig.text(0.06, 0.018, prov, fontsize=6.8, color="#8a949c")

    ax.set_axis_off()
    out = Path(a.out) if a.out else path.with_suffix(".png")
    fig.savefig(out, dpi=220, bbox_inches="tight", facecolor="white")
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
