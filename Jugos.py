import pandas as pd
import streamlit as st
import graphviz

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Auditoría de Proceso PFD", page_icon="🏭", layout="wide"
)

st.title("🏭 Auditoría Térmica y Balance de Materia/Energía")
st.markdown(
    "Simulador Avanzado con Evaporación por Porcentajes de Agua, Mermas y"
    " Cálculo Automático de Concentración Final."
)

# --- 1. BARRA LATERAL: CONFIGURACIÓN DE PARÁMETROS ---
st.sidebar.header("🎯 1. Meta de Producción")
w_m_out = st.sidebar.number_input(
    "Producto Final Deseado (kg/h):", value=4500.0, step=500.0
)
w_bout = st.sidebar.number_input("Brix Objetivo Final:", value=60.0, step=1.0)

st.sidebar.header("⚙️ 2. Molino / Triturador")
w_bin = st.sidebar.number_input("Brix Fruta Fresca:", value=12.0, step=0.5)
w_merma_molino = st.sidebar.slider(
    "Merma de Peso en Molino (%):", 0.0, 10.0, 2.0, 0.1
)

st.sidebar.header("🍇 3. Prensa de Extracción")
w_brix_jugo = st.sidebar.number_input(
    "Sólidos del Jugo Clarificado (°Brix):", value=12.5, step=0.1
)
w_brix_bagazo = st.sidebar.number_input(
    "Sólidos en Bagazo (°Brix):", value=4.0, step=0.5
)
pct_rend_jugo = st.sidebar.slider(
    "Rendimiento de Jugo Clarificado (% respecto a entrada prensa):",
    50.0,
    95.0,
    85.0,
    0.5,
)

st.sidebar.header("🔀 4. Divisor Principal & Bypass")
w_bp = st.sidebar.slider(
    "Bypass Generado en Divisor (%):", 0.0, 50.0, 30.0, 1.0
)

st.sidebar.header("🔥 5. Sistema de Evaporación (Basado en Facciones de Agua)")
pct_agua_evaporada = st.sidebar.slider(
    "Porcentaje de Agua que se Evapora (% respecto al agua de entrada):",
    0.0,
    90.0,
    75.0,
    1.0,
)
pct_agua_fuga = st.sidebar.slider(
    "Porcentaje de Agua que se Escapa / Fugas (%):", 0.0, 10.0, 1.5, 0.1
)
pct_agua_limpia = st.sidebar.slider(
    "Porcentaje de Agua Limpia / Condensado Recuperado (%):",
    0.0,
    100.0,
    95.0,
    1.0,
)

w_T_evap = st.sidebar.number_input(
    "Temp. Operación Evaporadores (°C):", value=100.0, step=1.0
)
dist_evap1 = st.sidebar.slider(
    "Carga de Evaporación E1 (%):", 10.0, 90.0, 55.0, 1.0
)

st.sidebar.header("💨 6. Caldera de Suministro")
lambda_vap_custom = st.sidebar.number_input(
    "Calor Latente Vapor Caldera (kJ/kg):", value=2257.0, step=10.0
)


