import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import random

# -----------------------------------------------------------------------------
# 0. Carga y Procesamiento de Datos Base (ETL desde archivo oficial DNP)
# -----------------------------------------------------------------------------
@st.cache_data
def cargar_datos():
    # 1. Catálogo Normativo (Mantenemos la base legal intacta)
    df_normatividad = pd.DataFrame({
        'Instrumento': ['Art. 111 (Ley 99/93) - 1% ICLD', 'Transferencias Sector Eléctrico', 'Tasa por Uso', 'Tasa Retributiva', 'Inversión Forzosa 1%', 'PSA', 'Recursos ESG'],
        'Tipo': ['Ley', 'Ley', 'Ley', 'Ley', 'Ley', 'Mixto', 'Voluntario']
    })

    # 2. Ingesta del Archivo Oficial DNP (TerriData)
    try:
        # Cargar el archivo directamente desde el repositorio
        df_terridata = pd.read_excel('data/TerriData_Dim7_Finanzas.xlsx')
        
        # Filtrar únicamente la variable de interés
        df_ic_raw = df_terridata[df_terridata['Indicador'] == 'Ingresos corrientes'].copy()
        
        # Función de limpieza de moneda (Transformación)
        def limpiar_moneda(valor):
            if pd.isna(valor):
                return 0
            if isinstance(valor, str):
                # Limpiar formato europeo (ej. 1.029.659,00)
                valor = valor.replace('.', '').replace(',', '.')
            return float(valor) * 1_000_000 # Convertir de millones a COP exactos
            
        df_ic_raw['Ingresos_Corrientes'] = df_ic_raw['Dato Numérico'].apply(limpiar_moneda)
        df_ic_raw['Minimo_1_Porciento'] = df_ic_raw['Ingresos_Corrientes'] * 0.01
        
        # Estandarizar columnas para los Módulos del Tablero
        df_ic = df_ic_raw[['Departamento', 'Entidad', 'Año', 'Ingresos_Corrientes', 'Minimo_1_Porciento']]
        df_ic = df_ic.rename(columns={'Entidad': 'Municipio'})
        
    except Exception as e:
        # Mensaje de alerta por si Streamlit Cloud no encuentra el archivo temporalmente
        st.error(f"Error en el ETL: No se pudo procesar el archivo TerriData. Revisa los logs. Error: {e}")
        df_ic = pd.DataFrame(columns=['Departamento', 'Municipio', 'Año', 'Ingresos_Corrientes', 'Minimo_1_Porciento'])

    # 3. Bases Temporales de Ejecución (Para no romper Módulos 1-4 mientras se hace el nuevo Excel)
    df_origenes = pd.DataFrame({
        'id_fuente': ['F001', 'F002', 'F003'],
        'tipo_recurso': ['Ley (Inversión 1%)', 'Ley (Transferencias)', 'Voluntario (Fondo)'],
        'entidad_recaudadora': ['Municipios/Gobernaciones', 'Sector Eléctrico', 'Fondo de Agua'],

        # F001 se reescribe dinámicamente con TerriData, no importa el número acá.
        # F002 (Eléctrico) sube a 4.5 Billones base Colombia
        # F003 (Voluntario) sube a 750 Mil Millones base Colombia
        'monto_recaudado': [0, 4500000000000, 750000000000] 
    })
    
    df_ejecucion = pd.DataFrame({
        'id_proyecto': ['P001', 'P002'],
        'id_fuente': ['F001', 'F002'],
        'monto_real_invertido': [30000000000, 90000000000],
        'entidad_ejecutora': ['ONG Territorial', 'Operador Hídrico'],
        'lat': [6.1158, 6.2917],
        'lon': [-75.4983, -75.5011],
        'region': ['Valle de Aburrá', 'Antioquia'],
        'vigencia': [2024, 2024]
    })
    
    df_impacto = pd.DataFrame({
        'id_proyecto': ['P001', 'P002'],
        'ha_restauradas': [120, 350]
    })

    return df_normatividad, df_origenes, df_ejecucion, df_impacto, df_ic

