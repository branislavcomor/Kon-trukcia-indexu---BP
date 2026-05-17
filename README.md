# Konštrukcia indexu pomocou obálkovej analýzy dát

Kódy k bakalárskej práci **Konštrukcia indexu pomocou obálkovej analýzy dát**,
Univerzita Komenského v Bratislave, Fakulta matematiky, fyziky a informatiky, 2025.

**Autor:** Branislav Čomor  
**Vedúci práce:** doc. RNDr. Zuzana Chladná, Dr.

---

## O projekte

Práca sa zaoberá konštrukciou kompozitných indexov klimatického ohrozenia slovenských
obcí pomocou metódy obálkovej analýzy dát (DEA). Na rozdiel od tradičného váženého
priemeru DEA odvodzuje váhy jednotlivých ukazovateľov optimálne — bez nutnosti ich
subjektívneho určenia.

Implementované sú tri indexy:
- **Index ohrozenia extrémnymi horúčavami**
- **Index ohrozenia suchom**
- **Index ohrozenia extrémnymi zrážkami**

Pre každý index sú porovnané dva prístupy:
- **Radiálny model** bez obmedzení na váhy
- **Radiálny model s preferenčnou maticou Q** (Assurance Region obmedzenia)

---

## Štruktúra repozitára

```
├── radialny_model.py      # Radiálny model bez preferenčných obmedzení
├── radialny_model_Q.py    # Radiálny model s preferenčnou maticou Q
├── mapa.py                # Vizualizácia výsledkov na mape Slovenska
└── README.md
```

---

## Metodika

### Radiálny model (bez Q)

Výstupovo orientovaný radiálny model bez vstupov. Pre každú obec *o* sa rieši:

```
max  η
s.t. Y λ ≥ η · y_o
     e^T λ ≤ 1
     λ ≥ 0
```

kde `Y` je matica výstupov všetkých obcí, `y_o` je vektor výstupov hodnotennej obce
a `η` je miera ohrozenia (η = 1 znamená obec na efektívnej hranici).

### Radiálny model s preferenčnou maticou Q

Rozšírenie o preferenčné obmedzenia:

```
max  η
s.t. Y λ + Q τ ≥ η · y_o
     e^T λ ≤ 1
     λ ≥ 0,  τ ≥ 0
```

Matica Q implementuje Assurance Region (AR) obmedzenia, ktoré vymedzujú prípustné
pomery medzi váhami výstupov.

---

## Požiadavky

```
Python >= 3.9
pandas
numpy
scipy
geopandas    # pre vizualizáciu mapy
matplotlib
```

Inštalácia:
```bash
pip install pandas numpy scipy geopandas matplotlib
```

---

## Dáta

Vstupné dáta (`databaza.xlsx`) pochádzajú z analýzy IEP MŽP SR:

> *Vedúci! Horia obce!* (2023)  
> https://www.minzp.sk/iep/publikacie/ekonomicke-analyzy/veduci-horia-obce.html

Databáza je voľne dostupná na uvedenej stránke.
