import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

# -----------------------------------------------------------------------------
# 0. Carga y Procesamiento de Datos (Caché para optimizar rendimiento)
# -----------------------------------------------------------------------------
@st.cache_data
def cargar_datos():
    # 1. Tabla de Orígenes de Recursos
    df_origenes = pd.DataFrame({
        'id_fuente': ['F001', 'F002', 'F003', 'F004', 'F005'],
        'tipo_recurso': ['Ley (Inversión 1%)', 'Ley (Transferencias)', 'Voluntario (Fondo)', 'Voluntario (ESG)', 'Ley (SGP)'],
        'entidad_recaudadora': ['Autoridad Ambiental Local', 'Sector Eléctrico', 'Fondo de Agua', 'Empresa Privada', 'Sistema General'],
        'monto_recaudado': [50000000000, 120000000000, 35000000000, 15000000000, 80000000000],
        'vigencia': [2024, 2024, 2024, 2024, 2024]
    })
    
    # 2. Tabla de Ejecución de Proyectos
    df_ejecucion = pd.DataFrame({
        'id_proyecto': ['P001', 'P002', 'P003', 'P004', 'P005'],
        'id_fuente': ['F001', 'F002', 'F003', 'F004', 'F005'],
        'monto_real_invertido': [30000000000, 90000000000, 32000000000, 10000000000, 40000000000],
        'entidad_ejecutora': ['ONG Territorial', 'Operador Hídrico', 'Corporación Cuenca', 'Junta de Acción Local', 'Municipio'],
        'ubicacion_estrategica': ['Embalse La Fe', 'Embalse Piedras Blancas', 'Corredor Ribereño Norte', 'Zona Recarga Sur', 'Microcuenca Alta'],
        'lat': [6.1158, 6.2917, 6.3500, 6.0500, 6.4000],
        'lon': [-75.4983, -75.5011, -75.5500, -75.6000, -75.4500],
        'cuenca': ['Río Pantanillo', 'Río Piedras', 'Río Porce', 'Río Aburrá', 'Río Grande']
    })
    
    # 3. Tabla de Impacto y Efectividad
    df_impacto = pd.DataFrame({
        'id_proyecto': ['P001', 'P002', 'P003', 'P004', 'P005'],
        'ha_restauradas': [120, 350, 80, 45, 200],
        'aislamientos_km': [15.5, 40.0, 10.2, 5.0, 25.4],
        'familias_psa': [45, 120, 30, 15, 80],
        'roi_ambiental': [1.2, 2.5, 1.8, 1.1, 2.0]
    })
    
    # Consolidar datos para el análisis de flujo
    df_flujo = pd.merge(df_origenes, df_ejecucion, on='id_fuente', how='left')
    df_flujo['brecha_perdida'] = df_flujo['monto_recaudado'] - df_flujo['monto_real_invertido']
    
    return df_origenes, df_ejecucion, df_impacto, df_flujo

df_origenes, df_ejecucion, df_impacto, df_flujo = cargar_datos()

# -----------------------------------------------------------------------------
# 1. Configuración de la Página y Estética General
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Tablero de Inversión Hídrica | Colombia", page_icon="💧", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #1f2937; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Barra Lateral
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://via.placeholder.com/300x100.png?text=Logo+Proyecto", use_container_width=True)
    st.title("Navegación")
    
    modulo_seleccionado = st.radio(
        "Ir a:",
        ["📊 1. El Panorama Nacional vs. Regional", "📉 2. El Embudo de la Verdad (Flujo)", "🗺️ 3. Visor Geoespacial de Impacto", "⚙️ 4. Simulador: Fondo Común"]
    )
    
    st.markdown("---")
    st.subheader("Filtros Globales")
    region = st.selectbox("Región de Análisis", ["Toda Colombia", "Antioquia", "Valle de Aburrá"], index=2)
    anio_fiscal = st.slider("Vigencia Fiscal", 2020, 2026, (2024, 2026))

# -----------------------------------------------------------------------------
# 3. Módulos
# -----------------------------------------------------------------------------

if modulo_seleccionado == "📊 1. El Panorama Nacional vs. Regional":
    st.title("Panorama de Recursos Ambientales e Hídricos")
    st.write("Datos cargados correctamente. Aquí conectaremos las métricas generales.")

