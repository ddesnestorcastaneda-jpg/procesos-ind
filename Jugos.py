import pandas as pd
import streamlit as st
import graphviz

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Auditoría de Proceso PFD", page_icon="🏭", layout="wide")

st.title("🏭 Auditoría Térmica y Balance de Materia/Energía")
st.markdown("Modelo con Control de Cut-Back: División Fija de Bypass (ej. 70/30) y Ajuste Variables según Concentración.")

# --- 1. BARRA LATERAL: CONFIGURACIÓN DE PARÁMETROS ---
st.sidebar.header("🎯 1. Meta de Producción")
w_m_out = st.sidebar.number_input("Producto Final Deseado (kg/h):", value=4500.0, step=500.0)
w_bout = st.sidebar.number_input("Brix Objetivo Final (°Brix):", value=60.0, step=1.0)

st.sidebar.header("⚙️ 2. Molino / Triturador")
w_bin = st.sidebar.number_input("Brix Fruta Fresca:", value=12.0, step=0.5)
w_merma_molino = st.sidebar.slider("Merma de Peso en Molino (%):", 0.0, 10.0, 2.0, 0.1)

st.sidebar.header("🍇 3. Prensa de Extracción")
w_brix_jugo = st.sidebar.number_input("Sólidos del Jugo Clarificado (°Brix):", value=12.5, step=0.1)
w_brix_bagazo = st.sidebar.number_input("Sólidos en Bagazo (°Brix):", value=4.0, step=0.5)
pct_rend_jugo = st.sidebar.slider("Rendimiento de Jugo Clarificado (%):", 50.0, 95.0, 85.0, 0.5)

st.sidebar.header("🔀 4. Divisor Principal & Bypass")
pct_bp_generado = st.sidebar.slider("Porcentaje de Jugo Desviado a Bypass (%):", 0.0, 50.0, 30.0, 1.0)

st.sidebar.header("🔥 5. Sistema de Evaporación & Concentración")
w_brix_e2 = st.sidebar.number_input("Concentración Salida Evaporador 2 (°Brix):", value=68.0, step=1.0)
pct_fuga_agua = st.sidebar.slider("Pérdida de Vapor / Fugas (% del vapor producido):", 0.0, 15.0, 2.0, 0.1)
pct_limpia_agua = st.sidebar.slider("Condensado / Agua Limpia Recuperada (% del vapor útil):", 0.0, 100.0, 95.0, 1.0)

w_T_evap = st.sidebar.number_input("Temp. Operación Evaporadores (°C):", value=100.0, step=1.0)
dist_evap1 = st.sidebar.slider("Carga de Evaporación E1 (%):", 10.0, 90.0, 55.0, 1.0)

st.sidebar.header("💨 6. Caldera de Suministro")
lambda_vap_custom = st.sidebar.number_input("Calor Latente Vapor Caldera (kJ/kg):", value=2257.0, step=10.0)


