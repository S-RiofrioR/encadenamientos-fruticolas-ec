"""
src/econometrics.py

FASE 2 - Modelo Logit ponderado (factor de expansion ENEMDU):
probabilidad de desempleo / subempleo por ingresos en la PEA rural,
dic-2025.

Variable de interes: trabajar en agricultura (rama1 == 'A').
Controles: sexo, edad (no lineal), educacion, interaccion agro*mujer.

Metodo: GLM familia binomial (= Logit) con freq_weights y errores HC1.

Salidas:
    outputs/tables/logit_coeficientes.csv
    outputs/tables/logit_efectos_marginales.csv
    outputs/figures/logit_efectos_marginales.png (300 DPI)

Ejecutar desde la raiz:
    python src/econometrics.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED = BASE_DIR / "data" / "processed"
TABLES = BASE_DIR / "outputs" / "tables"
FIGURES = BASE_DIR / "outputs" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="talk")


# ---------------------------------------------------------------------------
# 1. Carga y preparacion de la muestra
# ---------------------------------------------------------------------------
def cargar_microdatos() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "pea_rural_agricola.csv")
    print(f"Microdatos PEA rural: {len(df):,} obs. | "
          f"ponderada: {df['peso_expansion'].sum():,.0f} personas")
    return df


def preparar_muestra(df: pd.DataFrame) -> pd.DataFrame:
    """Construye variable dependiente y regresores."""
    d = df.copy()

    # y = 1 si desempleado o subempleado por ingresos; 0 si empleo pleno
    d["y"] = ((d["desempleado"] == 1) | (d["subempleo_ingreso"] == True)).astype(int)

    d["mujer"] = (d["sexo"] == 2).astype(int)
    d["agricola_int"] = d["agricola"].astype(int)
    d["edad_c"] = d["edad"] - d["edad"].mean()      # centrada p/ evitar multicolinealidad
    d["edad2"] = d["edad_c"] ** 2
    d["agro_x_mujer"] = d["agricola_int"] * d["mujer"]

    d = d.dropna(subset=["y", "mujer", "agricola_int", "edad_c"])
    print(f"Prevalencia de y=1 (desempleo/subempleo): {d['y'].mean():.1%}")
    return d


def construir_X(d: pd.DataFrame) -> pd.DataFrame:
    """Matriz de diseno con constante y dummies de educacion."""
    cols = ["agricola_int", "mujer", "edad_c", "edad2", "agro_x_mujer"]
    X = d[cols].astype(float).copy()

    if "nivel_instruccion" in d.columns:
        dummies = pd.get_dummies(
            d["nivel_instruccion"], prefix="educ", drop_first=True, dtype=float
        )
        X = pd.concat([X, dummies], axis=1)

    return sm.add_constant(X)


# ---------------------------------------------------------------------------
# 2. Estimacion Logit ponderada con errores robustos
# ---------------------------------------------------------------------------
def estimar_logit(d: pd.DataFrame, X: pd.DataFrame):
    y = d["y"]
    w = d["peso_expansion"]

    # GLM binomial == Logit; freq_weights = factor de expansion ENEMDU
    modelo = sm.GLM(y, X, family=sm.families.Binomial(), freq_weights=w)
    res = modelo.fit(cov_type="HC1")

    # Pseudo R2 de McFadden (modelo nulo solo con constante)
    nulo = sm.GLM(y, X[["const"]], family=sm.families.Binomial(),
                  freq_weights=w).fit()
    r2 = 1 - res.llf / nulo.llf
    return res, r2


# ---------------------------------------------------------------------------
# 3. Efectos marginales promedio (AME)
# ---------------------------------------------------------------------------
def efectos_marginales(res, X: pd.DataFrame) -> pd.DataFrame:
    """AME: binarias como diferencia de predicciones; continuas como beta*p*(1-p)."""
    Xc = X.drop(columns="const")
    p = res.predict(X).values
    filas = []
    for col in Xc.columns:
        valores = np.unique(Xc[col])
        if set(valores).issubset({0.0, 1.0}):          # variable binaria
            X1 = X.copy(); X1[col] = 1.0
            X0 = X.copy(); X0[col] = 0.0
            ame = (res.predict(X1).values - res.predict(X0).values).mean()
        else:                                           # variable continua
            ame = (res.params[col] * p * (1 - p)).mean()
        filas.append({"variable": col, "ame": ame, "ame_pp": ame * 100})
    return pd.DataFrame(filas).sort_values("ame", ascending=False)


# ---------------------------------------------------------------------------
# 4. Visualizacion 300 DPI
# ---------------------------------------------------------------------------
def graficar_ame(ame: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    data = ame.sort_values("ame_pp")
    colors = ["#e74c3c" if v > 0 else "#2ecc71" for v in data["ame_pp"]]
    ax.barh(data["variable"], data["ame_pp"], color=colors)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel("Efecto marginal (puntos porcentuales)")
    ax.set_title(
        "Determinantes del desempleo/subempleo rural\n"
        "(AME ponderado, dic-2025)",
        fontweight="bold"
    )
    plt.tight_layout()
    out = FIGURES / "logit_efectos_marginales.png"
    plt.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"  Figura guardada: {out.relative_to(BASE_DIR)}")
    plt.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("FASE 2 - LOGIT PONDERADO: DESEMPLEO/SUBEMPLEO RURAL")
    print("=" * 70)

    df = cargar_microdatos()
    d = preparar_muestra(df)
    X = construir_X(d)

    res, r2 = estimar_logit(d, X)

    # ---- Tabla de coeficientes + odds ratios ----
    coef = pd.DataFrame({
        "coef": res.params, "err_rob": res.bse,
        "z": res.tvalues, "p_valor": res.pvalues,
    })
    coef["odds_ratio"] = np.exp(coef["coef"])
    ci = np.exp(res.conf_int())
    coef["or_ic_inf"], coef["or_ic_sup"] = ci[0], ci[1]

    print("\n--- COEFICIENTES (errores robustos HC1) ---")
    print(coef.round(4).to_string())
    print(f"\nPseudo R2 (McFadden): {r2:.4f}")
    print(f"N obs: {len(d):,} | N ponderado: {d['peso_expansion'].sum():,.0f}")

    # ---- Efectos marginales ----
    ame = efectos_marginales(res, X)
    print("\n--- EFECTOS MARGINALES PROMEDIO (puntos porcentuales) ---")
    print(ame.round(3).to_string(index=False))

    # ---- Interpretacion automatica del hallazgo central ----
    agro = ame.loc[ame["variable"] == "agricola_int", "ame_pp"]
    if not agro.empty:
        print("\n--- HALLAZGO CENTRAL PARA EL INFORME ---")
        print(f"  Trabajar en agricultura aumenta en {agro.iloc[0]:.1f} puntos "
              f"porcentuales la probabilidad de desempleo/subempleo rural, "
              f"controlando por sexo, edad y educacion.")

    # ---- Exportar ----
    coef.to_csv(TABLES / "logit_coeficientes.csv")
    ame.to_csv(TABLES / "logit_efectos_marginales.csv", index=False)
    print(f"\n  Tablas guardadas en: {TABLES.relative_to(BASE_DIR)}")

    graficar_ame(ame)
    print("\n✅ Fase 2 completada.")


if __name__ == "__main__":
    main()