import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from fpdf import FPDF
from datetime import datetime
import re
import html

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

@st.cache_data(ttl=30)
def cargar_hoja(sheet_url, nombre_hoja):
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(sheet_url)
    worksheet = spreadsheet.worksheet(nombre_hoja)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)


def normalizar_texto(texto):
    texto = str(texto).lower().strip()
    texto = texto.replace("á", "a").replace("é", "e").replace("í", "i")
    texto = texto.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    texto = re.sub(r"[\r\n]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def limpiar_df(df):
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()
    return df


def numero(valor):
    try:
        if valor is None:
            return 0.0
        if isinstance(valor, str):
            valor = valor.replace("%", "").replace(",", ".").strip()
            if valor == "":
                return 0.0
        return float(valor)
    except Exception:
        return 0.0


def convertir_porcentaje(valor):
    valor = numero(valor)
    if 0.0 < valor <= 1.0:
        return valor * 100.0
    return valor


def texto_seguro_html(valor):
    return html.escape(str(valor)) if valor is not None else ""


def obtener_valor(row, claves, defecto=""):
    if not row:
        return defecto
    if isinstance(claves, str):
        claves = [claves]
    for clave in claves:
        if clave in row and str(row.get(clave, "")).strip() != "":
            return row.get(clave)
    return defecto


def filtrar(df, delegacion, trimestre):
    if df.empty:
        return df
    if "Delegación Policial" not in df.columns or "Trimestre" not in df.columns:
        return pd.DataFrame()
    mask_delegacion = df["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(delegacion)
    mask_trimestre = df["Trimestre"].apply(normalizar_texto) == normalizar_texto(trimestre)
    return df[mask_delegacion & mask_trimestre]


def filtrar_region(df, region, trimestre):
    if df.empty:
        return df
    if "Delegación Regional" not in df.columns or "Trimestre" not in df.columns:
        return pd.DataFrame()
    mask_region = df["Delegación Regional"].apply(normalizar_texto) == normalizar_texto(region)
    mask_trimestre = df["Trimestre"].apply(normalizar_texto) == normalizar_texto(trimestre)
    return df[mask_region & mask_trimestre]


def fecha_actual_cr():
    meses = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    hoy = datetime.now()
    return f"{hoy.day:02d} de {meses[hoy.month]} de {hoy.year}"


# =====================================================
# GENERADOR NATIVO DE PDF
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
        self.text(15, 23, sanitizar_para_pdf("Estrategia Sembremos Seguridad - SIGESS 2026"))

        self.set_draw_color(30, 58, 138)
        self.line(15, 27, 195, 27)
        self.ln(22)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(156, 163, 175)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "R")


def sanitizar_para_pdf(texto):
    if texto is None:
        return ""
    texto = str(texto)
    reemplazos = {
        "—": "-",
        "–": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "•": "-",
        "…": "...",
        "\u00a0": " "
    }
    for original, nuevo in reemplazos.items():
        texto = texto.replace(original, nuevo)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto.encode("latin-1", "replace").decode("latin-1")


def salida_pdf_bytes(pdf):
    salida = pdf.output(dest="S")
    if isinstance(salida, str):
        return salida.encode("latin-1", "replace")
    return bytes(salida)


def agregar_titulo_seccion(pdf, titulo):
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(31, 41, 55)
    pdf.set_fill_color(243, 244, 246)
    pdf.cell(0, 7, sanitizar_para_pdf(titulo), 0, 1, "L", True)
    pdf.ln(2)


def agregar_caja_texto(pdf, titulo, texto, borde=1):
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(31, 41, 55)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 5, sanitizar_para_pdf(titulo), 0, 1)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(31, 41, 55)
    contenido = sanitizar_para_pdf(texto if texto else "Sin datos registrados.")
    agregar_multicelda_segura(pdf, contenido, 5, borde)
    pdf.ln(3)

def agregar_multicelda_segura(pdf, texto, alto=5, borde=1):
    """
    Imprime texto en PDF evitando el error:
    FPDFException: Not enough horizontal space to render a single character.
    """
    pdf.set_x(pdf.l_margin)
    ancho = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.multi_cell(ancho, alto, sanitizar_para_pdf(texto), borde)
    pdf.set_x(pdf.l_margin)


