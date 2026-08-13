"""
src/build_dataset.py

Pipeline de consolidación: ENEMDU dic-2025 (base de personas) +
parámetros técnicos de cultivos -> dataset unificado.

Salidas (data/processed/):
    pea_rural_agricola.csv   microdatos ponderables de PEA rural
    cultivos_metricas.csv    metricas $/ha y empleos/ha de 6 cultivos
    indicadores_macro.csv    KPIs laborales ponderados

Ejecutar desde la raiz del proyecto:
    python src/build_dataset.py
"""

import re
from pathlib import Path

import pandas as pd
import pyreadstat

# ---------------------------------------------------------------------------
# RUTAS (se calculan desde la posicion de este script: a prueba de espacios)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
RAW = BASE_DIR / "data" / "raw"
PROCESSED = BASE_DIR / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

# De los 3 .sav disponibles usamos SOLO la base de PERSONAS (15+ anos)
ENEMDU_SAV = RAW / "1_BDD_ENEMDU_2025_12_SPSS" / "enemdu_persona_2025_12.sav"

# ---------------------------------------------------------------------------
# PARAMETROS OFICIALES (Guia de uso BDD ENEMDU dic-2025)
# ---------------------------------------------------------------------------
ZONA_RURAL = 2        # zona: 1=Urbana, 2=Rural
RAMA_AGRO = "A"       # rama1 CIIU Rev.4
SBU_MENSUAL = 470.0   # Salario Basico Unificado 2025 (USD/mes)

# ---------------------------------------------------------------------------
# PARAMETROS TECNICOS DE CULTIVOS (calibrados MAG/SIPA + benchmarks)
# ---------------------------------------------------------------------------
PARAMETROS_CULTIVOS = [
    {"cultivo": "Arándano", "tipo": "alto_valor", "rend_kg_ha": 8000,
     "precio_usd_kg": 4.50, "costo_usd_ha": 22000, "empleos_ha": 2.8, "jornales_ha": 260},
    {"cultivo": "Pitahaya", "tipo": "alto_valor", "rend_kg_ha": 12000,
     "precio_usd_kg": 2.20, "costo_usd_ha": 15000, "empleos_ha": 2.0, "jornales_ha": 240},
    {"cultivo": "Uvilla", "tipo": "alto_valor", "rend_kg_ha": 9000,
     "precio_usd_kg": 1.60, "costo_usd_ha": 9000, "empleos_ha": 1.8, "jornales_ha": 220},
    {"cultivo": "Aguacate Hass", "tipo": "alto_valor", "rend_kg_ha": 10000,
     "precio_usd_kg": 1.40, "costo_usd_ha": 9000, "empleos_ha": 1.2, "jornales_ha": 200},
    {"cultivo": "Cacao", "tipo": "tradicional", "rend_kg_ha": 1100,
     "precio_usd_kg": 3.10, "costo_usd_ha": 2200, "empleos_ha": 0.9, "jornales_ha": 180},
    {"cultivo": "Maíz Duro", "tipo": "bajo_valor", "rend_kg_ha": 5200,
     "precio_usd_kg": 0.28, "costo_usd_ha": 1200, "empleos_ha": 0.4, "jornales_ha": 120},
]


def detectar(meta, nombres, patron=None):
    """Busca variable por nombre exacto o patron en nombre+etiqueta."""
    for n in nombres:
        if n in meta.column_names:
            return n
    if patron:
        rx = re.compile(patron, re.I)
        for n, lab in zip(meta.column_names, meta.column_labels):
            if rx.search(f"{n} {lab}"):
                return n
    return None


def cargar_enemdu():
    if not ENEMDU_SAV.exists():
        raise FileNotFoundError(f"No existe el archivo: {ENEMDU_SAV}")
    print(f"Cargando: {ENEMDU_SAV.name}")
    df, meta = pyreadstat.read_sav(ENEMDU_SAV)
    print(f"   {len(df):,} filas | {len(meta.column_names)} variables "
          f"(QA guia INEC: 27,808 personas)")
    return df, meta


