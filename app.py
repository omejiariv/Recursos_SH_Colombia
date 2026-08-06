import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import numpy as np

# -----------------------------------------------------------------------------
# 0. Carga y Procesamiento Predictivo (ETL Híbrido: Finanzas + Ambiente)
# -----------------------------------------------------------------------------
@st.cache_data
def cargar_datos():
    # Catálogo Normativo Actualizado
    df_normatividad = pd.DataFrame({
        'Instrumento': ['Art. 111 (Ley 99/93) - 1% ICLD', 'Inversión - Ambiental (DNP)', 'Adquisición Predios/PSA (DNP)'],
        'Tipo': ['Ley (Mandatorio)', 'Ejecución Histórica/Proyectada', 'Medición Específica Art. 111']
    })

    # Funciones de limpieza de moneda
    def limpiar_moneda_millones(valor):
        if pd.isna(valor): return 0
        if isinstance(valor, str): valor = valor.replace('.', '').replace(',', '.')
        return float(valor) * 1_000_000

    def limpiar_moneda_pesos(valor):
        if pd.isna(valor): return 0
        if isinstance(valor, str): valor = valor.replace('.', '').replace(',', '.')
        return float(valor)

    # Algoritmo de Interpolación y Proyección Lineal (2000 - 2030)
    def proyectar_serie(df_historico, anio_inicio, anio_fin):
        datos_proyectados = []
        municipios = df_historico['Entidad'].unique()
        rango_anios = list(range(anio_inicio, anio_fin + 1))
        
        for mpio in municipios:
            df_mpio = df_historico[df_historico['Entidad'] == mpio].sort_values('Año')
            depto = df_mpio['Departamento'].iloc[0] if not df_mpio.empty else 'Antioquia'
            
            x_hist = df_mpio['Año'].values
            y_hist = df_mpio['Valor_COP'].values
            
            if len(x_hist) > 1:
                coeficientes = np.polyfit(x_hist, y_hist, 1)
                modelo = np.poly1d(coeficientes)
            else:
                modelo = lambda x: 0
                
            for anio in rango_anios:
                if anio in x_hist:
                    valor = y_hist[np.where(x_hist == anio)[0][0]]
                else:
                    valor = modelo(anio)
                valor = max(0, valor) # Evitar valores negativos en finanzas
                
                datos_proyectados.append({
                    'Departamento': depto, 'Municipio': mpio, 'Año': anio, 'Valor_COP': valor
                })
        return pd.DataFrame(datos_proyectados)

    try:
        # ---------------------------------------------------------
        # 1. INGESTA FINANCIERA (Dimensión 7)
        # ---------------------------------------------------------
        archivo_terridata_finanzas = 'data/TerriData_Dim7_Finanzas.xlsx'
        xls_fin = pd.ExcelFile(archivo_terridata_finanzas)
        
        # Ingresos Corrientes (Base de Cálculo)
        df_h1 = pd.read_excel(xls_fin, sheet_name='Hoja1')
        df_ic_raw = df_h1[df_h1['Indicador'] == 'Ingresos corrientes'].copy()
        df_ic_raw['Valor_COP'] = df_ic_raw['Dato Numérico'].apply(limpiar_moneda_millones)
        
        df_ic = proyectar_serie(df_ic_raw, 2000, 2030)
        df_ic = df_ic.rename(columns={'Valor_COP': 'Ingresos_Corrientes'})
        df_ic['Minimo_1_Porciento'] = df_ic['Ingresos_Corrientes'] * 0.01

        # Inversión Ambiental General
        df_h2 = pd.read_excel(xls_fin, sheet_name='Hoja2')
        df_inv_raw = df_h2[df_h2['Indicador'] == 'Inversión - Ambiental'].copy()
        df_inv_raw['Valor_COP'] = df_inv_raw['Dato Numérico'].apply(limpiar_moneda_pesos)
        
        df_inv = proyectar_serie(df_inv_raw, 2000, 2030)
        df_inv = df_inv.rename(columns={'Valor_COP': 'Inversion_Ambiental_Ejecutada'})

        # ---------------------------------------------------------
        # 2. INGESTA AMBIENTAL Y TERRITORIAL (Dimensión 11)
        # ---------------------------------------------------------
        archivo_terridata_amb = 'data/TerriData_Dim11_Amb_BDVSEc.xlsx'
        xls_amb = pd.ExcelFile(archivo_terridata_amb)
        df_amb = pd.read_excel(xls_amb, sheet_name='Hoja01')
        
        # Indicador A: Cumplimiento Específico Art 111 (% de Ingresos)
        ind_art111 = 'Porcentaje de ingresos corrientes destinados a adquisición de predios o PSA en cuencas abastecedoras de acueducto'
        df_art111_raw = df_amb[df_amb['Indicador'] == ind_art111].copy()
        df_art111_raw['Cumplimiento_Art111_Pct'] = pd.to_numeric(df_art111_raw['Dato Numérico'], errors='coerce').fillna(0)
        df_art111 = df_art111_raw[['Departamento', 'Entidad', 'Año', 'Cumplimiento_Art111_Pct']].rename(columns={'Entidad': 'Municipio'})
        
        # Indicador B: Área protegida SINAP (Hectáreas)
        ind_sinap = 'Área de la entidad territorial que hace parte del SINAP'
        df_sinap_raw = df_amb[df_amb['Indicador'] == ind_sinap].copy()
        df_sinap_raw['Area_SINAP_ha'] = pd.to_numeric(df_sinap_raw['Dato Numérico'], errors='coerce').fillna(0)
        df_sinap = df_sinap_raw[['Departamento', 'Entidad', 'Año', 'Area_SINAP_ha']].rename(columns={'Entidad': 'Municipio'})

        # ---------------------------------------------------------
        # 3. UNIFICACIÓN DEL CEREBRO DE DATOS (Master Merge)
        # ---------------------------------------------------------
        df_maestro = pd.merge(df_ic, df_inv, on=['Departamento', 'Municipio', 'Año'], how='left').fillna(0)
        df_maestro = pd.merge(df_maestro, df_art111, on=['Departamento', 'Municipio', 'Año'], how='left')
        df_maestro = pd.merge(df_maestro, df_sinap, on=['Departamento', 'Municipio', 'Año'], how='left')
        
        # Relleno Inteligente (Forward Fill) para indicadores estructurales
        df_maestro = df_maestro.sort_values(by=['Municipio', 'Año'])
        df_maestro['Cumplimiento_Art111_Pct'] = df_maestro.groupby('Municipio')['Cumplimiento_Art111_Pct'].ffill().fillna(0)
        df_maestro['Area_SINAP_ha'] = df_maestro.groupby('Municipio')['Area_SINAP_ha'].ffill().fillna(0)
        
        # 4. CÁLCULO FINANCIERO DEL IMPACTO REAL (DNP)
        # Convertimos el % histórico a pesos reales ejecutados en adquisición/PSA (La verdadera inversión de la Ley 99)
        df_maestro['Inversion_Art111_Real'] = df_maestro['Ingresos_Corrientes'] * (df_maestro['Cumplimiento_Art111_Pct'] / 100)

    except Exception as e:
        st.error(f"Error crítico en el ETL Predictivo/Ambiental: {e}")
        df_maestro = pd.DataFrame(columns=[
            'Departamento', 'Municipio', 'Año', 'Ingresos_Corrientes', 'Minimo_1_Porciento', 
            'Inversion_Ambiental_Ejecutada', 'Cumplimiento_Art111_Pct', 'Area_SINAP_ha', 'Inversion_Art111_Real'
        ])

    return df_normatividad, df_maestro