def generar_alertas_oe(r_oe):
    if not r_oe:
        return ["Sin datos de Órdenes de Ejecución para generar alertas."]

    sin_mal = numero(obtener_valor(r_oe, "OE sin planificación en MAL", 0))
    no_validas = numero(obtener_valor(r_oe, "OE no válidas", 0))

    criterio = obtener_valor(r_oe, "Criterio Técnico (sustento técnico)", "")
    evidencia = obtener_valor(r_oe, "Observaciones de Evidencia", "")
    validacion_final = obtener_valor(r_oe, ["Validación Final", "Validación Final "], "")

    texto_alerta = normalizar_texto(f"{criterio} {evidencia} {validacion_final}")

    alertas = []

    if "no se planifica" in texto_alerta or sin_mal > 0:
        alertas.append("Riesgo de planificación: existen OE sin planificación en Mesa de Articulación Local.")

    if "no hay coherencia" in texto_alerta:
        alertas.append("Riesgo de coherencia: se identifican diferencias entre planificación y ejecución.")

    if "no se observa evidencia" in texto_alerta or "sin evidencia" in texto_alerta:
        alertas.append("Riesgo documental: se identifican debilidades en la evidencia aportada.")

    if "no corresponden" in texto_alerta:
        alertas.append("Riesgo técnico: las acciones no corresponden plenamente a la problemática definida.")

    if no_validas > 0:
        alertas.append("Riesgo de validez: existen Órdenes de Ejecución clasificadas como no válidas.")

    if not alertas:
        alertas.append("No se identifican alertas críticas automáticas en el registro evaluado.")

    return alertas