# Llamado al ETL y despliegue de los 5 dataframes
df_normatividad, df_origenes, df_ejecucion_base, df_impacto_base, df_ic_base = cargar_datos()

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
# 2. Barra Lateral (Aquí "nace" la variable region)
# -----------------------------------------------------------------------------
with st.sidebar:
    # Cargar el Logo Institucional
    try:
        st.image('data/CuencaVerdeLogo_V1.JPG', use_container_width=True)
    except:
        st.caption("Fondo de Agua CuencaVerde") # Texto de respaldo por si falla la imagen
        
    st.markdown("---")
    st.subheader("Navegación")
    
    modulo_seleccionado = st.radio(
        "Ir a:",
        [
            "📊 1. El Panorama Nacional vs. Regional", 
            "📉 2. El Embudo de la Verdad (Flujo)", 
            "🗺️ 3. Visor Geoespacial de Impacto", 
            "⚙️ 4. Simulador: Fondo Común",
            "💰 5. Potencial del 1% (Art. 111)" # NUEVO MÓDULO
        ]
    )
    
    st.markdown("---")
    st.subheader("Filtros Globales")
    
    # El archivo TerriData contiene datos agregados para Colombia y desagregados para Antioquia
    region = st.selectbox("Región / Departamento", ["Toda Colombia", "Antioquia"], index=1)
    
    # Selector dinámico de municipio (Solo se activa si estamos en Antioquia)
    if region == "Antioquia":
        # Extraemos los municipios reales del DataFrame (excluyendo el agregado departamental 'Antioquia')
        municipios_reales = df_ic_base[(df_ic_base['Departamento'] == 'Antioquia') & (df_ic_base['Municipio'] != 'Antioquia')]['Municipio'].unique().tolist()
        municipios_reales.sort() # Orden alfabético para mejor experiencia de usuario
        municipios_reales.insert(0, "Todos") # Opción por defecto
        
        municipio_seleccionado = st.selectbox("Municipio Específico", municipios_reales)
    else:
        municipio_seleccionado = "Todos"
        
    # El rango temporal se ajusta a la realidad del archivo del DNP
    anio_fiscal = st.slider("Vigencia Fiscal (TerriData)", 2000, 2024, (2020, 2024))

# -----------------------------------------------------------------------------
# Motor de Filtrado Dinámico (Pandas Pipeline)
# -----------------------------------------------------------------------------
anio_inicio, anio_fin = anio_fiscal 

# 1. Filtro Temporal ESTRICTO para TerriData
df_ic = df_ic_base[(df_ic_base['Año'] >= anio_inicio) & (df_ic_base['Año'] <= anio_fin)]

# 2. Cálculo EXACTO del 1% y Escala Proporcional
if region == "Toda Colombia":
    recaudo_real_1_pct = df_ic[df_ic['Departamento'] == 'Colombia']['Minimo_1_Porciento'].sum()
    filtro_ejecucion = df_ejecucion_base['region'].unique()
    factor_escala = 1.0 
    ruta_seleccion = "Toda Colombia" # Ruta para la UI
else:
    # Datos solo de Antioquia
    df_ant = df_ic[(df_ic['Departamento'] == 'Antioquia') & (df_ic['Municipio'] != 'Antioquia')]
    total_antioquia_ic = df_ant['Ingresos_Corrientes'].sum() # Base para la regla de tres
    
    if municipio_seleccionado != "Todos":
        df_mun = df_ant[df_ant['Municipio'] == municipio_seleccionado]
        recaudo_real_1_pct = df_mun['Minimo_1_Porciento'].sum()
        
        # EL ARREGLO MATEMÁTICO: Escala proporcional según el peso económico real del municipio
        ingresos_mun = df_mun['Ingresos_Corrientes'].sum()
        factor_escala = ingresos_mun / total_antioquia_ic if total_antioquia_ic > 0 else 0
        
        filtro_ejecucion = [municipio_seleccionado]
        ruta_seleccion = f"{municipio_seleccionado} - {region}" # Ruta específica
    else:
        recaudo_real_1_pct = df_ant['Minimo_1_Porciento'].sum()
        filtro_ejecucion = ['Antioquia', 'Valle de Aburrá']
        factor_escala = 0.15 # Factor departamental aprox
        ruta_seleccion = region