# Despliegue del nuevo dataframe maestro
df_normatividad, df_maestro_base = cargar_datos()

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
    # Logo Institucional
    try:
        st.image('data/CuencaVerdeLogo_V1.JPG', use_container_width=True)
    except:
        st.caption("Fondo de Agua CuencaVerde")
        
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
    
    region = st.selectbox("Región / Departamento", ["Toda Colombia", "Antioquia"], index=1)
    
    if region == "Antioquia":
        # CORRECCIÓN: Leemos del nuevo dataframe maestro
        municipios_reales = df_maestro_base[(df_maestro_base['Departamento'] == 'Antioquia') & (df_maestro_base['Municipio'] != 'Antioquia')]['Municipio'].unique().tolist()
        municipios_reales.sort()
        municipios_reales.insert(0, "Todos")
        municipio_seleccionado = st.selectbox("Municipio Específico", municipios_reales)
    else:
        municipio_seleccionado = "Todos"
        
    anio_fiscal = st.slider("Vigencia Fiscal (TerriData + Proyecciones)", 2000, 2030, (2020, 2026))

# -----------------------------------------------------------------------------
# Motor de Filtrado Dinámico (El Nuevo Cerebro Híbrido)
# -----------------------------------------------------------------------------
anio_inicio, anio_fin = anio_fiscal 

