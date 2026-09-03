import graphviz
import pandas as pd
import streamlit as st

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Auditoría Industrial de Concentrados",
    page_icon="🏭",
    layout="wide",
)

st.title("🏭 Auditoría Térmica, Energética y Económica de Proceso")
st.markdown(
    "Modelo con Control Adaptativo de Cut-Back, Eficiencia de Maquinaria"
    " ($\eta$) y Balance de Frontera Físico Estricto."
)

# --- 1. BARRA LATERAL: CONFIGURACIÓN DE PARÁMETROS ---
st.sidebar.header("🎯 1. Meta de Producción")
w_m_out = st.sidebar.number_input(
    "Producto Final Deseado (kg/h):", value=10000.0, step=500.0
)
w_bout = st.sidebar.number_input(
    "Brix Objetivo Final (°Brix):", value=60.0, step=1.0
)

st.sidebar.header("🍇 2. Fruta & Extracción")
w_bin = st.sidebar.number_input("Brix Fruta Fresca:", value=11.5, step=0.5)
w_merma_molino = st.sidebar.slider(
    "Merma de Peso en Molino (%):", 0.0, 10.0, 2.0, 0.1
)
w_brix_jugo = st.sidebar.number_input(
    "Sólidos del Jugo Clarificado (°Brix):", value=12.0, step=0.1
)
w_brix_bagazo = st.sidebar.number_input(
    "Sólidos en Bagazo (°Brix):", value=4.0, step=0.5
)
pct_rend_jugo = st.sidebar.slider(
    "Rendimiento de Jugo Clarificado (%):", 30.0, 95.0, 85.0, 0.5
)

st.sidebar.header("🔥 3. Evaporador 1 (Agua Evaporada)")
pct_agua_evap_e1 = st.sidebar.slider(
    "Agua Evaporada en E1 (% del agua de entrada):", 10.0, 80.0, 40.0, 1.0
)
pct_fuga_agua_e1 = st.sidebar.slider(
    "Fugas / Vapor Escapado E1 (%):", 0.0, 15.0, 2.0, 0.1
)
pct_limpia_agua_e1 = st.sidebar.slider(
    "Condensado Recuperado E1 (%):", 0.0, 100.0, 95.0, 1.0
)

st.sidebar.header("🔀 4. Splitter Intermedio (Post-E1)")
pct_bp_generado = st.sidebar.slider(
    "Porcentaje de Jugo de E1 enviado a Bypass (%):", 0.0, 50.0, 25.0, 1.0
)

st.sidebar.header("🔥 5. Evaporador 2 (Sólidos Objetivo)")
w_brix_e2 = st.sidebar.number_input(
    "Concentración Salida Evaporador 2 (°Brix):", value=68.0, step=1.0
)
pct_fuga_agua_e2 = st.sidebar.slider(
    "Fugas / Vapor Escapado E2 (%):", 0.0, 15.0, 2.0, 0.1
)
pct_limpia_agua_e2 = st.sidebar.slider(
    "Condensado Recuperado E2 (%):", 0.0, 100.0, 95.0, 1.0
)

st.sidebar.header("⚙️ 6. Eficiencias de Maquinaria (η)")
eta_caldera = (
    st.sidebar.slider("Eficiencia Térmica Caldera (%):", 50.0, 100.0, 85.0, 1.0)
    / 100.0
)
eta_molino = (
    st.sidebar.slider(
        "Eficiencia Mecánica Molino (%):", 50.0, 100.0, 82.0, 1.0
    )
    / 100.0
)
eta_prensa = (
    st.sidebar.slider(
        "Eficiencia Mecánica Prensa (%):", 50.0, 100.0, 78.0, 1.0
    )
    / 100.0
)

st.sidebar.header("💰 7. Parámetros Económicos ($)")
p_fruta = st.sidebar.number_input("Costo Fruta ($/kg):", value=0.25, step=0.01)
p_vapor = st.sidebar.number_input(
    "Costo Vapor ($/tonelada):", value=30.0, step=1.0
) / 1000.0
p_elec = st.sidebar.number_input("Tarifa Eléctrica ($/kWh):", value=0.12, step=0.01)
p_prod = st.sidebar.number_input(
    "Precio Venta Concentrado ($/kg):", value=1.80, step=0.05
)

w_T_evap = st.sidebar.number_input(
    "Temp. Operación Evaporadores (°C):", value=100.0, step=1.0
)
lambda_vap_custom = st.sidebar.number_input(
    "Calor Latente Vapor Caldera (kJ/kg):", value=2257.0, step=10.0
)


