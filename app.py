import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import random

# -----------------------------------------------------------------------------
# 0. Carga y Procesamiento de Datos Base
# -----------------------------------------------------------------------------
import random

@st.cache_data
def cargar_datos():
    # 1. Catálogo Normativo
    df_normatividad = pd.DataFrame({
        'Instrumento': ['Art. 111 (Ley 99/93) - 1% ICLD', 'Transferencias Sector Eléctrico', 'Tasa por Uso', 'Tasa Retributiva', 'Inversión Forzosa 1%', 'PSA', 'Recursos ESG'],
        'Tipo': ['Ley', 'Ley', 'Ley', 'Ley', 'Ley', 'Mixto', 'Voluntario']
    })

    # 2. Orígenes y 3. Ejecución (Con columna de vigencia agregada)
    df_origenes = pd.DataFrame({
        'id_fuente': ['F001', 'F002', 'F003', 'F004', 'F005'],
        'tipo_recurso': ['Ley (Inversión 1%)', 'Ley (Transferencias)', 'Voluntario (Fondo)', 'Voluntario (ESG)', 'Ley (SGP)'],
        'entidad_recaudadora': ['Municipios/Gobernaciones', 'Sector Eléctrico', 'Fondo de Agua', 'Empresa Privada', 'Sistema General'],
        'monto_recaudado': [1340000000000, 850000000000, 150000000000, 50000000000, 600000000000] 
    })
    
    df_ejecucion = pd.DataFrame({
        'id_proyecto': ['P001', 'P002', 'P003', 'P004', 'P005'],
        'id_fuente': ['F001', 'F002', 'F003', 'F004', 'F005'],
        'monto_real_invertido': [30000000000, 90000000000, 32000000000, 10000000000, 40000000000],
        'entidad_ejecutora': ['ONG Territorial', 'Operador Hídrico', 'Corporación Cuenca', 'Junta de Acción Local', 'Municipio'],
        'lat': [6.1158, 6.2917, 6.3500, 6.0500, 8.5000],
        'lon': [-75.4983, -75.5011, -75.5500, -75.6000, -76.0000],
        'region': ['Valle de Aburrá', 'Valle de Aburrá', 'Antioquia', 'Valle de Aburrá', 'Toda Colombia'],
        'vigencia': [2024, 2025, 2024, 2026, 2025] # Nueva columna para el filtro de años
    })
    
    df_impacto = pd.DataFrame({
        'id_proyecto': ['P001', 'P002', 'P003', 'P004', 'P005'],
        'ha_restauradas': [120, 350, 80, 45, 200]
    })
    
    # 4. Datos de Ingresos Corrientes a Nivel Municipal
    anios = list(range(2020, 2027))
    
    # Simulamos una lista representativa de municipios de Antioquia (descendente)
    municipios_ant = ['Medellín', 'Bello', 'Itagüí', 'Envigado', 'Rionegro', 'Apartadó', 'Turbo', 'Caucasia', 'Guarne', 'El Retiro', 'Marinilla', 'La Ceja', 'Santa Fe de Antioquia', 'Murindó', 'Vigía del Fuerte']
    
    datos_ic = []
    
    # Generador para Antioquia
    presupuesto_base = 6000000000000 # Arrancamos con 6 Billones para Medellín
    for mpio in municipios_ant:
        for a in anios:
            crecimiento = random.uniform(1.02, 1.07)
            presupuesto_base = presupuesto_base * crecimiento
            datos_ic.append({
                'Departamento': 'Antioquia', 
                'Municipio': mpio,
                'Año': a, 
                'Ingresos_Corrientes': presupuesto_base, 
                'Minimo_1_Porciento': presupuesto_base * 0.01
            })
        # Reducimos drásticamente el presupuesto base para el siguiente municipio (curva descendente)
        presupuesto_base = presupuesto_base * 0.45 
        
    df_ingresos_corrientes = pd.DataFrame(datos_ic)
    
    return df_normatividad, df_origenes, df_ejecucion, df_impacto, df_ingresos_corrientes

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
    st.image("https://via.placeholder.com/300x100.png?text=Logo+Proyecto", use_container_width=True)
    st.title("Navegación")
    
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
    
    region = st.selectbox("Región / Departamento", ["Toda Colombia", "Antioquia", "Cundinamarca", "Valle de Aburrá"], index=1)
    
    # Lógica condicional para el selector de municipios
    municipio_seleccionado = "Todos"
    if region == "Antioquia":
        municipio_seleccionado = st.selectbox("Municipio Específico", ["Todos", "Medellín", "Guarne", "Rionegro", "El Retiro"])
    elif region == "Cundinamarca":
        municipio_seleccionado = st.selectbox("Municipio Específico", ["Todos", "Bogotá", "Chía", "Cajicá"])
        
    anio_fiscal = st.slider("Vigencia Fiscal", 2020, 2026, (2024, 2026))

