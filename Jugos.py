import graphviz
import pandas as pd
import streamlit as st

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Auditoría de Proceso PFD", page_icon="🏭", layout="wide"
)

st.title("🏭 Auditoría Térmica y Balance de Materia/Energía")
st.markdown(
    "Modelo de Bypass Intermedio: Evaporación E1 basada en Agua Evaporada ➔"
    " Splitter ➔ Evaporación E2 basada en °Brix Objetivo ➔ Mezclador Final."
)

# --- 1. BARRA LATERAL: CONFIGURACIÓN DE PARÁMETROS ---
st.sidebar.header("🎯 1. Meta de Producción")
w_m_out = st.sidebar.number_input(
    "Producto Final Deseado (kg/h):", value=12500.0, step=500.0
)
w_bout = st.sidebar.number_input(
    "Brix Objetivo Final (°Brix):", value=60.0, step=1.0
)

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
    "Rendimiento de Jugo Clarificado (%):", 50.0, 95.0, 85.0, 0.5
)

st.sidebar.header("🔥 4. Evaporador 1 (Parámetros por Agua Evaporada)")
pct_agua_evap_e1 = st.sidebar.slider(
    "Agua Evaporada en E1 (% del agua de entrada):", 10.0, 80.0, 40.0, 1.0
)
pct_fuga_agua_e1 = st.sidebar.slider(
    "Fugas / Vapor Escapado E1 (%):", 0.0, 15.0, 2.0, 0.1
)
pct_limpia_agua_e1 = st.sidebar.slider(
    "Condensado Recuperado E1 (%):", 0.0, 100.0, 95.0, 1.0
)

st.sidebar.header("🔀 5. Splitter Intermedio (Post-E1)")
pct_bp_generado = st.sidebar.slider(
    "Porcentaje de Jugo de E1 enviado a Bypass (%):", 0.0, 50.0, 25.0, 1.0
)

st.sidebar.header("🔥 6. Evaporador 2 (Parámetro por Sólidos / °Brix)")
w_brix_e2 = st.sidebar.number_input(
    "Concentración Requerida a la Salida de E2 (°Brix):", value=68.0, step=1.0
)
pct_fuga_agua_e2 = st.sidebar.slider(
    "Fugas / Vapor Escapado E2 (%):", 0.0, 15.0, 2.0, 0.1
)
pct_limpia_agua_e2 = st.sidebar.slider(
    "Condensado Recuperado E2 (%):", 0.0, 100.0, 95.0, 1.0
)

st.sidebar.header("🌡️ 7. Operación Térmica & Caldera")
w_T_evap = st.sidebar.number_input(
    "Temp. Operación Evaporadores (°C):", value=100.0, step=1.0
)
lambda_vap_custom = st.sidebar.number_input(
    "Calor Latente Vapor Caldera (kJ/kg):", value=2257.0, step=10.0
)


# --- 🚨 VALIDACIÓN DE INCONSISTENCIAS Y ALERTA HUMORÍSTICA ---
def validar_parametros():
  errores = []
  if w_bin >= w_bout:
    errores.append(
        "• El Brix de la fruta fresca es mayor o igual al objetivo final"
        " (¡estás diluyendo o inflando sólidos de la nada!)."
    )
  if w_brix_jugo >= w_brix_e2:
    errores.append(
        "• La concentración del jugo clarificado supera la salida esperada del"
        " Evaporador 2."
    )
  if w_bout >= w_brix_e2:
    errores.append(
        "• El Brix de la salida de E2 debe ser superior al Brix Objetivo para"
        " permitir la mezcla con el Bypass."
    )
  if w_bout > 100 or w_bin <= 0 or w_brix_e2 > 100:
    errores.append(
        "• Estás sobrepasando los límites físicos del 100% de materia seca o"
        " ingresando valores menores o iguales a cero."
    )

  if errores:
    st.error(
        "🌌 💥 **¡ALERTA DE INCONSISTENCIA GRAVITACIONAL!**\n\n"
        "Estás violando las leyes naturales de la conservación de la materia y"
        " podrías destruir al universo.\n\n"
        + "\n".join(errores)
    )


validar_parametros()