# 1. Filtro Temporal
df_temp = df_maestro_base[(df_maestro_base['Año'] >= anio_inicio) & (df_maestro_base['Año'] <= anio_fin)].copy()

# 2. Filtro Espacial
if region == "Toda Colombia":
    df_espacial = df_temp[df_temp['Departamento'] == 'Colombia']
    ruta_seleccion = "Toda Colombia"
    factor_escala = 1.0 # 100% de los recursos nacionales
else:
    df_espacial = df_temp[(df_temp['Departamento'] == 'Antioquia') & (df_temp['Municipio'] != 'Antioquia')]
    if municipio_seleccionado != "Todos":
        df_espacial = df_espacial[df_espacial['Municipio'] == municipio_seleccionado]
        ruta_seleccion = f"{municipio_seleccionado} - Antioquia"
    else:
        ruta_seleccion = "Antioquia"
    
    # Regla de tres matemática para calcular qué porcentaje del país representa el territorio seleccionado
    total_col_base = df_maestro_base[(df_maestro_base['Departamento'] == 'Colombia') & (df_maestro_base['Año'] == 2024)]['Minimo_1_Porciento'].sum()
    total_sel_base = df_espacial[df_espacial['Año'] == 2024]['Minimo_1_Porciento'].sum()
    factor_escala = total_sel_base / total_col_base if total_col_base > 0 else 0.05

# 3. Construcción del Flujo (Reintegrando el ecosistema completo)
recaudo_1_pct = df_espacial['Minimo_1_Porciento'].sum()
inversion_oficial = df_espacial['Inversion_Ambiental_Ejecutada'].sum()

# Bases escaladas de otras fuentes (Esperando Excel definitivo)
recaudo_electrico = 850000000000 * factor_escala
recaudo_voluntario = 150000000000 * factor_escala

# Topamos la ejecución oficial al 1% para poder calcular una brecha realista en ese rubro
ejecucion_1_pct = min(recaudo_1_pct, inversion_oficial) 
brecha_1_pct = recaudo_1_pct - ejecucion_1_pct

ejecucion_electrico = recaudo_electrico * 0.45 # Eficiencia simulada del 45%
brecha_electrico = recaudo_electrico - ejecucion_electrico

ejecucion_voluntario = recaudo_voluntario * 0.90 # Eficiencia simulada del 90%
brecha_voluntario = recaudo_voluntario - ejecucion_voluntario

# ESTA TABLA SOLUCIONA EL ERROR DEL SIMULADOR (Módulo 4)
df_flujo = pd.DataFrame({
    'tipo_recurso': ['Ley 99 (1% ICLD)', 'Ley (Transferencias)', 'Voluntario (Fondo)'],
    'monto_recaudado': [recaudo_1_pct, recaudo_electrico, recaudo_voluntario],
    'entidad_ejecutora': ['Inversión Ambiental Oficial', 'Operador Hídrico', 'ONG Territorial'],
    'monto_real_invertido': [ejecucion_1_pct, ejecucion_electrico, ejecucion_voluntario],
    'brecha_perdida': [brecha_1_pct, brecha_electrico, brecha_voluntario]
})

