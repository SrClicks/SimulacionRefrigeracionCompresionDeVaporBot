"""
Generador de Datos Industriales - Sistema de Refrigeración
Genera datos de operación basados en simulación termodinámica realista.
Los archivos se guardan en /data con nomenclatura de fecha.
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import random

# Configuración de rutas para imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.motor_termodinamico import simular_refrigerador

try:
    import pandas as pd
except ImportError:
    print("Error: pandas no está instalado. Ejecuta: pip install pandas")
    sys.exit(1)


# === CONFIGURACIÓN DEL GENERADOR ===
DIAS_SIMULACION = 7
FRECUENCIA_HORAS = 1
EQUIPOS = {
    "CAMARA_01_CARNES": {"t_interior": -18, "flujo": 0.12},
    "CAMARA_02_LACTEOS": {"t_interior": 4, "flujo": 0.08},
    "CAMARA_03_VERDURAS": {"t_interior": 4, "flujo": 0.08},
}
DATA_DIR = PROJECT_ROOT / "data"


def calcular_temperatura_ambiente(hora: int, dia_del_anio: int) -> float:
    """
    Simula temperatura de Punta Arenas con variación horaria y estacional.
    Clima subpolar: invierno muy frío (-5°C promedio), verano fresco (10°C promedio).
    """
    temp_base_invierno = -5
    temp_base_verano = 10
    
    # Variación estacional (simplificada)
    factor_estacion = 0.5 * (1 + (dia_del_anio - 172) / 172)  # Máximo en verano austral (día 172 = junio)
    temp_base = temp_base_invierno + (temp_base_verano - temp_base_invierno) * factor_estacion
    
    # Variación diurna: mínimo a las 6am, máximo a las 15pm
    variacion_diurna = 4 * ((1 - abs(hora - 15) / 12))
    
    # Ruido aleatorio para realismo
    ruido = random.gauss(0, 1.5)
    
    return round(temp_base + variacion_diurna + ruido, 1)


def simular_evento_apertura_puerta() -> float:
    """
    Simula el impacto de aperturas de puertas en el Delta T del condensador.
    Las aperturas frecuentes generan mayor carga térmica.
    """
    prob_apertura = random.random()
    
    if prob_apertura < 0.05:  # 5% de probabilidad de muchas aperturas
        return random.uniform(3, 8)
    elif prob_apertura < 0.20:  # 15% de probabilidad moderada
        return random.uniform(1, 3)
    
    return 0


def generar_datos() -> None:
    """Genera el dataset de operación industrial y lo guarda en CSV."""
    
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    archivo_destino = DATA_DIR / f"operacion_{fecha_actual}.csv"
    
    # Política de sobrescritura: eliminar archivo existente
    if archivo_destino.exists():
        archivo_destino.unlink()
        print(f"Archivo existente eliminado: {archivo_destino.name}")
    
    registros = []
    fecha_inicio = datetime.now() - timedelta(days=DIAS_SIMULACION)
    total_puntos = DIAS_SIMULACION * 24 // FRECUENCIA_HORAS
    
    print(f"Generando {total_puntos * len(EQUIPOS)} registros para {len(EQUIPOS)} equipos...")
    
    for i in range(total_puntos):
        fecha = fecha_inicio + timedelta(hours=i * FRECUENCIA_HORAS)
        dia_del_anio = fecha.timetuple().tm_yday
        hora = fecha.hour
        
        t_ambiente = calcular_temperatura_ambiente(hora, dia_del_anio)
        
        for id_equipo, params in EQUIPOS.items():
            
            # Delta T base del condensador (operación normal)
            delta_t_cond_base = 15
            
            # Impacto de aperturas de puerta
            delta_t_cond = delta_t_cond_base + simular_evento_apertura_puerta()
            
            # Simulación de falla progresiva en últimos 2 días (condensador sucio)
            dias_restantes = DIAS_SIMULACION - (i // 24)
            if dias_restantes <= 2:
                factor_degradacion = 1 + (2 - dias_restantes) * 0.7
                delta_t_cond = delta_t_cond * factor_degradacion
            
            # Variación en eficiencia según antigüedad simulada del equipo
            eta_base = 0.75
            variacion_eta = random.uniform(-0.03, 0.02)
            eta = max(0.60, min(0.85, eta_base + variacion_eta))
            
            try:
                resultado = simular_refrigerador(
                    T_ambiente_C=t_ambiente,
                    T_interior_C=params["t_interior"],
                    Flujo_masico_kg_s=params["flujo"],
                    eta_isentropica=eta,
                    Delta_T_cond_C=delta_t_cond
                )
                
                # Determinar estado del sistema según indicadores
                cop = resultado['scalar']['COP']
                temp_descarga = resultado['scalar']['Temp_Descarga_C']
                
                if delta_t_cond > 25 or cop < 2.0:
                    estado = "ALARMA"
                elif delta_t_cond > 20 or cop < 2.5:
                    estado = "ADVERTENCIA"
                else:
                    estado = "NORMAL"
                
                registros.append({
                    "timestamp": fecha.strftime("%Y-%m-%d %H:%M:%S"),
                    "id_equipo": id_equipo,
                    "t_ambiente_C": t_ambiente,
                    "t_interior_C": round(params["t_interior"] + random.uniform(-0.5, 0.5), 1),
                    "delta_t_cond_C": round(delta_t_cond, 1),
                    "eta_compresor": round(eta, 3),
                    "cop": round(cop, 2),
                    "temp_descarga_C": round(temp_descarga, 1),
                    "trabajo_kW": round(resultado['scalar']['Trabajo_Compresor_kW'], 3),
                    "calor_extraido_kW": round(resultado['scalar']['Calor_Extraido_kW'], 3),
                    "calidad_evap": round(resultado['scalar']['Calidad_Evap'], 3),
                    "estado": estado
                })
                
            except Exception as e:
                print(f"Error en simulación [{id_equipo} @ {fecha}]: {e}")
    
    # Exportar a CSV
    df = pd.DataFrame(registros)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(archivo_destino, index=False)
    
    print(f"\n[OK] Archivo generado: {archivo_destino.name}")
    print(f"     Ubicacion: /data/")
    print(f"     Registros: {len(df)}")
    print(f"     Periodo: {fecha_inicio.strftime('%Y-%m-%d')} -> {datetime.now().strftime('%Y-%m-%d')}")
    print(f"     Estados: {df['estado'].value_counts().to_dict()}")


if __name__ == "__main__":
    generar_datos()