def generar_pdf_nativo(r_mesas, r_oe, r_pao, region, delegacion, trimestre):
    pdf = ReporteSIGESS()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Valores generales
    val_pao = convertir_porcentaje(obtener_valor(r_pao, "AVANCE_PAO_%", 0)) if r_pao else 0.0
    val_mal = convertir_porcentaje(obtener_valor(r_mesas, "% Cumplimiento Integral", 0)) if r_mesas else 0.0
    val_oe = int(numero(obtener_valor(r_oe, "Total OE", 0))) if r_oe else 0

    cumplimiento_transitorio = convertir_porcentaje(
        obtener_valor(r_oe, "% cumplimiento ajustado", 0)
    ) if r_oe else 0.0

    # Metadatos
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(31, 41, 55)
    pdf.cell(40, 6, sanitizar_para_pdf("Delegación Regional:"), 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(60, 6, sanitizar_para_pdf(region), 0, 0)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 6, "Fecha Reporte:", 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(45, 6, sanitizar_para_pdf(fecha_actual_cr()), 0, 1)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(40, 6, "Unidad Cantonal:", 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(60, 6, sanitizar_para_pdf(delegacion), 0, 0)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 6, "Corte Evaluado:", 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(45, 6, sanitizar_para_pdf(trimestre), 0, 1)
    pdf.ln(5)

    # Resumen ejecutivo
    agregar_titulo_seccion(pdf, "1. RESUMEN EJECUTIVO DE RENDIMIENTO")

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(47, 7, "Cumplimiento M.A.L.", 1, 0, "C", True)
    pdf.cell(47, 7, "Eficiencia PAO", 1, 0, "C", True)
    pdf.cell(47, 7, "Volumen OE", 1, 0, "C", True)
    pdf.cell(49, 7, "Cumplimiento Transitorio", 1, 1, "C", True)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(31, 41, 55)
    pdf.cell(47, 9, f"{val_mal:.1f}%", 1, 0, "C")
    pdf.cell(47, 9, f"{val_pao:.1f}%", 1, 0, "C")
    pdf.cell(47, 9, f"{val_oe} OE", 1, 0, "C")
    pdf.cell(49, 9, f"{cumplimiento_transitorio:.1f}%", 1, 1, "C")
    pdf.ln(4)

    # Mesas
    agregar_titulo_seccion(pdf, "2. EVALUACIÓN DE MESAS DE ARTICULACIÓN LOCAL (M.A.L.)")
    just_mal = obtener_valor(
        r_mesas,
        "Justificación Técnica Operativa",
        "Sin registro de justificación técnica."
    ) if r_mesas else "Sin datos."
    agregar_caja_texto(pdf, "Dictamen de trazabilidad, madurez y gobernanza:", just_mal)

    # Órdenes de Ejecución
    agregar_titulo_seccion(pdf, "3. CENTRO DE VALIDACIÓN DE ÓRDENES DE EJECUCIÓN")

    total_oe = int(numero(obtener_valor(r_oe, "Total OE", 0))) if r_oe else 0
    acciones = int(numero(obtener_valor(r_oe, "Total acciones ejecutadas", 0))) if r_oe else 0
    articulacion = int(numero(obtener_valor(r_oe, "OE con articulación", 0))) if r_oe else 0
    oe_validas = int(numero(obtener_valor(r_oe, "OE válidas", 0))) if r_oe else 0
    parciales = int(numero(obtener_valor(r_oe, "OE con cumplimiento parcial", 0))) if r_oe else 0
    no_validas = int(numero(obtener_valor(r_oe, "OE no válidas", 0))) if r_oe else 0
    sin_mal = int(numero(obtener_valor(r_oe, "OE sin planificación en MAL", 0))) if r_oe else 0
    oportunidad = int(numero(obtener_valor(r_oe, "OE en oportunidad de mejora", 0))) if r_oe else 0
    ajustadas = int(numero(obtener_valor(r_oe, "OE ajustadas por contexto trimestral", 0))) if r_oe else 0

    estado = obtener_valor(r_oe, "Estado", "Sin estado") if r_oe else "Sin datos"

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(65, 7, "Indicador", 1, 0, "C", True)
    pdf.cell(35, 7, "Resultado", 1, 0, "C", True)
    pdf.cell(90, 7, "Observación", 1, 1, "C", True)

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(31, 41, 55)

    datos_oe = [
        ("Total OE", str(total_oe), "Órdenes de Ejecución registradas."),
        ("Acciones ejecutadas", str(acciones), "Acciones operativas desarrolladas."),
        ("OE con articulación", str(articulacion), "Corresponsabilidad interinstitucional."),
        ("OE válidas", str(oe_validas), "Registros con validez técnica."),
        ("OE parciales", str(parciales), "Cumplimiento parcial bajo criterio transitorio."),
        ("OE no válidas", str(no_validas), "Registros sin validez técnica."),
        ("OE sin M.A.L.", str(sin_mal), "Sin planificación en Mesa de Articulación Local."),
        ("OE oportunidad mejora", str(oportunidad), "Registros en oportunidad de mejora."),
        ("OE ajustadas", str(ajustadas), "Ajustes por contexto trimestral."),
        ("Cumplimiento parcial transitorio", f"{cumplimiento_transitorio:.1f}%", "No utiliza % cumplimiento OE por criterio transitorio."),
        ("Estado", estado, "Resultado general del periodo evaluado.")
    ]

    for indicador, resultado, observacion in datos_oe:
        pdf.cell(65, 6, sanitizar_para_pdf(indicador), 1)
        pdf.cell(35, 6, sanitizar_para_pdf(resultado), 1, 0, "C")
        pdf.cell(90, 6, sanitizar_para_pdf(observacion), 1, 1)

    pdf.ln(4)

    informe_oe = obtener_valor(
        r_oe,
        "Informe automático (justificación técnica operativa)",
        "Sin informe operativo."
    ) if r_oe else "Sin datos."
    agregar_caja_texto(pdf, "Dictamen operativo y análisis técnico:", informe_oe)

    validacion_final = obtener_valor(
        r_oe,
        ["Validación Final", "Validación Final "],
        "Pendiente de dictamen."
    ) if r_oe else "Sin datos."
    agregar_caja_texto(pdf, "Validación general:", validacion_final)

    instituciones = obtener_valor(
        r_oe,
        "Instituciones Participantes (Corresponsabilidad (articulación)",
        "Sin instituciones registradas."
    ) if r_oe else "Sin datos."

    problematicas = obtener_valor(
        r_oe,
        "Problemáticas y Factores",
        "Sin problemáticas registradas."
    ) if r_oe else "Sin datos."

    enfoque = obtener_valor(
        r_oe,
        "Enfoque de la OE",
        "Sin enfoque registrado."
    ) if r_oe else "Sin datos."

    acciones_resultados = obtener_valor(
        r_oe,
        ["Acciones y Resultados (síntesis de acciones) ", "Acciones y Resultados (síntesis de acciones)"],
        "Sin acciones registradas."
    ) if r_oe else "Sin datos."

    evidencia = obtener_valor(
        r_oe,
        "Observaciones de Evidencia",
        "Sin observaciones registradas."
    ) if r_oe else "Sin datos."

    criterio = obtener_valor(
        r_oe,
        "Criterio Técnico (sustento técnico)",
        "Sin criterio técnico registrado."
    ) if r_oe else "Sin datos."

    agregar_caja_texto(pdf, "Corresponsabilidad y articulación:", instituciones)
    agregar_caja_texto(pdf, "Factores de riesgo y problemáticas:", problematicas)
    agregar_caja_texto(pdf, "Enfoque aplicado a la OE:", enfoque)
    agregar_caja_texto(pdf, "Acciones y resultados operativos:", acciones_resultados)
    agregar_caja_texto(pdf, "Observaciones de evidencia:", evidencia)
    agregar_caja_texto(pdf, "Criterio técnico operativo:", criterio)

    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(31, 41, 55)
    pdf.cell(0, 6, "Alertas operativas automáticas:", 0, 1)

    pdf.set_font("Helvetica", "", 9)
    for alerta in generar_alertas_oe(r_oe):
        agregar_multicelda_segura(pdf, f"- {alerta}", 5, 1)

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(75, 85, 99)
    pdf.cell(0, 4, sanitizar_para_pdf("Coordinación Nacional Sembremos Seguridad - Fuerza Pública de Costa Rica."), 0, 1, "C")

    return salida_pdf_bytes(pdf)


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
        paper_bgcolor="#111827",
        font_color="white",
        height=240,
        margin=dict(l=30, r=30, t=50, b=20)
    )
    return fig


def grafico_barras(df, x, y, titulo=""):
    fig = px.bar(df, x=x, y=y, text=y, title=titulo)
    fig.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font_color="white",
        xaxis_tickangle=-25,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    fig.update_traces(marker_color="#3B82F6", textposition="outside")
    return fig


def grafico_linea_tiempo(df_historico, metrica_col, titulo):
    orden_trimestres = {
        "i trimestre": 1,
        "ii trimestre": 2,
        "iii trimestre": 3,
        "iv trimestre": 4
    }

    df_plot = df_historico.copy()
    df_plot["orden"] = df_plot["Trimestre"].apply(normalizar_texto).map(orden_trimestres)
    df_plot = df_plot.dropna(subset=["orden"]).sort_values("orden")
    df_plot["Valor_Limpio"] = df_plot[metrica_col].apply(convertir_porcentaje)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_plot["Trimestre"],
        y=df_plot["Valor_Limpio"],
        mode="lines+markers+text",
        text=df_plot["Valor_Limpio"].apply(lambda v: f"{v:.1f}%"),
        textposition="top center",
        line=dict(color="#22C55E", width=4),
        marker=dict(size=10, color="#22C55E")
    ))

    fig.update_layout(
        title=titulo,
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font_color="white",
        margin=dict(l=30, r=30, t=50, b=30),
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
# MENÚ LATERAL DE FILTROS Y CONTROLES
# =====================================================

try:
    st.sidebar.image("logo_sigess.png", use_container_width=True)
except Exception:
    st.sidebar.caption("SIGESS 2026 - Logotipo Operativo")

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
    control[
        control["Delegación Regional"].apply(normalizar_texto) == normalizar_texto(region)
    ]["Delegación Policial"].dropna().unique()
)