# --- 2. CÁLCULO DEL BALANCE MATEMÁTICO ---
def ejecutar_balance_bypass_intermedio(
    m_prod_final,
    brix_in,
    brix_obj,
    merma_molino,
    brix_jugo,
    brix_bagazo,
    rend_jugo,
    pct_evap_e1_agua,
    pct_fuga_e1,
    pct_recup_e1,
    pct_bp_gen,
    brix_e2_target,
    pct_fuga_e2,
    pct_recup_e2,
    T_evap,
    lambda_vap,
):
  T_ref, T_in = 0.0, 25.0
  cp_agua = 4.184

  def calcular_cp(brix):
    return 4.184 * (1.0 - 0.0054 * brix)

  # Validación interna de resguardo para Brix
  if brix_e2_target <= brix_obj:
    brix_e2_target = brix_obj + 5.0

  # 1. Concentración de Salida del Evaporador 1 (E1)
  agua_in_e1 = 1.0 - (brix_jugo / 100.0)
  agua_evap_e1_unit = agua_in_e1 * (pct_evap_e1_agua / 100.0)
  masa_out_e1_unit = 1.0 - agua_evap_e1_unit
  brix_e1_out = (brix_jugo / 100.0) / masa_out_e1_unit * 100.0

  # 2. Mezclador Final: Relación entre Salida E2 y Cut-Back de E1
  if brix_e2_target > brix_obj and brix_e1_out < brix_obj:
    m_bp_mix = (
        m_prod_final
        * (brix_e2_target - brix_obj)
        / (brix_e2_target - brix_e1_out)
    )
    m_evap2_out = m_prod_final - m_bp_mix
  else:
    m_bp_mix = 0.0
    m_evap2_out = m_prod_final
    brix_e2_target = brix_obj

  # 3. Flujos en Evaporador 2
  solidos_e2 = m_evap2_out * (brix_e2_target / 100.0)
  m_evap2_in = solidos_e2 / (brix_e1_out / 100.0)
  m_vap2_total = m_evap2_in - m_evap2_out

  # 4. Flujos en Splitter y Evaporador 1
  pct_e2_linea = 100.0 - pct_bp_gen
  if pct_e2_linea <= 0:
    pct_e2_linea = 1.0

  m_e1_out_total = m_evap2_in / (pct_e2_linea / 100.0)
  m_bp_total_generado = m_e1_out_total * (pct_bp_gen / 100.0)
  m_bp_excedente = max(0.0, m_bp_total_generado - m_bp_mix)

  m_solidos_totales = m_e1_out_total * (brix_e1_out / 100.0)
  m_jugo_clarificado = m_solidos_totales / (brix_jugo / 100.0)

  # Evaporación real en E1
  agua_in_e1_total = m_jugo_clarificado * (1.0 - (brix_jugo / 100.0))
  m_vap1_total = agua_in_e1_total * (pct_evap_e1_agua / 100.0)

  # Fugas y Condensados E1 y E2
  m_vap1_fugas = m_vap1_total * (pct_fuga_e1 / 100.0)
  m_vap1_util = m_vap1_total - m_vap1_fugas
  m_agua_limpia_e1 = m_vap1_util * (pct_recup_e1 / 100.0)

  m_vap2_fugas = m_vap2_total * (pct_fuga_e2 / 100.0)
  m_vap2_util = m_vap2_total - m_vap2_fugas
  m_agua_limpia_e2 = m_vap2_util * (pct_recup_e2 / 100.0)

  m_vapor_fugas_tot = m_vap1_fugas + m_vap2_fugas
  m_agua_limpia_tot = m_agua_limpia_e1 + m_agua_limpia_e2
  m_vapor_util_tot = m_vap1_util + m_vap2_util

  # 5. Prensa y Molino
  m_pulpa_molida = m_jugo_clarificado / (rend_jugo / 100.0)
  m_bagazo = m_pulpa_molida - m_jugo_clarificado
  m_fruta = m_pulpa_molida / (1.0 - (merma_molino / 100.0))
  m_merma_molino = m_fruta * (merma_molino / 100.0)

  # Corrientes para tabla y diagrama
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
          "Pérdida Mecánica/Evaporativa",
      ),
      (
          "Pulpa Molida (Entrada Prensa)",
          m_pulpa_molida,
          brix_in,
          T_in,
          False,
          "Salida Molino",
      ),
      (
          "Bagazo Húmedo (Prensa)",
          m_bagazo,
          brix_bagazo,
          T_in,
          False,
          "Separación Mecánica",
      ),
      (
          "Jugo Clarificado Total",
          m_jugo_clarificado,
          brix_jugo,
          T_in,
          False,
          "Jugo Clarificado Extracción",
      ),
      (
          "Jugo Salida Evap 1",
          m_e1_out_total,
          brix_e1_out,
          T_evap,
          False,
          "Salida E1 / Entrada a Splitter",
      ),
      (
          "Jugo a Evaporador 2",
          m_evap2_in,
          brix_e1_out,
          T_evap,
          False,
          f"Línea a E2 ({pct_e2_linea:.0f}%)",
      ),
      (
          "Bypass Generado Post-E1",
          m_bp_total_generado,
          brix_e1_out,
          T_evap,
          False,
          f"Línea de Bypass ({pct_bp_gen:.0f}%)",
      ),
      (
          "Cut-Back al Mezclador",
          m_bp_mix,
          brix_e1_out,
          T_evap,
          False,
          "Ajuste Requerido a Mezcla Final",
      ),
      (
          "Bypass Excedente / Sobrante",
          m_bp_excedente,
          brix_e1_out,
          T_evap,
          False,
          "Sobrante Desviado de Proceso",
      ),
      (
          "Jugo Salida Evap 2",
          m_evap2_out,
          brix_e2_target,
          T_evap,
          False,
          "Jugo Súper Concentrado Salida E2",
      ),
      (
          "Vapor Útil / Evaporado Total",
          m_vapor_util_tot,
          0.0,
          T_evap,
          True,
          "Vapor Extraído Útil Total",
      ),
      (
          "Vapor Escapado / Fugas Totales",
          m_vapor_fugas_tot,
          0.0,
          T_evap,
          True,
          "Pérdidas de Vapor Totales",
      ),
      (
          "Agua Limpia Recuperada Total",
          m_agua_limpia_tot,
          0.0,
          T_evap,
          False,
          "Condensado Recuperado Total",
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
        "Entalpía Sp h (kJ/kg)": round(h, 2),
        "Flujo Entálpico H (kJ/h)": round(H_flujo, 2),
        "Tipo de Proceso Termodinámico": tipo_proc,
    })

  df_resultados = pd.DataFrame(filas_tabla)

  # Carga Térmica y Energía
  h_in_e1 = calcular_cp(brix_jugo) * T_in
  h_out_e1 = calcular_cp(brix_e1_out) * T_evap
  h_v = (cp_agua * T_evap) + lambda_vap

  Q_evap1 = (
      (m_e1_out_total * h_out_e1)
      + (m_vap1_total * h_v)
      - (m_jugo_clarificado * h_in_e1)
  )

  h_out_e2 = calcular_cp(brix_e2_target) * T_evap
  Q_evap2 = (
      (m_evap2_out * h_out_e2)
      + (m_vap2_total * h_v)
      - (m_evap2_in * h_out_e1)
  )

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


