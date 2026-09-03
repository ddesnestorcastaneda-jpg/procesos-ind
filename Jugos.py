import graphviz
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Auditoría de Proceso PFD", page_icon="🏭", layout="wide"
)

st.title("🏭 Auditoría Térmica y Balance de Materia/Energía")
st.markdown(
    "Simulador Avanzado de Planta de Concentración de Jugo con Molino y Prensa"
    " Separados."
)

# --- 1. BARRA LATERAL: CONFIGURACIÓN POR ETAPAS ---
st.sidebar.header("🎯 1. Meta de Producción")
w_m_out = st.sidebar.number_input(
    "Producto Final Deseado (kg/h):", value=4500.0, step=500.0
)
w_bout = st.sidebar.number_input("Brix Objetivo Final:", value=60.0, step=1.0)

st.sidebar.header("🥭 2. Materia Prima & Extracción")
w_bin = st.sidebar.number_input("Brix Fruta Fresca:", value=12.0, step=0.5)
w_bag = st.sidebar.slider(
    "Retención de Bagazo en Prensa (%):", 5.0, 20.0, 10.0, 0.5
)

st.sidebar.header("🔀 3. Divisor Principal & Bypass")
w_bp = st.sidebar.slider(
    "Bypass Generado en Divisor (%):", 0.0, 50.0, 30.0, 1.0
)

st.sidebar.header("🔥 4. Sistema de Evaporación")
w_brix_e2 = st.sidebar.number_input(
    "Concentración Salida Evaporador 2 (°Brix):", value=68.0, step=1.0
)
w_T_evap = st.sidebar.number_input(
    "Temp. Operación Evaporadores (°C):", value=100.0, step=1.0
)
dist_evap1 = st.sidebar.slider(
    "Carga de Evaporación E1 (%):", 10.0, 90.0, 55.0, 1.0
)

st.sidebar.header("💨 5. Caldera de Suministro")
lambda_vap_custom = st.sidebar.number_input(
    "Calor Latente Vapor Caldera (kJ/kg):", value=2257.0, step=10.0
)


