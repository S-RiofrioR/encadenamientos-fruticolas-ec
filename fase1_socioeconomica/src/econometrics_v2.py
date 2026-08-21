"""
src/econometrics_v2.py

DIA 3 - FASE 3.1: Logit robustecido con imputacion de faltantes + brecha de genero.

Motivacion:
    El modelo del dia 2 uso N=221 (listwise deletion), desperdiciando el 94%
    de la muestra. Hoy imputamos faltantes y re-estimamos con N completo,
    comparando resultados para validar robustez.

Metodologia:
    - Imputacion: edad=mediana, sexo=moda, nivel_instruccion=moda
    - Logit ponderado (freq_weights=fexp), errores robustos HC1
    - Brecha de genero: probabilidades predichas (perfiles hipoteticos)

Salidas:
    outputs/tables/logit_robustecido_coeficientes.csv
    outputs/tables/logit_comparacion_modelos.csv
    outputs/tables/brecha_genero_probabilidades.csv
    outputs/figures/brecha_genero_probabilidades.png (300 DPI)

Ejecutar desde la raiz:
    python src/econometrics_v2.py
"""

from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED = BASE_DIR / "data" / "processed"
TABLES = BASE_DIR / "outputs" / "tables"
FIGURES = BASE_DIR / "outputs" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="talk")

# Resultados del dia 2 (modelo con listwise deletion) para comparacion
N_V1 = 221
AME_AGRO_V1_PP = 14.387


# ---------------------------------------------------------------------------
# 1. Carga e imputacion de faltantes
# ---------------------------------------------------------------------------
def cargar_e_imputar() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "pea_rural_agricola.csv")
    print(f"Observaciones originales: {len(df):,}")
    print("Faltantes detectados:")
    for col in ["edad", "sexo", "nivel_instruccion"]:
        if col in df.columns:
            print(f"   {col}: {df[col].isna().sum():,}")

    d = df.copy()
    if "edad" in d.columns:
        d["edad"] = d["edad"].fillna(d["edad"].median())
    if "sexo" in d.columns:
        d["sexo"] = d["sexo"].fillna(d["sexo"].mode()[0])
    if "nivel_instruccion" in d.columns:
        d["nivel_instruccion"] = d["nivel_instruccion"].fillna(
            d["nivel_instruccion"].mode()[0])
    return d


