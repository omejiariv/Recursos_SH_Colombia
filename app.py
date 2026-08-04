import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk

# -----------------------------------------------------------------------------
# 0. Carga y Procesamiento de Datos (Caché para optimizar rendimiento)
# -----------------------------------------------------------------------------
@st.cache_data
def cargar_datos():
    # En un entorno de producción, aquí conectaríamos a Supabase/PostGIS
    df_origenes = pd.read_csv('origenes_recursos.csv')
    df_ejecucion = pd.read_csv('ejecucion_proyectos.csv')
    df_impacto = pd.read_csv('impacto_efectividad.csv')
    
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
    # ... (Código del Módulo 1 que ya teníamos) ...
    st.write("Datos cargados correctamente. Aquí conectaremos las métricas generales.")

# --- MÓDULO 2: EL EMBUDO DE LA VERDAD ---
elif modulo_seleccionado == "📉 2. El Embudo de la Verdad (Flujo)":
    st.title("La Brecha de Ejecución: Del Recaudo al Territorio")
    st.write("""
    Este diagrama rastrea el capital desde su origen (obligatorio o voluntario) 
    hasta su destino final, evidenciando las ineficiencias, dispersión o recursos represados 
    antes de materializarse en infraestructura verde y conservación de cuencas.
    """)
    
    # Preparar nodos y enlaces para el Sankey
    # Nodos de Origen (Índices 0 a N-1)
    fuentes = df_flujo['tipo_recurso'].tolist()
    
    # Nodos de Destino
    # Índice N: Inversión Real Ejecutada
    # Índice N+1: Brecha (Retenidos / Administrativo)
    idx_ejecutada = len(fuentes)
    idx_brecha = len(fuentes) + 1
    
    nodos_label = fuentes + ["Inversión Real en Campo", "Brecha de Ejecución (Represados)"]
    nodos_color = ["#3498db" if "Ley" in f else "#2ecc71" for f in fuentes] + ["#27ae60", "#e74c3c"]
    
    origenes = []
    destinos = []
    valores = []
    
    # Construir los enlaces (Links)
    for i, row in df_flujo.iterrows():
        # Enlace del origen hacia lo Ejecutado
        origenes.append(i)
        destinos.append(idx_ejecutada)
        valores.append(row['monto_real_invertido'])
        
        # Enlace del origen hacia la Brecha
        origenes.append(i)
        destinos.append(idx_brecha)
        valores.append(row['brecha_perdida'])

    # Crear la figura interactiva de Sankey
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
          color = "rgba(189, 195, 199, 0.4)" # Gris translúcido para el flujo
        )
    )])

    fig.update_layout(
        title_text="Flujo Financiero Ambiental (Cifras en COP)", 
        font_size=12, 
        height=600,
        margin=dict(t=50, l=0, r=0, b=0)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Análisis inferior
    st.info(f"**Análisis Rápido:** De un recaudo total simulado de **${df_flujo['monto_recaudado'].sum():,.0f}**, solo **${df_flujo['monto_real_invertido'].sum():,.0f}** llega a ser ejecutado por actores en el territorio, dejando una brecha en el camino del **{(df_flujo['brecha_perdida'].sum() / df_flujo['monto_recaudado'].sum()) * 100:.1f}%**.")

# --- MÓDULO 3: VISOR GEOESPACIAL ---
elif modulo_seleccionado == "🗺️ 3. Visor Geoespacial de Impacto":
    st.title("Impacto Territorial y Escala Espacial")
    st.markdown("Mapeo 3D de intervenciones, infraestructura hídrica y cotas de elevación.")
    
    # Datos estructurados con la altimetría corregida
    mapa_data = pd.DataFrame({
        'hitos': ['Embalse La Fe', 'Embalse Piedras Blancas', 'Relleno Sanitario Regional', 'Corredor Ribereño Norte'],
        'lat': [6.1158, 6.2917, 6.3000, 6.3500], 
        'lon': [-75.4983, -75.5011, -75.5200, -75.5500],
        'elevacion_cota': [2100, 2300, 1000, 1500], # Cota del relleno configurada exactamente a 1,000 msnm
        'radio_dimension': [1200, 900, 500, 800], # Redimensionamiento para proporciones exactas
        'color': [[52, 152, 219, 180], [52, 152, 219, 180], [231, 76, 60, 180], [46, 204, 113, 180]]
    })

    # Configuración de la cámara apuntando al Valle de Aburrá con inclinación 3D
    view_state = pdk.ViewState(
        latitude=6.2518,
        longitude=-75.5636,
        zoom=10,
        pitch=50, # Inclinación para habilitar la perspectiva 3D
        bearing=-15
    )

    # Capa de columnas 3D que extruye la altimetría
    layer = pdk.Layer(
        "ColumnLayer",
        data=mapa_data,
        get_position='[lon, lat]',
        get_elevation='elevacion_cota',
        elevation_scale=1,
        get_radius='radio_dimension',
        get_fill_color='color',
        pickable=True,
        auto_highlight=True,
    )

    # Renderizado del mapa en Streamlit
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/light-v10',
        tooltip={"text": "{hitos}\nCota: {elevacion_cota} msnm"}
    ))
    
    st.success("El módulo ajusta la escala espacial y disposición geográfica de La Fe y Piedras Blancas, y mantiene la configuración de elevación del relleno sanitario a 1,000 metros sobre el nivel del mar para coincidir con el relieve geográfico.")

elif modulo_seleccionado == "⚙️ 4. Simulador: Fondo Común vs. Dispersión":
    st.title("Simulador Estratégico de Asignación Óptima")
    st.warning("Próximo paso: Lógica de simulación algorítmica.")
