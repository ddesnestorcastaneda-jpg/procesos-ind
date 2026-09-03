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
  pct_evap2 = 1