# --- MÓDULO 1: EL PANORAMA ---
if modulo_seleccionado == "📊 1. El Panorama Nacional vs. Regional":
    st.title("Panorama de Recursos Ambientales e Hídricos")
    st.markdown(f"**Área de análisis actual:** {region}")
    
    st.write("""
    En esta sección presentamos los KPIs principales del sistema financiero ambiental: 
    Total recaudado vs. Total ejecutado en campo.
    """)
    
    # Cálculos dinámicos para los KPIs basados en el DataFrame
    total_recaudado = df_flujo['monto_recaudado'].sum()
    total_ejecutado = df_flujo['monto_real_invertido'].sum()
    brecha = total_recaudado - total_ejecutado
    eficiencia = (total_ejecutado / total_recaudado) * 100
    
    recursos_ley = df_flujo[df_flujo['tipo_recurso'].str.contains('Ley')]['monto_recaudado'].sum()
    recursos_voluntarios = df_flujo[df_flujo['tipo_recurso'].str.contains('Voluntario')]['monto_recaudado'].sum()

    # Renderizado de métricas en columnas (Layout)
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Total Recaudado", value=f"${total_recaudado:,.0f}")
    col2.metric(label="Inversión Real Ejecutada", value=f"${total_ejecutado:,.0f}", delta=f"-${brecha:,.0f} (Brecha)", delta_color="inverse")
    col3.metric(label="Eficiencia del Sistema", value=f"{eficiencia:.1f}%")
    
    st.markdown("---")
    
    col4, col5 = st.columns(2)
    col4.metric(label="Recursos de Ley", value=f"${recursos_ley:,.0f}")
    col5.metric(label="Recursos Voluntarios (Privados/Fondos)", value=f"${recursos_voluntarios:,.0f}")

# --- MÓDULO 2: EL EMBUDO DE LA VERDAD ---
elif modulo_seleccionado == "📉 2. El Embudo de la Verdad (Flujo)":
    st.title("La Brecha de Ejecución: Del Recaudo al Territorio")
    st.write("""
    Este diagrama rastrea el capital desde su origen (obligatorio o voluntario) 
    hasta su destino final, evidenciando las ineficiencias, dispersión o recursos represados 
    antes de materializarse en infraestructura verde y conservación de cuencas.
    """)
    
    fuentes = df_flujo['tipo_recurso'].tolist()
    idx_ejecutada = len(fuentes)
    idx_brecha = len(fuentes) + 1
    
    nodos_label = fuentes + ["Inversión Real en Campo", "Brecha de Ejecución (Represados)"]
    nodos_color = ["#3498db" if "Ley" in f else "#2ecc71" for f in fuentes] + ["#27ae60", "#e74c3c"]
    
    origenes = []
    destinos = []
    valores = []
    
    for i, row in df_flujo.iterrows():
        origenes.append(i)
        destinos.append(idx_ejecutada)
        valores.append(row['monto_real_invertido'])
        
        origenes.append(i)
        destinos.append(idx_brecha)
        valores.append(row['brecha_perdida'])

    fig = go.Figure(data=[go.Sankey(
        node = dict(
          pad = 20,
          thickness = 30,
          line = dict(color = "black", width = 0.5),
          label = nodos_label,
          color = nodos_color
        ),
        link = dict(
          source = origenes,
          target = destinos,
          value = valores,
          color = "rgba(189, 195, 199, 0.4)" 
        )
    )])

    fig.update_layout(
        title_text="Flujo Financiero Ambiental (Cifras en COP)", 
        font_size=12, 
        height=600,
        margin=dict(t=50, l=0, r=0, b=0)
    )
    
    # Renderizado del gráfico
    st.plotly_chart(fig, use_container_width=True)
    
    # Cálculos previos para el análisis de eficiencia
    total_rec = df_flujo['monto_recaudado'].sum()
    total_ejec = df_flujo['monto_real_invertido'].sum()
    pct_brecha = (df_flujo['brecha_perdida'].sum() / total_rec) * 100
    
    # Texto de análisis con un enfoque técnico y expresivo
    texto_analisis = (
        f"**La Anatomía del Flujo y el Laberinto del Recurso:** De un volumen inicial de "
        f"**${total_rec:,.0f}** movilizados en el papel, el diagrama revela que solo "
        f"**${total_ejec:,.0f}** logran decantarse en soluciones tangibles en el territorio. "
        f"La corriente financiera sufre una dispersión constante, dejando una brecha "
        f"estructural del **{pct_brecha:.1f}%**."
    )
    
    # Usamos st.warning para resaltar visualmente el problema de la brecha
    st.warning(texto_analisis, icon="⚠️")
    