# ---------------------------------------------------------------------------
# 2. Preparacion de muestra y matriz de diseno
# ---------------------------------------------------------------------------
def preparar_muestra(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["y"] = ((d["desempleado"] == 1) | (d["subempleo_ingreso"] == True)).astype(int)
    d["mujer"] = (d["sexo"] == 2).astype(int)
    d["agricola_int"] = d["agricola"].astype(int)
    d["edad_c"] = d["edad"] - d["edad"].mean()
    d["edad2"] = d["edad_c"] ** 2
    d["agro_x_mujer"] = d["agricola_int"] * d["mujer"]

    if "nivel_instruccion" in d.columns:
        dummies = pd.get_dummies(d["nivel_instruccion"], prefix="educ",
                                 drop_first=True, dtype=float)
        d = pd.concat([d, dummies], axis=1)
    return d


def construir_X(d: pd.DataFrame) -> pd.DataFrame:
    cols = ["agricola_int", "mujer", "edad_c", "edad2", "agro_x_mujer"]
    cols += [c for c in d.columns if c.startswith("educ_")]
    X = d[cols].astype(float).copy()
    return sm.add_constant(X)


# ---------------------------------------------------------------------------
# 3. Estimacion y efectos marginales
# ---------------------------------------------------------------------------
def estimar_logit(y, X, w):
    modelo = sm.GLM(y, X, family=sm.families.Binomial(), freq_weights=w)
    return modelo.fit(cov_type="HC1")


def efectos_marginales(res, X) -> pd.DataFrame:
    Xc = X.drop(columns="const")
    p = res.predict(X).values
    filas = []
    for col in Xc.columns:
        vals = np.unique(Xc[col])
        if set(vals).issubset({0.0, 1.0}):
            X1 = X.copy(); X1[col] = 1.0
            X0 = X.copy(); X0[col] = 0.0
            ame = (res.predict(X1).values - res.predict(X0).values).mean()
        else:
            ame = (res.params[col] * p * (1 - p)).mean()
        filas.append({"variable": col, "ame_pp": ame * 100})
    return pd.DataFrame(filas).sort_values("ame_pp", ascending=False)


# ---------------------------------------------------------------------------
# 4. Brecha de genero (probabilidades predichas, version corregida)
# ---------------------------------------------------------------------------
def brecha_genero(res, X) -> pd.DataFrame:
    etiquetas = ["Hombre No-Agricola", "Hombre Agricola",
                 "Mujer No-Agricola", "Mujer Agricola"]
    perfiles = pd.DataFrame({
        "const": [1, 1, 1, 1],
        "agricola_int": [0, 1, 0, 1],
        "mujer": [0, 0, 1, 1],
        "edad_c": [0, 0, 0, 0],
        "edad2": [0, 0, 0, 0],
        "agro_x_mujer": [0, 0, 0, 1],
    })
    for c in X.columns:
        if c.startswith("educ_"):
            perfiles[c] = 0.0
    perfiles = perfiles[X.columns]

    probs = res.predict(perfiles)
    return pd.DataFrame({
        "perfil": etiquetas,
        "prob_pct": (probs * 100).round(1),
    })


def graficar_brecha(df_brecha) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ["#3498db", "#2980b9", "#e74c3c", "#c0392b"]
    bars = ax.bar(df_brecha["perfil"], df_brecha["prob_pct"],
                  color=colors, edgecolor="black")
    ax.set_ylabel("Probabilidad de desempleo / subempleo (%)")
    ax.set_title(
        "Brecha de genero y penalizacion agricola (Ecuador rural, dic-2025)\n"
        "Modelo Logit robustecido con imputacion (N completo)",
        fontweight="bold")
    ax.set_ylim(0, 100)
    for bar, val in zip(bars, df_brecha["prob_pct"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{val}%", ha="center", fontweight="bold")
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    out = FIGURES / "brecha_genero_probabilidades.png"
    plt.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"  Figura guardada: {out.relative_to(BASE_DIR)}")
    plt.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("FASE 3.1 - LOGIT ROBUSTECIDO (IMPUTACION) + BRECHA DE GENERO")
    print("=" * 70)

    d = cargar_e_imputar()
    d = preparar_muestra(d)
    X = construir_X(d)
    y = d["y"]
    w = d["peso_expansion"]

    res = estimar_logit(y, X, w)
    ame = efectos_marginales(res, X)

    print(f"\nN estimado: {len(d):,} | N ponderado: {w.sum():,.0f}")
    print(f"Prevalencia y=1: {y.mean():.1%}")

    print("\n--- EFECTOS MARGINALES (p.p.) - MODELO ROBUSTECIDO ---")
    print(ame.round(2).to_string(index=False))

    # Comparacion con el modelo del dia 2
    ame_agro_v2 = ame.loc[ame["variable"] == "agricola_int", "ame_pp"].iloc[0]
    comp = pd.DataFrame({
        "modelo": ["Dia 2 (listwise, N=221)", f"Dia 3 (imputado, N={len(d):,})"],
        "ame_agricultura_pp": [AME_AGRO_V1_PP, round(ame_agro_v2, 2)],
    })
    print("\n--- COMPARACION DE ROBUSTEZ ---")
    print(comp.to_string(index=False))

    # Brecha de genero
    df_brecha = brecha_genero(res, X)
    print("\n--- BRECHA DE GENERO (probabilidad predicha %) ---")
    print(df_brecha.to_string(index=False))

    # Exportar
    res_params = pd.DataFrame({
        "coef": res.params, "err_rob": res.bse, "p_valor": res.pvalues})
    res_params.to_csv(TABLES / "logit_robustecido_coeficientes.csv")
    comp.to_csv(TABLES / "logit_comparacion_modelos.csv", index=False)
    df_brecha.to_csv(TABLES / "brecha_genero_probabilidades.csv", index=False)
    print(f"\n  Tablas guardadas en: {TABLES.relative_to(BASE_DIR)}")

    graficar_brecha(df_brecha)

    print("\n--- VEREDICTO DE ROBUSTEZ ---")
    if np.sign(ame_agro_v2) == np.sign(AME_AGRO_V1_PP) and abs(ame_agro_v2) > 5:
        print("  ✅ El efecto de la agricultura se mantiene positivo y "
              "económicamente significativo con la muestra completa.")
        print("  ✅ Hallazgo robusto a la estrategia de manejo de faltantes.")
    else:
        print("  ⚠️ Revisar: el efecto cambió con la imputación.")

    print("\n✅ Fase 3.1 completada.")


if __name__ == "__main__":
    main()