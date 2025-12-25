import CoolProp.CoolProp as CP
import pint

u = pint.UnitRegistry()
Q_ = u.Quantity # type: ignore

def simular_refrigerador(T_ambiente_C, T_interior_C, Flujo_masico_kg_s, eta_isentropica=0.75, Delta_T_cond_C=15):
    """
    Simula un ciclo de refrigeración por compresión de vapor REAL.
    
    Parámetros:
        T_ambiente_C: Temperatura ambiente en °C
        T_interior_C: Temperatura interior objetivo en °C
        Flujo_masico_kg_s: Flujo másico del refrigerante en kg/s
        eta_isentropica: Eficiencia isentrópica del compresor (default: 0.75)
        Delta_T_cond_C: Diferencia de temperatura en el condensador en °C (default: 15)
    """
    refrigerante = 'R134a'

    # --- INPUTS ---
    T_ambiente = Q_(T_ambiente_C, "degC").to("kelvin")
    T_interior = Q_(T_interior_C, "degC").to("kelvin")
    Flujo_masico = Q_(Flujo_masico_kg_s, "kg/s")

    # Definimos Deltas térmicos (Diferencia de temperatura necesaria para transferir calor)
    Delta_T_cond = Q_(Delta_T_cond_C, "delta_degC") # El condensador debe estar más caliente que el aire

    # --- ESTADO 1: Entrada Compresor (Vapor Saturado) ---
    # T_interior define la evaporación
    h1 = Q_(CP.PropsSI("H", "T", T_interior.magnitude, "Q", 1, refrigerante), "J/kg")
    s1 = Q_(CP.PropsSI("S", "T", T_interior.magnitude, "Q", 1, refrigerante), "J/kg/K")

    # --- ESTADO 2: Entrada Condensador (Vapor Sobrecalentado) - CICLO REAL ---
    T_condensacion = T_ambiente + Delta_T_cond
    P_condensacion = Q_(CP.PropsSI("P", "T", T_condensacion.magnitude, "Q", 0, refrigerante), "Pa")

    P2 = P_condensacion
    
    # Cálculo de h2 IDEAL (compresión isentrópica)
    h2_ideal = Q_(CP.PropsSI("H", "P", P2.to("Pa").magnitude, "S", s1.to("J/kg/K").magnitude, refrigerante), "J/kg")
    
    # Cálculo de h2 REAL (considerando eficiencia isentrópica del compresor)
    # Fórmula: h2_real = h1 + (h2_ideal - h1) / eta_isentropica
    h2 = h1 + (h2_ideal - h1) / eta_isentropica
    
    # El trabajo real es mayor que el ideal debido a la ineficiencia del compresor
    Trabajo_necesario = Flujo_masico * (h2 - h1)
    
    # Entropía real en estado 2 (aumenta respecto a s1 debido a irreversibilidad)
    s2 = Q_(CP.PropsSI("S", "P", P2.to("Pa").magnitude, "H", h2.to("J/kg").magnitude, refrigerante), "J/kg/K")

    # --- ESTADO 3: Salida Condensador (Líquido Saturado) ---
    P3 = P2
    h3 = Q_(CP.PropsSI("H", "P", P3.to("Pa").magnitude, "Q", 0, refrigerante), "J/kg")
    T3 = Q_(CP.PropsSI("T", "P", P3.to("Pa").magnitude, "Q", 0, refrigerante), "kelvin")

    # --- ESTADO 4: Entrada Evaporador (Mezcla) ---
    h4 = h3
    P4 = Q_(CP.PropsSI("P", "T", T_interior.magnitude, "Q", 1, refrigerante), "Pa")
    x4 = CP.PropsSI("Q", "P", P4.to("Pa").magnitude, "H", h4.to("J/kg").magnitude, refrigerante)     # Para saber cuánto gas flash hay

    # --- CÁLCULOS FINALES ---
    Q_evap = Flujo_masico * (h1 - h4)
    
    # COP (Coeficiente de desempeño)
    COP = Q_evap / Trabajo_necesario

    # --- RESULTADOS ---
    # Empaquetamos los resultados en un diccionario
    resultados = {
        "scalar": {
            "Trabajo_Compresor_kW": Trabajo_necesario.to('kW').magnitude,
            "Calor_Extraido_kW": Q_evap.to('kW').magnitude,
            "COP": COP.magnitude,
            "Calidad_Evap": x4,
            "Temp_Descarga_C": CP.PropsSI('T','H',h2.magnitude,'P',P2.magnitude,refrigerante)-273.15,
            "Flujo_Masico_kg_s": Flujo_masico.magnitude
        },
        "states": {
            1: {"P": P4.to("Pa").magnitude, "T": T_interior.to("kelvin").magnitude, "h": h1.to("J/kg").magnitude, "s": s1.to("J/kg/K").magnitude, "desc": "Entrada Compresor"},
            2: {"P": P2.to("Pa").magnitude, "T": (T_ambiente + Delta_T_cond).to("kelvin").magnitude, "h": h2.to("J/kg").magnitude, "s": s2.to("J/kg/K").magnitude, "desc": "Entrada Condensador"}, # Nota: T calculada aprox en ciclo
            3: {"P": P3.to("Pa").magnitude, "T": T3.to("kelvin").magnitude, "h": h3.to("J/kg").magnitude, "s": CP.PropsSI("S", "P", P3.magnitude, "Q", 0, refrigerante), "desc": "Salida Condensador"},
            4: {"P": P4.to("Pa").magnitude, "T": T_interior.to("kelvin").magnitude, "h": h4.to("J/kg").magnitude, "s": CP.PropsSI("S", "P", P4.magnitude, "H", h4.magnitude, refrigerante), "desc": "Entrada Evaporador"},
        } 
    }
    
    # Recalculamos T real de descarga para el estado 2 (el modelo asume sobrecalentamiento isentrópico)
    T2_real = CP.PropsSI('T','H',h2.magnitude,'P',P2.magnitude,refrigerante)
    resultados["states"][2]["T"] = T2_real
    
    return resultados

def imprimir_resultados(res, t_amb_c):
    print(f"--- RESULTADOS (Ambiente: {t_amb_c} C) ---")
    print(f"- Trabajo Compresor: {res['scalar']['Trabajo_Compresor_kW']:.2f} kW")
    print(f"- Calor Extraido:    {res['scalar']['Calor_Extraido_kW']:.2f} kW")
    print(f"- COP del ciclo:     {res['scalar']['COP']:.2f}")
    print(f"- Calidad en Evap:   {res['scalar']['Calidad_Evap']:.2f} ({(res['scalar']['Calidad_Evap']*100):.1f}% es gas flash)")
    print(f"- Temp. Descarga:    {res['scalar']['Temp_Descarga_C']:.1f} C")


# --- BLOQUE INTERACTIVO ---
if __name__ == "__main__":
    print("\n--- CONFIGURACION DE LA SIMULACION ---")
    try:
        # Pedimos los datos al usuario
        t_amb_input = float(input("1. Ingrese Temperatura Ambiente (C): "))
        t_int_input = float(input("2. Ingrese Temperatura Interior Objetivo (C): "))
        flujo_input = float(input("3. Ingrese Flujo Masico (kg/s): "))
        
        print("\nCalculando...")
        
        # Llamamos a tu función con los datos ingresados
        resultados = simular_refrigerador(t_amb_input, t_int_input, flujo_input)
        imprimir_resultados(resultados, t_amb_input)
        
    except ValueError:
        print("Error: Por favor ingrese solo números (use punto para decimales).")