# -----------------------------------------------------------------------------
# Motor de Filtrado Dinámico (Pandas Pipeline)
# -----------------------------------------------------------------------------
anio_inicio, anio_fin = anio_fiscal # Desempacamos el slider de la barra lateral

# 1. Lógica de anidamiento territorial
if region == "Valle de Aburrá":
    filtro_regiones = ['Valle de Aburrá']
elif region == "Antioquia":
    filtro_regiones = ['Valle de Aburrá', 'Antioquia']
elif region == "Cundinamarca":
    filtro_regiones = ['Cundinamarca']
else:
    filtro_regiones = df_ejecucion_base['region'].unique() # Toda Colombia

# 2. Aplicar el filtro ESPACIAL y TEMPORAL a la tabla de ejecución
df_ejecucion = df_ejecucion_base[
    (df_ejecucion_base['region'].isin(filtro_regiones)) & 
    (df_ejecucion_base['vigencia'] >= anio_inicio) & 
    (df_ejecucion_base['vigencia'] <= anio_fin)
]

# 3. Filtrar tabla de impactos
df_impacto = df_impacto_base[df_impacto_base['id_proyecto'].isin(df_ejecucion['id_proyecto'])]

# 4. Filtrar tabla de Ingresos Corrientes (Módulo 5) por AÑO
df_ic = df_ic_base[
    (df_ic_base['Año'] >= anio_inicio) & 
    (df_ic_base['Año'] <= anio_fin)
]

# 5. Recalcular el flujo financiero principal
df_flujo = pd.merge(df_origenes, df_ejecucion, on='id_fuente', how='inner')
df_flujo['brecha_perdida'] = df_flujo['monto_recaudado'] - df_flujo['monto_real_invertido']