# --- 2. CÁLCULO DEL BALANCE MATEMÁTICO CON VALIDACIÓN FÍSICA ---
def ejecutar_balance_completo():
  T_ref, T_in = 0.0, 25.0
  cp_agua = 4.184

  def calcular_cp(brix):
    return 4.184 * (1.0 - 0.0054 * brix)

  # 1. Salida Evaporador 1 (E1)
  agua_in_e1 = 1.0 - (w_brix_jugo / 100.0)
  agua_evap_e1_unit = agua_in_e1 * (pct_agua_evap_e1 / 100.0)
  masa_out_e1_unit = 1.0 - agua_evap_e1_unit
  brix_e1_out = (w_brix_jugo / 100.0) / masa_out_e1_unit * 100.0

  # Ajuste de seguridad para E2
  brix_e2 = max(w_brix_e2, w_bout + 0.1)

  # 2. Despeje en Mezclador y Control de Límite Físico de Bypass
  # Fracción de bypass teórica requerida para llegar a brix_obj
  frac_bp_req = (brix_e2 - w_bout) / (brix_e2 - brix_e1_out)
  frac_bp_gen = pct_bp_generado / 100.0

  if frac_bp_req > frac_bp_gen:
    # LÍMITE FÍSICO ALCANZADO: El mezclador exige más bypass del disponible
    m_bp_mix = w_m_out * frac_bp_gen
    m_evap2_out = w_m_out - m_bp_mix
    m_bp_excedente = 0.0
    # Recalculamos el Brix final real (será mayor al objetivo debido a la falta de bypass diluyente)
    brix_final_real = (
        m_evap2_out * (brix_e2 / 100.0) + m_bp_mix * (brix_e1_out / 100.0)
    ) / w_m_out * 100.0
  else:
    # CASO NORMAL: El bypass alcanza y sobra
    m_bp_mix = w_m_out * frac_bp_req
    m_evap2_out = w_m_out - m_bp_mix
    brix_final_real = w_bout

  # 3. Flujos en Evaporador 2 y Splitter
  solidos_e2 = m_evap2_out * (brix_e2 / 100.0)
  m_evap2_in = solidos_e2 / (brix_e1_out / 100.0)
  m_vap2_total = m_evap2_in - m_evap2_out

  pct_e2_linea = 100.0 - pct_bp_generado
  m_e1_out_total = (
      m_evap2_in / (pct_e2_linea / 100.0) if pct_e2_linea > 0 else m_evap2_in
  )
  m_bp_total_generado = m_e1_out_total * frac_bp_gen

  if frac_bp_req <= frac_bp_gen:
    m_bp_excedente = m_bp_total_generado - m_bp_mix

  # 4. Flujos en Evaporador 1, Prensa y Molino
  solidos_totales = m_e1_out_total * (brix_e1_out / 100.0)
  m_jugo_clarificado = solidos_totales / (w_brix_jugo / 100.0)

  agua_in_e1_total = m_jugo_clarificado * (1.0 - (w_brix_jugo / 100.0))
  m_vap1_total = agua_in_e1_total * (pct_agua_evap_e1 / 100.0)

  # Fugas y Condensados
  m_vap1_fugas = m_vap1_total * (pct_fuga_agua_e1 / 100.0)
  m_vap1_util = m_vap1_total - m_vap1_fugas
  m_agua_limpia_e1 = m_vap1_util * (pct_limpia_agua_e1 / 100.0)

  m_vap2_fugas = m_vap2_total * (pct_fuga_agua_e2 / 100.0)
  m_vap2_util = m_vap2_total - m_vap2_fugas
  m_agua_limpia_e2 = m_vap2_util * (pct_limpia_agua_e2 / 100.0)

  m_pulpa_molida = m_jugo_clarificado / (pct_rend_jugo / 100.0)
  m_bagazo = m_pulpa_molida - m_jugo_clarificado
  m_fruta = m_pulpa_molida / (1.0 - (w_merma_molino / 100.0))
  m_merma_molino = m_fruta * (w_merma_molino / 100.0)

  # 5. Energías Termodinámicas y Eficiencias de Máquinas
  h_in_e1 = calcular_cp(w_brix_jugo) * T_in
  h_out_e1 = calcular_cp(brix_e1_out) * w_T_evap
  h_v = (cp_agua * w_T_evap) + lambda_vap_custom

  Q_evap1_neto = (
      (m_e1_out_total * h_out_e1)
      + (m_vap1_total * h_v)
      - (m_jugo_clarificado * h_in_e1)
  )
  h_out_e2 = calcular_cp(brix_e2) * w_T_evap
  Q_evap2_neto = (
      (m_evap2_out * h_out_e2)
      + (m_vap2_total * h_v)
      - (m_evap2_in * h_out_e1)
  )

  Q_total_neto = Q_evap1_neto + Q_evap2_neto
  m_vap_neto = Q_total_neto / lambda_vap_custom

  # Aplicando Eficiencia Térmica de Caldera
  Q_total_bruto = Q_total_neto / eta_caldera
  m_vap_bruto_caldera = m_vap_neto / eta_caldera

  # Potencias Eléctricas (Brutas vs Netas)
  kWh_neto_molino = (m_fruta / 1000.0) * 15.0
  kWh_bruto_molino = kWh_neto_molino / eta_molino

  kWh_neto_prensa = (m_pulpa_molida / 1000.0) * 22.0
  kWh_bruto_prensa = kWh_neto_prensa / eta_prensa

  kWh_bruto_total = kWh_bruto_molino + kWh_bruto_prensa

  # 6. Costos y Balance Económico
  costo_mp = m_fruta * p_fruta
  costo_vapor = m_vap_bruto_caldera * p_vapor
  costo_elec = kWh_bruto_total * p_elec
  costo_opex_total = costo_mp + costo_vapor + costo_elec

  ingresos_venta = w_m_out * p_prod
  margen_operativo = ingresos_venta - costo_opex_total
  costo_unitario_kg = costo_opex_total / w_m_out

  corrientes = [
      (
          "Fruta Fresca Requerida",
          m_fruta,
          w_bin,
          T_in,
          False,
          "Entrada Isostática / Calculada",
      ),
      (
          "Merma de Peso Molino",
          m_merma_molino,
          w_bin,
          T_in,
          False,
          "Pérdida Mecánica/Evaporativa",
      ),
      (
          "Pulpa Molida (Entrada Prensa)",
          m_pulpa_molida,
          w_bin,
          T_in,
          False,
          "Salida Molino",
      ),
      (
          "Bagazo Húmedo (Prensa)",
          m_bagazo,
          w_brix_bagazo,
          T_in,
          False,
          "Separación Mecánica",
      ),
      (
          "Jugo Clarificado Total",
          m_jugo_clarificado,
          w_brix_jugo,
          T_in,
          False,
          "Jugo Clarificado Extracción",
      ),
      (
          "Jugo Salida Evap 1",
          m_e1_out_total,
          brix_e1_out,
          w_T_evap,
          False,
          "Salida E1 / Entrada a Splitter",
      ),
      (
          "Jugo a Evaporador 2",
          m_evap2_in,
          brix_e1_out,
          w_T_evap,
          False,
          f"Línea a E2 ({pct_e2_linea:.0f}%)",
      ),
      (
          "Bypass Generado Post-E1",
          m_bp_total_generado,
          brix_e1_out,
          w_T_evap,
          False,
          f"Línea de Bypass ({pct_bp_generado:.0f}%)",
      ),
      (
          "Cut-Back al Mezclador",
          m_bp_mix,
          brix_e1_out,
          w_T_evap,
          False,
          "Ajuste Requerido a Mezcla Final",
      ),
      (
          "Bypass Excedente / Sobrante",
          m_bp_excedente,
          brix_e1_out,
          w_T_evap,
          False,
          "Sobrante Desviado de Proceso",
      ),
      (
          "Jugo Salida Evap 2",
          m_evap2_out,
          brix_e2,
          w_T_evap,
          False,
          "Jugo Súper Concentrado Salida E2",
      ),
      (
          "Producto Final Requerido",
          w_m_out,
          brix_final_real,
          60.0,
          False,
          "Mezclado Adiabático Final",
      ),
  ]

  filas_tabla = []
  dict_corrientes = {}
  for nombre, m, brix, T, es_vapor, tipo_proc in corrientes:
    cp = cp_agua if es_vapor else calcular_cp(brix)
    h = ((cp_agua * (T - T_ref)) + lambda_vap_custom) if es_vapor else cp * (T - T_ref)
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
        "Flujo Entálpico H (kJ/h)": round(H_flujo, 2),
        "Tipo de Proceso": tipo_proc,
    })

  df_res = pd.DataFrame(filas_tabla)

  res_kpis = {
      "Fruta_Requerida": m_fruta,
      "Brix_E1": brix_e1_out,
      "Brix_Final_Real": brix_final_real,
      "Vapor_Bruto": m_vap_bruto_caldera,
      "Elec_Bruta": kWh_bruto_total,
      "Costo_MP": costo_mp,
      "Costo_Vapor": costo_vapor,
      "Costo_Elec": costo_elec,
      "OPEX_Total": costo_opex_total,
      "Margen_Bruto": margen_operativo,
      "Costo_Unitario": costo_unitario_kg,
      "corrientes": dict_corrientes,
  }
  return df_res, res_kpis