# --- 2. LÓGICA DE CÁLCULO ---
def ejecutar_balance_avanzado(
    m_prod_final,
    brix_in,
    brix_obj,
    pct_bp,
    pct_bag,
    T_evap,
    pct_evap1,
    lambda_vap,
    brix_evap2_target,
):
  T_ref, T_in = 0.0, 25.0
  cp_agua = 4.184

  def calcular_cp(brix):
    return 4.184 * (1.0 - 0.0054 * brix)

  if brix_evap2_target <= brix_obj:
    brix_evap2_target = brix_obj + 1.0

  # 1. Balance en Mezclador Final
  m_bp_mix = (
      m_prod_final
      * (brix_evap2_target - brix_obj)
      / (brix_evap2_target - brix_in)
  )
  m_evap2_out = m_prod_final - m_bp_mix

  solidos_evap = m_evap2_out * (brix_evap2_target / 100.0)
  m_evap_in = solidos_evap / (brix_in / 100.0)

  # 2. Balance en Divisor Principal
  if pct_bp >= 100.0:
    pct_bp = 99.0

  m_jugo = m_evap_in / (1.0 - (pct_bp / 100.0))
  m_bp_total = m_jugo * (pct_bp / 100.0)

  if m_bp_total < m_bp_mix:
    m_bp_total = m_bp_mix
    m_jugo = m_evap_in + m_bp_total
    pct_bp = (m_bp_total / m_jugo) * 100.0

  m_bp_excedente = m_bp_total - m_bp_mix

  # 3. Balance de Molienda y Prensado (Separados)
  m_fruta = m_jugo / (1.0 - (pct_bag / 100.0))
  m_pulpa_molida = m_fruta  # Masa se conserva 1:1 en el molino
  m_bagazo = m_fruta * (pct_bag / 100.0)

  # 4. Balance en Evaporadores
  m_agua_total_evaporada = m_evap_in - m_evap2_out
  pct_evap2 = 100.0 - pct_evap1

  m_vap1 = m_agua_total_evaporada * (pct_evap1 / 100.0)
  m_vap2 = m_agua_total_evaporada * (pct_evap2 / 100.0)

  m_evap1_out = m_evap_in - m_vap1
  brix_evap1_out = (solidos_evap / m_evap1_out) * 100.0

  corrientes = [
      (
          "Fruta Fresca Requerida",
          m_fruta,
          brix_in,
          T_in,
          False,
          "Entrada Isostática / Calculada",
      ),
      (
          "Pulpa Molida (Salida Molino)",
          m_pulpa_molida,
          brix_in,
          T_in,
          False,
          "Reducción Mecánica de Tamaño (Q≈0)",
      ),
      (
          "Torta Bagazo",
          m_bagazo,
          0.0,
          T_in,
          False,
          "Separación Mecánica (Isotérmico, Q≈0)",
      ),
      (
          "Jugo Prensa Total",
          m_jugo,
          brix_in,
          T_in,
          False,
          "Separación Mecánica (Isotérmico, Q≈0)",
      ),
      (
          "Jugo a Evaporador 1",
          m_evap_in,
          brix_in,
          T_in,
          False,
          "División Principal de Flujo (Q=0)",
      ),
      (
          "Bypass Total Generado",
          m_bp_total,
          brix_in,
          T_in,
          False,
          "División Principal de Flujo (Q=0)",
      ),
      (
          "Bypass Ajustado a Mezcla",
          m_bp_mix,
          brix_in,
          T_in,
          False,
          "Control de Cut-Back a Mezclador (Q=0)",
      ),
      (
          "Bypass Excedente / Otro Proceso",
          m_bp_excedente,
          brix_in,
          T_in,
          False,
          "Desvío a Almacenamiento/Otros (Q=0)",
      ),
      (
          "Vapor Evap 1",
          m_vap1,
          0.0,
          T_evap,
          True,
          "Cambio de Fase Isobárico e Isotérmico",
      ),
      (
          "Jugo Salida Evap 1",
          m_evap1_out,
          brix_evap1_out,
          T_evap,
          False,
          "Transferencia Térmica No Adiabática (Q > 0)",
      ),
      (
          "Vapor Evap 2",
          m_vap2,
          0.0,
          T_evap,
          True,
          "Cambio de Fase Isobárico e Isotérmico",
      ),
      (
          "Jugo Salida Evap 2",
          m_evap2_out,
          brix_evap2_target,
          T_evap,
          False,
          "Transferencia Térmica No Adiabática (Q > 0)",
      ),
      (
          "Producto Final Requerido",
          m_prod_final,
          brix_obj,
          60.0,
          False,
          "Mezclado Adiabático (Garantiza °Brix)",
      ),
  ]

  dict_corrientes = {}
  filas_tabla = []
  for nombre, m, brix, T, es_vapor, tipo_proc in corrientes:
    cp = cp_agua if es_vapor else calcular_cp(brix)
    h = ((cp_agua * (T - T_ref)) + lambda_vap) if es_vapor else cp * (T - T_ref)
    H_flujo = m * h
    dict_corrientes[nombre] = {
        "m": m,
        "brix": brix,
        "T": T,
        "cp": cp,
        "h": h,
        "H": H_flujo,
        "tipo_proc": tipo_proc,
    }
    filas_tabla.append({
        "Corriente / Etapa": nombre,
        "Flujo Másico (kg/h)": round(m, 2),
        "Sólidos (°Brix)": round(brix, 2),
        "Temp (°C)": round(T, 1),
        "Cp (kJ/kg·°C)": round(cp, 3),
        "Entalpía Sp h (kJ/kg)": round(h, 2),
        "Flujo Entálpico H (kJ/h)": round(H_flujo, 2),
        "Tipo de Proceso Termodinámico": tipo_proc,
    })

  df_resultados = pd.DataFrame(filas_tabla)

  # Balances energéticos
  h_in_e1 = calcular_cp(brix_in) * T_in
  h_out_e1 = calcular_cp(brix_evap1_out) * T_evap
  h_v1 = (cp_agua * T_evap) + lambda_vap
  Q_evap1 = (m_evap1_out * h_out_e1) + (m_vap1 * h_v1) - (m_evap_in * h_in_e1)

  h_out_e2 = calcular_cp(brix_evap2_target) * T_evap
  h_v2 = (cp_agua * T_evap) + lambda_vap
  Q_evap2 = (m_evap2_out * h_out_e2) + (m_vap2 * h_v2) - (m_evap1_out * h_out_e1)

  Q_total = Q_evap1 + Q_evap2
  m_vapor_caldera = Q_total / lambda_vap

  res_energia = {
      "Q_Evap1": Q_evap1,
      "Q_Evap2": Q_evap2,
      "Q_Total": Q_total,
      "Vapor_Caldera": m_vapor_caldera,
      "corrientes": dict_corrientes,
      "Fruta_Requerida": m_fruta,
  }
  return df_resultados, res_energia