# --- 3. DIAGRAMA PFD EN GRAPHVIZ ---
def generar_diagrama_detallado(res, pct_bp, pct_e1_agua):
  c = res["corrientes"]
  pct_e2_linea = 100.0 - pct_bp
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
  dot.node("MOLINO", "MOLINO / TRITURADOR\n(Reducción & Merma)")
  dot.node("PRENSA", "PRENSA DE EXTRACCIÓN\n(Separación Sólido/Líquido)")
  dot.node("EVAP1", f"EVAPORADOR 1\n(Agua Evaporada: {pct_e1_agua:.0f}%)")
  dot.node(
      "SPLITTER",
      f"SPLITTER POST-E1\n(Línea E2: {pct_e2_linea:.0f}% / Bypass:"
      f" {pct_bp:.0f}%)",
      fillcolor="#2b6cb0",
      shape="diamond",
  )
  dot.node(
      "EVAP2",
      "EVAPORADOR 2\n(Conc. Requerida:"
      f" {c['Jugo Salida Evap 2']['brix']:.1f}°Brix)",
  )
  dot.node(
      "CONTROL_BP",
      "CONTROL DE CUT-BACK\n(Válvula Reguladora)",
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
        f" 💧 Ag/Liq: {m_liquido:,.1f} kg/h\n"
        f" 🧊 Sólidos: {m_solidos:,.1f} kg/h\n"
        f" T: {d['T']:.0f}°C | H: {d['H']:,.0f} kJ/h"
    )

  dot.node(
      "IN",
      f"ENTRADA: Fruta Requerida\n{fmt_lbl('Fruta Fresca Requerida')}",
      fillcolor="#c6f6d5",
  )
  dot.node(
      "MERMA",
      f"PÉRDIDA: Merma Molino\n{fmt_lbl('Merma de Peso Molino')}",
      fillcolor="#fed7d7",
  )
  dot.node(
      "BAGAZO",
      f"SALIDA: Bagazo Húmedo\n{fmt_lbl('Bagazo Húmedo (Prensa)')}",
      fillcolor="#feebc8",
  )
  dot.node(
      "EXCEDENTE",
      "EXCEDENTE BYPASS\n(Otro Proceso / Almacén)\n"
      f"{fmt_lbl('Bypass Excedente / Sobrante')}",
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
      "EVAP1",
      label=f" Jugo Clarificado\n{fmt_lbl('Jugo Clarificado Total')}",
      color="#2b6cb0",
  )

  dot.edge(
      "EVAP1",
      "SPLITTER",
      label=f" Jugo Pre-Concentrado E1\n{fmt_lbl('Jugo Salida Evap 1')}",
      color="#2b6cb0",
  )
  dot.edge(
      "SPLITTER",
      "EVAP2",
      label=(
          f" Jugo a Evap 2 ({pct_e2_linea:.0f}%)\n{fmt_lbl('Jugo a Evaporador"
          " 2')}"
      ),
      color="#2b6cb0",
  )
  dot.edge(
      "EVAP2",
      "MEZCLA",
      label=f" Jugo Conc. II\n{fmt_lbl('Jugo Salida Evap 2')}",
      color="#2b6cb0",
  )

  dot.edge(
      "SPLITTER",
      "CONTROL_BP",
      label=(
          f" Bypass Post-E1 ({pct_bp:.0f}%)\n"
          f"{fmt_lbl('Bypass Generado Post-E1')}"
      ),
      style="dashed",
      color="#dd6b20",
  )
  dot.edge(
      "CONTROL_BP",
      "MEZCLA",
      label=f" Cut-Back Requerido\n{fmt_lbl('Cut-Back al Mezclador')}",
      color="#2b6cb0",
  )
  dot.edge(
      "CONTROL_BP",
      "EXCEDENTE",
      label=" Sobrante Desviado",
      style="dashed",
      color="#dd6b20",
  )

  dot.edge("MEZCLA", "OUT", color="#2f855a", penwidth="2.5")

  dot.node(
      "FUGAS",
      "VAPOR ESCAPADO / FUGAS\n"
      f"{fmt_lbl('Vapor Escapado / Fugas Totales')}",
      fillcolor="#fed7d7",
      shape="note",
  )
  dot.node(
      "AGUA_LIMPIA",
      "AGUA LIMPIA RECUPERADA\n"
      f"{fmt_lbl('Agua Limpia Recuperada Total')}",
      fillcolor="#ebf8ff",
      shape="note",
  )

  dot.edge("EVAP1", "FUGAS", style="dotted", color="#e53e3e")
  dot.edge("EVAP1", "AGUA_LIMPIA", style="dotted", color="#3182ce")
  dot.edge("EVAP2", "FUGAS", style="dotted", color="#e53e3e")
  dot.edge("EVAP2", "AGUA_LIMPIA", style="dotted", color="#3182ce")

  return dot