# -----------------------------------------------------------------------------
# 3. Módulos

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
    col3.metric(
        label="Eficiencia del Sistema", 
        value=f"{eficiencia:.1f}%",
        help="Método de cálculo: (Inversión Real Ejecutada / Total Recaudado) * 100. Este indicador representa el porcentaje del capital que efectivamente se convierte en soluciones territoriales y obras en campo, tras descontar retenciones presupuestales, gastos burocráticos y tiempos muertos de contratación."
    )
    
    st.markdown("---")
    
    col4, col5 = st.columns(2)
    col4.metric(label="Recursos de Ley", value=f"${recursos_ley:,.0f}")
    col5.metric(label="Recursos Voluntarios (Privados/Fondos)", value=f"${recursos_voluntarios:,.0f}")

    with st.expander("📖 Soporte Jurídico y Clasificación de Recursos"):
        st.markdown("### Catálogo Normativo para la Protección del Agua")
        st.write("Esta tabla consolida los fundamentos legales y los mecanismos voluntarios que estructuran la movilización de capital ambiental en Colombia.")
        st.dataframe(df_normatividad, use_container_width=True)
        st.caption("Fuentes: Ley 99 de 1993, Decretos Reglamentarios (MinAmbiente), y reportes de sostenibilidad corporativa (ESG).")

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

    with st.expander("📖 Metodología de Análisis: La Brecha de Ejecución"):
        st.markdown("""
        * **Método de Visualización:** Diagrama de flujo de Sankey para mapear asimetrías de transferencia.
        * **Definición de Brecha:** Se calcula como la diferencia matemática entre el recaudo bruto (obligatorio o voluntario) y el volumen de capital efectivamente convertido en infraestructura verde u obras estructurales en campo.
        * **Causas Frecuentes:** Costos de transacción administrativos, fragmentación institucional, y tiempos de contratación prolongados que diluyen el valor del recurso en el tiempo.
        """)
    
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

    with st.expander("📖 Topografía y Rigor Cartográfico"):
        st.markdown("""
        * **Georreferenciación:** Sistema de Coordenadas WGS84 con renderizado topográfico libre.
        * **Precisión Altimétrica:** Las cotas de infraestructura crítica han sido configuradas estrictamente; por ejemplo, la ubicación del relleno sanitario respeta con exactitud su elevación geográfica real. 
        * **Proporcionalidad:** El dimensionamiento de los radios de influencia para los embalses principales (La Fe y Piedras Blancas) ha sido corregido espacialmente para reflejar su escala y proximidad frente a los núcleos urbanos.
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

# --- MÓDULO 5: POTENCIAL DEL 1% (INGRESOS CORRIENTES) ---
elif modulo_seleccionado == "💰 5. Potencial del 1% (Art. 111)":
    st.title("El Gigante Dormido: 1% de Ingresos Corrientes")
    st.write("""
    Según el Artículo 111 de la Ley 99 de 1993, los departamentos y municipios deben dedicar **mínimo el 1% de sus ingresos corrientes** 
    a la adquisición y mantenimiento de áreas de importancia estratégica para la conservación de recursos hídricos.
    """)
    
    # Selector de departamento 
    depto_seleccionado = st.selectbox("Seleccione el Departamento para el análisis del 1%:", df_ic['Departamento'].unique())
    
    # Filtrar por departamento seleccionado
    df_filtro_depto = df_ic[df_ic['Departamento'] == depto_seleccionado]
    
    # AGRUPACIÓN MUNICIPAL: Sumar los años seleccionados y ordenar de mayor a menor
    df_mpios = df_filtro_depto.groupby('Municipio')[['Ingresos_Corrientes', 'Minimo_1_Porciento']].sum().reset_index()
    df_mpios = df_mpios.sort_values(by='Ingresos_Corrientes', ascending=False)
    
    # KPI Resumen
    total_recaudo_potencial = df_mpios['Minimo_1_Porciento'].sum()
    st.metric(
        label=f"Potencial Total de Inversión ({anio_inicio}-{anio_fin}) - {depto_seleccionado}", 
        value=f"${total_recaudo_potencial:,.0f} COP"
    )
    
    # Gráfica Plotly: Eje X = Municipios (Ordenados), Eje Y = Dinero
    fig_ic = go.Figure()
    
    fig_ic.add_trace(go.Bar(
        x=df_mpios['Municipio'], 
        y=df_mpios['Ingresos_Corrientes'],
        name='Ingresos Corrientes Totales',
        marker_color='#bdc3c7'
    ))
    
    fig_ic.add_trace(go.Bar(
        x=df_mpios['Municipio'], 
        y=df_mpios['Minimo_1_Porciento'],
        name='1% Mandatorio (Conservación)',
        marker_color='#3498db'
    ))
    
    fig_ic.update_layout(
        title=f"Distribución Municipal de Ingresos y Obligación Ambiental (COP) - {depto_seleccionado}",
        barmode='overlay',
        yaxis_type="log", # Escala logarítmica esencial para poder ver a Medellín y Murindó en la misma gráfica
        height=600,
        xaxis_tickangle=-45 # Inclinamos los nombres de los municipios para que se lean bien
    )
    
    st.plotly_chart(fig_ic, use_container_width=True)
    
    st.markdown("### Datos Detallados por Municipio")
    st.dataframe(df_mpios.style.format({"Ingresos_Corrientes": "${:,.0f}", "Minimo_1_Porciento": "${:,.0f}"}), use_container_width=True)
    
    # Botón de Descarga CSV
    csv_ic = df_mpios.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Matriz Municipal (CSV)",
        data=csv_ic,
        file_name=f"Ingresos_Corrientes_{depto_seleccionado}_{anio_inicio}_{anio_fin}.csv",
        mime="text/csv",
    )