# --- 3. DIAGRAMA PFD GRAPHVIZ ---
def generar_diagrama(res):
  c = res["corrientes"]
  dot = graphviz.Digraph(comment="PFD Completo", format="png")
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
  dot.node("MOLINO", "MOLINO / TRITURADOR")
  dot.node("PRENSA", "PRENSA DE EXTRACCIÓN")
  dot.node(
      "EVAP1", f"EVAPORADOR 1\n(Agua Evap: {pct_agua_evap_e1:.0f}%)"
  )
  dot.node(
      "SPLITTER",
      f"SPLITTER POST-E1\n(Bypass: {pct_bp_generado:.0f}%)",
      fillcolor="#2b6cb0",
      shape="diamond",
  )
  dot.node("EVAP2", f"EVAPORADOR 2\n(Salida: {w_brix_e2:.1f}°Brix)")
  dot.node(
      "CONTROL_BP",
      "CONTROL DE CUT-BACK",
      fillcolor="#2b6cb0",
      shape="diamond",
  )
  dot.node("MEZCLA", "MEZCLADOR FINAL")

  dot.attr(
      "node",
      shape="rectangle",
      style="filled,rounded",
      fillcolor="#edf2f7",
      fontcolor="#1a202c",
      fontname="Helvetica",
      fontsize="8.5",
  )

  def fmt(nombre):
    d = c[nombre]
    return f" Total: {d['m']:,.1f} kg/h | Conc: {d['brix']:.1f} °Brix"

  dot.node("IN", f"ENTRADA: Fruta\n{fmt('Fruta Fresca Requerida')}", fillcolor="#c6f6d5")
  dot.node("OUT", f"PRODUCTO FINAL\n{fmt('Producto Final Requerido')}", fillcolor="#9ae6b4", shape="doublerectangle")

  dot.edge("IN", "MOLINO")
  dot.edge("MOLINO", "PRENSA", label=f" Pulpa\n{fmt('Pulpa Molida (Entrada Prensa)')}")
  dot.edge("PRENSA", "EVAP1", label=f" Jugo Clarificado\n{fmt('Jugo Clarificado Total')}")
  dot.edge("EVAP1", "SPLITTER", label=f" Jugo E1\n{fmt('Jugo Salida Evap 1')}")
  dot.edge("SPLITTER", "EVAP2", label=f" Línea E2\n{fmt('Jugo a Evaporador 2')}")
  dot.edge("EVAP2", "MEZCLA", label=f" Conc E2\n{fmt('Jugo Salida Evap 2')}")
  dot.edge("SPLITTER", "CONTROL_BP", label=" Bypass Generado", style="dashed")
  dot.edge("CONTROL_BP", "MEZCLA", label=f" Cut-Back\n{fmt('Cut-Back al Mezclador')}")
  dot.edge("MEZCLA", "OUT")

  return dot


