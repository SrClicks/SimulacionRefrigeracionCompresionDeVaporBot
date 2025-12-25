@echo off
chcp 65001 >nul
color 0B
title Sistema de Monitoreo UMAG

:: Establecer directorio de trabajo
cd /d "C:\Users\gajar\OneDrive\Documents\Google Drive SINCRONIZACION\PROYECTOS\⚙️ CODIGO\COMPRESION DE VAPOR\scripts"

:MENU
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                          ║
echo  ║        --- SISTEMA DE MONITOREO UMAG ---                 ║
echo  ║        Planta de Refrigeracion Industrial                ║
echo  ║                                                          ║
echo  ╠══════════════════════════════════════════════════════════╣
echo  ║                                                          ║
echo  ║    [1]  Simular Operacion (generar_datos.py)             ║
echo  ║                                                          ║
echo  ║    [2]  Iniciar Dashboard Telegram (bot_telegram.py)     ║
echo  ║                                                          ║
echo  ║    [3]  Salir                                            ║
echo  ║                                                          ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
set /p opcion="  Ingrese opcion [1-3]: "

if "%opcion%"=="1" goto SIMULAR
if "%opcion%"=="2" goto DASHBOARD
if "%opcion%"=="3" goto SALIR

echo.
echo  [!] Opcion invalida. Intente de nuevo.
timeout /t 2 >nul
goto MENU

:SIMULAR
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║         EJECUTANDO SIMULACION DE OPERACION               ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  [i] Generando datos de operacion...
echo.
python generar_datos.py
echo.
echo  [OK] Simulacion completada.
echo.
pause
goto MENU

:DASHBOARD
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║         INICIANDO DASHBOARD TELEGRAM                     ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  [i] Conectando con servidor de Telegram...
echo  [i] Presione Ctrl+C para detener el bot.
echo.
python bot_telegram.py
echo.
echo  ════════════════════════════════════════════════════════════
echo  [!] El Dashboard se ha detenido.
echo  ════════════════════════════════════════════════════════════
echo.
pause
goto MENU

:SALIR
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║              SISTEMA CERRADO CORRECTAMENTE               ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
timeout /t 2 >nul
exit
