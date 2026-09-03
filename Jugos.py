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
  dot.node("MOLINO", "MOLINO / TRITURADOR\n(Reducción & Merma)")
  dot.node("PRENSA", "PRENSA DE EXTRACCIÓN\n(Separación Sólido/Líquido)")
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
      "CONTROL DE BYPASS\n(Ajuste Cut-Back)",
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

  # Nodos de Entrada y Salidas
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
      f"SALIDA: Bagazo Húmedo\n{fmt_lbl('Bagazo Húmedo (Prensa)')}",
      fillcolor="#feebc8",
  )
  dot.node(
      "EXCEDENTE",
      (
          "EXCEDENTE BYPASS\n(Otro Proceso / Almacén)\n"
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

  # Conexiones Etapas de Extracción
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

  # Conexiones Evaporación
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

  # Conexiones Bypass y Mezcla
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

  # Térmico y Caldera
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


# Recuerda agregar al final del script para Renderizarlo en Streamlit:
st.subheader("🗺️ Diagrama de Flujo de Proceso (PFD)")
figura = generar_diagrama_detallado(res, w_bp, dist_evap1)
st.graphviz_chart(figura, use_container_width=True)
