"""
src/simulation.py

Simulación de escenarios de reconversión productiva.
Responde la pregunta central del estudio:

    ¿Cuántos empleos rurales formales adicionales se generarían
    si se reconvirtieran N hectáreas de cultivos de bajo valor
    (Maíz Duro) a frutas de alto valor orientadas a exportación?

Metodología:
    - Parámetros técnicos calibrados (MAG/SIPA + literatura)
    - 3 escenarios de política: conservador, moderado, ambicioso
    - Cálculo de multiplicador de empleo y delta de ingresos

Salidas:
    data/processed/simulacion_reconversion.csv
    outputs/figures/simulacion_heatmap_empleos_formales.png (300 DPI)
    outputs/figures/simulacion_multiplicadores_empleo.png (300 DPI)

Ejecutar desde la raíz del proyecto:
    python src/simulation.py
"""

from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # backend sin ventana, ideal para scripts
import matplotlib.pyplot as plt
import seaborn as sns

# ---------------------------------------------------------------------------
# Rutas (derivadas de la posición del script: a prueba de espacios)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED = BASE_DIR / "data" / "processed"
FIGURES = BASE_DIR / "outputs" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="talk")


# ---------------------------------------------------------------------------
# Parámetros técnicos de los 6 cultivos (idénticos a build_dataset.py)
# ---------------------------------------------------------------------------
CULTIVOS = [
    {"cultivo": "Arándano",      "rend_kg_ha": 8000,  "precio_usd_kg": 4.50,
     "empleos_ha": 2.8, "formalidad_pct": 0.75, "jornales_ha": 260, "tipo": "alto_valor"},
    {"cultivo": "Pitahaya",      "rend_kg_ha": 12000, "precio_usd_kg": 2.20,
     "empleos_ha": 2.0, "formalidad_pct": 0.65, "jornales_ha": 240, "tipo": "alto_valor"},
    {"cultivo": "Uvilla",        "rend_kg_ha": 9000,  "precio_usd_kg": 1.60,
     "empleos_ha": 1.8, "formalidad_pct": 0.55, "jornales_ha": 220, "tipo": "alto_valor"},
    {"cultivo": "Aguacate Hass", "rend_kg_ha": 10000, "precio_usd_kg": 1.40,
     "empleos_ha": 1.2, "formalidad_pct": 0.60, "jornales_ha": 200, "tipo": "alto_valor"},
    {"cultivo": "Cacao",         "rend_kg_ha": 1100,  "precio_usd_kg": 3.10,
     "empleos_ha": 0.9, "formalidad_pct": 0.30, "jornales_ha": 180, "tipo": "tradicional"},
    {"cultivo": "Maíz Duro",     "rend_kg_ha": 5200,  "precio_usd_kg": 0.28,
     "empleos_ha": 0.4, "formalidad_pct": 0.15, "jornales_ha": 120, "tipo": "bajo_valor"},
]


# ---------------------------------------------------------------------------
# Escenarios de política pública (hectáreas reconvertidas por año)
# ---------------------------------------------------------------------------
ESCENARIOS = {
    "Conservador":  {"hectareas": 5_000,  "horizonte_anios": 5,
                     "descripcion": "Piloto regional focalizado"},
    "Moderado":     {"hectareas": 15_000, "horizonte_anios": 5,
                     "descripcion": "Programa provincial articulado"},
    "Ambicioso":    {"hectareas": 50_000, "horizonte_anios": 5,
                     "descripcion": "Política nacional de reconversión"},
}

CULTIVO_ORIGEN = "Maíz Duro"  # el que se reemplaza


# ---------------------------------------------------------------------------
# Núcleo: cálculo del impacto por escenario y cultivo destino
# ---------------------------------------------------------------------------
def simular_reconversion() -> pd.DataFrame:
    """
    Calcula impacto neto de reconvertir N hectáreas de Maíz Duro
    a cada uno de los cultivos de alto valor, bajo 3 escenarios.
    """
    df_cult = pd.DataFrame(CULTIVOS)
    origen = df_cult[df_cult["cultivo"] == CULTIVO_ORIGEN].iloc[0]

    resultados = []
    for nombre_esc, cfg in ESCENARIOS.items():
        ha = cfg["hectareas"]
        for _, dest in df_cult[df_cult["cultivo"] != CULTIVO_ORIGEN].iterrows():
            # Deltas brutos
            d_empleos = (dest["empleos_ha"] - origen["empleos_ha"]) * ha
            d_jornales = (dest["jornales_ha"] - origen["jornales_ha"]) * ha
            d_ingreso = (dest["rend_kg_ha"] * dest["precio_usd_kg"]
                         - origen["rend_kg_ha"] * origen["precio_usd_kg"]) * ha

            # Empleo FORMAL neto (aporte clave del estudio)
            empleos_formales_dest = dest["empleos_ha"] * dest["formalidad_pct"] * ha
            empleos_formales_orig = origen["empleos_ha"] * origen["formalidad_pct"] * ha
            d_empleos_formales = empleos_formales_dest - empleos_formales_orig

            resultados.append({
                "escenario": nombre_esc,
                "descripcion_escenario": cfg["descripcion"],
                "hectareas_reconvertidas": ha,
                "cultivo_origen": CULTIVO_ORIGEN,
                "cultivo_destino": dest["cultivo"],
                "tipo_cultivo": dest["tipo"],
                "delta_empleos_totales": int(round(d_empleos)),
                "delta_empleos_formales": int(round(d_empleos_formales)),
                "delta_jornales_anuales": int(round(d_jornales)),
                "delta_valor_bruto_usd": int(round(d_ingreso)),
                "multiplicador_empleo": round(dest["empleos_ha"] / origen["empleos_ha"], 2),
            })
    return pd.DataFrame(resultados)


