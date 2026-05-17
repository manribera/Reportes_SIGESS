import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from fpdf import FPDF
import io

# =====================================================
# CONFIGURACIÓN GENERAL DE LA APP
# =====================================================

st.set_page_config(
    page_title="SIGESS 2026",
    layout="wide",
    initial_sidebar_state="expanded"
)

URL_MASTER = "https://docs.google.com/spreadsheets/d/1cl2OeKSqtt4YvOkVM90uHa6Xa4zGuknjUsYpsrXzL_c/edit?usp=sharing"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

# =====================================================
# INTERFAZ ESTÉTICA (CSS PERSONALIZADO)
# =====================================================

st.markdown("""
<style>
.stApp {
    background-color: #111827;
    color: #F9FAFB;
}
section[data-testid="stSidebar"] {
    background-color: #0F172A;
}
h1, h2, h3, h4 {
    color: #F9FAFB;
}
[data-testid="stMetric"] {
    background-color: #1F2937;
    border: 1px solid #374151;
    padding: 18px;
    border-radius: 14px;
}
div[data-testid="stMetricValue"] {
    color: #F9FAFB;
}
div[data-testid="stMetricLabel"] {
    color: #D1D5DB;
}
.card {
    background-color: #1F2937;
    border: 1px solid #374151;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 12px;
}
.success-card {
    border-left: 6px solid #22C55E;
}
.warning-card {
    border-left: 6px solid #F59E0B;
}
.danger-card {
    border-left: 6px solid #EF4444;
}
.info-card {
    border-left: 6px solid #3B82F6;
}
.small-text {
    color: #D1D5DB;
    font-size: 14px;
}
.big-title {
    font-size: 30px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# FUNCIONES DE LIMPIEZA, NORMALIZACIÓN Y FILTRADO
# =====================================================

@st.cache_data(ttl=300)
def cargar_hoja(sheet_url, nombre_hoja):
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(sheet_url)
    worksheet = spreadsheet.worksheet(nombre_hoja)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)


def normalizar_texto(texto):
    return (str(texto).lower().strip()
            .replace('á', 'a')
            .replace('é', 'e')
            .replace('í', 'i')
            .replace('ó', 'o')
            .replace('ú', 'u')
            .replace(r'[\r\n]+', ''))


def limpiar_df(df):
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()
    return df


def numero(valor):
    try:
        if isinstance(valor, str):
            valor = valor.replace('%', '').strip()
        return float(valor)
    except Exception:
        return 0.0


def convertir_porcentaje(valor):
    valor = numero(valor)
    if valor <= 1.0 and valor > 0.0:
        return valor * 100.0
    return valor


def filtrar(df, delegacion, trimestre):
    if df.empty:
        return df
    mask_delegacion = df["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(delegacion)
    mask_trimestre = df["Trimestre"].apply(normalizar_texto) == normalizar_texto(trimestre)
    return df[mask_delegacion & mask_trimestre]


def filtrar_region(df, region, trimestre):
    if df.empty:
        return df
    mask_region = df["Delegación Regional"].apply(normalizar_texto) == normalizar_texto(region)
    mask_trimestre = df["Trimestre"].apply(normalizar_texto) == normalizar_texto(trimestre)
    return df[mask_region & mask_trimestre]


# =====================================================
# GENERADOR NATIVO DE PDF CON REEMPLAZO SEGURO
# =====================================================

class ReporteSIGESS(FPDF):
    def header(self):
        try:
            self.image("logo_sigess.png", 160, 12, 38)
        except Exception:
            pass
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(30, 58, 138)
        self.text(15, 18, "MINISTERIO DE SEGURIDAD PÚBLICA")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(75, 85, 99)
        self.text(15, 23, "Estrategia Sembremos Seguridad — SIGESS 2026")
        self.set_draw_color(30, 58, 138)
        self.line(15, 27, 195, 27)
        self.ln(22)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(156, 163, 175)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "R")


def sanitizar_para_pdf(texto):
    if not texto:
        return ""
    # Evita caídas sustituyendo caracteres raros o de macros por equivalentes latin-1 legibles
    string_limpia = str(texto).encode('latin-1', 'replace').decode('latin-1')
    return string_limpia


def generar_pdf_nativo(r_mesas, r_oe, r_pao, region, delegacion, trimestre):
    pdf = ReporteSIGESS()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    
    val_pao = convertir_porcentaje(r_pao.get("AVANCE_PAO_%", 0)) if r_pao else 0.0
    val_mal = convertir_porcentaje(r_mesas.get("% Cumplimiento Integral", 0)) if r_mesas else 0.0
    val_oe = int(numero(r_oe.get("Total OE", 0))) if r_oe else 0

    # Metadatos
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(40, 6, "Delegación Regional:", 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(60, 6, sanitizar_para_pdf(region), 0, 0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 6, "Fecha Reporte:", 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(45, 6, "17/05/2026", 0, 1)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(40, 6, "Unidad Cantonal:", 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(60, 6, sanitizar_para_pdf(delegacion), 0, 0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 6, "Corte Evaluado:", 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(45, 6, sanitizar_para_pdf(trimestre), 0, 1)
    pdf.ln(5)

    # Bloque 1: Notas
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(243, 244, 246)
    pdf.cell(0, 7, " 1. RESUMEN EJECUTIVO DE RENDIMIENTO", 0, 1, "L", True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(60, 7, "Cumplimiento M.A.L.", 1, 0, "C", True)
    pdf.cell(60, 7, "Eficiencia Real PAO", 1, 0, "C", True)
    pdf.cell(60, 7, "Volumen de Órdenes (OE)", 1, 1, "C", True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(60, 10, f"{val_mal:.1f}%", 1, 0, "C")
    pdf.set_text_color(22, 197, 94)
    pdf.cell(60, 10, f"{val_pao:.1f}%", 1, 0, "C")
    pdf.set_text_color(31, 41, 55)
    pdf.cell(60, 10, f"{val_oe} OE", 1, 1, "C")
    pdf.ln(5)

    # Bloque 2: MESAS
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(31, 41, 55)
    pdf.set_fill_color(243, 244, 246)
    pdf.cell(0, 7, " 2. EVALUACIÓN DE MESAS DE ARTICULACIÓN LOCAL (M.A.L.)", 0, 1, "L", True)
    pdf.ln(2)
    
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(0, 5, "Dictamen de Trazabilidad, Madurez y Gobernanza:", 0, 1)
    pdf.set_font("Helvetica", "", 9.5)
    just_mal = r_mesas.get("Justificación Técnica Operativa", "Sin registro de justificación técnica.") if r_mesas else "Sin datos."
    pdf.multi_cell(0, 5, sanitizar_para_pdf(just_mal), 1)
    pdf.ln(5)

    # Bloque 3: OE
    pdf.set_fill_color(243, 244, 246)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, " 3. FISCALIZACIÓN OPERATIVA DE ÓRDENES DE EJECUCIÓN", 0, 1, "L", True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(0, 5, "Justificación Operativa Automatizada:", 0, 1)
    pdf.set_font("Helvetica", "", 9.5)
    informe_oe = r_oe.get("Informe automático (justificación técnica operativa)", "Sin informe operativo.") if r_oe else "Sin datos."
    pdf.multi_cell(0, 5, sanitizar_para_pdf(informe_oe), 1)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(0, 5, "Acciones de Campo Colectivas y Resultados Sembrados:", 0, 1)
    pdf.set_font("Helvetica", "", 9.5)
    sintesis_oe = r_oe.get("Acciones y Resultados (síntesis de acciones) ", r_oe.get("Acciones y Resultados (síntesis de acciones)", "Sin acciones registradas.")) if r_oe else "Sin datos."
    pdf.multi_cell(0, 5, sanitizar_para_pdf(sintesis_oe), 1)
    
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.cell(0, 4, "Coordinación Nacional Sembremos Seguridad — Fuerza Pública de Costa Rica.", 0, 1, "C")
    
    return pdf.output()


# =====================================================
# COMPONENTES VISUALES GRÁFICOS (PLOTLY)
# =====================================================

def grafico_gauge(valor, titulo):
    valor = convertir_porcentaje(valor)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        title={"text": titulo, "font": {"size": 18}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "white"},
            "bar": {"color": "#3B82F6"},
            "steps": [
                {"range": [0, 69], "color": "#7F1D1D"},
                {"range": [70, 84], "color": "#92400E"},
                {"range": [85, 100], "color": "#14532D"}
            ]
        }
    ))
    fig.update_layout(
        paper_bgcolor="#111827", font_color="white",
        height=240, margin=dict(l=30, r=30, t=50, b=20)
    )
    return fig


def grafico_barras(df, x, y, titulo=""):
    fig = px.bar(df, x=x, y=y, text=y, title=titulo)
    fig.update_layout(
        paper_bgcolor="#111827", plot_bgcolor="#111827",
        font_color="white", xaxis_tickangle=-25,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    fig.update_traces(marker_color='#3B82F6', textposition='outside')
    return fig


def grafico_linea_tiempo(df_historico, metrica_col, titulo):
    orden_trimestres = {"i trimestre": 1, "ii trimestre": 2, "iii trimestre": 3, "iv trimestre": 4}
    df_plot = df_historico.copy()
    df_plot["orden"] = df_plot["Trimestre"].apply(normalizar_texto).map(orden_trimestres)
    df_plot = df_plot.dropna(subset=["orden"]).sort_values("orden")
    df_plot["Valor_Limpio"] = df_plot[metrica_col].apply(convertir_porcentaje)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_plot["Trimestre"], 
        y=df_plot["Valor_Limpio"],
        mode='lines+markers+text',
        text=df_plot["Valor_Limpio"].apply(lambda v: f"{v:.1f}%"),
        textposition="top center",
        line=dict(color="#22C55E", width=4),
        marker=dict(size=10, color="#22C55E")
    ))
    
    fig.update_layout(
        title=titulo,
        paper_bgcolor="#111827", plot_bgcolor="#111827",
        font_color="white", margin=dict(l=30, r=30, t=50, b=30),
        yaxis=dict(range=[0, 110], gridcolor="#374151"),
        xaxis=dict(gridcolor="#374151")
    )
    return fig


# =====================================================
# EXTRACCIÓN DE DATOS DESDE GOOGLE SHEETS
# =====================================================

try:
    mesas = limpiar_df(cargar_hoja(URL_MASTER, "MESAS_FINAL"))
    oe = limpiar_df(cargar_hoja(URL_MASTER, "OE_FINAL"))
    pao = limpiar_df(cargar_hoja(URL_MASTER, "PAO_FINAL"))
    control = limpiar_df(cargar_hoja(URL_MASTER, "CONTROL_FILTROS"))
except Exception as e:
    st.error("Error al conectar con Google Sheets Maestro.")
    st.exception(e)
    st.stop()


# =====================================================
# MENÚ LATERAL DE FILTROS Y CONTROLES (SIDEBAR)
# =====================================================

try:
    st.sidebar.image("logo_sigess.png", use_container_width=True)
except Exception:
    st.sidebar.caption("🖼️ [SIGESS 2026 — Logotipo Operativo]")

st.sidebar.title("SIGESS 2026")
st.sidebar.caption("Centro de Monitoreo Estratégico")

pagina = st.sidebar.radio(
    "Navegación Módulos",
    [
        "Inicio Ejecutivo",
        "PAO Estratégico",
        "Órdenes de Ejecución",
        "Mesas de Articulación",
        "Comparativa de Trimestres",
        "Consolidado Regional"
    ]
)

st.sidebar.markdown("---")

regiones_disponibles = sorted(control["Delegación Regional"].dropna().unique())
region = st.sidebar.selectbox("Delegación Regional", regiones_disponibles)

delegaciones_vinculadas = sorted(
    control[control["Delegación Regional"].apply(normalizar_texto) == normalizar_texto(region)]["Delegación Policial"]
    .dropna().unique()
)
delegacion = st.sidebar.selectbox("Delegación Policial", delegaciones_vinculadas)

trimestre = st.sidebar.selectbox(
    "Trimestre de Consulta",
    ["I Trimestre", "II Trimestre", "III Trimestre", "IV Trimestre"]
)

# Carga de filas específicas
mesas_f = filtrar(mesas, delegacion, trimestre)
oe_f = filtrar(oe, delegacion, trimestre)
pao_f = filtrar(pao, delegacion, trimestre)

row_mesas = mesas_f.iloc[0].to_dict() if not mesas_f.empty else {}
row_oe = oe_f.iloc[0].to_dict() if not oe_f.empty else {}
row_pao = pao_f.iloc[0].to_dict() if not pao_f.empty else {}

# BOTÓN DE DESCARGA PDF INTEGRADO OPERACIONALMENTE
st.sidebar.markdown("---")
st.sidebar.subheader("Exportación Oficial")

try:
    pdf_bytes = generar_pdf_nativo(row_mesas, row_oe, row_pao, region, delegacion, trimestre)
    st.sidebar.download_button(
        label="Descargar Informe PDF",
        data=bytes(pdf_bytes),
        file_name=f"Informe_SIGESS_{delegacion.replace(' ', '_')}_{trimestre.replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
except Exception as pdf_err:
    st.sidebar.error("Error al procesar el archivo de descarga.")

st.sidebar.markdown("---")
st.sidebar.caption("Fuerza Pública de Costa Rica")


# =====================================================
# PROCESAMIENTO E INYECCIÓN DE DATOS FILTRADOS
# =====================================================

mesas_region = filtrar_region(mesas, region, trimestre)
oe_region = filtrar_region(oe, region, trimestre)
pao_region = filtrar_region(pao, region, trimestre)

mesas_historico = mesas[mesas["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(delegacion)]
oe_historico = oe[oe["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(delegacion)]


# =====================================================
# ENCABEZADO DE PANTALLA (CON MARGEN ANTI-BLOQUEO)
# =====================================================

# CORRECCIÓN: Espaciado directo mediante style inline para ganarle prioridad a la barra gris de la nube
st.markdown('<div class="big-title" style="margin-top: 60px;">SIGESS 2026 — CONTROL DE MANDO</div>', unsafe_allow_html=True)
st.caption(f"Región: {region} | Unidad Cantonal: {delegacion} | Corte Seleccionado: {trimestre}")
st.markdown("---")


# =====================================================
# MÓDULO 1: INICIO EJECUTIVO
# =====================================================

if pagina == "Inicio Ejecutivo":
    st.header("Resumen General de Rendimiento")

    total_mesas = len(mesas_f) if not mesas_f.empty else 0
    total_oe = len(oe_f) if not oe_f.empty else 0
    total_pao = len(pao_f) if not pao_f.empty else 0

    avance_pao = 0.0
    if "AVANCE_PAO_%" in row_pao:
        avance_pao = convertir_porcentaje(row_pao["AVANCE_PAO_%"])

    cumplimiento_mal = 0.0
    if "% Cumplimiento Integral" in row_mesas:
        cumplimiento_mal = convertir_porcentaje(row_mesas["% Cumplimiento Integral"])

    nota_anual_absoluta = mesas_historico["% Cumplimiento Integral"].apply(numero).sum() / 4.0
    nota_anual_absoluta = convertir_porcentaje(nota_anual_absoluta)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros MAL", total_mesas)
    c2.metric("Volumen O.E.", total_oe)
    c3.metric("Fichas PAO", total_pao)
    c4.metric("Eficiencia PAO %", f"{avance_pao:.1f}%")

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Cumplimiento M.A.L.")
        st.plotly_chart(grafico_gauge(cumplimiento_mal, "Nota Trimestral"), use_container_width=True)
    with col2:
        st.subheader("Progreso del PAO")
        st.plotly_chart(grafico_gauge(avance_pao, "Nota Trimestral"), use_container_width=True)
    with col3:
        st.subheader("Proyección Anual Absoluta")
        st.plotly_chart(grafico_gauge(nota_anual_absoluta, "Meta Cierre de Año"), use_container_width=True)

    st.markdown("---")
    st.subheader("Evolución Cronológica del Año (Líneas de Tiempo)")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        if not mesas_historico.empty:
            st.plotly_chart(grafico_linea_tiempo(mesas_historico, "% Cumplimiento Integral", "Tendencia del % Cumplimiento Integral MAL"), use_container_width=True)
    with col_t2:
        if not oe_historico.empty:
            col_pct = "% cumplimiento" if "% cumplimiento" in oe_historico.columns else "Total OE"
            st.plotly_chart(grafico_linea_tiempo(oe_historico, col_pct, "Tendencia del Rendimiento Órdenes de Ejecución"), use_container_width=True)


# =====================================================
# MÓDULO 2: PLAN ANUAL OPERATIVO (PAO)
# =====================================================

elif pagina == "PAO Estratégico":
    st.header("PAO Estratégico y Despliegue Metodológico")

    if not row_pao:
        st.info("Sin registros de auditoría PAO cargados para este periodo.")
    else:
        avance = convertir_porcentaje(row_pao.get("AVANCE_PAO_%", 0))
        total_pao = numero(row_pao.get("TOTAL_PAO_100", 0))
        despliegue = numero(row_pao.get("DESPLIEGUE_10", 0))
        estado_pao = row_pao.get("ESTADO_AVANCE_PAO", "Sin estado")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Avance Real", f"{avance:.1f}%")
        c2.metric("Puntos PAO", f"{total_pao:.0f} / 100")
        c3.metric("Despliegue", f"{despliegue:.1f} / 10")
        c4.metric("Estado", estado_pao)

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Semáforo de Control PAO")
            st.plotly_chart(grafico_gauge(avance, "Progreso PAO"), use_container_width=True)
        with col2:
            st.subheader("Cumplimiento por Puntos Clave")
            componentes = {
                "Validación DR": row_pao.get("INSTR_DR_5", 0),
                "Validación Delegación": row_pao.get("INSTR_DELEG_5", 0),
                "Recolección": row_pao.get("RECOLECCION_15", 0),
                "MIC-MAC": row_pao.get("MICMAC_15", 0),
                "Triángulo": row_pao.get("TRIANGULO_10", 0),
                "Líneas": row_pao.get("LINEAS_25", 0),
                "Informe": row_pao.get("INFORME_25", 0),
            }
            df_comp = pd.DataFrame({"Componente": list(componentes.keys()), "Puntaje": [numero(v) for v in componentes.values()]})
            st.plotly_chart(grafico_barras(df_comp, "Componente", "Puntaje"), use_container_width=True)


# =====================================================
# MÓDULO 3: ÓRDENES DE EJECUCIÓN (O.E. + AUDITORÍA)
# =====================================================

elif pagina == "Órdenes de Ejecución":
    st.header("Auditoría de Órdenes de Ejecución")

    if not row_oe:
        st.info("Sin registros cargados de O.E. para esta unidad policial.")
    else:
        total_oe = numero(row_oe.get("Total OE", 0))
        acciones = numero(row_oe.get("Total acciones ejecutadas", 0))
        articulacion = numero(row_oe.get("OE con articulación", 0))
        sin_mal = numero(row_oe.get("OE sin planificación en MAL", 0))

        validador_oe = row_oe.get("Validador de la OE", "No especificado / Pendiente")
        validacion_final = row_oe.get("Validación Final", row_oe.get("Validación Final ", "Pendiente de Dictamen"))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Volumen Total OE", int(total_oe))
        c2.metric("Acciones Realizadas", int(acciones))
        c3.metric("OE con Corresponsabilidad", int(articulacion))
        c4.metric("Fuera de M.A.L.", int(sin_mal))

        st.markdown("---")
        st.markdown(f"""
        <div class="card info-card">
            <h4>Ficha de Registro, Fiscalización y Control</h4>
            <p><b>Funcionario Técnico Evaluador:</b> {validador_oe}</p>
            <p><b>Dictamen de Evidencias de Campo:</b> {validacion_final}</p>
        </div>
        """, unsafe_allow_html=True)

        informe = row_oe.get("Informe automático (justificación técnica operativa)", "Sin informe operativo.")
        sintesis = row_oe.get("Acciones y Resultados (síntesis de acciones) ", row_oe.get("Acciones y Resultados (síntesis de acciones)", "Sin síntesis de acciones."))
        
        st.markdown(f'<div class="card success-card"><h3>Justificación Operativa Automatizada</h3><p>{informe}</p></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card warning-card"><h3>Acciones de Campo Colectivas</h3><p>{sintesis}</p></div>', unsafe_allow_html=True)


# =====================================================
# MÓDULO 4: MESAS DE ARTICULACIÓN (M.A.L. + AUDITORÍA)
# =====================================================

elif pagina == "Mesas de Articulación":
    st.header("Módulo de Mesas de Articulación Local")

    if not row_mesas:
        st.info("No hay evidencias registradas para esta Mesa de Articulación Local.")
    else:
        cumplimiento = convertir_porcentaje(row_mesas.get("% Cumplimiento Integral", 0))
        total_envios = numero(row_mesas.get("Total Envíos", 0))
        trazabilidad = row_mesas.get("Nivel de Trazabilidad", "Sin registro")
        fase = row_mesas.get("Fase de Madurez Operativa", "Sin registro")
        estado_gestion = row_mesas.get("Estado de Gestión", "Sin estado")
        validador_mesa = row_mesas.get("Validador de la Mesa", "Funcionario No Asignado")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Nota del Periodo", f"{cumplimiento:.1f}%")
        c2.metric("Formularios Recibidos", int(total_envios))
        c3.metric("Trazabilidad", trazabilidad)
        c4.metric("Condición de Entrega", estado_gestion)

        st.markdown("---")
        st.markdown(f"""
        <div class="card info-card">
            <h4>Estatus de Integridad de la Mesa</h4>
            <p><b>Auditor de Control de Gestión SIGESS:</b> {validador_mesa}</p>
            <p><b>Fase Territorial Registrada:</b> {fase}</p>
        </div>
        """, unsafe_allow_html=True)

        justificacion = row_mesas.get("Justificación Técnica Operativa", "Sin registro pericial.")
        st.markdown(f'<div class="card success-card"><h3>Justificación Técnica Operativa</h3><p>{justificacion}</p></div>', unsafe_allow_html=True)


# =====================================================
# MÓDULO 5: COMPARATIVA DE TRIMESTRES
# =====================================================

elif pagina == "Comparativa de Trimestres":
    st.header("Módulo de Comparación Multi-Periodo (Benchmarking Side-by-Side)")
    st.markdown("---")

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        t_izq = st.selectbox("Seleccione Periodo Base (Izquierda)", ["I Trimestre", "II Trimestre", "III Trimestre", "IV Trimestre"], index=0)
    with col_sel2:
        t_der = st.selectbox("Seleccione Periodo Comparativo (Derecha)", ["I Trimestre", "II Trimestre", "III Trimestre", "IV Trimestre"], index=1)

    df_izq = filtrar(mesas, delegacion, t_izq)
    df_der = filtrar(mesas, delegacion, t_der)

    if df_izq.empty and df_der.empty:
        st.warning("No existen registros cargados para ninguno de los dos trimestres seleccionados.")
    else:
        nota_izq = convertir_porcentaje(df_izq["% Cumplimiento Integral"].iloc[0]) if not df_izq.empty else 0.0
        nota_der = convertir_porcentaje(df_der["% Cumplimiento Integral"].iloc[0]) if not df_der.empty else 0.0

        c_i, c_d = st.columns(2)
        with c_i:
            st.plotly_chart(grafico_gauge(nota_izq, f"Nota en {t_izq}"), use_container_width=True)
            if not df_izq.empty:
                st.markdown(f"""<div class="card info-card"><h5>Detalle Técnico {t_izq}</h5>
                <p><b>Estado de Gestión:</b> {df_izq['Estado de Gestión'].iloc[0]}<br>
                <b>Gobernanza:</b> {df_izq['Índice Gobernanza Local'].iloc[0]}</p></div>""", unsafe_allow_html=True)
        with c_d:
            st.plotly_chart(grafico_gauge(nota_der, f"Nota en {t_der}"), use_container_width=True)
            if not df_der.empty:
                st.markdown(f"""<div class="card success-card"><h5>Detalle Técnico {t_der}</h5>
                <p><b>Estado de Gestión:</b> {df_der['Estado de Gestión'].iloc[0]}<br>
                <b>Gobernanza:</b> {df_der['Índice Gobernanza Local'].iloc[0]}</p></div>""", unsafe_allow_html=True)

        st.markdown("---")
        df_delta = pd.DataFrame({
            "Periodo Evaluado": [t_izq, t_der],
            "Porcentaje de Cumplimiento %": [nota_izq, nota_der]
        })
        st.plotly_chart(grafico_barras(df_delta, "Periodo Evaluado", "Porcentaje de Cumplimiento %"), use_container_width=True)


# =====================================================
# MÓDULO 6: CONSOLIDADO REGIONAL
# =====================================================

elif pagina == "Consolidado Regional":
    st.header(f"Diagnóstico Comparativo de Mandos — {region}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Registros M.A.L. Región", len(mesas_region))
    c2.metric("Órdenes de Ejecución Región", len(oe_region))
    c3.metric("Fichas PAO Región", len(pao_region))

    st.markdown("---")
    mask_cantones = control["Delegación Regional"].apply(normalizar_texto) == normalizar_texto(region)
    cantones_region = sorted(control[mask_cantones]["Delegación Policial"].dropna().unique())

    datos_resumen = []
    for c in cantones_region:
        df_pao_c = pao_region[pao_region["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(c)]
        avance_pao_reg = convertir_porcentaje(df_pao_c["AVANCE_PAO_%"].iloc[0]) if not df_pao_c.empty else 0.0

        datos_resumen.append({
            "Delegación Policial": c,
            "Eficiencia PAO %": avance_pao_reg
        })

    df_resumen = pd.DataFrame(datos_resumen)
    st.subheader("Eficiencia del PAO por Comandancia")
    fig1 = px.bar(df_resumen, x="Delegación Policial", y="Eficiencia PAO %", text="Eficiencia PAO %")
    fig1.update_layout(paper_bgcolor="#111827", plot_bgcolor="#111827", font_color="white", xaxis_tickangle=-45)
    fig1.update_traces(marker_color='#10B981', texttemplate='%{text:.1f}%', textposition='outside')
    st.plotly_chart(fig1, use_container_width=True)
