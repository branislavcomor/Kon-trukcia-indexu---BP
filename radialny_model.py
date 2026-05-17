"""
radialny_model.py
-----------------
Radiálny model bez preferenčných obmedzení (CCR) a s preferenčnou
maticou Q (Assurance Region obmedzenia) — výpočet pre oba modely naraz.

Vstup:  databaza.xlsx   — databáza klimatických ukazovateľov
Výstup: vysledky.xlsx   — skóre a skupiny (1–10) pre oba modely

Použitie:
    python radialny_model.py
"""

import pandas as pd
import numpy as np
from scipy.optimize import linprog

# =====================================================================
# 1. NASTAVENIA — uprav podľa potreby
# =====================================================================

FILE_PATH   = "databaza.xlsx"   # cesta k vstupným dátam
SHEET_NAME  = "data"            # názov listu v Exceli
OUTPUT_PATH = "vysledky.xlsx"   # cesta k výstupu

# Názvy stĺpcov s ukazovateľmi
# Poradie zodpovedá u1, u2, ..., u6 v preferenčnej matici Q
FEATURES = [
    "haz_heat_clim_45",    # u1: budúce extrémne horúčavy
    "haz_heat_days",       # u2: tropické dni
    "soc_pop_age70plus",   # u3: seniori nad 70 rokov
    "soc_pop_age_up4",     # u4: deti do 4 rokov
    "l_cov_urb_tcd",       # u5: stromy v sídlach
    "l_cov_urb_imd",       # u6: nepriepustné povrchy
]

# Ukazovatele kde NIŽŠIA hodnota = vyššie ohrozenie (treba otočiť)
FLIP = ["l_cov_urb_tcd"]

EPSILON = 1e-6   # náhrada nulových hodnôt po normalizácii

# =====================================================================
# 2. PREFERENČNÁ MATICA Q
#
# Bodová logika: 25 / 35 / 5 / 5 / 15 / 15
# Cieľové pomery susedných váh:
#   u2/u1 = 1.4,  u3/u2 = 1/7,  u4/u3 = 1.0,  u5/u4 = 3.0,  u6/u5 = 1.0
#
# Intervaly ±10 % okolo cieľových pomerov.
# =====================================================================

TARGET_RATIOS = [1.4, 1/7, 1.0, 3.0, 1.0]   # u2/u1, u3/u2, u4/u3, u5/u4, u6/u5
REL_WIDTH     = 0.10                           # ±10 %


def build_Q(target_ratios, rel_width):
    """
    Zostrojí maticu Q z cieľových pomerov a relatívnej šírky intervalov.

    Pre každý pomer a <= u_{k+1}/u_k <= b sú pridané dva stĺpce:
        [ a, -1, 0, ... ]   (dolná hranica: a*u_k - u_{k+1} <= 0)
        [-b,  1, 0, ... ]   (horná hranica: -b*u_k + u_{k+1} <= 0)
    """
    m = len(target_ratios) + 1
    q = 2 * len(target_ratios)
    Q = np.zeros((m, q))
    for k, r in enumerate(target_ratios):
        lo = r * (1 - rel_width)
        hi = r * (1 + rel_width)
        Q[k,     2 * k]     =  lo
        Q[k + 1, 2 * k]     = -1.0
        Q[k,     2 * k + 1] = -hi
        Q[k + 1, 2 * k + 1] =  1.0
    return Q


Q = build_Q(TARGET_RATIOS, REL_WIDTH)

# =====================================================================
# 3. NAČÍTANIE A PRÍPRAVA DÁT
# =====================================================================

df = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)
df = df.iloc[1:].copy().reset_index(drop=True)   # prvý riadok = popis

base_cols = ["dist", "muni", "id"] + FEATURES
df = df[base_cols].copy()
for c in FEATURES:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df = df.dropna(subset=FEATURES).reset_index(drop=True)

print(f"Načítaných {len(df)} obcí.")

# =====================================================================
# 4. NORMALIZÁCIA (min-max, vyššie = väčšie ohrozenie)
# =====================================================================

