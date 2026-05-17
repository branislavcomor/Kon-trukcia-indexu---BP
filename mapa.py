# -*- coding: utf-8 -*-
"""

"""

"""
mapa.py
-------
Vizualizácia výsledkov radiálneho modelu na mape Slovenska.

Vstupy:
  - json_hranice.txt  : TopoJSON s hranicami obcí SR
  - vysledky.xlsx     : Excel so stĺpcami 'id' a 'skupina' (1–10)

Výstup:
  - mapa.png          : mapa Slovenska s farebnými stupňami ohrozenia
"""

"""
mapa.py
-------
Vizualizácia výsledkov radiálneho modelu na mape Slovenska.

Vstupy:
  - json_hranice.txt  : TopoJSON s hranicami obcí SR
  - vysledky.xlsx     : Excel so stĺpcami 'id' a 'skupina' (1–10)

Výstup:
  - mapa.png          : mapa Slovenska s farebnými stupňami ohrozenia
"""

import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from shapely.geometry import shape

# =====================================================================
# 1. NASTAVENIA — uprav podľa potreby
# =====================================================================

TOPO_PATH      = "json_hranice.txt"              # cesta k TopoJSON súboru
VYSLEDKY_PATH  = "vysledky_horucavy_analyza.xlsx" # cesta k výsledkom
ID_COL         = "id"                             # názov stĺpca s ID obce
SKUPINA_COL    = "skupina_heat_q_5"               # názov stĺpca so skupinou (1–10)
NAZOV_INDEXU   = "Index ohrozenia extrémnymi horúčavami"
OUTPUT_PATH    = "mapa.png"

# =====================================================================
# 2. NAČÍTANIE TOPOJSON A PREVOD NA GEODATAFRAME
# =====================================================================

def topojson_to_geodataframe(topo_path, object_name="obce"):
    """Načíta TopoJSON a prevedie ho na GeoDataFrame."""
    with open(topo_path, encoding="utf-8") as f:
        topo = json.load(f)

    transform = topo.get("transform", {})
    scale  = transform.get("scale",     [1, 1])
    transl = transform.get("translate", [0, 0])

    def decode_arc(arc):
        """Dekóduje delta-kódovaný arc na súradnice."""
        coords = []
        x, y = 0, 0
        for dx, dy in arc:
            x += dx
            y += dy
            coords.append([
                x * scale[0] + transl[0],
                y * scale[1] + transl[1]
            ])
        return coords

    arcs = [decode_arc(a) for a in topo["arcs"]]

    def resolve_arcs(arc_indices):
        """Zostaví ring zo zoznamu indexov arcov."""
        ring = []
        for idx in arc_indices:
            if idx >= 0:
                seg = arcs[idx]
            else:
                seg = arcs[~idx][::-1]
            ring.extend(seg if not ring else seg[1:])
        return ring

    rows = []
    for geom in topo["objects"][object_name]["geometries"]:
        props = geom.get("properties", {})
        gtype = geom["type"]
        arcs_raw = geom.get("arcs", [])

        if gtype == "Polygon":
            rings = [resolve_arcs(r) for r in arcs_raw]
            geo = {"type": "Polygon", "coordinates": rings}
        elif gtype == "MultiPolygon":
            polys = [[resolve_arcs(r) for r in poly] for poly in arcs_raw]
            geo = {"type": "MultiPolygon", "coordinates": polys}
        else:
            continue

        rows.append({
            "geometry": shape(geo),
            "id_full":  geom.get("id", ""),
            "name":     props.get("name", ""),
        })

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    # Skrátime ID na posledných 6 číslic pre zlúčenie s databázou
    gdf["id"] = gdf["id_full"].str[-6:]
    return gdf


# =====================================================================
# 3. NAČÍTANIE VÝSLEDKOV
# =====================================================================

def load_results(path, id_col, skupina_col):
    df = pd.read_excel(path)
    df[id_col] = df[id_col].astype(str).str.strip().str.zfill(6)
    return df[[id_col, skupina_col]].copy()


# =====================================================================
# 4. VIZUALIZÁCIA
# =====================================================================

def plot_map(gdf_merged, skupina_col, nazov, output_path):
    # Farebná paleta: zelená (nízke ohrozenie) → červená (vysoké ohrozenie)
    colors = [
        "#1a9850", "#66bd63", "#a6d96a", "#d9ef8b", "#ffffbf",
        "#fee08b", "#fdae61", "#f46d43", "#d73027", "#a50026"
    ]

    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_axis_off()

    # Kresli skupiny 1–10
    for skupina in range(1, 11):
        subset = gdf_merged[gdf_merged[skupina_col] == skupina]
        if len(subset) > 0:
            subset.plot(ax=ax, color=colors[skupina - 1],
                        linewidth=0.05, edgecolor="#888888")

    # Obce bez výsledku (NaN) — šedá
    no_data = gdf_merged[gdf_merged[skupina_col].isna()]
    if len(no_data) > 0:
        no_data.plot(ax=ax, color="#cccccc",
                     linewidth=0.05, edgecolor="#888888")

    # Legenda
    patches = [
        mpatches.Patch(color=colors[i],
                       label=f"Stupeň {i+1}" + (" (najnižší)" if i == 0
                             else " (najvyšší)" if i == 9 else ""))
        for i in range(10)
    ]
    ax.legend(handles=patches, loc="lower left", fontsize=8,
              title="Stupeň ohrozenia", title_fontsize=9,
              framealpha=0.9, ncol=2)

    ax.set_title(nazov, fontsize=14, pad=12, color="#2C2C2A")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight",
                facecolor="white")
    plt.close()
    print(f"Mapa uložená: {output_path}")


# =====================================================================
# 5. HLAVNÝ SKRIPT
# =====================================================================

if __name__ == "__main__":

    print("Načítavam TopoJSON...")
    gdf = topojson_to_geodataframe(TOPO_PATH)
    print(f"  Načítaných {len(gdf)} obcí z TopoJSON.")

    print("Načítavam výsledky...")
    df_res = load_results(VYSLEDKY_PATH, ID_COL, SKUPINA_COL)
    print(f"  Načítaných {len(df_res)} obcí z výsledkov.")

    print("Zlučujem dáta...")
    gdf_merged = gdf.merge(df_res, on="id", how="left")
    matched = gdf_merged[SKUPINA_COL].notna().sum()
    print(f"  Zlúčených {matched} obcí.")

    print("Kreslím mapu...")
    plot_map(gdf_merged, SKUPINA_COL, NAZOV_INDEXU, OUTPUT_PATH)