# 3. EL PUENTE: Inyectar la realidad a los Módulos 1 al 4
df_origenes_dinamico = df_origenes.copy()
df_origenes_dinamico['monto_recaudado'] = df_origenes_dinamico['monto_recaudado'].astype(float)

df_origenes_dinamico.loc[df_origenes_dinamico['id_fuente'] == 'F001', 'monto_recaudado'] = recaudo_real_1_pct
df_origenes_dinamico.loc[df_origenes_dinamico['id_fuente'] == 'F002', 'monto_recaudado'] *= factor_escala
df_origenes_dinamico.loc[df_origenes_dinamico['id_fuente'] == 'F003', 'monto_recaudado'] *= factor_escala

# 4. Filtrar y escalar ejecución
df_ejecucion = df_ejecucion_base[df_ejecucion_base['region'].isin(filtro_ejecucion)].copy()
if not df_ejecucion.empty:
    df_ejecucion['monto_real_invertido'] *= factor_escala

# 5. Flujo financiero y Brecha
df_flujo = pd.merge(df_origenes_dinamico, df_ejecucion, on='id_fuente', how='left').fillna(0)
df_flujo['brecha_perdida'] = df_flujo['monto_recaudado'] - df_flujo['monto_real_invertido']
df_flujo['brecha_perdida'] = df_flujo['brecha_perdida'].clip(lower=0) 

# 6. Impactos
df_impacto = df_impacto_base[df_impacto_base['id_proyecto'].isin(df_ejecucion['id_proyecto'])]

# -----------------------------------------------------------------------------
# 3. Módulos