# --- 2. CÁLCULO DEL BALANCE DE MATERIA Y ENERGÍA ---
def ejecutar_balance_avanzado(
    m_prod_final,
    brix_in,
    brix_obj,
    merma_molino,
    brix_jugo,
    brix_bagazo,
    rend_jugo,
    pct_bp,
    T_evap,
    pct_evap1,
    lambda_vap,
    pct_evap_agua,
    pct_fuga_agua,
    pct_limpia_agua,
):
  T_ref, T_in = 0.0, 25.0
  cp_agua = 4.184

  def calcular_cp(brix):
    return 4.184 * (1.0 - 0.0054 * brix)

  # Estimación iterativa del balance global a partir del producto final objetivo
  m_jugo_estimado = m_prod_final * (brix_obj / brix_jugo)

  if pct_bp >= 100.0:
    pct_bp = 99.0

  m_evap_in = m_jugo_estimado * (1.0 - (pct_bp / 100.0))
  m_bp_total = m_jugo_estimado * (pct_bp / 100.0)

  # Agua y Sólidos a la entrada del sistema de evaporación
  m_solidos_evap = m_evap_in * (brix_jugo / 100.0)
  m_agua_evap_in = m_evap_in - m_solidos_evap

  # Fracciones de agua calculadas
  m_agua_evaporada_util = m_agua_evap_in * (pct_evap_agua / 100.0)
  m_agua_escapada = m_agua_evap_in * (pct_fuga_agua / 100.0)
  m_agua_retirada_total = m_agua_evaporada_util + m_agua_escapada
  m_agua_limpia_recuperada = m_agua_evaporada_util * (pct_limpia_agua / 100.0)

  # Salida del Evaporador 2 y Cálculo de Concentración Final (brix_evap2_calc)
  m_agua_evap2_out = m_agua_evap_in - m_agua_retirada_total
  m_evap2_out = m_solidos_evap + m_agua_evap2_out

  if m_evap2_out > 0:
    brix_evap2_calc = (m_solidos_evap / m_evap2_out) * 100.0
  else:
    brix_evap2_calc = 100.0

  # Ajuste de Mezcla Cut-Back
  m_bp_mix = (
      m_prod_final
      * (brix_evap2_calc - brix_obj)
      / (brix_evap2_calc - brix_jugo)
  )
  if m_bp_mix < 0:
    m_bp_mix = 0.0
  m_bp_excedente = max(0.0, m_bp_total - m_bp_mix)

  # Prensa de Extracción
  m_jugo_total = m_evap_in + m_bp_total
  m_pulpa_molida = m_jugo_total / (rend_jugo / 100.0)
  m_bagazo = m_pulpa_molida - m_jugo_total

  # Molino / Triturador
  m_fruta = m_pulpa_molida / (1.0 - (merma_molino / 100.0))
  m_merma_molino = m_fruta * (merma_molino / 100.0)

  # Distribución Evaporador 1 y Evaporador 2
  pct_evap2 = 100.0 - pct_evap1
  m_vap1 = m_agua_retirada_total * (pct_evap1 / 100.0)
  m_vap2 = m_agua_retirada_total * (pct_evap2 / 100.0)

  m_evap1_out = m_evap_in - m_vap1
  brix_evap1_out = (m_solidos_evap / m_evap1_out) * 100.0

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
          "Merma de Peso Molino",
          m_merma_molino,
          brix_in,
          T_in,
          False,
          "Pérdida Mecánica/Evaporativa (Q≈0)",
      ),
      (
          "Pulpa Molida (Entrada Prensa)",
          m_pulpa_molida,
          brix_in,
          T_in,
          False,
          "Salida Molino a Prensado (Q≈0)",
      ),
      (
          "Bagazo Húmedo (Prensa)",
          m_bagazo,
          brix_bagazo,
          T_in,
          False,
          "Separación Mecánica Sólidos/Líquido",
      ),
      (
          "Jugo Clarificado Total",
          m_jugo_total,
          brix_jugo,
          T_in,
          False,
          "Jugo Clarificado Extracción",
      ),
      (
          "Jugo a Evaporador 1",
          m_evap_in,
          brix_jugo,
          T_in,
          False,
          "División Principal de Flujo (Q=0)",
      ),
      (
          "Bypass Total Generado",
          m_bp_total,
          brix_jugo,
          T_in,
          False,
          "División Principal de Flujo (Q=0)",
      ),
      (
          "Bypass Ajustado a Mezcla",
          m_bp_mix,
          brix_jugo,
          T_in,
          False,
          "Control de Cut-Back a Mezclador (Q=0)",
      ),
      (
          "Bypass Excedente / Otro Proceso",
          m_bp_excedente,
          brix_jugo,
          T_in,
          False,
          "Desvío a Almacenamiento/Otros (Q=0)",
      ),
      (
          "Vapor Evaporado Útil",
          m_agua_evaporada_util,
          0.0,
          T_evap,
          True,
          "Vapor Extraído del Sistema",
      ),
      (
          "Vapor Fuga / Escapado",
          m_agua_escapada,
          0.0,
          T_evap,
          True,
          "Pérdida de Vapor por Fugas",
      ),
      (
          "Agua Limpia / Condensado Recuperado",
          m_agua_limpia_recuperada,
          0.0,
          T_evap,
          False,
          "Condensado Recuperado del Proceso",
      ),
      (
          "Jugo Salida Evap 1",
          m_evap1_out,
          brix_evap1_out,
          T_evap,
          False,
          "Concentración Intermedia E1",
      ),
      (
          "Jugo Salida Evap 2",
          m_evap2_out,
          brix_evap2_calc,
          T_evap,
          False,
          "Concentración Calculada al Final del Evaporador",
      ),
      (
          "Producto Final Requerido",
          m_prod_final,
          brix_obj,
          60.0,
          False,
          "Mezclado Adiabático Final",
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
        "Entalpia Sp h (kJ/kg)": round(h, 2),
        "Flujo Entalpico H (kJ/h)": round(H_flujo, 2),
        "Tipo de Proceso Termodinamico": tipo_proc,
    })

  df_resultados = pd.DataFrame(filas_tabla)

  # Balances energéticos
  h_in_e1 = calcular_cp(brix_jugo) * T_in
  h_out_e1 = calcular_cp(brix_evap1_out) * T_evap
  h_v1 = (cp_agua * T_evap) + lambda_vap
  Q_evap1 = (m_evap1_out * h_out_e1) + (m_vap1 * h_v1) - (m_evap_in * h_in_e1)

  h_out_e2 = calcular_cp(brix_evap2_calc) * T_evap
  h_v2 = (cp_agua * T_evap) + lambda_vap
  Q_evap2 = (m_evap2_out * h_out_e2) + (m_vap2 * h_v2) - (m_evap1_out * h_out_e1)

  Q_total = Q_evap1 + Q_evap2
  m_vapor_caldera = Q_total / lambda_vap

  res_energia = {
      "Q_Evap1": Q_evap1,
      "Q_Evap2": Q_evap2,
      "Q_Total": Q_total,
      "Vapor_Caldera": m_vapor_caldera,
      "brix_evap2_calc": brix_evap2_calc,
      "corrientes": dict_corrientes,
      "Fruta_Requerida": m_fruta,
  }
  return df_resultados, res_energia