# ---------------------------------------------------------------------------
# Resumen ejecutivo
# ---------------------------------------------------------------------------
def resumen_ejecutivo(df: pd.DataFrame) -> pd.DataFrame:
    """Top-3 cultivos destino por escenario según empleo formal generado."""
    top = (df.sort_values(["escenario", "delta_empleos_formales"],
                          ascending=[True, False])
             .groupby("escenario", as_index=False)
             .head(3))
    return top


# ---------------------------------------------------------------------------
# Visualizaciones 300 DPI
# ---------------------------------------------------------------------------
def graficar_heatmap(df: pd.DataFrame) -> None:
    """Heatmap de empleo formal neto (escenario × cultivo destino)."""
    pivot = df.pivot_table(
        index="cultivo_destino", columns="escenario",
        values="delta_empleos_formales", aggfunc="sum"
    )
    orden = ["Conservador", "Moderado", "Ambicioso"]
    pivot = pivot[orden]

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(
        pivot / 1000, annot=True, fmt=".1f", cmap="YlGn",
        linewidths=1, linecolor="white", ax=ax, cbar_kws={"label": "Miles de empleos"}
    )
    ax.set_title(
        "Empleos rurales FORMALES netos generados por reconversión\n"
        "(miles de puestos, horizonte anual)",
        fontweight="bold", pad=15
    )
    ax.set_xlabel("Escenario de política pública")
    ax.set_ylabel("Cultivo destino")
    plt.tight_layout()
    out = FIGURES / "simulacion_heatmap_empleos_formales.png"
    plt.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"  Figura guardada: {out.relative_to(BASE_DIR)}")
    plt.close()


def graficar_multiplicadores(df: pd.DataFrame) -> None:
    """Barras: multiplicador de empleo por cultivo destino vs Maíz Duro."""
    data = (df[df["escenario"] == "Moderado"]
            .drop_duplicates("cultivo_destino")
            .sort_values("multiplicador_empleo", ascending=True))

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(data["cultivo_destino"], data["multiplicador_empleo"],
                   color=["#2ecc71" if t == "alto_valor"
                          else "#3498db" if t == "tradicional" else "#95a5a6"
                          for t in data["tipo_cultivo"]])
    ax.axvline(1, color="gray", linestyle="--", linewidth=1.5)
    ax.set_xlabel("Multiplicador de empleo vs Maíz Duro")
    ax.set_title(
        "Intensidad laboral relativa: frutas de alto valor vs Maíz Duro",
        fontweight="bold"
    )
    for bar, val in zip(bars, data["multiplicador_empleo"]):
        ax.text(val + 0.1, bar.get_y() + bar.get_height()/2,
                f"{val:.1f}x", va="center", fontweight="bold")
    plt.tight_layout()
    out = FIGURES / "simulacion_multiplicadores_empleo.png"
    plt.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"  Figura guardada: {out.relative_to(BASE_DIR)}")
    plt.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("SIMULACIÓN DE RECONVERSIÓN PRODUCTIVA")
    print("=" * 70)

    df = simular_reconversion()

    # Exportar detalle completo
    out_det = PROCESSED / "simulacion_reconversion.csv"
    df.to_csv(out_det, index=False, encoding="utf-8")
    print(f"\n  Detalle exportado: {out_det.relative_to(BASE_DIR)}")
    print(f"  Total escenarios evaluados: {len(df)}")

    # Resumen ejecutivo
    print("\n" + "-" * 70)
    print("RESUMEN EJECUTIVO - Top-3 cultivos destino por escenario")
    print("-" * 70)
    res = resumen_ejecutivo(df)
    cols_show = ["escenario", "cultivo_destino",
                 "delta_empleos_formales", "delta_valor_bruto_usd",
                 "multiplicador_empleo"]
    print(res[cols_show].to_string(index=False))

    # Hallazgo clave
    mejor = df.loc[df["delta_empleos_formales"].idxmax()]
    print("\n" + "-" * 70)
    print("HALLAZGO CLAVE PARA POLÍTICA PÚBLICA")
    print("-" * 70)
    print(f"  Reconversión a {mejor['cultivo_destino']} en escenario "
          f"'{mejor['escenario']}':")
    print(f"   - Empleos FORMALES netos: {mejor['delta_empleos_formales']:,}")
    print(f"   - Valor bruto adicional:  "
          f"USD {mejor['delta_valor_bruto_usd']:,.0f}")
    print(f"   - Multiplicador empleo:   {mejor['multiplicador_empleo']}x vs Maíz Duro")

    # Gráficos
    print("\n" + "-" * 70)
    print("GENERANDO GRÁFICOS 300 DPI")
    print("-" * 70)
    graficar_heatmap(df)
    graficar_multiplicadores(df)

    print("\n✅ Fase 1 completada.")


if __name__ == "__main__":
    main()