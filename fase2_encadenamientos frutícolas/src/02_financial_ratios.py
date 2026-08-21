"""
Script: 02_financial_ratios.py
FASE 2 - Encadenamientos Fruticolas Ecuador

OBJETIVO:
    Calcular ratios financieros, rankings y metricas de concentracion
    de mercado (HHI) para el sector agroexportador de frutas.

ENTRADAS:
    - data/processed/df_empresas_fruticolas.csv
    - data/processed/df_sri_compras_ventas.csv

SALIDAS:
    - outputs/rankings/top_10_ventas.csv
    - outputs/rankings/top_10_rentabilidad.csv
    - outputs/rankings/hhi_concentracion.csv
    - outputs/rankings/ratios_financieros_sectoriales.csv
"""

from pathlib import Path
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# CONFIGURACION
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
PROC_DIR = BASE_DIR / "data" / "processed"
OUT_DIR  = BASE_DIR / "outputs" / "rankings"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. CARGA DE DATOS
# ---------------------------------------------------------------------------
def cargar_datos():
    """Carga los CSVs generados por el ETL en R."""
    print("=" * 70)
    print("FASE 2 - ANALISIS FINANCIERO Y RANKINGS")
    print("=" * 70)

    path_emp = PROC_DIR / "df_empresas_fruticolas.csv"
    path_sri = PROC_DIR / "df_sri_compras_ventas.csv"

    if not path_emp.exists():
        raise FileNotFoundError(f"No existe: {path_emp}")

    df_emp = pd.read_csv(path_emp)
    print(f"\nEmpresas cargadas: {len(df_emp):,}")

    df_sri = None
    if path_sri.exists():
        df_sri = pd.read_csv(path_sri)
        print(f"Registros SRI: {len(df_sri):,}")

    return df_emp, df_sri


# ---------------------------------------------------------------------------
# 2. CALCULO DE RATIOS FINANCIEROS
# ---------------------------------------------------------------------------
def calcular_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula ratios financieros clave por empresa.
    Maneja divisiones por cero y valores atipicos.
    """
    d = df.copy()

    # Asegurar tipos numericos
    cols_num = ["activo_total", "pasivo_total", "patrimonio",
                "ventas_netas", "utilidad_neta"]
    for col in cols_num:
        if col in d.columns:
            d[col] = pd.to_numeric(d[col], errors="coerce").fillna(0)

    # Derivar utilidad operativa si no existe (aproximacion)
    if "utilidad_operativa" not in d.columns:
        # Aproximacion: utilidad neta / 0.75 (asumiendo 25% impuestos)
        d["utilidad_operativa"] = d["utilidad_neta"] / 0.75

    # ---- RENTABILIDAD ----
    d["ROE_pct"] = np.where(
        d["patrimonio"] > 0,
        (d["utilidad_neta"] / d["patrimonio"]) * 100,
        np.nan
    )
    d["ROA_pct"] = np.where(
        d["activo_total"] > 0,
        (d["utilidad_neta"] / d["activo_total"]) * 100,
        np.nan
    )
    d["margen_neto_pct"] = np.where(
        d["ventas_netas"] > 0,
        (d["utilidad_neta"] / d["ventas_netas"]) * 100,
        np.nan
    )
    d["margen_operativo_pct"] = np.where(
        d["ventas_netas"] > 0,
        (d["utilidad_operativa"] / d["ventas_netas"]) * 100,
        np.nan
    )

    # ---- LIQUIDEZ Y SOLVENCIA ----
    # Aproximacion de activo corriente (tipico 55% del total en agroexport)
    d["activo_corriente"] = d["activo_total"] * 0.55
    d["pasivo_corriente"] = d["pasivo_total"] * 0.45

    d["razon_corriente"] = np.where(
        d["pasivo_corriente"] > 0,
        d["activo_corriente"] / d["pasivo_corriente"],
        np.nan
    )
    d["prueba_acida"] = np.where(
        d["pasivo_corriente"] > 0,
        (d["activo_corriente"] * 0.60) / d["pasivo_corriente"],  # inventarios ~40%
        np.nan
    )
    d["endeudamiento_pct"] = np.where(
        d["activo_total"] > 0,
        (d["pasivo_total"] / d["activo_total"]) * 100,
        np.nan
    )

    # ---- EFICIENCIA ----
    d["rotacion_activos"] = np.where(
        d["activo_total"] > 0,
        d["ventas_netas"] / d["activo_total"],
        np.nan
    )

    # ---- FILTRO DE OUTLIERS (winsorize al 1-99%) ----
    for ratio in ["ROE_pct", "ROA_pct", "margen_neto_pct", "razon_corriente"]:
        if ratio in d.columns:
            q1 = d[ratio].quantile(0.01)
            q99 = d[ratio].quantile(0.99)
            d[ratio] = d[ratio].clip(q1, q99)

    return d


# ---------------------------------------------------------------------------
# 3. RANKINGS
# ---------------------------------------------------------------------------
def ranking_top_ventas(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Top N empresas por volumen de ventas."""
    cols = [c for c in ["ruc_norm", "razon_social", "ciiu_norm", "sector",
                         "ventas_netas", "utilidad_neta", "margen_neto_pct",
                         "ROE_pct", "anio"] if c in df.columns]
    top = (df[df["ventas_netas"] > 0]
           .nlargest(top_n, "ventas_netas")[cols]
           .reset_index(drop=True))
    top.index = top.index + 1  # ranking 1-based
    top.index.name = "ranking"
    return top


