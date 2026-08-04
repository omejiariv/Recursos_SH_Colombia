# generar_datos.py

import pandas as pd
import numpy as np

# 1. Tabla de Orígenes de Recursos (Recaudo Teórico)
origenes_data = {
    'id_fuente': ['F001', 'F002', 'F003', 'F004', 'F005'],
    'tipo_recurso': ['Ley (Inversión 1%)', 'Ley (Transferencias)', 'Voluntario (Fondo)', 'Voluntario (ESG)', 'Ley (SGP)'],
    'entidad_recaudadora': ['Autoridad Ambiental Local', 'Sector Eléctrico', 'Fondo de Agua', 'Empresa Privada', 'Sistema General'],
    'monto_recaudado': [50000000000, 120000000000, 35000000000, 15000000000, 80000000000], # Valores en COP
    'vigencia': [2024, 2024, 2024, 2024, 2024]
}
df_origenes = pd.DataFrame(origenes_data)
df_origenes.to_csv('origenes_recursos.csv', index=False)

# 2. Tabla de Ejecución de Proyectos (Inversión Real en Campo)
ejecucion_data = {
    'id_proyecto': ['P001', 'P002', 'P003', 'P004', 'P005'],
    'id_fuente': ['F001', 'F002', 'F003', 'F004', 'F005'],
    'monto_real_invertido': [30000000000, 90000000000, 32000000000, 10000000000, 40000000000], # Refleja la brecha de ejecución
    'entidad_ejecutora': ['ONG Territorial', 'Operador Hídrico', 'Corporación Cuenca', 'Junta de Acción Local', 'Municipio'],
    'ubicacion_estrategica': ['Embalse La Fe', 'Embalse Piedras Blancas', 'Corredor Ribereño Norte', 'Zona Recarga Sur', 'Microcuenca Alta'],
    'lat': [6.1158, 6.2917, 6.3500, 6.0500, 6.4000], # Coordenadas base en Antioquia/Valle de Aburrá
    'lon': [-75.4983, -75.5011, -75.5500, -75.6000, -75.4500],
    'cuenca': ['Río Pantanillo', 'Río Piedras', 'Río Porce', 'Río Aburrá', 'Río Grande']
}
df_ejecucion = pd.DataFrame(ejecucion_data)
df_ejecucion.to_csv('ejecucion_proyectos.csv', index=False)

# 3. Tabla de Impacto y Efectividad (Métricas Territoriales)
impacto_data = {
    'id_proyecto': ['P001', 'P002', 'P003', 'P004', 'P005'],
    'ha_restauradas': [120, 350, 80, 45, 200],
    'aislamientos_km': [15.5, 40.0, 10.2, 5.0, 25.4],
    'familias_psa': [45, 120, 30, 15, 80],
    'roi_ambiental': [1.2, 2.5, 1.8, 1.1, 2.0] # Índice sintético de costo-beneficio ecológico
}
df_impacto = pd.DataFrame(impacto_data)
df_impacto.to_csv('impacto_efectividad.csv', index=False)

print("¡Datos base generados con éxito! Archivos listos: origenes_recursos.csv, ejecucion_proyectos.csv, impacto_efectividad.csv")