# --- MÓDULO 1: EL PANORAMA NACIONAL VS. REGIONAL ---
if modulo_seleccionado == "📊 1. El Panorama Nacional vs. Regional":
    st.title("Panorama de Recursos Ambientales e Hídricos")
    
    # 1. RUTA DE SELECCIÓN Y CONTEXTO
    st.info(f"📍 **Área de análisis actual:** `{ruta_seleccion}` | 📅 **Vigencia Fiscal:** `{anio_inicio} - {anio_fin}`")
    st.markdown("En esta sección presentamos los KPIs principales del ecosistema financiero ambiental de la región seleccionada.")
    
    total_recaudado = df_flujo['monto_recaudado'].sum()
    total_ejecutado = df_flujo['monto_real_invertido'].sum()
    brecha = df_flujo['brecha_perdida'].sum()
    eficiencia = (total_ejecutado / total_recaudado) * 100 if total_recaudado > 0 else 0

    # 2. MÉTRICAS CON TOOLTIPS (HELPS)
    st.markdown("### Resumen Macro")
    col1, col2, col3 = st.columns(3)
    col1.metric(
        label="Total Capital Movilizado", 
        value=f"${total_recaudado:,.0f}",
        help="Suma total de recursos de Ley (basado en el 1% de ingresos corrientes reales del DNP) y recursos proyectados (Sector Eléctrico y Voluntarios) para el área y tiempo seleccionados."
    )
    col2.metric(
        label="Inversión Real Ejecutada", 
        value=f"${total_ejecutado:,.0f}", 
        delta=f"-${brecha:,.0f} (Brecha/Fricción)", 
        delta_color="inverse",
        help="Dinero que efectivamente se decantó en obras, proyectos e infraestructura en territorio."
    )
    col3.metric(
        label="Eficiencia del Sistema", 
        value=f"{eficiencia:.1f}%",
        help="Porcentaje del capital que sobrevive a los costos de transacción, burocracia y tiempos muertos. Cálculo: (Inversión Ejecutada / Capital Movilizado) * 100."
    )
    
    st.markdown("---")
    
    # 3. GRÁFICO Y DESGLOSE EN DOS COLUMNAS
    st.markdown("### Composición del Capital Ambiental")
    col_izq, col_der = st.columns([1, 1])
    
    with col_izq:
        recursos_ley = df_flujo[df_flujo['tipo_recurso'].str.contains("Ley")]['monto_recaudado'].sum()
        recursos_vol = df_flujo[df_flujo['tipo_recurso'].str.contains("Voluntario")]['monto_recaudado'].sum()
        
        st.metric("🏛️ Recursos de Ley (Mandatorios)", f"${recursos_ley:,.0f}", help="Incluye el Art. 111 (1% IC) y las Transferencias del Sector Eléctrico.")
        st.metric("🤝 Recursos Voluntarios (Privados/Fondos)", f"${recursos_vol:,.0f}", help="Aportes ESG del sector corporativo y mecanismos de Fondos de Agua.")
        
        with st.expander("📖 Soporte Jurídico y Clasificación de Recursos"):
            st.markdown("Esta tabla consolida los fundamentos legales que estructuran la movilización de capital.")
            st.dataframe(df_normatividad, use_container_width=True)

    with col_der:
        # Gráfico de Dona con Plotly para darle vida visual al módulo
        df_grafico = df_origenes_dinamico[df_origenes_dinamico['monto_recaudado'] > 0]
        fig_dona = go.Figure(data=[go.Pie(
            labels=df_grafico['tipo_recurso'], 
            values=df_grafico['monto_recaudado'],
            hole=.5,
            marker_colors=['#3498db', '#2ecc71', '#f1c40f', '#e74c3c', '#9b59b6'],
            textinfo='percent'
        )])
        fig_dona.update_layout(
            showlegend=True, 
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            margin=dict(t=10, b=10, l=10, r=10),
            height=300
        )
        st.plotly_chart(fig_dona, use_container_width=True)

    # 4. FUENTE DE DATOS PERMANENTE (Transparencia)
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("🔍 **Fuente Oficial de Datos:** Base construida sobre los reportes del *Departamento Nacional de Planeación (DNP) - TerriData* (Operaciones efectivas de caja). El cálculo del Art. 111 se deriva estrictamente de los ingresos corrientes históricos reportados por las entidades territoriales. Los recursos adicionales representan un factor de simulación escalado al peso económico del municipio.")

    with st.expander("📖 Soporte Jurídico y Clasificación de Recursos"):
        st.markdown("### Catálogo Normativo para la Protección del Agua")
        st.write("Esta tabla consolida los fundamentos legales y los mecanismos voluntarios que estructuran la movilización de capital ambiental en Colombia.")
        st.dataframe(df_normatividad, use_container_width=True)
        st.caption("Fuentes: Ley 99 de 1993, Decretos Reglamentarios (MinAmbiente), y reportes de sostenibilidad corporativa (ESG).")

