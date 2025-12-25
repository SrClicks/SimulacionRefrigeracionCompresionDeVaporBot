"""
Bot de Telegram - Dashboard Interactivo de Ingenieria Industrial
Sistema de monitoreo de camaras de refrigeracion con graficos y diagnosticos.
"""
import sys
import os
import io
from pathlib import Path
from datetime import datetime, timedelta

# Configuracion de rutas
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
DATA_DIR = PROJECT_ROOT / "data"

try:
    import logging
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')  # Backend sin GUI para servidores
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from dotenv import load_dotenv
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
    from telegram.error import Conflict, NetworkError
except ImportError as e:
    print(f"Error: Dependencia faltante - {e}")
    print("Ejecuta: pip install python-telegram-bot pandas python-dotenv matplotlib")
    sys.exit(1)

# Silenciar logs técnicos de librerías externas
logging.getLogger("telegram").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)

# Cargar variables de entorno
load_dotenv(PROJECT_ROOT / ".env")

# === CONFIGURACION ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
COSTO_KWH_CLP = 120

SETPOINTS = {
    "CAMARA_01_CARNES": -18,
    "CAMARA_02_LACTEOS": 4,
    "CAMARA_03_VERDURAS": 4,
}

# Colores para graficos
COLORES_EQUIPOS = {
    "CAMARA_01_CARNES": "#E74C3C",
    "CAMARA_02_LACTEOS": "#3498DB", 
    "CAMARA_03_VERDURAS": "#27AE60",
}


def leer_datos_hoy() -> pd.DataFrame | None:
    """Lee el CSV del dia actual, retorna None si no existe."""
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    archivo = DATA_DIR / f"operacion_{fecha_hoy}.csv"
    
    if not archivo.exists():
        return None
    
    df = pd.read_csv(archivo)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def obtener_semaforo(estado: str, cop: float) -> str:
    """Retorna emoji de semaforo segun estado y COP."""
    if estado == "ALARMA" or cop < 2.0:
        return "🔴"
    elif estado == "ADVERTENCIA":
        return "🟡"
    return "🟢"


def generar_menu_principal() -> InlineKeyboardMarkup:
    """Menu principal del dashboard."""
    keyboard = [
        [InlineKeyboardButton("📊 Estado Actual", callback_data="estado")],
        [InlineKeyboardButton("💰 Costos y Eficiencia", callback_data="costos")],
        [InlineKeyboardButton("📈 Tendencias Térmicas", callback_data="tendencias")],
        [InlineKeyboardButton("🛠️ Diagnóstico Salud", callback_data="diagnostico")],
        [InlineKeyboardButton("📚 Ver Parámetros Ideales", callback_data="referencia")],
    ]
    return InlineKeyboardMarkup(keyboard)


def generar_botones_con_refresh(seccion: str, equipos_alarma: list = None) -> InlineKeyboardMarkup:
    """Genera botones incluyendo refresh y drill-down para alarmas."""
    keyboard = []
    
    # Botones de drill-down para equipos en alarma
    if equipos_alarma:
        for equipo in equipos_alarma:
            # Mapeo de IDs a Nombres Visuales con Iconos
            if "CARNES" in equipo:
                nombre_visual = "🥩 Carnes"
            elif "LACTEOS" in equipo:
                nombre_visual = "🥛 Lácteos"
            elif "VERDURAS" in equipo:
                nombre_visual = "🥦 Verduras"
            else:
                nombre_visual = equipo.split("_")[2] # Fallback
            
            # Incluir sección de origen en el callback para navegación correcta
            keyboard.append([
                InlineKeyboardButton(f"🔍 Analizar Falla: {nombre_visual}", callback_data=f"falla_{seccion}_{equipo}")
            ])
    
    keyboard.append([InlineKeyboardButton("🔄 Actualizar Datos", callback_data=f"refresh_{seccion}")])
    keyboard.append([InlineKeyboardButton("🔙 Menu Principal", callback_data="menu")])
    
    return InlineKeyboardMarkup(keyboard)