# --- MÓDULO 3: VISOR GEOESPACIAL ---
elif modulo_seleccionado == "🗺️ 3. Visor Geoespacial de Impacto":
    st.title("Impacto Territorial y Escala Espacial")
    st.markdown("Mapeo topográfico de intervenciones e infraestructura hídrica regional.")
    
    # Coordenadas y radios ajustados
    mapa_data = [
        {"hitos": "Embalse La Fe", "lat": 6.1158, "lon": -75.4983, "cota": 2100, "radio": 1200, "color": "#3498db"},
        {"hitos": "Embalse Piedras Blancas", "lat": 6.2917, "lon": -75.5011, "cota": 2300, "radio": 900, "color": "#3498db"},
        {"hitos": "Relleno Sanitario Regional", "lat": 6.3000, "lon": -75.5200, "cota": 1000, "radio": 500, "color": "#e74c3c"},
        {"hitos": "Corredor Ribereño Norte", "lat": 6.3500, "lon": -75.5500, "cota": 1500, "radio": 800, "color": "#2ecc71"}
    ]

    # Crear mapa base con OpenTopoMap (Ideal para cuencas hidrográficas)
    m = folium.Map(location=[6.2518, -75.5636], zoom_start=10, tiles="OpenTopoMap")

    # Agregar círculos proporcionales
    for d in mapa_data:
        folium.Circle(
            location=[d['lat'], d['lon']],
            radius=d['radio'],
            color=d['color'],
            fill=True,
            fill_color=d['color'],
            fill_opacity=0.7,
            popup=f"<b>{d['hitos']}</b><br>Cota: {d['cota']} msnm"
        ).add_to(m)

    # Renderizar en Streamlit
    st_folium(m, width=1200, height=600)
    
    st.success("El módulo ajusta la escala espacial y disposición geográfica de La Fe y Piedras Blancas, y mantiene la configuración de elevación del relleno sanitario a 1,000 metros sobre el nivel del mar para coincidir con el relieve geográfico.")

# --- MÓDULO 4: EL SIMULADOR DE FONDO COMÚN ---
elif modulo_seleccionado == "⚙️ 4. Simulador: Fondo Común":
    st.title("Simulador Estratégico de Asignación Óptima")
    
    st.write("""
    Compara el modelo actual de inversiones fragmentadas frente a un esquema de **Fondo Común** con plan estratégico unificado.
    Ajusta el porcentaje de recursos unificados para proyectar el incremento en impacto territorial.
    """)
    
    col_sim1, col_sim2 = st.columns([1, 2])
    
    with col_sim1:
        st.subheader("Parámetros del Modelo")
        porcentaje_fondo = st.slider("% de Recursos en Fondo Común", min_value=0, max_value=100, value=20, step=10)
        criterio_priorizacion = st.selectbox("Criterio de Inversión", ["Estrés Hídrico", "Riesgo de Desabastecimiento", "ROI Ecológico"])
        
        # Cálculos de simulación
        inversion_total = df_flujo['monto_recaudado'].sum()
        eficiencia_base = (df_flujo['monto_real_invertido'].sum() / inversion_total) * 100
        
        # Cada 10% unificado incrementa la eficiencia y reduce costos administrativos
        eficiencia_simulada = eficiencia_base + (porcentaje_fondo * 0.25)
        eficiencia_simulada = min(eficiencia_simulada, 98.0) # Tope lógico
        
        st.metric(label="Eficiencia Financiera Proyectada", 
                  value=f"{eficiencia_simulada:.1f}%", 
                  delta=f"{(eficiencia_simulada - eficiencia_base):.1f}% de mejora")

    with col_sim2:
        st.subheader("Proyección de Impacto: Hectáreas Restauradas")
        
        # Proyección de impacto en territorio
        ha_base = df_impacto['ha_restauradas'].sum()
        # Se asume un multiplicador de impacto por la centralización estratégica
        ha_proyectadas = ha_base * (1 + (porcentaje_fondo * 0.008))
        
        # Gráfica comparativa usando Plotly Graph Objects
        fig_sim = go.Figure(data=[
            go.Bar(
                name='Impacto',
                x=["Escenario Actual (Fragmentado)", "Escenario Simulado (Fondo Común)"],
                y=[ha_base, ha_proyectadas],
                text=[f"{ha_base:,.0f} ha", f"{ha_proyectadas:,.0f} ha"],
                textposition='auto',
                marker_color=["#e74c3c", "#2ecc71"]
            )
        ])
        
        fig_sim.update_layout(
            height=400, 
            margin=dict(t=30, b=0, l=0, r=0),
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig_sim, use_container_width=True)
        
        st.info(f"💡 **Insight Territorial:** Al unificar el **{porcentaje_fondo}%** de los recursos en un fondo común bajo el criterio de **{criterio_priorizacion}**, la capacidad de restauración pasaría de {ha_base:,.0f} hectáreas a **{ha_proyectadas:,.0f} hectáreas**, eliminando esfuerzos duplicados en subcuencas.")