def procesar_pea_rural(df, meta):
    """Filtra PEA rural y construye flags laborales ponderables."""
    v = {
        "zona": detectar(meta, ["zona"], r"zona|\barea\b"),
        "rama": detectar(meta, ["rama1"], r"rama"),
        "empleo": detectar(meta, ["empleo"]),
        "desemp": detectar(meta, ["desempleo"]),
        "fexp": detectar(meta, ["fexp"], r"factor|ponder|expansi"),
        "ingrl": detectar(meta, ["ingrl"], r"ingreso.*laboral"),
        "secemp": detectar(meta, ["secemp"], r"formal|sector"),
        "edad": detectar(meta, ["edad", "p08"], r"edad"),
        "sexo": detectar(meta, ["sexo", "p06"], r"sexo"),
        "educ": detectar(meta, ["nnivins"], r"nivel.*instrucci"),
        "region": detectar(meta, ["rn"], r"region"),
    }

    # CORRECCION 1: solo estas son obligatorias; 'region' es opcional en dic-2025
    criticas = ["zona", "rama", "empleo", "desemp", "fexp", "ingrl", "secemp"]
    faltan = [k for k in criticas if v[k] is None]
    if faltan:
        print("Variables criticas no encontradas:", faltan)
        print("Muestra de columnas:", meta.column_names[:40])
        raise KeyError(f"Faltan variables ENEMDU: {faltan}")

    if v["region"] is None:
        print("   Nota: 'rn' (region natural) no viene en dic-2025; se omite.")

    print("   categorias zona  :", meta.variable_value_labels.get(v["zona"], {}))
    print("   categorias secemp:", meta.variable_value_labels.get(v["secemp"], {}))

    d = df.copy()
    d["rural"] = d[v["zona"]] == ZONA_RURAL
    d["ocupado"] = d[v["empleo"]] == 1
    d["desempleado"] = d[v["desemp"]] == 1
    d["pea"] = d["ocupado"] | d["desempleado"]
    d["agricola"] = d[v["rama"]] == 1

    pea = d[d["rural"] & d["pea"]].copy()

    pea["subempleo_ingreso"] = (
        pea["ocupado"] & (pea[v["ingrl"]].fillna(0) < SBU_MENSUAL)
    )
    pea["informal"] = pea[v["secemp"]].isin([2, 3])

    # CORRECCION 2: renombrar solo las columnas que si existen
    dict_rename = {
        v["fexp"]: "peso_expansion",
        v["ingrl"]: "ingreso_laboral",
        v["secemp"]: "sector",
    }
    if v["edad"]:
        dict_rename[v["edad"]] = "edad"
    if v["sexo"]:
        dict_rename[v["sexo"]] = "sexo"
    if v["educ"]:
        dict_rename[v["educ"]] = "nivel_instruccion"
    if v["region"]:
        dict_rename[v["region"]] = "region_natural"

    pea = pea.rename(columns=dict_rename)
    print(f"   PEA rural: {len(pea):,} obs. | "
          f"poblacion ponderada = {pea['peso_expansion'].sum():,.0f}")
    return pea


def calcular_indicadores(pea):
    """KPIs ponderados por factor de expansion."""
    w = pea["peso_expansion"]
    oc = pea["ocupado"]
    ag = pea["agricola"]
    ind = {
        "periodo": "Diciembre 2025",
        "pea_rural_total": int(w.sum()),
        "pea_rural_agricola": int(w[ag].sum()),
        "tasa_desempleo_rural_pct": round(
            (pea["desempleado"] * w).sum() / w.sum() * 100, 2),
        "subempleo_ingreso_agricola_pct": round(
            (pea.loc[ag & oc, "subempleo_ingreso"] * w.loc[ag & oc]).sum()
            / w.loc[ag & oc].sum() * 100, 2),
        "ingreso_medio_agricola_usd": round(
            (pea.loc[ag & oc, "ingreso_laboral"] * w.loc[ag & oc]).sum()
            / w.loc[ag & oc].sum(), 2),
        "informalidad_agricola_pct": round(
            (pea.loc[ag, "informal"] * w.loc[ag]).sum() / w.loc[ag].sum() * 100, 2),
    }
    return pd.DataFrame([ind])


def metricas_cultivos():
    """Metricas economicas y laborales de los 6 cultivos."""
    c = pd.DataFrame(PARAMETROS_CULTIVOS)
    c["ingreso_bruto_usd_ha"] = c["rend_kg_ha"] * c["precio_usd_kg"]
    c["margen_usd_ha"] = c["ingreso_bruto_usd_ha"] - c["costo_usd_ha"]
    c["margen_pct"] = (c["margen_usd_ha"] / c["ingreso_bruto_usd_ha"] * 100).round(1)
    c["rend_usd_m2"] = (c["ingreso_bruto_usd_ha"] / 10000).round(4)
    base_maiz = c.loc[c["cultivo"] == "Maíz Duro", "empleos_ha"].iloc[0]
    c["multiplicador_empleo_vs_maiz"] = (c["empleos_ha"] / base_maiz).round(2)
    c["fuente"] = "parametro_tecnico_calibrado"
    return c


def main():
    print("=" * 70)
    print("PIPELINE DE CONSOLIDACION - Encadenamientos Fruticolas EC")
    print("=" * 70)

    df, meta = cargar_enemdu()
    pea = procesar_pea_rural(df, meta)
    indicadores = calcular_indicadores(pea)
    cultivos = metricas_cultivos()

    pea.to_csv(PROCESSED / "pea_rural_agricola.csv", index=False)
    cultivos.to_csv(PROCESSED / "cultivos_metricas.csv", index=False)
    indicadores.to_csv(PROCESSED / "indicadores_macro.csv", index=False)

    print("\nDataset unificado en data/processed/:")
    for f in ["pea_rural_agricola.csv", "cultivos_metricas.csv", "indicadores_macro.csv"]:
        print("   -", f)

    print("\nCULTIVOS (vista previa):")
    print(cultivos[["cultivo", "ingreso_bruto_usd_ha", "empleos_ha",
                    "multiplicador_empleo_vs_maiz"]].to_string(index=False))

    print("\nINDICADORES LABORALES RURALES:")
    print(indicadores.T.to_string())
    print("\nPipeline completado sin errores.")


if __name__ == "__main__":
    main()