# --- 2. CÁLCULO DEL BALANCE DE MATERIA Y ENERGÍA ---
def ejecutar_balance_cutback_adaptativo(
    m_prod_final, brix_in, brix_obj, merma_molino,
    brix_jugo, brix_bagazo, rend_jugo, pct_bp_gen,
    T_evap, pct_evap1, lambda_vap, brix_e2_target,
    pct_fuga_vapor, pct_recup_condensado
):
    T_ref, T_in = 0.0, 25.0
    cp_agua = 4.184
    def calcular_cp(brix): return 4.184 * (1.0 - 0.0054 * brix)

    # 1. Balance en Mezclador Final
    if brix_e2_target > brix_obj:
        m_bp_mix = m_prod_final * (brix_e2_target - brix_obj) / (brix_e2_target - brix_jugo)
        m_evap2_out = m_prod_final - m_bp_mix
    else:
        m_bp_mix = 0.0
        m_evap2_out = m_prod_final
        brix_e2_target = brix_obj

    # 2. Balance en Evaporadores
    m_solidos_evap = m_evap2_out * (brix_e2_target / 100.0)
    m_evap_in = m_solidos_evap / (brix_jugo / 100.0)

    # 3. Flujo Total de Jugo y División por Bypass (ej. 70 / 30)
    pct_evap_linea = 100.0 - pct_bp_gen
    if pct_evap_linea <= 0: pct_evap_linea = 1.0

    m_jugo_total = m_evap_in / (pct_evap_linea / 100.0)
    m_bp_total_generado = m_jugo_total * (pct_bp_gen / 100.0)

    # Comparación entre lo generado por el bypass y lo que requiere la mezcla
    m_bp_excedente = max(0.0, m_bp_total_generado - m_bp_mix)

    # 4. Agua Evaporada, Fugas y Agua Limpia
    m_vapor_total_retirado = m_evap_in - m_evap2_out
    m_vapor_fugas = m_vapor_total_retirado * (pct_fuga_vapor / 100.0)
    m_vapor_util = m_vapor_total_retirado - m_vapor_fugas
    m_agua_limpia = m_vapor_util * (pct_recup_condensado / 100.0)

    # 5. Prensa de Extracción y Molino
    m_pulpa_molida = m_jugo_total / (rend_jugo / 100.0)
    m_bagazo = m_pulpa_molida - m_jugo_total
    m_fruta = m_pulpa_molida / (1.0 - (merma_molino / 100.0))
    m_merma_molino = m_fruta * (merma_molino / 100.0)

    # 6. Distribución Evaporador 1 y Evaporador 2
    m_vap1 = m_vapor_total_retirado * (pct_evap1 / 100.0)
    m_vap2 = m_vapor_total_retirado * ((100.0 - pct_evap1) / 100.0)

    m_evap1_out = m_evap_in - m_vap1
    brix_evap1_out = (m_solidos_evap / m_evap1_out) * 100.0

    corrientes = [
        ("Fruta Fresca Requerida", m_fruta, brix_in, T_in, False, "Entrada Isostática / Calculada"),
        ("Merma de Peso Molino", m_merma_molino, brix_in, T_in, False, "Pérdida Mecánica/Evaporativa"),
        ("Pulpa Molida (Entrada Prensa)", m_pulpa_molida, brix_in, T_in, False, "Salida Molino"),
        ("Bagazo Húmedo (Prensa)", m_bagazo, brix_bagazo, T_in, False, "Separación Mecánica"),
        ("Jugo Clarificado Total", m_jugo_total, brix_jugo, T_in, False, "Jugo Clarificado Extracción"),
        ("Jugo a Evaporador 1", m_evap_in, brix_jugo, T_in, False, f"Línea de Evaporación ({pct_evap_linea:.0f}%)"),
        ("Bypass Total Generado", m_bp_total_generado, brix_jugo, T_in, False, f"Línea de Bypass ({pct_bp_gen:.0f}%)"),
        ("Bypass Utilizado (Cut-Back)", m_bp_mix, brix_jugo, T_in, False, "Reingreso Requerido a Mezclador"),
        ("Bypass Excedente / Otro Proceso", m_bp_excedente, brix_jugo, T_in, False, "Sobrante Desviado de Proceso"),
        ("Vapor Útil / Evaporado", m_vapor_util, 0.0, T_evap, True, "Vapor Extraído Útil"),
        ("Vapor Escapado / Fugas", m_vapor_fugas, 0.0, T_evap, True, "Pérdida de Vapor por Fugas"),
        ("Agua Limpia Recuperada", m_agua_limpia, 0.0, T_evap, False, "Condensado Recuperado"),
        ("Jugo Salida Evap 1", m_evap1_out, brix_evap1_out, T_evap, False, "Concentración Intermedia E1"),
        ("Jugo Salida Evap 2", m_evap2_out, brix_e2_target, T_evap, False, "Concentración Entrada a Mezclador"),
        ("Producto Final Requerido", m_prod_final, brix_obj, 60.0, False, "Mezclado Adiabático Final")
    ]

    dict_corrientes = {}
    filas_tabla = []
    for nombre, m, brix, T, es_vapor, tipo_proc in corrientes:
        cp = cp_agua if es_vapor else calcular_cp(brix)
        h = ((cp_agua * (T - T_ref)) + lambda_vap) if es_vapor else cp * (T - T_ref)
        H_flujo = m * h
        dict_corrientes[nombre] = {"m": m, "brix": brix, "T": T, "cp": cp, "h": h, "H": H_flujo, "tipo_proc": tipo_proc}
        filas_tabla.append({
            "Corriente / Etapa": nombre, "Flujo Másico (kg/h)": round(m, 2),
            "Sólidos (°Brix)": round(brix, 2), "Temp (°C)": round(T, 1),
            "Cp (kJ/kg·°C)": round(cp, 3), "Entalpía Sp h (kJ/kg)": round(h, 2),
            "Flujo Entálpico H (kJ/h)": round(H_flujo, 2), "Tipo de Proceso Termodinámico": tipo_proc
        })

    df_resultados = pd.DataFrame(filas_tabla)

    # Balance Energético
    h_in_e1 = calcular_cp(brix_jugo) * T_in
    h_out_e1 = calcular_cp(brix_evap1_out) * T_evap
    h_v1 = (cp_agua * T_evap) + lambda_vap
    Q_evap1 = (m_evap1_out * h_out_e1) + (m_vap1 * h_v1) - (m_evap_in * h_in_e1)

    h_out_e2 = calcular_cp(brix_e2_target) * T_evap
    h_v2 = (cp_agua * T_evap) + lambda_vap
    Q_evap2 = (m_evap2_out * h_out_e2) + (m_vap2 * h_v2) - (m_evap1_out * h_out_e1)

    Q_total = Q_evap1 + Q_evap2
    m_vapor_caldera = Q_total / lambda_vap

    res_energia = {
        "Q_Evap1": Q_evap1, "Q_Evap2": Q_evap2, "Q_Total": Q_total,
        "Vapor_Caldera": m_vapor_caldera, "corrientes": dict_corrientes,
        "Fruta_Requerida": m_fruta
    }
    return df_resultados, res_energia