delegacion = st.sidebar.selectbox("Delegación Policial", delegaciones_vinculadas)

trimestre = st.sidebar.selectbox(
    "Trimestre de Consulta",
    ["I Trimestre", "II Trimestre", "III Trimestre", "IV Trimestre"]
)

st.sidebar.markdown("---")
st.sidebar.caption("Estrategia Sembremos Seguridad")
if st.sidebar.button("Actualizar datos", use_container_width=True):
    st.cache_data.clear()
    st.rerun()


# =====================================================
# PROCESAMIENTO DE DATOS FILTRADOS
# =====================================================

mesas_f = filtrar(mesas, delegacion, trimestre)
oe_f = filtrar(oe, delegacion, trimestre)
pao_f = filtrar(pao, delegacion, trimestre)

row_mesas = mesas_f.iloc[0].to_dict() if not mesas_f.empty else {}
row_oe = oe_f.iloc[0].to_dict() if not oe_f.empty else {}
row_pao = pao_f.iloc[0].to_dict() if not pao_f.empty else {}

mesas_region = filtrar_region(mesas, region, trimestre)
oe_region = filtrar_region(oe, region, trimestre)
pao_region = filtrar_region(pao, region, trimestre)

mesas_historico = mesas[
    mesas["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(delegacion)
] if "Delegación Policial" in mesas.columns else pd.DataFrame()

oe_historico = oe[
    oe["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(delegacion)
] if "Delegación Policial" in oe.columns else pd.DataFrame()


# =====================================================
# ENCABEZADO DE PANTALLA
# =====================================================

st.markdown(
    '<div class="big-title" style="margin-top: 60px;">SIGESS 2026 — CONTROL DE MANDO</div>',
    unsafe_allow_html=True
)
st.caption(f"Región: {region} | Unidad Cantonal: {delegacion} | Corte Seleccionado: {trimestre}")
st.markdown("---")


# =====================================================
# MÓDULO 1: INICIO EJECUTIVO
# =====================================================

if pagina == "Inicio Ejecutivo":
    st.header("Resumen General de Rendimiento")

    total_mesas = len(mesas_f) if not mesas_f.empty else 0
    total_oe = int(numero(row_oe.get("Total OE", 0))) if row_oe else 0
    total_pao = len(pao_f) if not pao_f.empty else 0

    avance_pao = convertir_porcentaje(row_pao.get("AVANCE_PAO_%", 0)) if row_pao else 0.0
    cumplimiento_mal = convertir_porcentaje(row_mesas.get("% Cumplimiento Integral", 0)) if row_mesas else 0.0

    if not mesas_historico.empty and "% Cumplimiento Integral" in mesas_historico.columns:
        nota_anual_absoluta = mesas_historico["% Cumplimiento Integral"].apply(numero).sum() / 4.0
        nota_anual_absoluta = convertir_porcentaje(nota_anual_absoluta)
    else:
        nota_anual_absoluta = 0.0

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
    st.subheader("Evolución Cronológica del Año")

    col_t1, col_t2 = st.columns(2)

    with col_t1:
        if not mesas_historico.empty and "% Cumplimiento Integral" in mesas_historico.columns:
            st.plotly_chart(
                grafico_linea_tiempo(
                    mesas_historico,
                    "% Cumplimiento Integral",
                    "Tendencia del % Cumplimiento Integral MAL"
                ),
                use_container_width=True
            )
        else:
            st.info("Sin histórico MAL para graficar.")

    with col_t2:
        if not oe_historico.empty:
            col_pct = "% cumplimiento ajustado" if "% cumplimiento ajustado" in oe_historico.columns else "Total OE"
            st.plotly_chart(
                grafico_linea_tiempo(
                    oe_historico,
                    col_pct,
                    "Tendencia del Cumplimiento Parcial Transitorio OE"
                ),
                use_container_width=True
            )
        else:
            st.info("Sin histórico OE para graficar.")


# =====================================================
# MÓDULO 2: PLAN ANUAL OPERATIVO
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

            df_comp = pd.DataFrame({
                "Componente": list(componentes.keys()),
                "Puntaje": [numero(v) for v in componentes.values()]
            })

            st.plotly_chart(
                grafico_barras(df_comp, "Componente", "Puntaje"),
                use_container_width=True
            )


# =====================================================
# MÓDULO 3: ÓRDENES DE EJECUCIÓN
# =====================================================

elif pagina == "Órdenes de Ejecución":
    st.header("Centro de Fiscalización de Órdenes de Ejecución")

    if not row_oe:
        st.info("Sin registros cargados de O.E. para esta unidad policial.")
    else:
        total_oe = numero(row_oe.get("Total OE", 0))
        acciones = numero(row_oe.get("Total acciones ejecutadas", 0))
        articulacion = numero(row_oe.get("OE con articulación", 0))
        oe_validas = numero(row_oe.get("OE válidas", 0))
        oe_parciales = numero(row_oe.get("OE con cumplimiento parcial", 0))
        oe_no_validas = numero(row_oe.get("OE no válidas", 0))
        sin_mal = numero(row_oe.get("OE sin planificación en MAL", 0))
        oportunidad = numero(row_oe.get("OE en oportunidad de mejora", 0))
        ajustadas = numero(row_oe.get("OE ajustadas por contexto trimestral", 0))

        # IMPORTANTE:
        # Por transitorio, NO se usa "% cumplimiento" de OE.
        # Se usa "% cumplimiento ajustado" como cumplimiento parcial transitorio.
        cumplimiento = convertir_porcentaje(row_oe.get("% cumplimiento ajustado", 0))
        cumplimiento_ajustado = cumplimiento

        estado = row_oe.get("Estado", "Sin estado")
        validador_oe = row_oe.get("Validador de la OE", "No especificado / Pendiente")
        validacion_final = row_oe.get("Validación Final", row_oe.get("Validación Final ", "Pendiente de Dictamen"))

        instituciones = row_oe.get(
            "Instituciones Participantes (Corresponsabilidad (articulación)",
            "Sin instituciones registradas."
        )

        problematicas = row_oe.get(
            "Problemáticas y Factores",
            "Sin problemáticas registradas."
        )

        acciones_resultados = row_oe.get(
            "Acciones y Resultados (síntesis de acciones) ",
            row_oe.get("Acciones y Resultados (síntesis de acciones)", "Sin síntesis de acciones.")
        )

        evidencia = row_oe.get(
            "Observaciones de Evidencia",
            "Sin observaciones de evidencia."
        )

        criterio = row_oe.get(
            "Criterio Técnico (sustento técnico)",
            "Sin criterio técnico registrado."
        )

        enfoque = row_oe.get(
            "Enfoque de la OE",
            "Sin enfoque registrado."
        )

        informe = row_oe.get(
            "Informe automático (justificación técnica operativa)",
            "Sin informe operativo."
        )

        # Bloque superior
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total OE", int(total_oe))
        c2.metric("Acciones Ejecutadas", int(acciones))
        c3.metric("OE con Articulación", int(articulacion))
        c4.metric("Cumplimiento Parcial Transitorio", f"{cumplimiento:.1f}%")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("OE Válidas", int(oe_validas))
        c6.metric("OE Parciales", int(oe_parciales))
        c7.metric("OE No Válidas", int(oe_no_validas))
        c8.metric("OE sin M.A.L.", int(sin_mal))

        st.markdown("---")

        # Semáforo y gráfico
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("Semáforo Técnico")
            st.plotly_chart(
                grafico_gauge(cumplimiento, "Cumplimiento Parcial Transitorio"),
                use_container_width=True
            )

        with col2:
            st.subheader("Distribución de Órdenes de Ejecución")

            df_oe_estado = pd.DataFrame({
                "Categoría": [
                    "OE válidas",
                    "OE parciales",
                    "OE no válidas",
                    "OE sin M.A.L.",
                    "OE oportunidad mejora",
                    "OE ajustadas"
                ],
                "Cantidad": [
                    oe_validas,
                    oe_parciales,
                    oe_no_validas,
                    sin_mal,
                    oportunidad,
                    ajustadas
                ]
            })

            st.plotly_chart(
                grafico_barras(df_oe_estado, "Categoría", "Cantidad", "Estado técnico de OE"),
                use_container_width=True
            )

        st.markdown("---")

        # Dictamen operativo
        st.subheader("Dictamen Técnico Operativo")

        st.markdown(f"""
        <div class="card info-card">
            <h4>Estado General de la Gestión</h4>
            <p><b>Estado:</b> {texto_seguro_html(estado)}</p>
            <p><b>Validación Final:</b> {texto_seguro_html(validacion_final)}</p>
            <p><b>Funcionario Técnico Evaluador:</b> {texto_seguro_html(validador_oe)}</p>
            <p><b>Cumplimiento Parcial Transitorio:</b> {cumplimiento_ajustado:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="card success-card">
            <h4>Justificación Operativa Automatizada</h4>
            <p>{texto_seguro_html(informe)}</p>
        </div>
        """, unsafe_allow_html=True)

        # Trazabilidad
        st.subheader("Trazabilidad, Corresponsabilidad y Enfoque")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown(f"""
            <div class="card info-card">
                <h4>Instituciones Participantes</h4>
                <p>{texto_seguro_html(instituciones)}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="card warning-card">
                <h4>Problemáticas y Factores de Riesgo</h4>
                <p>{texto_seguro_html(problematicas)}</p>
            </div>
            """, unsafe_allow_html=True)

        with col_b:
            st.markdown(f"""
            <div class="card info-card">
                <h4>Enfoque de la Orden de Ejecución</h4>
                <p>{texto_seguro_html(enfoque)}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="card success-card">
                <h4>Acciones y Resultados</h4>
                <p>{texto_seguro_html(acciones_resultados)}</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Evidencia y criterio
        st.subheader("Evidencia y Criterio Técnico")

        col_e, col_c = st.columns(2)

        with col_e:
            st.markdown(f"""
            <div class="card warning-card">
                <h4>Observaciones de Evidencia</h4>
                <p>{texto_seguro_html(evidencia)}</p>
            </div>
            """, unsafe_allow_html=True)

        with col_c:
            st.markdown(f"""
            <div class="card danger-card">
                <h4>Criterio Técnico</h4>
                <p>{texto_seguro_html(criterio)}</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Alertas automáticas
        st.subheader("Alertas Operativas Automáticas")

        alertas = generar_alertas_oe(row_oe)

        if len(alertas) == 1 and alertas[0].startswith("No se identifican"):
            st.success(alertas[0])
        else:
            for alerta in alertas:
                st.markdown(f"""
                <div class="card danger-card">
                    <h4>Alerta</h4>
                    <p>{texto_seguro_html(alerta)}</p>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # Generación de informe
        st.subheader("Generación de Informe Oficial")

        if "pdf_oe_generado" not in st.session_state:
            st.session_state["pdf_oe_generado"] = None

        if "nombre_pdf_oe" not in st.session_state:
            st.session_state["nombre_pdf_oe"] = None

        if st.button("Crear informe de Órdenes de Ejecución", use_container_width=True):
            try:
                with st.spinner("Generando informe oficial..."):
                    pdf_generado = generar_pdf_nativo(
                        row_mesas,
                        row_oe,
                        row_pao,
                        region,
                        delegacion,
                        trimestre
                    )

                    st.session_state["pdf_oe_generado"] = pdf_generado
                    st.session_state["nombre_pdf_oe"] = (
                        f"IF_{trimestre.replace(' ', '_')}_OE_OI_"
                        f"{delegacion.replace(' ', '_')}.pdf"
                    )

                st.success("Informe generado correctamente. Ahora puede descargarlo.")

            except Exception as e:
                st.error("No se pudo generar el informe PDF.")
                st.exception(e)

        if st.session_state["pdf_oe_generado"] is not None:
            st.download_button(
                label="Descargar informe PDF",
                data=st.session_state["pdf_oe_generado"],
                file_name=st.session_state["nombre_pdf_oe"],
                mime="application/pdf",
                use_container_width=True
            )


# =====================================================
# MÓDULO 4: MESAS DE ARTICULACIÓN
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
            <p><b>Auditor de Control de Gestión SIGESS:</b> {texto_seguro_html(validador_mesa)}</p>
            <p><b>Fase Territorial Registrada:</b> {texto_seguro_html(fase)}</p>
        </div>
        """, unsafe_allow_html=True)

        justificacion = row_mesas.get("Justificación Técnica Operativa", "Sin registro pericial.")

        st.markdown(f"""
        <div class="card success-card">
            <h3>Justificación Técnica Operativa</h3>
            <p>{texto_seguro_html(justificacion)}</p>
        </div>
        """, unsafe_allow_html=True)


# =====================================================
# MÓDULO 5: COMPARATIVA DE TRIMESTRES
# =====================================================

elif pagina == "Comparativa de Trimestres":
    st.header("Módulo de Comparación Multi-Periodo")
    st.markdown("---")

    col_sel1, col_sel2 = st.columns(2)

    with col_sel1:
        t_izq = st.selectbox(
            "Seleccione Periodo Base (Izquierda)",
            ["I Trimestre", "II Trimestre", "III Trimestre", "IV Trimestre"],
            index=0
        )

    with col_sel2:
        t_der = st.selectbox(
            "Seleccione Periodo Comparativo (Derecha)",
            ["I Trimestre", "II Trimestre", "III Trimestre", "IV Trimestre"],
            index=1
        )

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
                estado_i = df_izq["Estado de Gestión"].iloc[0] if "Estado de Gestión" in df_izq.columns else "Sin estado"
                gob_i = df_izq["Índice Gobernanza Local"].iloc[0] if "Índice Gobernanza Local" in df_izq.columns else "Sin dato"

                st.markdown(f"""
                <div class="card info-card">
                    <h5>Detalle Técnico {texto_seguro_html(t_izq)}</h5>
                    <p><b>Estado de Gestión:</b> {texto_seguro_html(estado_i)}<br>
                    <b>Gobernanza:</b> {texto_seguro_html(gob_i)}</p>
                </div>
                """, unsafe_allow_html=True)

        with c_d:
            st.plotly_chart(grafico_gauge(nota_der, f"Nota en {t_der}"), use_container_width=True)

            if not df_der.empty:
                estado_d = df_der["Estado de Gestión"].iloc[0] if "Estado de Gestión" in df_der.columns else "Sin estado"
                gob_d = df_der["Índice Gobernanza Local"].iloc[0] if "Índice Gobernanza Local" in df_der.columns else "Sin dato"

                st.markdown(f"""
                <div class="card success-card">
                    <h5>Detalle Técnico {texto_seguro_html(t_der)}</h5>
                    <p><b>Estado de Gestión:</b> {texto_seguro_html(estado_d)}<br>
                    <b>Gobernanza:</b> {texto_seguro_html(gob_d)}</p>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        df_delta = pd.DataFrame({
            "Periodo Evaluado": [t_izq, t_der],
            "Porcentaje de Cumplimiento %": [nota_izq, nota_der]
        })

        st.plotly_chart(
            grafico_barras(df_delta, "Periodo Evaluado", "Porcentaje de Cumplimiento %"),
            use_container_width=True
        )


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
        df_pao_c = pao_region[
            pao_region["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(c)
        ] if not pao_region.empty else pd.DataFrame()

        df_oe_c = oe_region[
            oe_region["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(c)
        ] if not oe_region.empty else pd.DataFrame()

        df_mesas_c = mesas_region[
            mesas_region["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(c)
        ] if not mesas_region.empty else pd.DataFrame()

        avance_pao_reg = convertir_porcentaje(df_pao_c["AVANCE_PAO_%"].iloc[0]) if not df_pao_c.empty and "AVANCE_PAO_%" in df_pao_c.columns else 0.0
        cumplimiento_mal_reg = convertir_porcentaje(df_mesas_c["% Cumplimiento Integral"].iloc[0]) if not df_mesas_c.empty and "% Cumplimiento Integral" in df_mesas_c.columns else 0.0
        cumplimiento_oe_reg = convertir_porcentaje(df_oe_c["% cumplimiento ajustado"].iloc[0]) if not df_oe_c.empty and "% cumplimiento ajustado" in df_oe_c.columns else 0.0
        total_oe_reg = numero(df_oe_c["Total OE"].iloc[0]) if not df_oe_c.empty and "Total OE" in df_oe_c.columns else 0.0

        datos_resumen.append({
            "Delegación Policial": c,
            "Eficiencia PAO %": avance_pao_reg,
            "Cumplimiento MAL %": cumplimiento_mal_reg,
            "Cumplimiento OE Transitorio %": cumplimiento_oe_reg,
            "Total OE": total_oe_reg
        })

    df_resumen = pd.DataFrame(datos_resumen)

    st.subheader("Resumen Regional por Delegación")
    st.dataframe(df_resumen, use_container_width=True)

    st.subheader("Eficiencia del PAO por Delegación")
    st.plotly_chart(
        grafico_barras(df_resumen, "Delegación Policial", "Eficiencia PAO %", "Eficiencia PAO %"),
        use_container_width=True
    )

    st.subheader("Cumplimiento Parcial Transitorio OE por Delegación")
    st.plotly_chart(
        grafico_barras(
            df_resumen,
            "Delegación Policial",
            "Cumplimiento OE Transitorio %",
            "Cumplimiento Parcial Transitorio OE"
        ),
        use_container_width=True
    )

    st.subheader("Cumplimiento MAL por Delegación")
    st.plotly_chart(
        grafico_barras(df_resumen, "Delegación Policial", "Cumplimiento MAL %", "Cumplimiento MAL %"),
        use_container_width=True
    )