total_recaudado = df_flujo['monto_recaudado'].sum()
total_ejecutado = df_flujo['monto_real_invertido'].sum()
brecha_total = df_flujo['brecha_perdida'].sum()
eficiencia = (total_ejecutado / total_recaudado) * 100 if total_recaudado > 0 else 0

# -----------------------------------------------------------------------------
# 3. Módulos

# --- MÓDULO 1: EL PANORAMA NACIONAL VS. REGIONAL ---
if modulo_seleccionado == "📊 1. El Panorama Nacional vs. Regional":
    st.title("Panorama de Recursos Ambientales e Hídricos")
    st.info(f"📍 **Área de análisis actual:** `{ruta_seleccion}` | 📅 **Vigencia Fiscal:** `{anio_inicio} - {anio_fin}`")
    
    st.markdown("### Resumen Macro")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Capital Movilizado", f"${total_recaudado:,.0f}")
    col2.metric("Inversión Real Ejecutada", f"${total_ejecutado:,.0f}", delta=f"-${brecha_total:,.0f} (Brecha/Fricción)", delta_color="inverse")
    col3.metric("Eficiencia del Sistema", f"{eficiencia:.1f}%")
    
    st.markdown("---")
    st.markdown("### Composición de la Inversión Territorial")
    
    col_izq, col_der = st.columns([1, 1])
    with col_izq:
        recursos_ley = df_flujo[df_flujo['tipo_recurso'].str.contains("Ley")]['monto_recaudado'].sum()
        recursos_vol = df_flujo[df_flujo['tipo_recurso'].str.contains("Voluntario")]['monto_recaudado'].sum()
        st.metric("🏛️ Recursos de Ley (Mandatorios)", f"${recursos_ley:,.0f}")
        st.metric("🤝 Recursos Voluntarios (Privados/Fondos)", f"${recursos_vol:,.0f}")
        
        with st.expander("📖 Soporte Jurídico y Clasificación de Recursos"):
            st.dataframe(df_normatividad, use_container_width=True)
            
    with col_der:
        import plotly.graph_objects as go
        fig_dona = go.Figure(data=[go.Pie(
            labels=df_flujo['tipo_recurso'], 
            values=df_flujo['monto_recaudado'],
            hole=.5,
            marker_colors=['#3498db', '#2ecc71', '#f1c40f']
        )])
        fig_dona.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
        st.plotly_chart(fig_dona, use_container_width=True)
        
    st.caption("🔍 **Fuente:** 1% ICLD e Inversión Oficial basados 100% en DNP (TerriData). Otras fuentes utilizan estimaciones estructurales escaladas temporalmente al territorio.")

