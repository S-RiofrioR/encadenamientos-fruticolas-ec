"""
src/robustez_genero.py (Version Robusta)

BONUS DIA 3: Tests de robustez y analisis de brecha de genero.
1. Logit vs Probit (robustez ante funcion de enlace).
2. Brecha de Genero via Probabilidades Predichas (Predictive Margins).
   (Evita el error de matriz singular por separacion perfecta en submuestras pequenas).

Salidas:
    outputs/tables/robustez_comparativa.csv
    outputs/figures/brecha_genero_probabilidades.png (300 DPI)
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

# Ignorar warnings de separacion perfecta (los manejamos con method='bfgs')
warnings.filterwarnings("ignore", category=sm.tools.sm_exceptions.PerfectSeparationWarning)

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED = BASE_DIR / "data" / "processed"
TABLES = BASE_DIR / "outputs" / "tables"
FIGURES = BASE_DIR / "outputs" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="talk")

# ---------------------------------------------------------------------------
# 1. Preparacion de datos
# ---------------------------------------------------------------------------
def preparar_base():
    df = pd.read_csv(PROCESSED / "pea_rural_agricola.csv")
    d = df.copy()
    d["y"] = ((d["desempleado"] == 1) | (d["subempleo_ingreso"] == True)).astype(int)
    d["mujer"] = (d["sexo"] == 2).astype(int)
    d["agricola_int"] = d["agricola"].astype(int)
    d["edad_c"] = d["edad"] - d["edad"].mean()
    d["edad2"] = d["edad_c"] ** 2
    d["agro_x_mujer"] = d["agricola_int"] * d["mujer"]
    
    d = d.dropna(subset=["y", "mujer", "agricola_int", "edad_c"])
    
    if "nivel_instruccion" in d.columns:
        dummies = pd.get_dummies(d["nivel_instruccion"], prefix="educ", drop_first=True, dtype=float)
        d = pd.concat([d, dummies], axis=1)
        
    return d

def construir_X(d):
    cols_base = ["agricola_int", "mujer", "edad_c", "edad2", "agro_x_mujer"]
    cols_educ = [c for c in d.columns if c.startswith("educ_")]
    X = d[cols_base + cols_educ].astype(float).copy()
    return sm.add_constant(X)

# ---------------------------------------------------------------------------
# 2. Estimacion Robusta (Logit vs Probit con method='bfgs')
# ---------------------------------------------------------------------------
def estimar_robustez(y, X, w):
    resultados = {}
    
    # A. Logit (usamos sm.Logit con bfgs que es mas estable que GLM ante cuasi-separacion)
    try:
        res_logit = sm.Logit(y, X).fit(method='bfgs', maxiter=100, disp=0, cov_type='HC1')
        resultados["Logit"] = res_logit
    except Exception as e:
        print(f"  Warning Logit: {e}")
        
    # B. Probit
    try:
        res_probit = sm.Probit(y, X).fit(method='bfgs', maxiter=100, disp=0, cov_type='HC1')
        resultados["Probit"] = res_probit
    except Exception as e:
        print(f"  Warning Probit: {e}")
        
    return resultados

# ---------------------------------------------------------------------------
# 3. Analisis de Brecha de Genero (Probabilidades Predichas)
# ---------------------------------------------------------------------------
def calcular_brecha_genero(res_logit, X_template):
    """
    Calcula la probabilidad predicha de subempleo para 4 perfiles tipicos.
    """
    # 1. Definir las etiquetas de los perfiles por separado
    etiquetas_perfil = ["Hombre No-Agricola", "Hombre Agricola", "Mujer No-Agricola", "Mujer Agricola"]
    
    # 2. Crear DataFrame solo con variables numericas del modelo
    perfiles_num = pd.DataFrame({
        "const": [1, 1, 1, 1],
        "agricola_int": [0, 1, 0, 1],
        "mujer": [0, 0, 1, 1],
        "edad_c": [0, 0, 0, 0],  # Edad promedio (centrada en 0)
        "edad2": [0, 0, 0, 0],
        "agro_x_mujer": [0, 0, 0, 1],
    })
    
    # Agregar columnas de educacion en 0 (categoria base / referencia)
    cols_educ = [c for c in X_template.columns if c.startswith("educ_")]
    for c in cols_educ:
        perfiles_num[c] = 0.0
        
    # Asegurar mismo orden de columnas que la matriz X del modelo
    perfiles_num = perfiles_num[X_template.columns]
    
    # 3. Predecir probabilidades
    probs = res_logit.predict(perfiles_num)
    
    # 4. Reconstruir el DataFrame final con las etiquetas
    df_brecha = pd.DataFrame({
        "perfil": etiquetas_perfil,
        "prob_subempleo": probs,
        "prob_pct": (probs * 100).round(1)
    })
    
    return df_brecha

# ---------------------------------------------------------------------------
# 4. Visualizacion
# ---------------------------------------------------------------------------
def graficar_brecha(df_brecha):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ["#3498db", "#2980b9", "#e74c3c", "#c0392b"]
    bars = ax.bar(df_brecha["perfil"], df_brecha["prob_pct"], color=colors, edgecolor="black")
    
    ax.set_ylabel("Probabilidad de Desempleo / Subempleo (%)", fontsize=12)
    ax.set_title(
        "Brecha de Genero y Penalizacion Agricola en el Rural Ecuatoriano\n"
        "(Probabilidades predichas por modelo Logit, controlando por edad y educacion)",
        fontweight="bold", fontsize=14
    )
    ax.set_ylim(0, 100)
    
    for bar, val in zip(bars, df_brecha["prob_pct"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{val}%", ha="center", fontweight="bold", fontsize=12)
        
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
    print("BONUS: ROBUSTEZ Y BRECHA DE GENERO (Version Estable)")
    print("=" * 70)
    
    d = preparar_base()
    X = construir_X(d)
    y = d["y"]
    w = d["peso_expansion"]
    
    print("\nEstimando Logit y Probit (method='bfgs' para evitar matriz singular)...")
    resultados = estimar_robustez(y, X, w)
    
    # Tabla comparativa de coeficientes clave (agricola_int)
    df_comp = pd.DataFrame()
    for nombre, res in resultados.items():
        try:
            coef = res.params["agricola_int"]
            pval = res.pvalues["agricola_int"]
            df_comp[nombre] = [f"{coef:.3f} (p={pval:.3f})"]
        except:
            df_comp[nombre] = ["No convirgio"]
            
    df_comp.index = ["Efecto Agricultura (coef)"]
    print("\n--- ROBUSTEZ: EFECTO DE TRABAJAR EN AGRICULTURA ---")
    print(df_comp.T)
    
    # Brecha de genero
    if "Logit" in resultados:
        print("\nCalculando probabilidades predichas por perfil...")
        df_brecha = calcular_brecha_genero(resultados["Logit"], X)
        
        print("\n--- BRECHA DE GENERO Y PENALIZACION AGRICOLA ---")
        print(df_brecha[["perfil", "prob_pct"]].to_string(index=False))
        
        df_brecha.to_csv(TABLES / "brecha_genero_probabilidades.csv", index=False)
        graficar_brecha(df_brecha)
    else:
        print("  No se pudo calcular la brecha por fallo en Logit.")
        
    print("\n✅ Bonus completado.")

if __name__ == "__main__":
    main()