def ranking_top_rentabilidad(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Top N empresas por ROE (rentabilidad sobre patrimonio)."""
    # Filtrar empresas con patrimonio positivo y ventas significativas
    candidatos = df[(df["patrimonio"] > 100000) & (df["ventas_netas"] > 500000)].copy()
    cols = [c for c in ["ruc_norm", "razon_social", "ciiu_norm",
                         "ROE_pct", "ROA_pct", "margen_neto_pct",
                         "ventas_netas", "utilidad_neta", "anio"] if c in candidatos.columns]
    top = (candidatos.dropna(subset=["ROE_pct"])
           .nlargest(top_n, "ROE_pct")[cols]
           .reset_index(drop=True))
    top.index = top.index + 1
    top.index.name = "ranking"
    return top


# ---------------------------------------------------------------------------
# 4. INDICE DE CONCENTRACION HHI (Herfindahl-Hirschman)
# ---------------------------------------------------------------------------
def calcular_hhi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula el Indice Herfindahl-Hirschman por anio.
    HHI < 1500: mercado competitivo
    HHI 1500-2500: moderadamente concentrado
    HHI > 2500: altamente concentrado
    """
    resultados = []

    for anio, grupo in df.groupby("anio"):
        ventas_totales = grupo["ventas_netas"].sum()
        if ventas_totales <= 0:
            continue

        # Participacion de mercado de cada empresa (en %)
        grupo = grupo[grupo["ventas_netas"] > 0].copy()
        grupo["cuota_mercado_pct"] = (grupo["ventas_netas"] / ventas_totales) * 100

        # HHI = suma de (cuota_i)^2
        hhi = (grupo["cuota_mercado_pct"] ** 2).sum()

        # CR4: suma de las 4 empresas mas grandes
        cr4 = grupo.nlargest(4, "cuota_mercado_pct")["cuota_mercado_pct"].sum()

        # CR10: suma de las 10 empresas mas grandes
        cr10 = grupo.nlargest(10, "cuota_mercado_pct")["cuota_mercado_pct"].sum()

        # Clasificacion del mercado
        if hhi < 1500:
            clasificacion = "Competitivo"
        elif hhi < 2500:
            clasificacion = "Moderadamente concentrado"
        else:
            clasificacion = "Altamente concentrado"

        resultados.append({
            "anio": int(anio),
            "num_empresas": len(grupo),
            "ventas_totales_usd": round(ventas_totales, 2),
            "HHI": round(hhi, 2),
            "CR4_pct": round(cr4, 2),
            "CR10_pct": round(cr10, 2),
            "clasificacion": clasificacion,
        })

    return pd.DataFrame(resultados)


# ---------------------------------------------------------------------------
# 5. ESTADISTICAS SECTORIALES AGREGADAS
# ---------------------------------------------------------------------------
def estadisticas_sectoriales(df: pd.DataFrame) -> pd.DataFrame:
    """Estadisticas agregadas del sector por anio."""
    stats = df.groupby("anio").agg(
        num_empresas=("ruc_norm", "count"),
        ventas_totales=("ventas_netas", "sum"),
        activos_totales=("activo_total", "sum"),
        utilidad_agregada=("utilidad_neta", "sum"),
        ROE_promedio=("ROE_pct", "mean"),
        ROE_mediana=("ROE_pct", "median"),
        margen_neto_promedio=("margen_neto_pct", "mean"),
        endeudamiento_promedio=("endeudamiento_pct", "mean"),
        rotacion_activos_promedio=("rotacion_activos", "mean"),
    ).reset_index()

    # Ratios sectoriales derivados
    stats["ROA_sectorial_pct"] = (stats["utilidad_agregada"] / stats["activos_totales"]) * 100
    stats["margen_neto_sectorial_pct"] = (stats["utilidad_agregada"] / stats["ventas_totales"]) * 100

    return stats.round(2)


# ---------------------------------------------------------------------------
# 6. QA - CONTROL DE CALIDAD
# ---------------------------------------------------------------------------
def reporte_qa(df: pd.DataFrame) -> dict:
    """Reporte de calidad de datos financieros."""
    qa = {
        "total_empresas": len(df),
        "RUC_duplicados": df["ruc_norm"].duplicated().sum(),
        "ventas_cero": (df["ventas_netas"] == 0).sum(),
        "patrimonio_negativo": (df["patrimonio"] < 0).sum(),
        "ROE_atipico": ((df["ROE_pct"] > 200) | (df["ROE_pct"] < -100)).sum(),
        "endeudamiento_mayor_100": (df["endeudamiento_pct"] > 100).sum(),
    }
    return qa


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    df_emp, df_sri = cargar_datos()

    print("\n[1/5] Calculando ratios financieros...")
    df_ratios = calcular_ratios(df_emp)

    print("[2/5] Generando rankings Top 10...")
    top_ventas = ranking_top_ventas(df_ratios, top_n=10)
    top_rentab = ranking_top_rentabilidad(df_ratios, top_n=10)

    print("[3/5] Calculando concentracion de mercado (HHI)...")
    hhi = calcular_hhi(df_ratios)

    print("[4/5] Generando estadisticas sectoriales...")
    stats = estadisticas_sectoriales(df_ratios)

    print("[5/5] Ejecutando QA...")
    qa = reporte_qa(df_ratios)

    # -----------------------------------------------------------------------
    # REPORTES
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TOP 10 EMPRESAS POR VOLUMEN DE VENTAS")
    print("=" * 70)
    cols_show = [c for c in ["razon_social", "ventas_netas", "utilidad_neta",
                              "margen_neto_pct", "ROE_pct"] if c in top_ventas.columns]
    print(top_ventas[cols_show].to_string())

    print("\n" + "=" * 70)
    print("TOP 10 EMPRESAS POR RENTABILIDAD (ROE)")
    print("=" * 70)
    cols_show = [c for c in ["razon_social", "ROE_pct", "ROA_pct",
                              "margen_neto_pct", "ventas_netas"] if c in top_rentab.columns]
    print(top_rentab[cols_show].to_string())

    print("\n" + "=" * 70)
    print("CONCENTRACION DE MERCADO (HHI)")
    print("=" * 70)
    print(hhi.to_string(index=False))

    print("\n" + "=" * 70)
    print("ESTADISTICAS SECTORIALES AGREGADAS")
    print("=" * 70)
    print(stats.T.to_string())

    print("\n" + "=" * 70)
    print("REPORTE DE CALIDAD (QA)")
    print("=" * 70)
    for k, v in qa.items():
        print(f"  {k:35s} {v:>10,}" if isinstance(v, int) else f"  {k:35s} {v}")

    # -----------------------------------------------------------------------
    # EXPORTACION
    # -----------------------------------------------------------------------
    print("\n[Exportando CSVs...]")
    top_ventas.to_csv(OUT_DIR / "top_10_ventas.csv", encoding="utf-8")
    top_rentab.to_csv(OUT_DIR / "top_10_rentabilidad.csv", encoding="utf-8")
    hhi.to_csv(OUT_DIR / "hhi_concentracion.csv", index=False, encoding="utf-8")
    stats.to_csv(OUT_DIR / "ratios_financieros_sectoriales.csv",
                 index=False, encoding="utf-8")
    df_ratios.to_csv(OUT_DIR / "df_ratios_completo.csv", index=False, encoding="utf-8")

    print(f"\nArchivos generados en: {OUT_DIR}")
    print("  - top_10_ventas.csv")
    print("  - top_10_rentabilidad.csv")
    print("  - hhi_concentracion.csv")
    print("  - ratios_financieros_sectoriales.csv")
    print("  - df_ratios_completo.csv")

    print("\nFASE 2 (PASO 2) COMPLETADA")


if __name__ == "__main__":
    main()