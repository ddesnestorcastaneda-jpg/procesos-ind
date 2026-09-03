import pandas as pd
import streamlit as st

# Opcional: import graphviz si está instalado en tu entorno local

st.set_page_config(
    page_title="Auditoría de Proceso PFD", page_icon="🏭", layout="wide"
)

st.title("🏭 Auditoría Térmica y Balance de Materia/Energía")
st.markdown(
    "Simulador Avanzado con Merma en Molino y Balance Completo de Sólidos en"
    " Prensado."
)

# --- 1. BARRA LATERAL: CONFIGURACIÓN POR ETAPAS ---
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
    "Rendimiento de Jugo Clarificado (% respecto a entrada de prensa):",
    50.0,
    95.0,
    85.0,
    0.5,
)

st.sidebar.header("🔀 4. Divisor Principal & Bypass")
w_bp = st.sidebar.slider(
    "Bypass Generado en Divisor (%):", 0.0, 50.0, 30.0, 1.0
)

st.sidebar.header("🔥 5. Sistema de Evaporación")
w_brix_e2 = st.sidebar.number_input(
    "Concentración Salida Evaporador 2 (°Brix):", value=68.0, step=1.0
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


# --- 2. LÓGICA DE CÁLCULO ---
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
    brix_evap2_target,
):
  T_ref, T_in = 0.0, 25.0
  cp_agua = 4.184

  def calcular_cp(brix):
    return 4.184 * (1.0 - 0.0054 * brix)

  if brix_evap2_target <= brix_obj:
    brix_evap2_target = brix_obj + 1.0

  # 1. Balance en Mezclador Final (Mixer)
  # m_evap2_out * brix_evap2_target + m_bp_mix * brix_jugo = m_prod_final * brix_obj
  m_bp_mix = (
      m_prod_final
      * (brix_evap2_target - brix_obj)
      / (brix_evap2_target - brix_jugo)
  )
  m_evap2_out = m_prod_final - m_bp_mix

  solidos_evap = m_evap2_out * (brix_evap2_target / 100.0)
  m_evap_in = solidos_evap / (brix_jugo / 100.0)

  # 2. Divisor Principal
  if pct_bp >= 100.0:
    pct_bp = 99.0

  m_jugo_total = m_evap_in / (1.0 - (pct_bp / 100.0))
  m_bp_total = m_jugo_total * (pct_bp / 100.0)

  if m_bp_total < m_bp_mix:
    m_bp_total = m_bp_mix
    m_jugo_total = m_evap_in + m_bp_total
    pct_bp = (m_bp_total / m_jugo_total) * 100.0

  m_bp_excedente = m_bp_total - m_bp_mix

  # 3. Balance de Prensa
  # Jugo clarificado total extraído
  # m_jugo_total = m_pulpa_molida * (rend_jugo / 100)
  m_pulpa_molida = m_jugo_total / (rend_jugo / 100.0)
  m_bagazo = m_pulpa_molida - m_jugo_total

  # 4. Balance de Molino
  # m_pulpa_molida = m_fruta * (1 - merma_molino/100)
  m_fruta = m_pulpa_molida / (1.0 - (merma_molino / 100.0))
  m_merma_molino = m_fruta * (merma_molino / 100.0)

  # 5. Evaporadores
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
  h_in_e1 = calcular_cp(brix_jugo) * T_in
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


# --- 3. RENDERING PRINCIPAL ---
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
    w_brix_e2,
)

col1, col2, col3 = st.columns(3)
col1.metric("Fruta Fresca Requerida", f"{res['Fruta_Requerida']:,.1f} kg/h")
col2.metric("Carga Térmica Total (Q)", f"{res['Q_Total']:,.0f} kJ/h")
col3.metric("Consumo Vapor Caldera", f"{res['Vapor_Caldera']:,.1f} kg/h")

st.subheader("📋 Tabla de Auditoría de Materia, Energía y Procesos")
st.dataframe(df, use_container_width=True)
