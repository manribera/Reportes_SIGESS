import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials

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
.block-container {
    padding-top: 1.5rem;
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


def limpiar_df(df):
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()

    for col in ["Delegación Regional", "Delegación Policial", "Trimestre"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[\r\n]+', '', regex=True).str.strip()
            
    if "Trimestre" in df.columns:
        df["Trimestre"] = df["Trimestre"].str.replace(r'\s+', ' ', regex=True).str.strip()

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


def normalizar_texto(texto):
    return (str(texto).lower().strip()
            .replace('á', 'a')
            .replace('é', 'e')
            .replace('í', 'i')
            .replace('ó', 'o')
            .replace('ú', 'u'))


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


def clasificar_estado(valor):
    valor = convertir_porcentaje(valor)
    if valor >= 85:
        return "CUMPLE", "success-card"
    elif valor >= 70:
        return "CUMPLE PARCIALMENTE", "warning-card"
    else:
        return "NO CUMPLE / BAJO AVANCE", "danger-card"


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
    df_plot["Valor"] = df_plot[metrica_col].apply(convertir_porcentaje)
    
    fig = px.line(df_plot, x="Trimestre", y="Valor", text="Valor", title=titulo, markers=True)
    fig.update_layout(
        paper_bgcolor="#111827", plot_bgcolor="#111827",
        font_color="white", margin=dict(l=30, r=30, t=40, b=30),
        yaxis=dict(range=[0, 110])
    )
    fig.update_traces(line_color="#22C55E", width=4, marker=dict(size=10), texttemplate='%{text:.1f}%', textposition="top center")
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
    st.error("Error al conectar con Google Sheets.")
    st.exception(e)
    st.stop()


# =====================================================
# MENÚ LATERAL DE FILTROS (SIDEBAR)
# =====================================================

try:
    # Cambia esto por el nombre de tu archivo local (ej: "logo.png") o una URL directa
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

st.sidebar.markdown("---")
st.sidebar.caption("Fuerza Pública de Costa Rica")


# =====================================================
# PROCESAMIENTO E INYECCIÓN DE DATOS FILTRADOS
# =====================================================

mesas_f = filtrar(mesas, delegacion, trimestre)
oe_f = filtrar(oe, delegacion, trimestre)
pao_f = filtrar(pao, delegacion, trimestre)

mesas_region = filtrar_region(mesas, region, trimestre)
oe_region = filtrar_region(oe, region, trimestre)
pao_region = filtrar_region(pao, region, trimestre)

# Datos históricos longitudinales de la unidad seleccionada
mesas_historico = mesas[mesas["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(delegacion)]
oe_historico = oe[oe["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(delegacion)]


# =====================================================
# ENCABEZADO DE PANTALLA
# =====================================================

st.markdown('<div class="big-title">SIGESS 2026 — CONTROL DE MANDO</div>', unsafe_allow_html=True)
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
    if not pao_f.empty and "AVANCE_PAO_%" in pao_f.columns:
        avance_pao = convertir_porcentaje(pao_f["AVANCE_PAO_%"].iloc[0])

    cumplimiento_mal = 0.0
    if not mesas_f.empty and "% Cumplimiento Integral" in mesas_f.columns:
        cumplimiento_mal = convertir_porcentaje(mesas_f["% Cumplimiento Integral"].iloc[0])

    # Cálculo Ponderado Real Anual Absoluto (Cerrado a 4 periodos obligatorios)
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

    if pao_f.empty:
        st.info("Sin registros de auditoría PAO cargados para este periodo.")
    else:
        fila = pao_f.iloc[0]
        avance = convertir_porcentaje(fila.get("AVANCE_PAO_%", 0))
        total_pao = numero(fila.get("TOTAL_PAO_100", 0))
        despliegue = numero(fila.get("DESPLIEGUE_10", 0))
        estado_pao = fila.get("ESTADO_AVANCE_PAO", "Sin estado")

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
                "Validación DR": fila.get("INSTR_DR_5", 0),
                "Validación Delegación": fila.get("INSTR_DELEG_5", 0),
                "Recolección": fila.get("RECOLECCION_15", 0),
                "MIC-MAC": fila.get("MICMAC_15", 0),
                "Triángulo": fila.get("TRIANGULO_10", 0),
                "Líneas": fila.get("LINEAS_25", 0),
                "Informe": fila.get("INFORME_25", 0),
            }
            df_comp = pd.DataFrame({"Componente": list(componentes.keys()), "Puntaje": [numero(v) for v in componentes.values()]})
            st.plotly_chart(grafico_barras(df_comp, "Componente", "Puntaje"), use_container_width=True)


# =====================================================
# MÓDULO 3: ÓRDENES DE EJECUCIÓN (O.E. + AUDITORÍA)
# =====================================================

elif pagina == "Órdenes de Ejecución":
    st.header("Auditoría de Órdenes de Ejecución")

    if oe_f.empty:
        st.info("Sin registros cargados de O.E. para esta unidad policial.")
    else:
        fila = oe_f.iloc[0]
        total_oe = numero(fila.get("Total OE", 0))
        acciones = numero(fila.get("Total acciones ejecutadas", 0))
        articulacion = numero(fila.get("OE con articulación", 0))
        sin_mal = numero(fila.get("OE sin planificación en MAL", 0))
        pct_oe = convertir_porcentaje(fila.get("% cumplimiento", 0))

        # INTEGRACIÓN: AUDITOR DE LAS ÓRDENES DE EJECUCIÓN
        validador_oe = fila.get("Validador de la OE", "No especificado / Pendiente")
        validacion_final = fila.get("Validación Final", fila.get("Validación Final ", "Pendiente de Dictamen"))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Volumen Total OE", int(total_oe))
        c2.metric("Acciones Realizadas", int(acciones))
        c3.metric("OE con Corresponsabilidad", int(articulacion))
        c4.metric("Fuera de M.A.L.", int(sin_mal))

        st.markdown("---")
        
        # CARD DE IDENTIFICACIÓN DEL VALIDADOR
        st.markdown(f"""
        <div class="card info-card">
            <h4>Ficha de Registro, Fiscalización y Control</h4>
            <p><b>Funcionario Técnico Evaluador:</b> {validador_oe}</p>
            <p><b>Dictamen de Evidencias de Campo:</b> {validacion_final}</p>
        </div>
        """, unsafe_allow_html=True)

        informe = fila.get("Informe automático (justificación técnica operativa)", "Sin informe operativo.")
        sintesis = fila.get("Acciones y Resultados (síntesis de acciones) ", fila.get("Acciones y Resultados (síntesis de acciones)", "Sin síntesis de acciones."))
        
        st.markdown(f'<div class="card success-card"><h3>Justificación Operativa Automatizada</h3><p>{informe}</p></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card warning-card"><h3>Acciones de Campo Colectivas</h3><p>{sintesis}</p></div>', unsafe_allow_html=True)


# =====================================================
# MÓDULO 4: MESAS DE ARTICULACIÓN (M.A.L. + AUDITORÍA)
# =====================================================

elif pagina == "Mesas de Articulación":
    st.header("Módulo de Mesas de Articulación Local")

    if mesas_f.empty:
        st.info("No hay evidencias registradas para esta Mesa de Articulación Local.")
    else:
        fila = mesas_f.iloc[0]
        cumplimiento = convertir_porcentaje(fila.get("% Cumplimiento Integral", 0))
        total_envios = numero(fila.get("Total Envíos", 0))
        trazabilidad = fila.get("Nivel de Trazabilidad", "Sin registro")
        fase = fila.get("Fase de Madurez Operativa", "Sin registro")
        estado_gestion = fila.get("Estado de Gestión", "Sin estado")

        # INTEGRACIÓN: AUDITOR ANALISTA DE LA MESA DE ARTICULACIÓN
        validador_mesa = fila.get("Validador de la Mesa", "Funcionario No Asignado")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Nota del Periodo", f"{cumplimiento:.1f}%")
        c2.metric("Formularios Recibidos", int(total_envios))
        c3.metric("Trazabilidad", trazabilidad)
        c4.metric("Condición de Entrega", estado_gestion)

        st.markdown("---")
        
        # CARD DE IDENTIFICACIÓN DEL VALIDADOR DE LA MESA
        st.markdown(f"""
        <div class="card info-card">
            <h4>Estatus de Integridad de la Mesa</h4>
            <p><b>Auditor de Control de Gestión SIGESS:</b> {validador_mesa}</p>
            <p><b>Fase Territorial Registrada:</b> {fase}</p>
        </div>
        """, unsafe_allow_html=True)

        justificacion = fila.get("Justificación Técnica Operativa", "Sin registro pericial.")
        st.markdown(f'<div class="card success-card"><h3>Justificación Técnica Operativa</h3><p>{justificacion}</p></div>', unsafe_allow_html=True)


# =====================================================
# MÓDULO 5: COMPARATIVA DE TRIMESTRES (NUEVA PÁGINA)
# =====================================================

elif pagina == "Comparativa de Trimestres":
    st.header("Módulo de Comparación Multi-Periodo (Benchmarking Side-by-Side)")
    st.caption(f"Análisis evolutivo directo para la unidad: {delegacion}")
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
                <b>Gobernanza:</b> {df_izq['Índice Gobernanza Local'].iloc[0]}<br>
                <b>Validador:</b> {df_izq['Validador de la Mesa'].iloc[0]}</p></div>""", unsafe_allow_html=True)
        with c_d:
            st.plotly_chart(grafico_gauge(nota_der, f"Nota en {t_der}"), use_container_width=True)
            if not df_der.empty:
                st.markdown(f"""<div class="card success-card"><h5>Detalle Técnico {t_der}</h5>
                <p><b>Estado de Gestión:</b> {df_der['Estado de Gestión'].iloc[0]}<br>
                <b>Gobernanza:</b> {df_der['Índice Gobernanza Local'].iloc[0]}<br>
                <b>Validador:</b> {df_der['Validador de la Mesa'].iloc[0]}</p></div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Delta Real de Variación")
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
        df_mal_c = mesas_region[mesas_region["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(c)]
        df_oe_c = oe_region[oe_region["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(c)]
        df_pao_c = pao_region[pao_region["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(c)]

        avance_pao_reg = 0.0
        if not df_pao_c.empty and "AVANCE_PAO_%" in df_pao_c.columns:
            avance_pao_reg = convertir_porcentaje(df_pao_c["AVANCE_PAO_%"].iloc[0])

        datos_resumen.append({
            "Delegación Policial": c,
            "Envíos M.A.L.": len(df_mal_c),
            "Volumen O.E.": len(df_oe_c),
            "Auditorías PAO": len(df_pao_c),
            "Eficiencia PAO %": avance_pao_reg
        })

    df_resumen = pd.DataFrame(datos_resumen)

    st.subheader("Eficiencia del PAO por Comandancia")
    fig1 = px.bar(df_resumen, x="Delegación Policial", y="Eficiencia PAO %", text="Eficiencia PAO %")
    fig1.update_layout(paper_bgcolor="#111827", plot_bgcolor="#111827", font_color="white", xaxis_tickangle=-45)
    fig1.update_traces(marker_color='#10B981', texttemplate='%{text:.1f}%', textposition='outside')
    st.plotly_chart(fig1, use_container_width=True)