# --- 4. EJECUCIÓN Y TABLEROS DE RESULTADOS ---
df, kpis = ejecutar_balance_completo()

if kpis["Brix_Final_Real"] > w_bout:
  st.warning(
      f"⚠️ **ADVERTENCIA DE FRONTERA FÍSICA:** El bypass disponible no es"
      f" suficiente para diluir la alta concentración de E2 ({w_brix_e2}°Brix)."
      f" La concentración final real del producto subió a"
      f" **{kpis['Brix_Final_Real']:.2f}°Brix**."
  )

col1, col2, col3, col4 = st.columns(4)
col1.metric("Fruta Fresca Requerida", f"{kpis['Fruta_Requerida']:,.1f} kg/h")
col2.metric("Vapor Bruto Caldera (η)", f"{kpis['Vapor_Bruto']:,.1f} kg/h")
col3.metric("Electricidad Bruta (η)", f"{kpis['Elec_Bruta']:,.1f} kWh/h")
col4.metric("Costo Unitario", f"${kpis['Costo_Unitario']:.3f} / kg")

st.subheader("💰 Balance Económico de Operación (OPEX / Hora)")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Costo Fruta", f"${kpis['Costo_MP']:,.2f} / h")
m2.metric("Costo Vapor", f"${kpis['Costo_Vapor']:,.2f} / h")
m3.metric("Costo Electricidad", f"${kpis['Costo_Elec']:,.2f} / h")
m4.metric("Margen Operativo Bruto", f"${kpis['Margen_Bruto']:,.2f} / h")

st.subheader("📋 Auditoría de Materia, Energía y Procesos")
st.dataframe(df, use_container_width=True)

st.subheader("🗺️ Diagrama PFD de Proceso")
figura = generar_diagrama(kpis)
st.graphviz_chart(figura.source, use_container_width=True)