# --- 3. GENERADOR DE DIAGRAMA GRAPHVIZ ---
def generar_diagrama_detallado(res, pct_bp, pct_e1):
  c = res["corrientes"]
  dot = graphviz.Digraph(comment="PFD Detallado", format="png")
  dot.attr(
      rankdir="LR",
      size="16",
      nodesep="0.6",
      ranksep="1.2",
      fontname="Helvetica",
  )

  # Nodos principales de proceso
  dot.attr(
      "node",
      shape="box",
      style="filled",
      fillcolor="#1a365d",
      fontcolor="white",
      fontname="Helvetica-Bold",
      fontsize="10",
  )
  dot.node("MOLINO", "MOLINO / TRITURADOR\n(Reducción Mecánica)")
  dot.node("PRENSA", "PRENSA DE EXTRACCIÓN\n(Separación Mecánica)")
  dot.node(
      "DIV_PRINCIPAL",
      f"DIVISOR PRINCIPAL\n(Bypass: {pct_bp}%)",
      fillcolor="#2b6cb0",
      shape="diamond",
  )
  dot.node("EVAP1", f"EVAPORADOR 1\n(Carga: {pct_e1}%)")
  dot.node("EVAP2", f"EVAPORADOR 2\n(Carga: {100.0 - pct_e1:.1f}%)")
  dot.node(
      "CONTROL_BP",
      "CONTROL DE BYPASS\n(Ajuste de Cut-Back)",
      fillcolor="#2b6cb0",
      shape="diamond",
  )
  dot.node("MEZCLA", "MEZCLADOR FINAL\n(Mezclado Adiabático)")

  dot.attr(
      "node",
      shape="rectangle",
      style="filled,rounded",
      fillcolor="#edf2f7",
      fontcolor="#1a202c",
      fontname="Helvetica",
      fontsize="8.5",
  )

  def fmt_lbl(nombre_corr):
    d = c[nombre_corr]
    m_solidos = d["m"] * (d["brix"] / 100.0)
    m_liquido = d["m"] - m_solidos
    return (
        f" Total: {d['m']:,.1f} kg/h | Conc: {d['brix']:.1f} °Brix\n"
        f" 💧 Liq (Agua): {m_liquido:,.1f} kg/h\n"
        f" 🧊 Sólidos: {m_solidos:,.1f} kg/h\n"
        f" T: {d['T']:.0f}°C | H: {d['H']:,.0f} kJ/h"
    )

  # Nodos de Entrada y Salida
  dot.node(
      "IN",
      f"ENTRADA: Fruta Requerida\n{fmt_lbl('Fruta Fresca Requerida')}",
      fillcolor="#c6f6d5",
  )
  dot.node(
      "BAGAZO",
      f"SALIDA: Torta Bagazo\n{fmt_lbl('Torta Bagazo')}",
      fillcolor="#feebc8",
  )
  dot.node(
      "EXCEDENTE",
      (
          "EXCEDENTE DE BYPASS\n(Otro Proceso / Almacenamiento)\n"
          f"{fmt_lbl('Bypass Excedente / Otro Proceso')}"
      ),
      fillcolor="#feebc8",
  )
  dot.node(
      "OUT",
      f"PRODUCTO REQUERIDO\n{fmt_lbl('Producto Final Requerido')}",
      fillcolor="#9ae6b4",
      shape="doublerectangle",
  )

  # Conexiones de preparación y extracción
  dot.edge("IN", "MOLINO", color="#2f855a", penwidth="2")
  dot.edge(
      "MOLINO",
      "PRENSA",
      label=f" Pulpa Molida\n{fmt_lbl('Pulpa Molida (Salida Molino)')}",
      color="#2f855a",
  )
  dot.edge("PRENSA", "BAGAZO", label=" Torta Bagazo", color="#dd6b20")
  dot.edge(
      "PRENSA",
      "DIV_PRINCIPAL",
      label=f" Jugo Prensa\n{fmt_lbl('Jugo Prensa Total')}",
      color="#2b6cb0",
  )

  # Rama de Evaporación
  dot.edge(
      "DIV_PRINCIPAL",
      "EVAP1",
      label=f" A Evaporación\n{fmt_lbl('Jugo a Evaporador 1')}",
      color="#2b6cb0",
  )
  dot.edge(
      "EVAP1",
      "EVAP2",
      label=f" Jugo Conc. I\n{fmt_lbl('Jugo Salida Evap 1')}",
      color="#2b6cb0",
  )
  dot.edge(
      "EVAP2",
      "MEZCLA",
      label=f" Jugo Conc. II\n{fmt_lbl('Jugo Salida Evap 2')}",
      color="#2b6cb0",
  )

  # Rama de Bypass y Control
  dot.edge(
      "DIV_PRINCIPAL",
      "CONTROL_BP",
      label=f" Bypass Total ({pct_bp}%)\n{fmt_lbl('Bypass Total Generado')}",
      style="dashed",
      color="#dd6b20",
  )
  dot.edge(
      "CONTROL_BP",
      "MEZCLA",
      label=f" Cut-back Requerido\n{fmt_lbl('Bypass Ajustado a Mezcla')}",
      color="#2b6cb0",
  )
  dot.edge(
      "CONTROL_BP",
      "EXCEDENTE",
      label=" Excedente Desviado",
      style="dashed",
      color="#dd6b20",
  )

  dot.edge("MEZCLA", "OUT", color="#2f855a", penwidth="2.5")

  # Vapores Generados
  dot.node(
      "VAP1",
      f"VAPOR GENERADO 1\n 💧 Vapor: {c['Vapor Evap 1']['m']:,.1f} kg/h\n 🧊"
      " Sólidos: 0.0 kg/h",
      fillcolor="#e2e8f0",
      shape="note",
  )
  dot.node(
      "VAP2",
      f"VAPOR GENERADO 2\n 💧 Vapor: {c['Vapor Evap 2']['m']:,.1f} kg/h\n 🧊"
      " Sólidos: 0.0 kg/h",
      fillcolor="#e2e8f0",
      shape="note",
  )
  dot.edge("EVAP1", "VAP1", style="dotted", color="#718096")
  dot.edge("EVAP2", "VAP2", style="dotted", color="#718096")

  # Servicios Térmicos y Caldera
  dot.node(
      "Q1",
      f"Q1 = {res['Q_Evap1']:,.0f} kJ/h",
      fillcolor="#fed7d7",
      fontcolor="#9b2c2c",
      shape="oval",
  )
  dot.node(
      "Q2",
      f"Q2 = {res['Q_Evap2']:,.0f} kJ/h",
      fillcolor="#fed7d7",
      fontcolor="#9b2c2c",
      shape="oval",
  )
  dot.node(
      "CALDERA",
      f"CALDERA CENTRAL\nQ Total: {res['Q_Total']:,.0f} kJ/h\nVapor:"
      f" {res['Vapor_Caldera']:,.1f} kg/h",
      fillcolor="#e53e3e",
      fontcolor="white",
      shape="component",
  )

  dot.edge("CALDERA", "Q1", style="dashed", color="#e53e3e")
  dot.edge("CALDERA", "Q2", style="dashed", color="#e53e3e")
  dot.edge("Q1", "EVAP1", color="#e53e3e")
  dot.edge("Q2", "EVAP2", color="#e53e3e")

  return dot


# --- 4. RENDERING PRINCIPAL ---
df, res = ejecutar_balance_avanzado(
    w_m_out,
    w_bin,
    w_bout,
    w_bp,
    w_bag,
    w_T_evap,
    dist_evap1,
    lambda_vap_custom,
    w_brix_e2,
)

col1, col2, col3 = st.columns(3)
col1.metric("Fruta Fresca Requerida", f"{res['Fruta_Requerida']:,.1f} kg/h")
col2.metric("Carga Térmica Total (Q)", f"{res['Q_Total']:,.0f} kJ/h")
col3.metric("Consumo Vapor Caldera", f"{res['Vapor_Caldera']:,.1f} kg/h")

st.subheader("📋 Tabla de Auditoría de Materia, Energía y Procesos")
st.dataframe(df, use_container_width=True)

st.subheader("🗺️ Diagrama de Flujo de Proceso (PFD)")
figura = generar_diagrama_detallado(res, w_bp, dist_evap1)
st.graphviz_chart(figura, use_container_width=True)
