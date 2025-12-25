"""Diagnóstico de cálculo de costos"""
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
COSTO_KWH_CLP = 120

# Leer solo el archivo más reciente
archivos = list(DATA_DIR.glob("operacion_*.csv"))
print(f"Archivos encontrados: {len(archivos)}")
archivos_ordenados = sorted(archivos, key=lambda x: x.stem, reverse=True)
archivo = archivos_ordenados[0]
print(f"Usando archivo: {archivo.name}")

# Combinar
df = pd.read_csv(archivo)
df['timestamp'] = pd.to_datetime(df['timestamp'])
print(f"\nRegistros totales: {len(df)}")

# Analizar por fecha
df['fecha'] = df['timestamp'].dt.date
fecha_hoy = df['fecha'].max()
print(f"\nFecha de HOY: {fecha_hoy}")
print(f"Dias unicos: {df['fecha'].nunique()}")

print("\n=== DESGLOSE POR DIA ===")
for fecha in sorted(df['fecha'].unique()):
    df_dia = df[df['fecha'] == fecha]
    registros = len(df_dia)
    trabajo = df_dia['trabajo_kW'].sum()
    costo = trabajo * COSTO_KWH_CLP
    horas = registros // 3  # 3 equipos por hora
    print(f"  {fecha}: {horas}h datos, trabajo={trabajo:.1f} kWh, costo=${costo:,.0f} CLP")

# Calcular promedio historico
df_historico = df[df['fecha'] < fecha_hoy]
df_hoy = df[df['fecha'] == fecha_hoy]

print("\n=== CALCULO PROMEDIO HISTORICO ===")
if not df_historico.empty:
    gasto_por_dia = df_historico.groupby('fecha')['trabajo_kW'].sum() * COSTO_KWH_CLP
    print("Gasto por dia historico:")
    for fecha, gasto in gasto_por_dia.items():
        print(f"  {fecha}: ${gasto:,.0f} CLP")
    
    promedio = gasto_por_dia.mean()
    print(f"\nPromedio diario historico: ${promedio:,.0f} CLP")
    print(f"Dias en historico: {len(gasto_por_dia)}")

print("\n=== CALCULO HOY ===")
if not df_hoy.empty:
    gasto_hoy = df_hoy['trabajo_kW'].sum() * COSTO_KWH_CLP
    horas_hoy = len(df_hoy) // 3
    proyeccion = (gasto_hoy / horas_hoy) * 24 if horas_hoy > 0 else 0
    print(f"Gasto actual: ${gasto_hoy:,.0f} CLP")
    print(f"Horas de datos: {horas_hoy}h")
    print(f"Proyeccion 24h: ${proyeccion:,.0f} CLP")
    
    if promedio > 0:
        desviacion = ((proyeccion - promedio) / promedio) * 100
        print(f"Desviacion vs historico: {desviacion:+.1f}%")
