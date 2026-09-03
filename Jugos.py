import graphviz
import pandas as pd
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Auditoría de Proceso PFD", page_icon="🏭", layout="wide"
)

st.title("🏭 Auditoría Térmica y Balance de Materia/Energía")
st.markdown(
    "Simulador de Planta de Concentración de Jugo para Prácticas de Ingeniería."
)


# --- 1. LÓGICA DE CÁLCULO ---
def ejecutar_balance_completo(m_fruta, brix_in, brix_obj, pct_bp, pct_bag):
  T_ref, T_in, T_evap = 0.0, 25.0, 100.0
  lambda_vap = 2257.0
  cp_agua = 4.184

  def calcular_cp(brix):
    return 4.184 * (1.0 - 0.0054 * brix)

  m_bagazo = m_fruta * (pct_bag / 100.0)
  m_jugo = m_fruta - m_bagazo
  brix_jugo = brix_in

  solidos_totales = m_jugo * (brix_jugo / 100.0)
  m_prod_final = solidos_totales / (brix_obj / 100.0)
  m_agua_total_evaporada = m_jugo - m_prod_final

  m_bypass = m_jugo * (pct_bp / 100.0)
  m_evap1_in = m_jugo - m_bypass

  m_vap1 = m_agua_total_evaporada * 0.55
  m_vap2 = m_agua_total_evaporada * 0.45

  m_evap1_out = m_evap1_in - m_vap1
  brix_evap1_out = (
      (m_evap1_in * (brix_jugo / 100.0)) / m_evap1_out
  ) * 100.0

  m_evap2_out = m_evap1_out - m_vap2
  brix_evap2_out = (
      (m_evap1_in * (brix_jugo / 100.0)) / m_evap2_out
  ) * 100.0

  corrientes = [
      (
          "Fruta Fresca",
          m_fruta,
          brix_in,
          T_in,
          False,
          "Entrada Isostática / Referencia",
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
          "Jugo Prensa",
          m_jugo,
          brix_jugo,
          T_in,
          False,
          "Separación Mecánica (Isotérmico, Q≈0)",
      ),
      (
          "Jugo a Evap 1",
          m_evap1_in,
          brix_jugo,
          T_in,
          False,
          "División de Flujo / Divisor Adiabático (Q=0)",
      ),
      (
          "Bypass",
          m_bypass,
          brix_jugo,
          T_in,
          False,
          "División de Flujo / Divisor Adiabático (Q=0)",
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
          brix_evap2_out,
          T_evap,
          False,
          "Transferencia Térmica No Adiabática (Q > 0)",
      ),
      (
          "Producto Final",
          m_prod_final,
          brix_obj,
          60.0,
          False,
          "Mezclado Adiabático (Q=0, Espontáneo)",
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
        "Flujo Masico (kg/h)": round(m, 2),
        "Sólidos (°Brix)": round(brix, 2),
        "Temp (°C)": round(T, 1),
        "Cp (kJ/kg·°C)": round(cp, 3),
        "Entalpía Sp h (kJ/kg)": round(h, 2),
        "Flujo Entálpico H (kJ/h)": round(H_flujo, 2),
        "Tipo de Proceso Termodinámico": tipo_proc,
    })

  df_resultados = pd.DataFrame(filas_tabla)

  h_in_e1 = calcular_cp(brix_jugo) * T_in
  h_out_e1 = calcular_cp(brix_evap1_out) * T_evap
  h_v1 = (cp_agua * T_evap) + lambda_vap
  Q_evap1 = (m_evap1_out * h_out_e1) + (m_vap1 * h_v1) - (m_evap1_in * h_in_e1)

  h_out_e2 = calcular_cp(brix_evap2_out) * T_evap
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
  }
  return df_resultados, res_energia