# --- 3. DIAGRAMA PFD EN GRAPHVIZ ---
def generar_diagrama_detallado(res, pct_bp, pct_e1):
    c = res["corrientes"]
    pct_evap_linea = 100.0 - pct_bp
    dot = graphviz.Digraph(comment="PFD Detallado", format="png")
    dot.attr(rankdir="LR", size="16", nodesep="0.6", ranksep="1.2", fontname="Helvetica")

    dot.attr('node', shape='box', style='filled', fillcolor='#1a365d', fontcolor='white', fontname='Helvetica-Bold', fontsize='10')
    dot.node("MOLINO", "MOLINO / TRITURADOR\n(Reducción & Merma)")
    dot.node("PRENSA", "PRENSA DE EXTRACCIÓN\n(Separación Sólido/Líquido)")
    dot.node("DIV_PRINCIPAL", f"DIVISOR PRINCIPAL\n(Línea Evap: {pct_evap_linea:.0f}% / Bypass: {pct_bp:.0f}%)", fillcolor="#2b6cb0", shape="diamond")
    dot.node("EVAP1", f"EVAPORADOR 1\n(Carga: {pct_e1}%)")
    dot.node("EVAP2", f"EVAPORADOR 2\n(Conc. Salida: {c['Jugo Salida Evap 2']['brix']:.1f}°Brix)")
    dot.node("CONTROL_BP", "CONTROL DE CUT-BACK\n(Válvula Reguladora)", fillcolor="#2b6cb0", shape="diamond")
    dot.node("MEZCLA", "MEZCLADOR FINAL\n(Mezclado Adiabático)")

    dot.attr('node', shape='rectangle', style='filled,rounded', fillcolor='#edf2f7', fontcolor='#1a202c', fontname='Helvetica', fontsize='8.5')

    def fmt_lbl(nombre_corr):
        d = c[nombre_corr]
        m_solidos = d['m'] * (d['brix'] / 100.0)
        m_liquido = d['m'] - m_solidos
        return f" Total: {d['m']:,.1f} kg/h | Conc: {d['brix']:.1f} °Brix\n 💧 Ag/Liq: {m_liquido:,.1f} kg/h\n 🧊 Sólidos: {m_solidos:,.1f} kg/h\n T: {d['T']:.0f}°C | H: {d['H']:,.0f} kJ/h"

    dot.node("IN", f"ENTRADA: Fruta Requerida\n{fmt_lbl('Fruta Fresca Requerida')}", fillcolor="#c6f6d5")
    dot.node("MERMA", f"PÉRDIDA: Merma Molino\n{fmt_lbl('Merma de Peso Molino')}", fillcolor="#fed7d7")
    dot.node("BAGAZO", f"SALIDA: Bagazo Húmedo\n{fmt_lbl('Bagazo Húmedo (Prensa)')}", fillcolor="#feebc8")
    dot.node("EXCEDENTE", f"EXCEDENTE BYPASS\n(Otro Proceso / Almacén)\n{fmt_lbl('Bypass Excedente / Otro Proceso')}", fillcolor="#feebc8")
    dot.node("OUT", f"PRODUCTO REQUERIDO\n{fmt_lbl('Producto Final Requerido')}", fillcolor="#9ae6b4", shape="doublerectangle")

    dot.edge("IN", "MOLINO", color="#2f855a", penwidth="2")
    dot.edge("MOLINO", "MERMA", label=" Merma de Peso", color="#e53e3e")
    dot.edge("MOLINO", "PRENSA", label=f" Pulpa Molida\n{fmt_lbl('Pulpa Molida (Entrada Prensa)')}", color="#2f855a")
    dot.edge("PRENSA", "BAGAZO", label=" Bagazo Residual", color="#dd6b20")
    dot.edge("PRENSA", "DIV_PRINCIPAL", label=f" Jugo Clarificado\n{fmt_lbl('Jugo Clarificado Total')}", color="#2b6cb0")

    dot.edge("DIV_PRINCIPAL", "EVAP1", label=f" Jugo a Evap ({pct_evap_linea:.0f}%)\n{fmt_lbl('Jugo a Evaporador 1')}", color="#2b6cb0")
    dot.edge("EVAP1", "EVAP2", label=f" Jugo Conc. I\n{fmt_lbl('Jugo Salida Evap 1')}", color="#2b6cb0")
    dot.edge("EVAP2", "MEZCLA", label=f" Jugo Conc. II\n{fmt_lbl('Jugo Salida Evap 2')}", color="#2b6cb0")

    dot.edge("DIV_PRINCIPAL", "CONTROL_BP", label=f" Bypass Generado ({pct_bp:.0f}%)\n{fmt_lbl('Bypass Total Generado')}", style="dashed", color="#dd6b20")
    dot.edge("CONTROL_BP", "MEZCLA", label=f" Cut-Back Requerido\n{fmt_lbl('Bypass Utilizado (Cut-Back)')}", color="#2b6cb0")
    dot.edge("CONTROL_BP", "EXCEDENTE", label=" Excedente Sobrante", style="dashed", color="#dd6b20")

    dot.edge("MEZCLA", "OUT", color="#2f855a", penwidth="2.5")

    dot.node("FUGAS", f"VAPOR ESCAPADO / FUGAS\n{fmt_lbl('Vapor Escapado / Fugas')}", fillcolor="#fed7d7", shape="note")
    dot.node("AGUA_LIMPIA", f"AGUA LIMPIA RECUPERADA\n{fmt_lbl('Agua Limpia Recuperada')}", fillcolor="#ebf8ff", shape="note")

    dot.edge("EVAP2", "FUGAS", style="dotted", color="#e53e3e")
    dot.edge("EVAP2", "AGUA_LIMPIA", style="dotted", color="#3182ce")

    return dot