def generar_boton_volver() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton("🔙 Menu Principal", callback_data="menu")]]
    return InlineKeyboardMarkup(keyboard)


def generar_boton_volver_seccion(seccion_origen: str) -> InlineKeyboardMarkup:
    """Botón para volver a la sección de origen desde el detalle de falla."""
    # Mapeo de secciones a nombres visuales
    nombres_secciones = {
        "estado": "📊 Estado Actual",
        "costos": "💰 Costos y Eficiencia",
        "diagnostico": "🛠️ Diagnóstico"
    }
    nombre_visual = nombres_secciones.get(seccion_origen, "Sección Anterior")
    
    keyboard = [
        [InlineKeyboardButton(f"⬅️ Volver a {nombre_visual}", callback_data=seccion_origen)],
        [InlineKeyboardButton("🔙 Menu Principal", callback_data="menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def generar_grafico_tendencias(df: pd.DataFrame) -> io.BytesIO | None:
    """Genera grafico de tendencias termicas en memoria."""
    if df is None or len(df) < 2:
        return None
    
    # Filtrar ultimas 24 horas
    ahora = df['timestamp'].max()
    hace_24h = ahora - timedelta(hours=24)
    df_24h = df[df['timestamp'] >= hace_24h]
    
    if len(df_24h) < 2:
        return None
    
    # Configuracion del grafico
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#16213e')
    
    for equipo in df_24h['id_equipo'].unique():
        df_equipo = df_24h[df_24h['id_equipo'] == equipo].sort_values('timestamp')
        color = COLORES_EQUIPOS.get(equipo, '#FFFFFF')
        nombre = equipo.split("_")[2]
        # Offset visual para evitar superposicion exacta entre Lacteos y Verduras (ambos setpoint 4.0)
        valores = df_equipo['t_interior_C']
        if "LACTEOS" in equipo:
            valores = valores + 0.15
        elif "VERDURAS" in equipo:
            valores = valores - 0.15

        ax.plot(df_equipo['timestamp'], valores, 
                label=nombre, color=color, linewidth=2, marker='o', markersize=3)
    
    # Lineas de setpoint
    for equipo, setpoint in SETPOINTS.items():
        ax.axhline(y=setpoint, color='#888888', linestyle='--', alpha=0.5, linewidth=1)
    
    ax.set_xlabel('Hora', color='white', fontsize=11)
    ax.set_ylabel('Temperatura (°C)', color='white', fontsize=11)
    ax.set_title('Tendencias Térmicas - Últimas 24 Horas', color='white', fontsize=14, fontweight='bold')
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    plt.xticks(rotation=45, color='white')
    plt.yticks(color='white')
    
    ax.legend(loc='upper right', facecolor='#1a1a2e', edgecolor='white', labelcolor='white')
    ax.grid(True, alpha=0.3, color='white')
    
    for spine in ax.spines.values():
        spine.set_color('white')
        spine.set_alpha(0.3)
    
    plt.tight_layout()
    
    # Guardar en buffer de memoria
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', facecolor=fig.get_facecolor(), edgecolor='none')
    buffer.seek(0)
    plt.close(fig)
    
    return buffer


def analizar_falla_equipo(df: pd.DataFrame, id_equipo: str) -> str:
    """Genera diagnostico detallado de fallas para un equipo con valores de referencia."""
    df_equipo = df[df['id_equipo'] == id_equipo].sort_values('timestamp')
    
    if df_equipo.empty:
        return "No hay datos disponibles para este equipo."
    
    # Determinar tipo de cámara para metas de COP
    es_carnes = "CARNES" in id_equipo
    meta_cop = "2.9-3.2" if es_carnes else "6.0-7.5"
    
    # Detectar eventos de alarma
    alarmas = df_equipo[df_equipo['estado'] == 'ALARMA']
    
    if alarmas.empty:
        return f"*{id_equipo}*\n\nSin alertas registradas en el periodo."
    
    mensaje = f"*ANÁLISIS DE FALLA*\n_{id_equipo}_\n\n"
    
    # Primera alarma del dia
    primera_alarma = alarmas.iloc[0]
    mensaje += f"Inicio Desviación: {primera_alarma['timestamp'].strftime('%H:%M')}\n"
    
    # Duracion total en alarma
    total_alarmas = len(alarmas)
    mensaje += f"Registros Críticos: {total_alarmas}\n"
    mensaje += f"Duración Estimada: ~{total_alarmas} horas\n\n"
    
    # COP durante alarmas con metas
    cop_promedio = alarmas['cop'].mean()
    cop_minimo = alarmas['cop'].min()
    
    # Semáforo de alerta para COP
    cop_alerta = "🔴 " if cop_promedio < 2.5 else ""
    cop_min_alerta = "🔴 " if cop_minimo < 2.0 else ""
    
    mensaje += f"*Métricas del Evento:*\n"
    mensaje += f"  {cop_alerta}COP Promedio: {cop_promedio:.2f} (Meta: {meta_cop})\n"
    mensaje += f"  {cop_min_alerta}COP Mínimo: {cop_minimo:.2f} (Meta: {meta_cop})\n"
    
    # Temperatura maxima de descarga con referencia
    if 'temp_descarga_C' in alarmas.columns:
        temp_max = alarmas['temp_descarga_C'].max()
        temp_alerta = "🔴 " if temp_max > 100 else ""
        mensaje += f"  {temp_alerta}T° Descarga Máx: {temp_max:.1f} °C (Máx: 100°C)\n"
    
    # Delta T con referencia
    if 'delta_t_cond_C' in alarmas.columns:
        delta_t_prom = alarmas['delta_t_cond_C'].mean()
        delta_alerta = "🔴 " if delta_t_prom > 25 else ""
        mensaje += f"  {delta_alerta}ΔT Condensador: {delta_t_prom:.1f} °C (Ideal: 15°C)\n"
    
    # Diagnostico probable
    mensaje += "\n*Diagnóstico Probable:*\n"
    if cop_promedio < 2.5:
        mensaje += "- Obstrucción en condensador\n"
        mensaje += "- Posible pérdida de carga ref.\n"
    if 'delta_t_cond_C' in alarmas.columns and alarmas['delta_t_cond_C'].mean() > 25:
        mensaje += "- Sobrecarga térmica detectada\n"
    
    mensaje += "\n_Acción: Inspección física requerida_"
    
    return mensaje


# === HANDLERS DE TELEGRAM ===

async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensaje = (
        "📊 *DASHBOARD INDUSTRIAL*\n"
        "_Sistema de Refrigeración - Punta Arenas_\n\n"
        "Seleccione módulo de monitoreo:"
    )
    await update.message.reply_text(
        mensaje,
        parse_mode="Markdown",
        reply_markup=generar_menu_principal()
    )


async def mostrar_estado_actual(update: Update, context: ContextTypes.DEFAULT_TYPE, es_refresh: bool = False) -> None:
    query = update.callback_query
    await query.answer()
    
    df = leer_datos_hoy()
    
    if df is None:
        await query.edit_message_text(
            "🔴 *ERROR:* Datos no disponibles.\nVerifique ejecución del generador.",
            reply_markup=generar_boton_volver(),
            parse_mode="Markdown"
        )
        return
    
    ultimas = df.groupby("id_equipo").last().reset_index()
    equipos_alarma = []
    
    hora_actual = datetime.now().strftime("%H:%M:%S")
    mensaje = f"📊 *ESTADO ACTUAL DE FLOTA*\n_Sincronización: {hora_actual}_\n\n"
    
    for _, row in ultimas.iterrows():
        equipo = row["id_equipo"]
        nombre = equipo.replace("_", " ").replace("CAMARA ", "")
        t_interior = row["t_interior_C"]
        estado = row["estado"]
        cop = row["cop"]
        
        semaforo = obtener_semaforo(estado, cop)
        # Modo Enfriando (❄️) si está bajo 0°C, de lo contrario Operativo (🟢)
        modo_icon = "❄️" if t_interior < 0 else "🟢"
        
        if estado == "ALARMA" or cop < 2.0:
            equipos_alarma.append(equipo)
            semaforo = "🔴"
        
        mensaje += f"{semaforo} *{nombre}*\n"
        mensaje += f"    🌡️ T°: {t_interior} °C | 📉 COP: {cop:.2f}\n"
        mensaje += f"    {modo_icon} Modo: {'Refrigeración' if t_interior < 0 else 'Nominal'} | {estado}\n\n"
    
    await query.edit_message_text(
        mensaje,
        parse_mode="Markdown",
        reply_markup=generar_botones_con_refresh("estado", equipos_alarma)
    )


def leer_todos_los_datos() -> pd.DataFrame | None:
    """Lee el archivo CSV más reciente (contiene historial acumulado)."""
    archivos = list(DATA_DIR.glob("operacion_*.csv"))
    
    if not archivos:
        return None
    
    # Ordenar por fecha en el nombre del archivo y tomar el más reciente
    archivos_ordenados = sorted(archivos, key=lambda x: x.stem, reverse=True)
    archivo_mas_reciente = archivos_ordenados[0]
    
    try:
        df = pd.read_csv(archivo_mas_reciente)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df.sort_values('timestamp')
    except Exception:
        return None


async def mostrar_costos(update: Update, context: ContextTypes.DEFAULT_TYPE, es_refresh: bool = False) -> None:
    query = update.callback_query
    await query.answer()
    
    # Leer todos los datos disponibles (histórico + hoy)
    df = leer_todos_los_datos()
    
    if df is None or df.empty:
        await query.edit_message_text(
            "🔴 *ERROR:* No hay datos de costos disponibles.",
            reply_markup=generar_boton_volver(),
            parse_mode="Markdown"
        )
        return
    
    # === PROCESAMIENTO DE FECHAS ===
    df['fecha'] = df['timestamp'].dt.date
    fecha_hoy = df['fecha'].max()  # La fecha más reciente en el archivo
    
    # === SEGMENTACIÓN DE DATOS ===
    df_historico = df[df['fecha'] < fecha_hoy]
    df_hoy = df[df['fecha'] == fecha_hoy]
    
    ahora = datetime.now()
    hora_actual = ahora.strftime("%H:%M:%S")
    
    # === CÁLCULOS SEMANALES ===
    consumo_total_kwh = df["trabajo_kW"].sum()
    gasto_total_semanal = consumo_total_kwh * COSTO_KWH_CLP
    
    # Promedio diario histórico
    if not df_historico.empty:
        gasto_por_dia = df_historico.groupby('fecha')['trabajo_kW'].sum() * COSTO_KWH_CLP
        promedio_diario_historico = gasto_por_dia.mean()
        dias_historico = len(gasto_por_dia)
    else:
        promedio_diario_historico = 0
        dias_historico = 0
    
    # === CÁLCULOS DE HOY ===
    if not df_hoy.empty:
        consumo_hoy_kwh = df_hoy["trabajo_kW"].sum()
        gasto_hoy_actual = consumo_hoy_kwh * COSTO_KWH_CLP
        cop_promedio_hoy = df_hoy["cop"].mean()
        
        # Calcular horas transcurridas basado en timestamps del archivo (datos reales)
        hora_inicio = df_hoy['timestamp'].min()
        hora_fin = df_hoy['timestamp'].max()
        horas_datos = max(1, (hora_fin - hora_inicio).total_seconds() / 3600 + 1)
        
        # Proyección: (Gasto hoy / horas de datos) * 24 horas
        proyeccion_hoy = (gasto_hoy_actual / horas_datos) * 24
        
        # Detectar equipos con COP crítico
        resumen_equipos = df_hoy.groupby("id_equipo")["cop"].mean()
        equipos_criticos = resumen_equipos[resumen_equipos < 3.0].index.tolist()
        hay_equipos_criticos = len(equipos_criticos) > 0
        
        # Desviación vs promedio histórico
        if promedio_diario_historico > 0:
            desviacion = ((proyeccion_hoy - promedio_diario_historico) / promedio_diario_historico) * 100
        else:
            desviacion = 0
    else:
        gasto_hoy_actual = 0
        cop_promedio_hoy = 0
        proyeccion_hoy = 0
        desviacion = 0
        horas_datos = 0
        hay_equipos_criticos = False
        equipos_criticos = []
    
    # === CONSTRUCCIÓN DEL MENSAJE ===
    mensaje = f"💰 *GESTIÓN DE COSTOS*\n_Actualizado: {hora_actual}_\n\n"
    
    # 📅 Resumen Semanal
    mensaje += "━━━━━━━━━━━━━━━━━━━━━━\n"
    mensaje += "📅 *RESUMEN SEMANAL*\n"
    mensaje += f"   💵 Gasto Acumulado: *${gasto_total_semanal:,.0f} CLP*\n"
    mensaje += f"   📊 Promedio Diario: *${promedio_diario_historico:,.0f} CLP*\n"
    mensaje += f"   📆 Días Analizados: {dias_historico + 1}\n\n"
    
    # ⚡ Situación de HOY
    mensaje += "━━━━━━━━━━━━━━━━━━━━━━\n"
    mensaje += "⚡ *SITUACIÓN DE HOY*\n"
    mensaje += f"   🕐 Horas con Datos: {horas_datos:.0f}h\n"
    mensaje += f"   💰 Gasto Actual: *${gasto_hoy_actual:,.0f} CLP*\n"
    
    # Mostrar proyección solo si hay suficientes datos (al menos 4 horas)
    if horas_datos >= 4:
        # Emoji de advertencia según criterios
        if desviacion >= 20:
            emoji_proyeccion = "🔴 "
        elif desviacion >= 10:
            emoji_proyeccion = "🟡 "
        elif desviacion <= -15:
            emoji_proyeccion = "🟢 "
        else:
            emoji_proyeccion = ""
        mensaje += f"   📈 Proyección 24h: {emoji_proyeccion}*${proyeccion_hoy:,.0f} CLP*\n"
        
        # Color y texto de desviación según criterios del usuario
        signo = "+" if desviacion > 0 else ""
        if desviacion >= 20:
            emoji_desv = "🔴"
            texto_estado = "FALLA CRÍTICA"
        elif desviacion >= 10:
            emoji_desv = "🟡"
            texto_estado = "Alerta Temprana"
        elif desviacion <= -15:
            emoji_desv = "🟢"
            texto_estado = "Ahorro Extraordinario"
        elif abs(desviacion) <= 10:
            emoji_desv = "⚪"
            texto_estado = "Normal"
        else:
            emoji_desv = "⚪"
            texto_estado = "Normal"
        
        mensaje += f"   {emoji_desv} Desviación: *{signo}{desviacion:.1f}%* ({texto_estado})\n"
    else:
        mensaje += f"   ⏳ _Proyección disponible con +4h de datos_\n"
    
    mensaje += "\n"
    
    # 💡 Diagnóstico según situación
    if horas_datos >= 4:
        mensaje += "━━━━━━━━━━━━━━━━━━━━━━\n"
        mensaje += "💡 *DIAGNÓSTICO*\n"
        
        if desviacion >= 20:
            # Falla Crítica
            mensaje += "   🚨 *FALLA CRÍTICA*\n"
            desviacion_diaria_clp = proyeccion_hoy - promedio_diario_historico
            perdida_mensual = desviacion_diaria_clp * 30
            mensaje += f"   📉 Sobrecosto Diario: *${desviacion_diaria_clp:,.0f} CLP*\n"
            mensaje += f"   � Pérdida Mensual: *${perdida_mensual:,.0f} CLP*\n"
            mensaje += "   _Acción: Revisar refrigerante, condensador, válvulas_\n"
        elif desviacion >= 10:
            # Alerta Temprana
            mensaje += "   ⚠️ *ALERTA TEMPRANA*\n"
            desviacion_diaria_clp = proyeccion_hoy - promedio_diario_historico
            mensaje += f"   📉 Sobrecosto Estimado: *${desviacion_diaria_clp:,.0f} CLP/día*\n"
            mensaje += "   _Acción: Revisar limpieza de condensadores_\n"
        elif desviacion <= -15 and not hay_equipos_criticos:
            # Ahorro Extraordinario (solo si no hay equipos críticos)
            mensaje += "   ✅ *AHORRO EXTRAORDINARIO*\n"
            mensaje += "   _Alta eficiencia, condiciones climáticas favorables_\n"
        elif hay_equipos_criticos:
            # Hay equipos críticos aunque la desviación parezca favorable
            mensaje += "   ⚠️ *EQUIPOS EN ESTADO CRÍTICO*\n"
            for eq in equipos_criticos:
                nombre_eq = eq.split("_")[2] if "_" in eq else eq
                mensaje += f"   🔴 {nombre_eq}: COP bajo, revisar sistema\n"
            if desviacion < 0:
                mensaje += "   _Nota: Desviación negativa por datos parciales del día_\n"
        else:
            # Operación Normal
            mensaje += "   ✅ *OPERACIÓN NORMAL*\n"
            mensaje += "   _Consumo dentro de parámetros esperados_\n"
        
        mensaje += "\n"
    
    # Semáforo de eficiencia COP
    eval_semaforo = "🟢" if cop_promedio_hoy >= 4.0 else ("🟡" if cop_promedio_hoy >= 3.0 else "🔴")
    evaluacion = "Rendimiento Óptimo" if cop_promedio_hoy >= 4.0 else ("Eficiencia Nominal" if cop_promedio_hoy >= 3.0 else "Consumo Crítico")
    mensaje += f"{eval_semaforo} COP Promedio Hoy: *{cop_promedio_hoy:.2f}* | _{evaluacion}_\n\n"
    
    # Desglose por equipo
    mensaje += "━━━━━━━━━━━━━━━━━━━━━━\n"
    mensaje += "*Detalle por Unidad:*\n"
    resumen = df_hoy.groupby("id_equipo").agg({
        "cop": "mean",
        "trabajo_kW": "sum"
    }).reset_index()
    
    equipos_alarma = []
    for _, row in resumen.iterrows():
        equipo = row["id_equipo"]
        if "CARNES" in equipo:
            nombre = "🥩 Carnes"
        elif "LACTEOS" in equipo:
            nombre = "🥛 Lácteos"
        elif "VERDURAS" in equipo:
            nombre = "🥦 Verduras"
        else:
            nombre = row["id_equipo"].split("_")[1] + " " + row["id_equipo"].split("_")[2]
        
        costo_equipo = row["trabajo_kW"] * COSTO_KWH_CLP
        cop_equipo = row["cop"]
        
        semaforo = "🟢" if cop_equipo >= 3.0 else "🔴"
        if cop_equipo < 3.0:
            equipos_alarma.append(equipo)
        
        mensaje += f"   {semaforo} {nombre}: ${costo_equipo:,.0f} | 📉 {cop_equipo:.2f}\n"
    
    await query.edit_message_text(
        mensaje,
        parse_mode="Markdown",
        reply_markup=generar_botones_con_refresh("costos", equipos_alarma)
    )


async def mostrar_tendencias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Generando grafico...")
    
    df = leer_datos_hoy()
    
    if df is None or len(df) < 2:
        await query.edit_message_text(
            "Datos insuficientes para generar grafico.\nSe requieren al menos 2 registros.",
            reply_markup=generar_boton_volver()
        )
        return
    
    try:
        buffer = generar_grafico_tendencias(df)
        
        if buffer is None:
            await query.edit_message_text(
                "🟡 *AVISO:* Trazabilidad incompleta (requiere min. 24h de operación).",
                reply_markup=generar_boton_volver(),
                parse_mode="Markdown"
            )
            return
        
        # Eliminar mensaje actual y enviar foto
        await query.message.delete()
        
        hora_actual = datetime.now().strftime("%H:%M:%S")
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=buffer,
            caption=f"📈 *TENDENCIAS TÉRMICAS*\n_Generado: {hora_actual}_",
            parse_mode="Markdown",
            reply_markup=generar_boton_volver()
        )
        
    except Exception as e:
        await query.edit_message_text(
            f"Error al generar grafico: {str(e)}",
            reply_markup=generar_boton_volver()
        )


async def mostrar_diagnostico(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    df = leer_datos_hoy()
    
    if df is None:
        await query.edit_message_text(
            "🔴 *ERROR:* Diagnóstico no disponible.",
            reply_markup=generar_boton_volver(),
            parse_mode="Markdown"
        )
        return
    
    hora_actual = datetime.now().strftime("%H:%M:%S")
    mensaje = f"🛠️ *DIAGNÓSTICO DE SALUD*\n_Actualizado: {hora_actual}_\n\n"
    
    # Analisis de temperatura de descarga
    if 'temp_descarga_C' in df.columns:
        temp_criticas = df[df["temp_descarga_C"] > 100]
        if len(temp_criticas) > 0:
            mensaje += "🔴 *ALERTA TÉCNICA*\n"
            mensaje += f"   {len(temp_criticas)} anomalías detectadas\n"
            mensaje += "   🌡️ T° Descarga > 100 °C (Riesgo Compresor)\n\n"
        else:
            mensaje += "🟢 Descarga Compresor: Nominal.\n\n"
    
    # Analisis por equipo
    mensaje += "*Integridad por Unidad:*\n"
    equipos_alarma = []
    
    for equipo, setpoint in SETPOINTS.items():
        df_equipo = df[df["id_equipo"] == equipo]
        if df_equipo.empty:
            continue
            
        alarmas = df_equipo[df_equipo['estado'] == 'ALARMA']
        cop_prom = df_equipo['cop'].mean()
        nombre = equipo.split("_")[2]
        
        if len(alarmas) > 0 or cop_prom < 2.5:
            equipos_alarma.append(equipo)
            mensaje += f"   🔴 {nombre}: {len(alarmas)} fallas | 📉 {cop_prom:.2f}\n"
        else:
            mensaje += f"   🟢 {nombre}: Operación Estable | 📉 {cop_prom:.2f}\n"
    
    # Resumen de estados
    mensaje += "\n*Resumen de Flota:*\n"
    estados = df["estado"].value_counts()
    for estado, count in estados.items():
        porcentaje = (count / len(df)) * 100
        semaforo = "🟢" if estado == "NORMAL" else "🔴"
        mensaje += f"   {semaforo} {estado}: {count} ({porcentaje:.1f}%)\n"
    
    await query.edit_message_text(
        mensaje,
        parse_mode="Markdown",
        reply_markup=generar_botones_con_refresh("diagnostico", None)
    )


async def mostrar_detalle_falla(update: Update, context: ContextTypes.DEFAULT_TYPE, id_equipo: str, seccion_origen: str = "diagnostico") -> None:
    query = update.callback_query
    await query.answer()
    
    df = leer_datos_hoy()
    
    if df is None:
        await query.edit_message_text(
            "🔴 *ERROR:* Sin datos para análisis.",
            reply_markup=generar_boton_volver(),
            parse_mode="Markdown"
        )
        return
    
    mensaje = analizar_falla_equipo(df, id_equipo)
    
    # Convertir el texto de analizar_falla_equipo para integrar emojis
    mensaje = mensaje.replace("Inicio Desviación:", "🕒 Inicio Falla:")
    mensaje += "\n\n🔙 Presione botón para retornar."
    
    await query.edit_message_text(
        mensaje,
        parse_mode="Markdown",
        reply_markup=generar_boton_volver_seccion(seccion_origen)
    )


async def mostrar_referencia_tecnica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra los parámetros ideales de diseño del sistema."""
    query = update.callback_query
    await query.answer()
    
    mensaje = (
        "📚 *REFERENCIA TÉCNICA*\n"
        "_Parámetros Ideales de Diseño_\n\n"
        
        "*📉 Coeficiente de Desempeño (COP):*\n"
        "   🥩 Cámara Carnes (-18°C): `2.9 - 3.2`\n"
        "   🥛 Cámara Lácteos (4°C): `6.0 - 7.5`\n"
        "   🥦 Cámara Verduras (4°C): `6.0 - 7.5`\n\n"
        
        "*🌡️ Temperaturas Críticas:*\n"
        "   T° Descarga Máxima: `100°C`\n"
        "   _Sobre este valor hay riesgo de daño al compresor_\n\n"
        
        "*🔥 Delta T Condensador:*\n"
        "   ΔT Ideal: `15°C`\n"
        "   ΔT Advertencia: `> 20°C`\n"
        "   ΔT Crítico: `> 25°C`\n"
        "   _Valores altos indican obstrucción o suciedad_\n\n"
        
        "*⚠️ Umbrales de Alarma:*\n"
        "   COP < 2.5 → Eficiencia Crítica\n"
        "   COP < 2.0 → Falla Inminente\n\n"
        
        "_Referencia: Manual de Operación Rev. 2024_"
    )
    
    await query.edit_message_text(
        mensaje,
        parse_mode="Markdown",
        reply_markup=generar_boton_volver()
    )


async def manejar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Router principal de callbacks."""
    query = update.callback_query
    data = query.data
    
    if data == "menu":
        await query.answer()
        
        texto_menu = (
            "📊 *DASHBOARD INDUSTRIAL*\n"
            "_Telemetría Planta - Punta Arenas_\n\n"
            "Seleccione módulo:"
        )
        markup = generar_menu_principal()
        
        # Si el mensaje tiene foto (caption no es None), no se puede editar a texto.
        # En ese caso, borramos y enviamos uno nuevo.
        if query.message.caption or query.message.photo:
            await query.message.delete()
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=texto_menu,
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
            await query.edit_message_text(
                texto_menu,
                parse_mode="Markdown",
                reply_markup=markup
            )
    
    elif data == "estado" or data == "refresh_estado":
        await mostrar_estado_actual(update, context, es_refresh=(data == "refresh_estado"))
    
    elif data == "costos" or data == "refresh_costos":
        await mostrar_costos(update, context, es_refresh=(data == "refresh_costos"))
    
    elif data == "tendencias":
        await mostrar_tendencias(update, context)
    
    elif data == "diagnostico" or data == "refresh_diagnostico":
        await mostrar_diagnostico(update, context)
    
    elif data == "referencia":
        await mostrar_referencia_tecnica(update, context)
    
    elif data.startswith("falla_"):
        # Formato: falla_SECCION_CAMARA_XX_NOMBRE
        partes = data.split("_", 2)  # ['falla', 'seccion', 'CAMARA_XX_NOMBRE']
        seccion_origen = partes[1] if len(partes) > 2 else "diagnostico"
        id_equipo = partes[2] if len(partes) > 2 else data.replace("falla_", "")
        await mostrar_detalle_falla(update, context, id_equipo, seccion_origen)


def main() -> None:
    if not TELEGRAM_TOKEN:
        print("Error: No se encontro TELEGRAM_TOKEN en .env")
        sys.exit(1)
    
    print("Iniciando Dashboard Industrial...")
    print("Presiona Ctrl+C para detener\n")
    
    try:
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        app.add_handler(CommandHandler("start", comando_start))
        app.add_handler(CallbackQueryHandler(manejar_callback))
        
        print("[OK] Bot activo y escuchando...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Conflict:
        print("\n" + "="*60)
        print("⚠️  CONFLICTO DETECTADO")
        print("="*60)
        print("El bot ya se está ejecutando en otra ventana.")
        print("Cierre la instancia anterior para continuar.")
        print("="*60 + "\n")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n[OK] Bot detenido por el usuario.")
        sys.exit(0)
        
    except NetworkError as e:
        print("\n" + "="*60)
        print("🔴 ERROR DE CONEXIÓN")
        print("="*60)
        print(f"No se pudo conectar con Telegram: {e}")
        print("Verifique su conexión a internet.")
        print("="*60 + "\n")
        sys.exit(1)
        
    except Exception as e:
        print("\n" + "="*60)
        print("🔴 ERROR INESPERADO")
        print("="*60)
        print(f"Tipo: {type(e).__name__}")
        print(f"Detalle: {e}")
        print("="*60 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