# --- MÓDULO 2: EL EMBUDO DE LA VERDAD (FLUJO) ---
elif modulo_seleccionado == "📉 2. El Embudo de la Verdad (Flujo)":
    st.title("El Embudo de la Verdad")
    st.write("Rastreo de la eficiencia del capital: Desde el origen del recurso hasta la ejecución en territorio.")
    
    st.info(f"📍 **Área de análisis:** `{ruta_seleccion}` | 📅 **Vigencia Fiscal:** `{anio_inicio} - {anio_fin}`")

    # Si no hay datos de recaudo, mostramos una alerta para no romper el gráfico
    if df_flujo['monto_recaudado'].sum() == 0:
        st.warning("No hay recursos recaudados registrados para esta selección temporal y espacial.")
    else:
        # 1. PREPARACIÓN DE NODOS PARA EL SANKEY
        # Identificamos las fuentes (origen) y los ejecutores (destino)
        fuentes = df_flujo['tipo_recurso'].unique().tolist()
        ejecutores = df_flujo[df_flujo['entidad_ejecutora'].notna()]['entidad_ejecutora'].unique().tolist()
        nodo_brecha = "Brecha / Retención (Sin Ejecutar)"
        
        # Lista maestra de nodos y su diccionario de índices (Plotly Sankey usa números, no nombres)
        nodos = fuentes + ejecutores + [nodo_brecha]
        nodo_indices = {nodo: i for i, nodo in enumerate(nodos)}
        
        source = []
        target = []
        value = []
        
        # 2. CONSTRUCCIÓN DE LOS ENLACES (LINKS)
        for index, row in df_flujo.iterrows():
            fuente_idx = nodo_indices[row['tipo_recurso']]
            
            # Camino A: El dinero que SÍ llegó a ejecutarse
            if pd.notna(row['entidad_ejecutora']) and row['monto_real_invertido'] > 0:
                ejecutor_idx = nodo_indices[row['entidad_ejecutora']]
                source.append(fuente_idx)
                target.append(ejecutor_idx)
                value.append(row['monto_real_invertido'])
                
            # Camino B: La pérdida o brecha
            if row['brecha_perdida'] > 0:
                brecha_idx = nodo_indices[nodo_brecha]
                source.append(fuente_idx)
                target.append(brecha_idx)
                value.append(row['brecha_perdida'])

        # 3. COLORES DINÁMICOS
        # Asignamos rojo a la brecha, verde a los ejecutores y azul a las fuentes
        colores_nodos = []
        for nodo in nodos:
            if nodo == nodo_brecha:
                colores_nodos.append("rgba(231, 76, 60, 0.8)") # Rojo
            elif nodo in ejecutores:
                colores_nodos.append("rgba(46, 204, 113, 0.8)") # Verde
            else:
                colores_nodos.append("rgba(52, 152, 219, 0.8)") # Azul

        # 4. RENDERIZADO DEL GRÁFICO PLOTLY SANKEY
        fig_sankey = go.Figure(data=[go.Sankey(
            valueformat = ",.0f",
            valuesuffix = " COP",
            node = dict(
              pad = 20,
              thickness = 25,
              line = dict(color = "black", width = 0.5),
              label = nodos,
              color = colores_nodos
            ),
            link = dict(
              source = source,
              target = target,
              value = value,
              color = "rgba(189, 195, 199, 0.4)" 
          ),
          textfont=dict(color="black", size=14, family="Arial") # FUENTE FORZADA: Tamaño más grande y color sólido
        )])
          
        fig_sankey.update_layout(
            title_text="Diagrama de Flujo del Ecosistema Financiero Ambiental", 
            font_size=14, # Tamaño base de la fuente aumentado
            height=600,   # Aumentamos un poco la altura para darle más "aire" a los nodos
            margin=dict(t=40, b=20, l=20, r=20),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig_sankey, use_container_width=True)
        
        with st.expander("📊 Ver matriz de datos del flujo"):
            df_mostrar = df_flujo[['tipo_recurso', 'entidad_recaudadora', 'monto_recaudado', 'entidad_ejecutora', 'monto_real_invertido', 'brecha_perdida']]
            st.dataframe(df_mostrar.style.format({
                "monto_recaudado": "${:,.0f}", 
                "monto_real_invertido": "${:,.0f}", 
                "brecha_perdida": "${:,.0f}"
            }), use_container_width=True)
            
    with st.expander("📖 Metodología de Análisis: La Brecha de Ejecución"):
        st.markdown("""
        * **Método de Visualización:** Diagrama de flujo de Sankey para mapear asimetrías de transferencia.
        * **Definición de Brecha:** Se calcula como la diferencia matemática entre el recaudo bruto (obligatorio o voluntario) y el volumen de capital efectivamente convertido en infraestructura verde u obras estructurales en campo.
        * **Causas Frecuentes:** Costos de transacción administrativos, fragmentación institucional, y tiempos de contratación prolongados que diluyen el valor del recurso en el tiempo.
        """)
    