# --- 4. EJECUCIÓN Y RENDERIZADO ---
df, res = ejecutar_balance_cutback_adaptativo(
    w_m_out, w_bin, w_bout, w_merma_molino,
    w_brix_jugo, w_brix_bagazo, pct_rend_jugo, pct_bp_generado,
    w_T_evap, dist_evap1, lambda_vap_custom, w_brix_e2,
    pct_fuga_agua, pct_limpia_agua
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Fruta Fresca Requerida", f"{res['Fruta_Requerida']:,.1f} kg/h")
col2.metric("Cut-Back al Mezclador", f"{res['corrientes']['Bypass Utilizado (Cut-Back)']['m']:,.1f} kg/h")
col3.metric("Bypass Excedente", f"{res['corrientes']['Bypass Excedente / Otro Proceso']['m']:,.1f} kg/h")
col4.metric("Consumo Vapor Caldera", f"{res['Vapor_Caldera']:,.1f} kg/h")

st.subheader("📋 Tabla de Auditoría de Materia, Energía y Procesos")
st.dataframe(df, use_container_width=True)

st.subheader("🗺️ Diagrama de Flujo de Proceso (PFD)")
figura = generar_diagrama_detallado(res, pct_bp_generado, dist_evap1)
st.graphviz_chart(figura.source, use_container_width=True)