# --- 3. GENERADOR DE DIAGRAMA PFD EN GRAPHVIZ ---
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

  dot.attr(
      "node",
      shape="box",
      style="filled",
      fillcolor="#1a365d",
      fontcolor="white",
      fontname="Helvetica-Bold",
      fontsize="10",
  )
  dot.node("MOLINO", "MOLINO / TRITURADOR\n(Reduccion & Merma)")
  dot.node("PRENSA", "PRENSA DE EXTRACCION\n(Separacion Solido/Liquido)")
  dot.node(
      "DIV_PRINCIPAL",
      f"DIVISOR PRINCIPAL\n(Bypass: {pct_bp}%)",
      fillcolor="#2b6cb0",
      shape="diamond",
  )
  dot.node("EVAP1", f"EVAPORADOR 1\n(Carga: {pct_e1}%)")
  dot.node(
      "EVAP2",
      f"EVAPORADOR 2\n(Conc. Calculada:"
      f" {res['brix_evap2_calc']:.1f}°Brix)",
  )
  dot.node(
      "CONTROL_BP",
      "CONTROL DE BYPASS\n(Ajuste Cut-Back)",
      fillcolor="#2b6cb0",
      shape="diamond",
  )
  dot.node("MEZCLA", "MEZCLADOR FINAL\n(Mezclado Adiabatico)")

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
        f" 💧 Ag/Liq: {m_liquido:,.1f} kg/h\n"
        f" 🧊 Solidos: {m_solidos:,.1f} kg/h\n"
        f" T: {d['T']:.0f}°C | H: {d['H']:,.0f} kJ/h"
    )

  dot.node(
      "IN",
      f"ENTRADA: Fruta Requerida\n{fmt_lbl('Fruta Fresca Requerida')}",
      fillcolor="#c6f6d5",
  )
  dot.node(
      "MERMA",
      f"PERDIDA: Merma Molino\n{fmt_lbl('Merma de Peso Molino')}",
      fillcolor="#fed7d7",
  )
  dot.node(
      "BAGAZO",
      f"SALIDA: Bagazo Humedo\n{fmt_lbl('Bagazo Húmedo (Prensa)')}",
      fillcolor="#feebc8",
  )
  dot.node(
      "EXCEDENTE",
      (
          "EXCEDENTE BYPASS\n(Otro Proceso / Almacen)\n"
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

  dot.edge("IN", "MOLINO", color="#2f855a", penwidth="2")
  dot.edge("MOLINO", "MERMA", label=" Merma de Peso", color="#e53e3e")
  dot.edge(
      "MOLINO",
      "PRENSA",
      label=f" Pulpa Molida\n{fmt_lbl('Pulpa Molida (Entrada Prensa)')}",
      color="#2f855a",
  )
  dot.edge("PRENSA", "BAGAZO", label=" Bagazo Residual", color="#dd6b20")
  dot.edge(
      "PRENSA",
      "DIV_PRINCIPAL",
      label=f" Jugo Clarificado\n{fmt_lbl('Jugo Clarificado Total')}",
      color="#2b6cb0",
  )

  dot.edge(
      "DIV_PRINCIPAL",
      "EVAP1",
      label=f" Jugo a Evap 1\n{fmt_lbl('Jugo a Evaporador 1')}",
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

  # Fugas y Agua Limpia
  dot.node(
      "FUGAS",
      f"VAPOR ESCAPADO / FUGAS\n{fmt_lbl('Vapor Fuga / Escapado')}",
      fillcolor="#fed7d7",
      shape="note",
  )
  dot.node(
      "AGUA_LIMPIA",
      "AGUA LIMPIA"
      f" RECUPERADA\n{fmt_lbl('Agua Limpia / Condensado Recuperado')}",
      fillcolor="#ebf8ff",
      shape="note",
  )

  dot.edge("EVAP2", "FUGAS", style="dotted", color="#e53e3e", label=" Fugas")
  dot.edge(
      "EVAP2",
      "AGUA_LIMPIA",
      style="dotted",
      color="#3182ce",
      label=" Condensado",
  )

  return dot


# --- 4. EJECUCIÓN Y RENDERIZADO EN PANTALLA ---
df, res = ejecutar_balance_avanzado(
    w_m_out,
    w_bin,
    w_bout,
    w_merma_molino,
    w_brix_jugo,
    w_brix_bagazo,
    pct_rend_jugo,
    w_bp,
    w_T_evap,
    dist_evap1,
    lambda_vap_custom,
    pct_agua_evaporada,
    pct_agua_fuga,
    pct_agua_limpia,
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Fruta Fresca Requerida", f"{res['Fruta_Requerida']:,.1f} kg/h")
col2.metric("Concentración Salida Evaporador", f"{res['brix_evap2_calc']:.2f} °Brix")
col3.metric("Carga Térmica Total (Q)", f"{res['Q_Total']:,.0f} kJ/h")
col4.metric("Consumo Vapor Caldera", f"{res['Vapor_Caldera']:,.1f} kg/h")

st.subheader("📋 Tabla de Auditoría de Materia, Energía y Procesos")
st.dataframe(df, use_container_width=True)

st.subheader("🗺️ Diagrama de Flujo de Proceso (PFD)")
figura = generar_diagrama_detallado(res, w_bp, dist_evap1)

st.graphviz_chart(figura.source, use_container_width=True)
