# 🌱 Encadenamientos Frutícolas de Alto Valor y Reducción del Desempleo Rural en Ecuador

**Análisis econométrico del impacto de la reconversión productiva hacia frutas de alto valor sobre el empleo rural ecuatoriano.**

🌐 **Dashboard interactivo:** https://encadenamientos-fruticolas-ec-z8trh5uxofurv9q6hcp64z.streamlit.app/

👤 **Autor:** Hugo Salomón Riofrío Rosero  
📧 **Contacto:** hriofrior@unemi.edu.ec  
📅 **Fecha:** Diciembre 2025  
📊 **Fuentes:** ENEMDU (INEC), MAG/SIPA, FAOSTAT, BCE

---

## 📌 Resumen Ejecutivo

Este estudio analiza cómo la reconversión de cultivos tradicionales de bajo valor (como Maíz Duro) hacia frutas de alto valor orientadas a exportación (Arándano, Pitahaya, Uvilla, Aguacate Hass) puede impactar el empleo rural formal en Ecuador.

### 🔑 Hallazgos Principales

| Indicador | Resultado | Fuente |
|---|---|---|
| PEA Rural Total | 2,968,606 personas | ENEMDU dic-2025 |
| PEA Rural Agrícola | 2,106,939 personas | ENEMDU dic-2025 |
| Tasa Desempleo Rural | 1.5% | ENEMDU dic-2025 |
| Informalidad Agrícola | **88.7%** | ENEMDU dic-2025 |
| Ingreso Medio Agrícola | **$206/mes** (vs SBU $470) | ENEMDU dic-2025 |
| Multiplicador Arándano vs Maíz | **7.0x empleos/ha** | Parámetros MAG/SIPA |
| Efecto Agricultura sobre subempleo (AME) | **+14.4 a +25.9 pp** | Logit ponderado |
| Empleos formales generados (escenario 50k ha) | **102,000** | Simulación |

---

## 🎯 Pregunta de Investigación

> ¿La reconversión productiva hacia frutas de alto valor orientadas a exportación puede reducir la precariedad laboral estructural del sector agrícola rural ecuatoriano?

---

## 🔬 Metodología

### Datos
- **ENEMDU dic-2025** (INEC): 27,808 observaciones individuales, factor de expansión `fexp`
- **Parámetros técnicos MAG/SIPA**: rendimientos, precios en finca, costos, jornales
- **FAOSTAT QCL**: benchmark internacional de rendimientos
- **BCE**: contexto macroeconómico de exportaciones no petroleras

### Métodos Econométricos
1. **Estadística descriptiva ponderada** por factor de expansión
2. **Modelo Logit ponderado** (GLM binomial con `freq_weights=fexp`) con errores robustos HC1
3. **Efectos Marginales Promedio (AME)** para interpretación en puntos porcentuales
4. **Tests de robustez**: comparación Logit vs Probit
5. **Análisis de brecha de género**: probabilidades predichas por perfiles

### Especificación del Modelo
P(desempleo/subempleo = 1) = f(agricola, mujer, edad, edad²,
agro×mujer, educacion, + ε)


---

## 📊 Resultados Clave

### 1. Diagnóstico del Mercado Laboral Rural

El sector agrícola rural ecuatoriano presenta una **trampa estructural de precariedad**:

- **88.7% de informalidad** (vs ~50% urbano)
- Ingreso medio de **$206/mes**, menos de la mitad del SBU ($470)
- **87.9% de subempleo por ingresos** entre ocupados agrícolas

### 2. Evidencia Econométrica (Logit Ponderado)

**Hallazgo central:** Trabajar en agricultura aumenta entre **14.4 y 25.9 puntos porcentuales** la probabilidad de desempleo/subempleo rural, controlando por edad, sexo y educación (p < 0.001, OR = 37.9).

| Variable | AME (p.p.) | Interpretación |
|---|---|---|
| agricola_int | +14.4 a +25.9 | Penalización por trabajar en agro |
| mujer | -0.8 a -19.5 | Efecto protector femenino |
| educ_5.0 (superior) | -47.5 | Educación como movilidad social |
| edad_c | Variable según modelo | Perfil no lineal |

**Robustez confirmada:** Los resultados se mantienen consistentes entre Logit y Probit (p<0.01 en ambos).

### 3. Brecha de Género en el Rural

Probabilidades predichas por perfil (controlando por edad y educación):

| Perfil | Prob. Subempleo |
|---|---|
| Hombre No-Agrícola | 89.5% |
| **Hombre Agrícola** | **97.4%** |
| Mujer No-Agrícola | 89.1% |
| **Mujer Agrícola** | **95.9%** |

El sector agrícola lleva la precariedad al límite (96-97%), afectando a ambos géneros casi por igual.

### 4. Simulación de Reconversión Productiva

Impacto de reconvertir hectáreas de **Maíz Duro** a frutas de alto valor:

| Cultivo Destino | Multiplicador Empleo | Escenario Ambicioso (50k ha) |
|---|---|---|
| **Arándano** | **7.0x** | +102,000 empleos formales |
| Pitahaya | 5.0x | +62,000 empleos formales |
| Uvilla | 4.5x | +46,500 empleos formales |
| Aguacate Hass | 3.0x | +30,600 empleos formales |
| Cacao | 2.25x | +23,100 empleos formales |

**Valor bruto adicional en escenario ambicioso:** USD 1.73 billones (Arándano).

---

## 📁 Estructura del Proyecto
encadenamientos-fruticolas-ec/
├── src/
│ ├── build_dataset.py # Pipeline ENEMDU + parámetros cultivos
│ ├── simulation.py # Simulación 15 escenarios
│ ├── econometrics.py # Logit ponderado principal
│ ├── econometrics_v2.py # Logit robustecido (imputación)
│ └── robustez_genero.py # Probit + brecha de género
├── data/
│ ├── raw/ # Microdatos originales (no incluidos en repo)
│ └── processed/ # Datasets limpios (CSV)
├── notebooks/
│ └── 01_exploracion_inicial.ipynb
├── outputs/
│ ├── figures/ # Gráficos 300 DPI
│ └── tables/ # Tablas econométricas CSV
├── dashboard.py # App Streamlit
├── requirements.txt
└── README.md


---

## 💻 Reproducir el Análisis

### Requisitos
- Python 3.11+
- Entorno virtual recomendado

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/S-RiofrioR/encadenamientos-fruticolas-ec.git
cd encadenamientos-fruticolas-ec

# 2. Crear y activar entorno virtual
python -m venv .venv
source .venv/Scripts/activate  # Windows Git Bash
# source .venv/bin/activate    # Linux/macOS

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Descargar microdatos ENEMDU dic-2025 desde:
#    https://ecuadorencifras.ec.ec/microdatos/
#    Colocar en: data/raw/1_BDD_ENEMDU_2025_12_SPSS/

# 5. Ejecutar pipeline completo
python src/build_dataset.py

# 6. (Opcional) Ejecutar simulación
python src/simulation.py

# 7. (Opcional) Ejecutar modelo econométrico
python src/econometrics.py

# 8. (Opcional) Levantar dashboard local
streamlit run dashboard.py