# --- MÓDULO 3: VISOR GEOESPACIAL DE IMPACTO ---
elif modulo_seleccionado == "🗺️ 3. Visor Geoespacial de Impacto":
    st.title("Impacto Territorial y Escala Espacial")
    st.write("Mapeo topográfico de intervenciones, infraestructura hídrica regional y áreas de conservación.")
    
    # 1. Crear Layout: Mapa a la izquierda (70%), Panel a la derecha (30%)
    col_mapa, col_info = st.columns([7, 3])
    
    with col_mapa:
        # Centrado estratégico hacia el norte del Valle de Aburrá
        m = folium.Map(location=[6.4500, -75.5500], zoom_start=9, tiles='OpenTopoMap')
        
        # --- CAPA 1: Áreas Intervenidas (CuencaVerde) ---
        ruta_intervenciones = 'data/AreasintervenidasCV.geojson'
        try:
            folium.GeoJson(
                ruta_intervenciones,
                name="Áreas Intervenidas (CV)",
                style_function=lambda x: {
                    'fillColor': '#2ecc71', # Verde esmeralda
                    'color': '#27ae60',
                    'weight': 1.5,
                    'fillOpacity': 0.6,
                }
            ).add_to(m)
        except Exception as e:
            st.warning(f"⚠️ Error cargando Áreas Intervenidas: {e}")

        # --- CAPA 2: Áreas Protegidas SIDAP ---
        ruta_sidap = 'data/AreasProtegidas_SIDAP.geojson'
        try:
            folium.GeoJson(
                ruta_sidap,
                name="Áreas Protegidas (SIDAP)",
                style_function=lambda x: {
                    'fillColor': '#3498db', # Azul claro
                    'color': '#2980b9',
                    'weight': 1.5,
                    'fillOpacity': 0.4,
                }
            ).add_to(m)
        except Exception as e:
            st.warning(f"⚠️ Error cargando SIDAP: {e}")

        # Control para apagar/prender capas
        folium.LayerControl().add_to(m)
        
        # Renderizar mapa (use_container_width expande el mapa al máximo de su columna)
        st_folium(m, width=1000, height=650, use_container_width=True, returned_objects=[])

    with col_info:
        # 2. PANEL DE INFORMACIÓN DERECHO
        st.markdown("### Contexto Territorial")
        st.info("💡 **Dato Estratégico:** Las áreas de intervención buscan asegurar la oferta hídrica en las cuencas abastecedoras, conectando los esfuerzos de restauración focalizada con la red del SIDAP.")
        
        # Métricas de ejemplo (Se conectarán a los polígonos más adelante)
        st.metric(label="Hectáreas bajo Conservación", value="Por calcular...")
        st.metric(label="Inversión Focalizada", value="Por calcular...")
        
        st.markdown("---")
        st.markdown("**Convenciones Cartográficas:**")
        st.markdown("🟢 **Áreas Intervenidas (CV):** Polígonos de gestión, restauración y protección hídrica activa.")
        st.markdown("🔵 **Áreas Protegidas (SIDAP):** Zonas de reserva oficial y figuras de protección institucional.")
        
    with st.expander("📖 Topografía y Rigor Cartográfico"):
        st.markdown("""
        * **Georreferenciación:** Sistema de Coordenadas WGS84 con renderizado topográfico libre.
        * **Validación Espacial:** La superposición de capas permite identificar si la movilización de capital está ocurriendo dentro o fuera de las zonas núcleo de protección institucional.
        """)

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

    with st.expander("📖 Algoritmo de Optimización: El Fondo Común"):
        st.markdown("""
        * **Hipótesis del Modelo:** La concentración del capital disperso en un *Fondo Único Estratégico* reduce los costos de fricción y permite una planificación focalizada basada en el estrés hídrico de las cuencas.
        * **Fórmula de Eficiencia:** $Eficiencia = (Ejecucion_{Base} / Recaudo) + (\% Fondo * \alpha_{Centralizacion})$. El coeficiente $\alpha$ representa el ahorro en economía de escala.
        * **Referentes:** Esquemas de fondos de agua latinoamericanos y lineamientos de Soluciones Basadas en la Naturaleza (SbN) de la UICN.
        """)