# --- MÓDULO 2: EL EMBUDO DE LA VERDAD (FLUJO) ---
elif modulo_seleccionado == "📉 2. El Embudo de la Verdad (Flujo)":
    st.title("El Embudo de la Verdad")
    st.info(f"📍 **Área de análisis:** `{ruta_seleccion}` | 📅 **Vigencia Fiscal:** `{anio_inicio} - {anio_fin}`")

    if df_flujo['monto_recaudado'].sum() == 0:
        st.warning("No hay recursos para esta selección.")
    else:
        import plotly.graph_objects as go
        
        fuentes = df_flujo['tipo_recurso'].tolist()
        ejecutores = df_flujo['entidad_ejecutora'].tolist()
        nodo_brecha = "Brecha / Retención (Sin Ejecutar)"
        
        nodos = fuentes + ejecutores + [nodo_brecha]
        nodo_indices = {nodo: i for i, nodo in enumerate(nodos)}
        
        source, target, value = [], [], []
        
        for index, row in df_flujo.iterrows():
            fuente_idx = nodo_indices[row['tipo_recurso']]
            
            if row['monto_real_invertido'] > 0:
                ejecutor_idx = nodo_indices[row['entidad_ejecutora']]
                source.append(fuente_idx)
                target.append(ejecutor_idx)
                value.append(row['monto_real_invertido'])
                
            if row['brecha_perdida'] > 0:
                brecha_idx = nodo_indices[nodo_brecha]
                source.append(fuente_idx)
                target.append(brecha_idx)
                value.append(row['brecha_perdida'])

        colores_nodos = ["rgba(231, 76, 60, 0.8)" if n == nodo_brecha else "rgba(46, 204, 113, 0.8)" if n in ejecutores else "rgba(52, 152, 219, 0.8)" for n in nodos]

        fig_sankey = go.Figure(data=[go.Sankey(
            valueformat = ",.0f", valuesuffix = " COP",
            node = dict(pad=20, thickness=25, line=dict(color="black", width=0.5), label=nodos, color=colores_nodos),
            link = dict(source=source, target=target, value=value, color="rgba(189, 195, 199, 0.4)"),
            textfont=dict(color="black", size=14, family="Arial")
        )])
        fig_sankey.update_layout(height=500, margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_sankey, use_container_width=True)
    
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

# --- MÓDULO 5: POTENCIAL DEL 1% ---
elif modulo_seleccionado == "💰 5. Potencial del 1% (Art. 111)":
    st.title("El Gigante Dormido: 1% vs Inversión Histórica")
    
    if region == "Toda Colombia":
        st.warning("Seleccione Antioquia para ver el desglose comparativo municipal.")
    else:
        import plotly.graph_objects as go
        df_agrupado = df_espacial.groupby('Municipio')[['Ingresos_Corrientes', 'Minimo_1_Porciento', 'Inversion_Ambiental_Ejecutada']].sum().reset_index()
        df_agrupado = df_agrupado.sort_values(by='Ingresos_Corrientes', ascending=False)
        
        # --- EL NUEVO BOTÓN SELECTOR DE ESCALA ---
        st.markdown("### Configuración Visual")
        escala_seleccionada = st.radio(
            "Tipo de Escala en el Gráfico:", 
            ["Logarítmica (Permite visibilizar municipios pequeños)", "Lineal (Muestra la proporción económica real)"], 
            horizontal=True
        )
        tipo_escala = "log" if "Logarítmica" in escala_seleccionada else "linear"
        
        fig_ic = go.Figure()
        fig_ic.add_trace(go.Bar(x=df_agrupado['Municipio'], y=df_agrupado['Minimo_1_Porciento'], name='Potencial 1% (Mandatorio)', marker_color='#3498db'))
        fig_ic.add_trace(go.Bar(x=df_agrupado['Municipio'], y=df_agrupado['Inversion_Ambiental_Ejecutada'], name='Inversión Ejecutada Oficial', marker_color='#2ecc71'))
        
        # Le pasamos la variable tipo_escala al layout
        fig_ic.update_layout(title=f"Brecha Municipal en {ruta_seleccion}", barmode='group', yaxis_type=tipo_escala, height=600, xaxis_tickangle=-45)
        st.plotly_chart(fig_ic, use_container_width=True)
        
        st.dataframe(df_agrupado.style.format({"Ingresos_Corrientes": "${:,.0f}", "Minimo_1_Porciento": "${:,.0f}", "Inversion_Ambiental_Ejecutada": "${:,.0f}"}), use_container_width=True)
        
        # EL ARREGLO: El CSV ahora solo se genera si estamos viendo Antioquia (donde df_agrupado existe)
        csv_ic = df_agrupado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Matriz Oficial (CSV)",
            data=csv_ic,
            file_name=f"Ingresos_vs_Inversion_TerriData_{region}.csv",
            mime="text/csv",
        )
        