# --- 4. EJECUCIÓN Y RENDERIZADO ---
df, res = ejecutar_balance_bypass_intermedio(
    w_m_out,
    w_bin,
    w_bout,
    w_merma_molino,
    w_brix_jugo,
    w_brix_bagazo,
    pct_rend_jugo,
    pct_agua_evap_e1,
    pct_fuga_agua_e1,
    pct_limpia_agua_e1,
    pct_bp_generado,
    w_brix_e2,
    pct_fuga_agua_e2,
    pct_limpia_agua_e2,
    w_T_evap,
    lambda_vap_custom,
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Fruta Fresca Requerida", f"{res['Fruta_Requerida']:,.1f} kg/h")
col2.metric(
    "Conc. Salida Evap 1",
    f"{res['corrientes']['Jugo Salida Evap 1']['brix']:.2f} °Brix",
)
col3.metric(
    "Cut-Back al Mezclador",
    f"{res['corrientes']['Cut-Back al Mezclador']['m']:,.1f} kg/h",
)
col4.metric("Consumo Vapor Caldera", f"{res['Vapor_Caldera']:,.1f} kg/h")

st.subheader("📋 Tabla de Auditoría de Materia, Energía y Procesos")
st.dataframe(df, use_container_width=True)

st.subheader("🗺️ Diagrama de Flujo de Proceso (PFD)")
figura = generar_diagrama_detallado(res, pct_bp_generado, pct_agua_evap_e1)
st.graphviz_chart(figura.source, use_container_width=True)