# --- MÓDULO 5: POTENCIAL DEL 1% (INGRESOS CORRIENTES - TERRIDATA) ---
elif modulo_seleccionado == "💰 5. Potencial del 1% (Art. 111)":
    st.title("El Gigante Dormido: 1% de Ingresos Corrientes")
    st.write("""
    Según el Artículo 111 de la Ley 99 de 1993, los departamentos y municipios deben dedicar **mínimo el 1% de sus ingresos corrientes** 
    a la adquisición y mantenimiento de áreas de importancia estratégica para la conservación de recursos hídricos.
    """)
    
    # Filtramos la tabla ya recortada en tiempo (df_ic) según la región seleccionada
    if region == "Toda Colombia":
        # TerriData tiene a 'Colombia' como un departamento agrupado
        df_filtro_espacial = df_ic[df_ic['Departamento'] == 'Colombia']
        titulo_grafico = "Evolución Nacional de Ingresos y Obligación Ambiental (COP)"
    else:
        # Seleccionamos Antioquia, excluyendo el agregado departamental para ver solo municipios
        df_filtro_espacial = df_ic[(df_ic['Departamento'] == 'Antioquia') & (df_ic['Municipio'] != 'Antioquia')]
        
        # Si el usuario eligió un municipio específico en la barra lateral, filtramos más
        if municipio_seleccionado != "Todos":
            df_filtro_espacial = df_filtro_espacial[df_filtro_espacial['Municipio'] == municipio_seleccionado]
            
        titulo_grafico = f"Distribución Municipal de Ingresos y Obligación Ambiental (COP) - {region}"

    # AGRUPACIÓN: Sumar los años seleccionados (anio_inicio a anio_fin) y ordenar de mayor a menor
    df_agrupado = df_filtro_espacial.groupby('Municipio')[['Ingresos_Corrientes', 'Minimo_1_Porciento']].sum().reset_index()
    df_agrupado = df_agrupado.sort_values(by='Ingresos_Corrientes', ascending=False)
    
    # KPI Resumen
    total_recaudo_potencial = df_agrupado['Minimo_1_Porciento'].sum()
    st.metric(
        label=f"Potencial Total de Inversión ({anio_inicio}-{anio_fin}) - {region}", 
        value=f"${total_recaudo_potencial:,.0f} COP"
    )
    
    # Gráfica Plotly
    fig_ic = go.Figure()
    
    fig_ic.add_trace(go.Bar(
        x=df_agrupado['Municipio'], 
        y=df_agrupado['Ingresos_Corrientes'],
        name='Ingresos Corrientes Totales',
        marker_color='#bdc3c7'
    ))
    
    fig_ic.add_trace(go.Bar(
        x=df_agrupado['Municipio'], 
        y=df_agrupado['Minimo_1_Porciento'],
        name='1% Mandatorio (Conservación)',
        marker_color='#3498db'
    ))
    
    fig_ic.update_layout(
        title=titulo_grafico,
        barmode='overlay',
        yaxis_type="log", # Fundamental para ver a Medellín y a un municipio de sexta categoría en la misma gráfica sin que la barra menor desaparezca visualmente
        height=600,
        xaxis_tickangle=-45 # Inclinamos el texto para leer los 125 municipios
    )
    
    st.plotly_chart(fig_ic, use_container_width=True)
    
    st.markdown("### Datos Detallados")
    st.dataframe(df_agrupado.style.format({"Ingresos_Corrientes": "${:,.0f}", "Minimo_1_Porciento": "${:,.0f}"}), use_container_width=True)
    
    # Botón de Descarga CSV
    csv_ic = df_agrupado.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Matriz Oficial (CSV)",
        data=csv_ic,
        file_name=f"Ingresos_Corrientes_TerriData_{region}_{anio_inicio}_{anio_fin}.csv",
        mime="text/csv",
    )
