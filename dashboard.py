"""
dashboard.py

Dashboard interactivo Streamlit para el estudio:
"Encadenamientos Frutícolas de Alto Valor y Reducción del Desempleo Rural en Ecuador"

Ejecutar desde la raíz del proyecto:
    streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Encadenamientos Frutícolas EC",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------
@st.cache_data
def cargar_datos():
    base = Path(__file__).resolve().parent / "data" / "processed"
    return {
        "indicadores": pd.read_csv(base / "indicadores_macro.csv"),
        "cultivos": pd.read_csv(base / "cultivos_metricas.csv"),
        "simulacion": pd.read_csv(base / "simulacion_reconversion.csv"),
        "brecha": pd.read_csv(Path(__file__).resolve().parent / "outputs" / "tables" / "brecha_genero_probabilidades.csv"),
    }

data = cargar_datos()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("🌱 Encadenamientos Frutícolas EC")
st.sidebar.markdown("---")
st.sidebar.markdown("**Fuente:** ENEMDU dic-2025 (INEC) + MAG/SIPA")
st.sidebar.markdown("**Autor:** Salomón Riofrío Rosero")
st.sidebar.markdown("---")

seccion = st.sidebar.radio(
    "Selecciona una sección:",
    ["📊 Diagnóstico Rural", "🌾 Cultivos Comparados", "🔄 Simulador de Reconversión", "⚖️ Brecha de Género"]
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("Encadenamientos Frutícolas de Alto Valor")
st.markdown("### Impacto sobre el empleo rural en Ecuador")
st.markdown("---")

# ---------------------------------------------------------------------------
# SECCIÓN 1: Diagnóstico Rural
# ---------------------------------------------------------------------------
if seccion == "📊 Diagnóstico Rural":
    st.header("Diagnóstico del Mercado Laboral Rural (dic-2025)")
    
    ind = data["indicadores"].iloc[0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("PEA Rural Total", f"{ind['pea_rural_total']:,.0f}")
    col2.metric("PEA Agrícola", f"{ind['pea_rural_agricola']:,.0f}")
    col3.metric("Tasa Desempleo Rural", f"{ind['tasa_desempleo_rural_pct']}%")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Subempleo Agrícola", f"{ind['subempleo_ingreso_agricola_pct']}%",
                delta="Alto", delta_color="inverse")
    col2.metric("Informalidad Agrícola", f"{ind['informalidad_agricola_pct']}%",
                delta="Crítico", delta_color="inverse")
    col3.metric("Ingreso Medio Agrícola", f"${ind['ingreso_medio_agricola_usd']:.0f}/mes",
                delta=f"vs SBU $470", delta_color="inverse")
    
    st.markdown("---")
    st.info("""
    **Hallazgo clave:** El 88.7% del empleo agrícola rural es informal y genera ingresos 
    promedio de $206/mes, menos de la mitad del Salario Básico Unificado ($470).
    """)

# ---------------------------------------------------------------------------
# SECCIÓN 2: Cultivos Comparados
# ---------------------------------------------------------------------------
elif seccion == "🌾 Cultivos Comparados":
    st.header("Comparativa de los 6 Cultivos del Estudio")
    
    cult = data["cultivos"].copy()
    
    # Gráfico de dispersión
    fig = px.scatter(
        cult, x="empleos_ha", y="ingreso_bruto_usd_ha",
        size="multiplicador_empleo_vs_maiz",
        color="tipo",
        hover_name="cultivo",
        labels={
            "empleos_ha": "Empleos directos / ha",
            "ingreso_bruto_usd_ha": "Ingreso bruto USD / ha",
            "tipo": "Tipo de cultivo"
        },
        title="Ingreso vs Intensidad de Empleo por Cultivo"
    )
    for _, r in cult.iterrows():
        fig.add_annotation(
            x=r["empleos_ha"], y=r["ingreso_bruto_usd_ha"],
            text=r["cultivo"], showarrow=False, yshift=10
        )
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Tabla detallada
    st.subheader("Métricas detalladas por hectárea")
    st.dataframe(
        cult[["cultivo", "tipo", "rend_kg_ha", "precio_usd_kg", 
              "ingreso_bruto_usd_ha", "empleos_ha", "multiplicador_empleo_vs_maiz"]]
        .rename(columns={
            "rend_kg_ha": "Rend. (kg/ha)",
            "precio_usd_kg": "Precio ($/kg)",
            "ingreso_bruto_usd_ha": "Ingreso ($/ha)",
            "empleos_ha": "Empleos/ha",
            "multiplicador_empleo_vs_maiz": "Multiplicador vs Maíz"
        }),
        use_container_width=True,
        hide_index=True
    )
    
    st.info("""
    **El Arándano multiplica por 7x el empleo por hectárea** respecto al Maíz Duro,
    con ingresos brutos 25 veces superiores ($36,000 vs $1,456 USD/ha).
    """)

# ---------------------------------------------------------------------------
# SECCIÓN 3: Simulador de Reconversión
# ---------------------------------------------------------------------------
elif seccion == "🔄 Simulador de Reconversión":
    st.header("Simulador de Reconversión Productiva")
    st.markdown("Calcula el impacto de reconvertir hectáreas de **Maíz Duro** a frutas de alto valor.")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        hectareas = st.slider(
            "Hectáreas a reconvertir:",
            min_value=1000, max_value=100000, value=10000, step=1000,
            format="%d ha"
        )
        
        cultivo_destino = st.selectbox(
            "Cultivo destino:",
            ["Arándano", "Pitahaya", "Uvilla", "Aguacate Hass", "Cacao"],
            index=0
        )
    
    with col2:
        # Filtrar la simulación
        sim = data["simulacion"]
        row = sim[(sim["hectareas_reconvertidas"] == hectareas) & 
                  (sim["cultivo_destino"] == cultivo_destino)]
        
        if row.empty:
            # Calcular manualmente si no está en la tabla
            cult = data["cultivos"]
            origen = cult[cult["cultivo"] == "Maíz Duro"].iloc[0]
            destino = cult[cult["cultivo"] == cultivo_destino].iloc[0]
            
            d_empleos = int((destino["empleos_ha"] - origen["empleos_ha"]) * hectareas)
            d_ingreso = int((destino["ingreso_bruto_usd_ha"] - origen["ingreso_bruto_usd_ha"]) * hectareas)
            multiplicador = destino["multiplicador_empleo_vs_maiz"]
        else:
            d_empleos = int(row.iloc[0]["delta_empleos_totales"])
            d_ingreso = int(row.iloc[0]["delta_valor_bruto_usd"])
            multiplicador = row.iloc[0]["multiplicador_empleo"]
        
        st.markdown(f"### Impacto de reconvertir {hectareas:,} ha a {cultivo_destino}")
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Empleos netos generados", f"{d_empleos:,}",
                     delta=f"{multiplicador:.1f}x vs Maíz")
        col_b.metric("Valor bruto adicional", f"${d_ingreso:,.0f}")
        col_c.metric("Empleos por hectárea", f"{d_empleos/hectareas:.2f}")
        
        st.markdown("---")
        st.success(f"""
        **Interpretación:** Reconvertir **{hectareas:,} hectáreas** de Maíz Duro a {cultivo_destino}
        generaría aproximadamente **{d_empleos:,} empleos rurales adicionales**
        y un valor bruto de **${d_ingreso/1e6:,.1f} millones de USD** al año.
        """)

# ---------------------------------------------------------------------------
# SECCIÓN 4: Brecha de Género
# ---------------------------------------------------------------------------
elif seccion == "⚖️ Brecha de Género":
    st.header("Brecha de Género y Penalización Agrícola")
    st.markdown("Probabilidades predichas por modelo Logit (controlando por edad y educación).")
    
    bg = data["brecha"]
    
    fig = go.Figure(data=[
        go.Bar(
            x=bg["perfil"],
            y=bg["prob_pct"],
            marker_color=["#3498db", "#e74c3c", "#3498db", "#e74c3c"],
            text=[f"{v}%" for v in bg["prob_pct"]],
            textposition="auto"
        )
    ])
    fig.update_layout(
        title="Probabilidad de desempleo/subempleo rural por perfil",
        yaxis_title="Probabilidad (%)",
        yaxis_range=[0, 100],
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.warning("""
        **Hombres rurales:**
        - No agrícolas: 89.5% en precariedad
        - Agrícolas: **97.4%** (+7.9 pp de castigo)
        """)
    with col2:
        st.error("""
        **Mujeres rurales:**
        - No agrícolas: 89.1% en precariedad
        - Agrícolas: **95.9%** (+6.8 pp de castigo)
        """)
    
    st.info("""
    **Conclusión de política:** La reconversión hacia fruticultura de alto valor 
    (con empleos formales en empaque y cosecha) es una herramienta de **equidad de género**.
    """)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption("""
📊 **Fuentes:** ENEMDU dic-2025 (INEC), MAG/SIPA, FAOSTAT  
🔬 **Metodología:** Logit ponderado con errores robustos HC1  
📅 **Última actualización:** Diciembre 2025
""")