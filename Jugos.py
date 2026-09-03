st.sidebar.header("🍇 Selección de Fruta / Materia Prima")
fruta_sel = st.sidebar.selectbox(
    "Selecciona el tipo de fruta:",
    ["Personalizado", "Naranja", "Uva", "Manzana", "Maracuyá"],
)

# Valores por defecto dinámicos según la fruta
if fruta_sel == "Naranja":
  default_brix_in, default_rend, default_brix_obj = 11.5, 85.0, 60.0
elif fruta_sel == "Uva":
  default_brix_in, default_rend, default_brix_obj = 16.0, 88.0, 68.0
elif fruta_sel == "Manzana":
  default_brix_in, default_rend, default_brix_obj = 12.0, 80.0, 70.0
elif fruta_sel == "Maracuyá":
  default_brix_in, default_rend, default_brix_obj = 14.0, 40.0, 50.0
else:
  default_brix_in, default_rend, default_brix_obj = 12.0, 85.0, 60.0

w_bin = st.sidebar.number_input(
    "Brix Fruta Fresca:", value=default_brix_in, step=0.5
)
pct_rend_jugo = st.sidebar.slider(
    "Rendimiento de Jugo Clarificado (%):", 30.0, 95.0, default_rend, 0.5
)
w_bout = st.sidebar.number_input(
    "Brix Objetivo Final (°Brix):", value=default_brix_obj, step=1.0
)

# 🚨 VALIDACIÓN DE INCONSISTENCIA Y ALERTA FÍSICA 🚨
# Se activa si los Brix de entrada son mayores o iguales al objetivo final (dilución imposible)
# o si se introducen valores imposibles (> 100°Brix o <= 0°Brix)
if w_bin >= w_bout or w_bin <= 0 or w_bout > 100:
  st.error(
      "🌌 💥 **¡ALERTA DE INCONSISTENCIA GRAVITACIONAL!**\n\n"
      "Estás violando las leyes naturales y podrías destruir al universo. "
      "El producto concentrado no puede tener menor o igual concentración "
      "de sólidos que la fruta fresca de entrada, ni superar los 100 °Brix."
  )