def minmax(s):
    mn, mx = s.min(), s.max()
    return (s - mn) / (mx - mn) if mx > mn else pd.Series(0.0, index=s.index)

norm = df.copy()
for c in FEATURES:
    norm[c] = 1.0 - minmax(df[c]) if c in FLIP else minmax(df[c])
    norm[c] = norm[c].clip(lower=EPSILON)

Y = norm[FEATURES].to_numpy().T   # matica výstupov (m x n)
m, n = Y.shape

# =====================================================================
# 5. SOLVERY
# =====================================================================

def solve_ccr(y_o, Y):
    """Radiálny model bez Q."""
    m, n = Y.shape
    tv = n + 1
    c  = np.zeros(tv); c[-1] = -1.0
    A, b = [], []
    for r in range(m):
        row = np.zeros(tv)
        row[:n] = -Y[r, :]; row[-1] = y_o[r]
        A.append(row); b.append(0.0)
    row = np.zeros(tv); row[:n] = 1.0
    A.append(row); b.append(1.0)
    bounds = [(0, None)] * n + [(None, None)]
    res = linprog(c=c, A_ub=np.array(A), b_ub=np.array(b),
                  bounds=bounds, method="highs")
    return res.x[-1] if res.success else float("nan")


def solve_q(y_o, Y, Q):
    """Radiálny model s preferenčnou maticou Q."""
    m, n = Y.shape
    q    = Q.shape[1]
    tv   = n + q + 1
    c    = np.zeros(tv); c[-1] = -1.0
    A, b = [], []
    for r in range(m):
        row = np.zeros(tv)
        row[:n]      = -Y[r, :]
        row[n:n + q] = -Q[r, :]
        row[-1]      = y_o[r]
        A.append(row); b.append(0.0)
    row = np.zeros(tv); row[:n] = 1.0
    A.append(row); b.append(1.0)
    bounds = [(0, None)] * (n + q) + [(None, None)]
    res = linprog(c=c, A_ub=np.array(A), b_ub=np.array(b),
                  bounds=bounds, method="highs")
    return res.x[-1] if res.success else float("nan")

# =====================================================================
# 6. VÝPOČET PRE VŠETKY OBCE
# =====================================================================

etas_ccr, etas_q = [], []

for o in range(n):
    if o % 500 == 0:
        print(f"  Počítam {o + 1}/{n} ...")
    y_o = Y[:, o]
    etas_ccr.append(solve_ccr(y_o, Y))
    etas_q.append(solve_q(y_o, Y, Q))

df["score_ccr"] = etas_ccr
df["score_Q"]   = etas_q

# =====================================================================
# 7. ROZDELENIE DO 10 SKUPÍN (1 = najmenej, 10 = najviac ohrozené)
# =====================================================================

def make_groups(s):
    raw = pd.qcut(s, q=10, labels=False, duplicates="drop")
    return (10 - raw).astype(int)

df["skupina_ccr"] = make_groups(df["score_ccr"])
df["skupina_Q"]   = make_groups(df["score_Q"])

# =====================================================================
# 8. VÝPIS ŠTATISTÍK
# =====================================================================

tol = 1e-6
for name, sc, sk in [("CCR", "score_ccr", "skupina_ccr"),
                      ("Q",   "score_Q",   "skupina_Q")]:
    n_ef = (np.abs(df[sc] - 1.0) <= tol).sum()
    print(f"\n--- {name} model ---")
    print(f"  Obcí na efektívnej hranici: {n_ef}")
    print(f"  Min skóre: {df[sc].min():.4f}  |  Max skóre: {df[sc].max():.4f}")
    print(f"  Najviac ohrozené obce (skupina 10):")
    top = df[df[sk] == 10][["muni", "dist", sc]].head(5)
    print(top.to_string(index=False))

# =====================================================================
# 9. EXPORT
# =====================================================================

out = df[["dist", "muni", "id",
          "score_ccr", "skupina_ccr",
          "score_Q",   "skupina_Q"]].copy()
out.to_excel(OUTPUT_PATH, index=False)
print(f"\nVýsledky uložené: {OUTPUT_PATH}")