def generar_diagrama_detallado(m_fruta, brix_in, brix_obj, pct_bp, res):
  c = res["corrientes"]
  dot = graphviz.Digraph(comment="PFD Detallado", format="png")
  dot.attr(
      rankdir="LR",
      size="16",
      nodesep="0.6",
      ranksep="1.2",
      fontname="Helvetica",
  )

  dot.attr(
      "node",
      shape="box",
      style="filled",
      fillcolor="#1a365d",
      fontcolor="white",
      fontname="Helvetica-Bold",
      fontsize="10",
  )
  dot.node("MOLINO", "MOLINO Y PRENSA\n(Sep. Mecánica / Isotérmico)")
  dot.node("EVAP1", "EVAPORADOR 1\n(Calentamiento / No Adiabático)")
  dot.node(
      "SPLIT",
      "DESVÍO\n(Divisor Adiabático)",
      fillcolor="#2b6cb0",
      shape="diamond",
  )
  dot.node("EVAP2", "EVAPORADOR 2\n(Calentamiento / No Adiabático)")
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
    return (
        f" m: {d['m']:,.1f} kg/h | T: {d['T']:.0f}°C\n"
        f" Proc: {d['tipo_proc']}\n"
        f" H: {d['H']:,.0f} kJ/h"
    )

  dot.node(
      "IN",
      f"ENTRADA: Fruta Fresca\n{fmt_lbl('Fruta Fresca')}",
      fillcolor="#c6f6d5",
  )
  dot.node(
      "BAGAZO",
      f"SALIDA: Torta Bagazo\n{fmt_lbl('Torta Bagazo')}",
      fillcolor="#feebc8",
  )
  dot.node(
      "OUT",
      f"PRODUCTO FINAL\n{fmt_lbl('Producto Final')}",
      fillcolor="#9ae6b4",
      shape="doublerectangle",
  )

  dot.edge("IN", "MOLINO", color="#2f855a", penwidth="2")
  dot.edge("MOLINO", "BAGAZO", label=" Bagazo", color="#dd6b20")
  dot.edge(
      "MOLINO",
      "EVAP1",
      label=f" Jugo Clarificado\n{fmt_lbl('Jugo Prensa')}",
      color="#2b6cb0",
  )
  dot.edge("EVAP1", "SPLIT", label=" Mezcla Concentrada I", color="#2b6cb0")
  dot.edge(
      "SPLIT",
      "EVAP2",
      label=f" Al Evap 2\n{fmt_lbl('Jugo a Evap 1')}",
      color="#2b6cb0",
  )
  dot.edge(
      "SPLIT",
      "MEZCLA",
      label=f" Bypass ({pct_bp}%)\n{fmt_lbl('Bypass')}",
      style="dashed",
      color="#dd6b20",
  )
  dot.edge(
      "EVAP2",
      "MEZCLA",
      label=f" Salida Evap 2\n{fmt_lbl('Jugo Salida Evap 2')}",
      color="#2b6cb0",
  )
  dot.edge("MEZCLA", "OUT", color="#2f855a", penwidth="2.5")

  dot.node(
      "VAP1",
      f"VAPOR GENERADO 1\n{fmt_lbl('Vapor Evap 1')}",
      fillcolor="#e2e8f0",
      shape="note",
  )
  dot.node(
      "VAP2",
      f"VAPOR GENERADO 2\n{fmt_lbl('Vapor Evap 2')}",
      fillcolor="#e2e8f0",
      shape="note",
  )
  dot.edge("EVAP1", "VAP1", style="dotted", color="#718096")
  dot.edge("EVAP2", "VAP2", style="dotted", color="#718096")

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


# --- 2. BARRA LATERAL (CONTROLES) ---
st.sidebar.header("⚙️ Parámetros del Sistema")
w_m = st.sidebar.number_input("Masa Fruta (kg/h):", value=25000.0, step=1000.0)
w_bin = st.sidebar.number_input("Brix Fruta:", value=12.0, step=0.5)
w_bout = st.sidebar.number_input("Brix Obj:", value=60.0, step=1.0)
w_bp = st.sidebar.number_input("% Bypass:", value=30.0, step=5.0)
w_bag = st.sidebar.number_input("% Bagazo:", value=10.0, step=1.0)

# --- 3. RENDERING EN STREAMLIT ---
df, res = ejecutar_balance_completo(w_m, w_bin, w_bout, w_bp, w_bag)

# Métricas rápidas arriba
col1, col2, col3 = st.columns(3)
col1.metric("Carga Térmica Total (Q)", f"{res['Q_Total']:,.0f} kJ/h")
col2.metric("Consumo Vapor Caldera", f"{res['Vapor_Caldera']:,.1f} kg/h")
col3.metric("Jugo Concentrado Final", f"{res['corrientes']['Producto Final']['m']:,.1f} kg/h")

st.subheader("📋 Tabla de Auditoría de Materia, Energía y Procesos")
st.dataframe(df, use_container_width=True)

st.subheader("🗺️ Diagrama de Flujo de Proceso (PFD)")
figura = generar_diagrama_detallado(w_m, w_bin, w_bout, w_bp, res)
st.graphviz_chart(figura, use_container_width=True)
