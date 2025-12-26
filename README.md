# 🧊 Sistema de Monitoreo - Planta de Refrigeración Industrial

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram_Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![CoolProp](https://img.shields.io/badge/CoolProp-Thermodynamics-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Sistema de simulación y monitoreo de un ciclo de compresión de vapor para refrigeración industrial, con dashboard interactivo vía Telegram.**

[Características](#-características) •
[Instalación](#-instalación) •
[Uso](#-uso) •
[Arquitectura](#-arquitectura) •
[Licencia](#-licencia)

</div>

---

## 📋 Descripción

Este proyecto simula el comportamiento de una **planta de refrigeración industrial** basada en el ciclo de compresión de vapor. Incluye:

- **Motor termodinámico** que calcula estados del refrigerante usando CoolProp
- **Generador de datos sintéticos** que simula operación continua con variaciones realistas
- **Bot de Telegram** como dashboard HMI/SCADA para monitoreo en tiempo real

## ✨ Características

| Módulo | Descripción |
|--------|-------------|
| 🔬 **Motor Termodinámico** | Cálculo de COP, trabajo del compresor, calores de evaporación/condensación |
| 📊 **Simulador de Datos** | Generación de series temporales con anomalías configurables |
| 🤖 **Dashboard Telegram** | Interfaz industrial con gráficos, alertas y diagnósticos |
| 📈 **Análisis de Costos** | Proyección de consumo energético y desviaciones |
| 🔔 **Sistema de Alertas** | Detección de fallas térmicas y anomalías operativas |

## 🛠️ Instalación

### Prerrequisitos

- Python 3.9 o superior
- Cuenta de Telegram y token de bot (obtener de [@BotFather](https://t.me/BotFather))

### Pasos

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/SrClicks/SimulacionRefrigeracionCompresionDeVaporBot.git
   cd SimulacionRefrigeracionCompresionDeVaporBot
   ```

2. **Crear entorno virtual** (recomendado)
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env y agregar tu TELEGRAM_TOKEN
   ```

## 🚀 Uso

### Opción 1: Usar el menú interactivo (Windows)

```batch
Gestion_Sistema.bat
```

### Opción 2: Ejecutar manualmente

```bash
# Generar datos de simulación
python scripts/generar_datos.py

# Iniciar el bot de Telegram
python scripts/bot_telegram.py
```

### Comandos del Bot

| Comando | Descripción |
|---------|-------------|
| `/start` | Menú principal del sistema |
| `📊 MONITOREO` | Estado actual de la planta |
| `🛠️ DIAGNÓSTICO` | Detección de fallas |
| `💰 COSTOS` | Análisis energético |
| `📈 TENDENCIAS` | Gráficos históricos |

## 🏗️ Arquitectura

```
📁 SimulacionRefrigeracionBot/
├── 📄 .env.example          # Plantilla de configuración
├── 📄 .gitignore            # Archivos excluidos de Git
├── 📄 README.md             # Este archivo
├── 📄 requirements.txt      # Dependencias Python
├── 📄 LICENSE               # Licencia MIT
├── 📄 Gestion_Sistema.bat   # Menú interactivo Windows
│
├── 📁 backend/              # Lógica de negocio
│   ├── __init__.py
│   └── motor_termodinamico.py   # Cálculos termodinámicos
│
├── 📁 scripts/              # Scripts ejecutables
│   ├── bot_telegram.py      # Dashboard Telegram
│   └── generar_datos.py     # Simulador de datos
│
└── 📁 data/                 # Datos generados (gitignored)
    └── *.csv
```

## 🔧 Tecnologías

- **[CoolProp](http://www.coolprop.org/)** - Propiedades termodinámicas de refrigerantes
- **[python-telegram-bot](https://python-telegram-bot.org/)** - API de Telegram
- **[Pandas](https://pandas.pydata.org/)** - Manipulación de datos
- **[Matplotlib](https://matplotlib.org/)** - Generación de gráficos
- **[Pint](https://pint.readthedocs.io/)** - Manejo de unidades físicas

## 📊 Ejemplo de Salida

```
╔══════════════════════════════════════════╗
║  📊 ESTADO ACTUAL DEL SISTEMA            ║
╠══════════════════════════════════════════╣
║  🌡️ T. Evaporación:    -25.3 °C         ║
║  🌡️ T. Condensación:   +42.1 °C         ║
║  📉 COP:                3.42             ║
║  ⚡ Potencia:           15.7 kW          ║
║  🟢 Estado:             NORMAL           ║
╚══════════════════════════════════════════╝
```

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

## 👤 Autor

Desarrollado como proyecto académico / industrial para monitoreo de sistemas de refrigeración.

---

<div align="center">

**⭐ Si este proyecto te fue útil, considera darle una estrella en GitHub ⭐**

</div>
