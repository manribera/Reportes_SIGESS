import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials

# =====================================================
# CONFIGURACIÓN
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
# ESTILO
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
h1, h2, h3 {
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
# FUNCIONES
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
            df[col] = df[col].astype(str).str.strip()

    return df


def numero(valor):
    try:
        return float(valor)
    except Exception:
        return 0


def convertir_porcentaje(valor):
    valor = numero(valor)
    if valor <= 1:
        return valor * 100
    return valor


def filtrar(df, delegacion, trimestre):
    if df.empty:
        return df

    return df[
        (df["Delegación Policial"] == delegacion) &
        (df["Trimestre"] == trimestre)
    ]


def filtrar_region(df, region, trimestre):
    if df.empty:
        return df

    return df[
        (df["Delegación Regional"] == region) &
        (df["Trimestre"] == trimestre)
    ]


def clasificar_estado(valor):
    valor = convertir_porcentaje(valor)

    if valor >= 85:
        return "CUMPLE", "success-card"
    elif valor >= 70:
        return "CUMPLE PARCIALMENTE", "warning-card"
    else:
        return "NO CUMPLE / BAJO AVANCE", "danger-card"


def grafico_gauge(valor, titulo):
    valor = convertir_porcentaje(valor)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        title={"text": titulo},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#22C55E"},
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
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def grafico_barras(df, x, y, titulo=""):
    fig = px.bar(
        df,
        x=x,
        y=y,
        text=y,
        title=titulo
    )
    fig.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font_color="white",
        xaxis_tickangle=-25,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig


# =====================================================
# CARGA DE DATOS
# =====================================================

try:
    mesas = limpiar_df(cargar_hoja(URL_MASTER, "MESAS_FINAL"))
    oe = limpiar_df(cargar_hoja(URL_MASTER, "OE_FINAL"))
    pao = limpiar_df(cargar_hoja(URL_MASTER, "PAO_FINAL"))
    control = limpiar_df(cargar_hoja(URL_MASTER, "CONTROL_FILTROS"))
except Exception as e:
    st.error("No se pudieron cargar los datos desde Google Sheets.")
    st.exception(e)
    st.stop()

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("SIGESS 2026")
st.sidebar.caption("Centro de Monitoreo Estratégico")

pagina = st.sidebar.radio(
    "Navegación",
    [
        "Inicio Ejecutivo",
        "PAO Estratégico",
        "Órdenes de Ejecución",
        "Mesas de Articulación",
        "Consolidado Regional"
    ]
)

st.sidebar.markdown("---")

region = st.sidebar.selectbox(
    "Delegación Regional",
    sorted(control["Delegación Regional"].dropna().unique())
)

delegaciones = sorted(
    control[control["Delegación Regional"] == region]["Delegación Policial"]
    .dropna()
    .unique()
)

delegacion = st.sidebar.selectbox(
    "Delegación Policial",
    delegaciones
)

trimestre = st.sidebar.selectbox(
    "Trimestre",
    ["I Trimestre", "II Trimestre", "III Trimestre", "IV Trimestre"]
)

st.sidebar.markdown("---")
st.sidebar.caption("Fuente: SIGESS 2026")

# =====================================================
# DATOS FILTRADOS
# =====================================================

mesas_f = filtrar(mesas, delegacion, trimestre)
oe_f = filtrar(oe, delegacion, trimestre)
pao_f = filtrar(pao, delegacion, trimestre)

mesas_region = filtrar_region(mesas, region, trimestre)
oe_region = filtrar_region(oe, region, trimestre)
pao_region = filtrar_region(pao, region, trimestre)

# =====================================================
# ENCABEZADO GENERAL
# =====================================================

st.markdown('<div class="big-title">SIGESS 2026</div>', unsafe_allow_html=True)
st.caption(f"{region} | {delegacion} | {trimestre}")
st.markdown("---")

# =====================================================
# INICIO EJECUTIVO
# =====================================================

if pagina == "Inicio Ejecutivo":

    st.header("Inicio Ejecutivo")

    total_mesas = len(mesas_f)
    total_oe = len(oe_f)
    total_pao = len(pao_f)

    avance_pao = 0
    if not pao_f.empty and "AVANCE_PAO_%" in pao_f.columns:
        avance_pao = convertir_porcentaje(pao_f["AVANCE_PAO_%"].iloc[0])

    cumplimiento_mal = 0
    if not mesas_f.empty and "% Cumplimiento Integral" in mesas_f.columns:
        cumplimiento_mal = convertir_porcentaje(mesas_f["% Cumplimiento Integral"].iloc[0])

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Mesas", total_mesas)
    c2.metric("Órdenes de Ejecución", total_oe)
    c3.metric("PAO", total_pao)
    c4.metric("Avance PAO", f"{avance_pao:.1f}%")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Cumplimiento MAL")
        st.plotly_chart(grafico_gauge(cumplimiento_mal, "MAL"), use_container_width=True)

    with col2:
        st.subheader("Avance PAO")
        st.plotly_chart(grafico_gauge(avance_pao, "PAO"), use_container_width=True)

    st.markdown("---")

    estado, clase = clasificar_estado(avance_pao)

    st.markdown(f"""
    <div class="card {clase}">
        <h3>Lectura Ejecutiva</h3>
        <p>La delegación seleccionada presenta un estado general de <b>{estado}</b> para el periodo evaluado.</p>
        <p class="small-text">
        El sistema muestra la información disponible por componente. Si una sección aparece sin registros,
        esto no implica error del sistema, sino ausencia de datos registrados para la delegación y trimestre seleccionados.
        </p>
    </div>
    """, unsafe_allow_html=True)

# =====================================================
# PAO ESTRATÉGICO
# =====================================================

elif pagina == "PAO Estratégico":

    st.header("PAO Estratégico / Despliegue")

    if pao_f.empty:
        st.info("Sin registros PAO para esta delegación y trimestre.")
    else:
        fila = pao_f.iloc[0]

        avance = convertir_porcentaje(fila.get("AVANCE_PAO_%", 0))
        total_pao = numero(fila.get("TOTAL_PAO_100", 0))
        despliegue = numero(fila.get("DESPLIEGUE_10", 0))
        estado_pao = fila.get("ESTADO_AVANCE_PAO", "Sin estado")
        estado_general = fila.get("ESTADO", "Sin estado")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Avance PAO", f"{avance:.1f}%")
        c2.metric("Total PAO", f"{total_pao:.0f} / 100")
        c3.metric("Despliegue", f"{despliegue:.1f} / 10")
        c4.metric("Estado", estado_pao)

        st.markdown("---")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("Semáforo PAO")
            st.plotly_chart(grafico_gauge(avance, "Avance PAO"), use_container_width=True)

        with col2:
            st.subheader("Componentes PAO")

            componentes = {
                "Validación DR": fila.get("INSTR_DR_5", 0),
                "Validación Delegación": fila.get("INSTR_DELEG_5", 0),
                "Recolección": fila.get("RECOLECCION_15", 0),
                "MIC-MAC": fila.get("MICMAC_15", 0),
                "Triángulo": fila.get("TRIANGULO_10", 0),
                "Líneas": fila.get("LINEAS_25", 0),
                "Informe": fila.get("INFORME_25", 0),
            }

            df_componentes = pd.DataFrame({
                "Componente": list(componentes.keys()),
                "Puntaje": [numero(v) for v in componentes.values()]
            })

            st.plotly_chart(
                grafico_barras(df_componentes, "Componente", "Puntaje"),
                use_container_width=True
            )

        st.markdown("---")

        st.subheader("Estado de Componentes")

        cols = st.columns(4)

        for i, row in df_componentes.iterrows():
            comp = row["Componente"]
            puntaje = row["Puntaje"]

            clase = "success-card" if puntaje > 0 else "danger-card"
            estado_txt = "Consolidado" if puntaje > 0 else "Pendiente"

            with cols[i % 4]:
                st.markdown(f"""
                <div class="card {clase}">
                    <b>{comp}</b><br>
                    <span class="small-text">{estado_txt}</span><br>
                    <b>{puntaje}</b>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        diagnostico = fila.get("DIAGNOSTICO_PAO", "Sin diagnóstico registrado.")
        observaciones = fila.get("OBSERVACIONES", "Sin observaciones.")

        st.markdown(f"""
        <div class="card info-card">
            <h3>Diagnóstico PAO</h3>
            <p>{diagnostico}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="card warning-card">
            <h3>Observaciones</h3>
            <p>{observaciones}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Ver datos PAO"):
            st.dataframe(pao_f, use_container_width=True)

# =====================================================
# ÓRDENES DE EJECUCIÓN
# =====================================================

elif pagina == "Órdenes de Ejecución":

    st.header("Órdenes de Ejecución")

    if oe_f.empty:
        st.info("Sin registros de OE para esta delegación y trimestre.")
    else:
        fila = oe_f.iloc[0]

        total_oe = numero(fila.get("Total OE", 0))
        acciones = numero(fila.get("Total acciones ejecutadas", 0))
        articulacion = numero(fila.get("OE con articulación", 0))
        validas = numero(fila.get("OE válidas", 0))
        parciales = numero(fila.get("OE con cumplimiento parcial", 0))
        sin_mal = numero(fila.get("OE sin planificación en MAL", 0))

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Total OE", int(total_oe))
        c2.metric("Acciones ejecutadas", int(acciones))
        c3.metric("OE con articulación", int(articulacion))
        c4.metric("OE sin MAL", int(sin_mal))

        st.markdown("---")

        indicadores = pd.DataFrame({
            "Indicador": [
                "Total OE",
                "Acciones ejecutadas",
                "OE con articulación",
                "OE válidas",
                "OE parciales",
                "OE sin MAL"
            ],
            "Valor": [
                total_oe,
                acciones,
                articulacion,
                validas,
                parciales,
                sin_mal
            ]
        })

        st.plotly_chart(
            grafico_barras(indicadores, "Indicador", "Valor"),
            use_container_width=True
        )

        st.markdown("---")

        informe = fila.get("Informe automático (justificación técnica operativa)", "Sin informe.")
        sintesis = fila.get("Acciones y Resultados (síntesis de acciones)", "Sin síntesis.")
        criterio = fila.get("Criterio Técnico (sustento técnico)", "Sin criterio técnico.")
        validacion = fila.get("Validación Final", fila.get("Validación Final ", "Sin validación."))

        st.markdown(f"""
        <div class="card info-card">
            <h3>Justificación Técnica</h3>
            <p>{informe}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="card success-card">
            <h3>Síntesis de Acciones</h3>
            <p>{sintesis}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="card warning-card">
            <h3>Criterio Técnico</h3>
            <p>{criterio}</p>
            <p><b>Validación:</b> {validacion}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Ver datos OE"):
            st.dataframe(oe_f, use_container_width=True)

# =====================================================
# MESAS DE ARTICULACIÓN
# =====================================================

elif pagina == "Mesas de Articulación":

    st.header("Mesas de Articulación Local")

    if mesas_f.empty:
        st.info("Sin registros de Mesas para esta delegación y trimestre.")
    else:
        fila = mesas_f.iloc[0]

        cumplimiento = convertir_porcentaje(fila.get("% Cumplimiento Integral", 0))
        total_envios = numero(fila.get("Total Envíos", 0))
        trazabilidad = fila.get("Nivel de Trazabilidad", "Sin registro")
        fase = fila.get("Fase de Madurez Operativa", "Sin registro")
        estado = fila.get("Estado de Gestión", "Sin estado")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Cumplimiento", f"{cumplimiento:.1f}%")
        c2.metric("Total envíos", int(total_envios))
        c3.metric("Trazabilidad", trazabilidad)
        c4.metric("Estado", estado)

        st.markdown("---")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("Cumplimiento Integral MAL")
            st.plotly_chart(grafico_gauge(cumplimiento, "Cumplimiento MAL"), use_container_width=True)

        with col2:
            st.subheader("Estado Operativo")
            st.markdown(f"""
            <div class="card info-card">
                <h3>{fase}</h3>
                <p><b>Nivel de trazabilidad:</b> {trazabilidad}</p>
                <p><b>Estado:</b> {estado}</p>
            </div>
            """, unsafe_allow_html=True)

        justificacion = fila.get("Justificación Técnica Operativa", "Sin justificación registrada.")
        gobernanza = fila.get("Índice Gobernanza Local", "Sin registro")
        minuta = fila.get("Minuta", "Sin registro")
        asistencia = fila.get("Asistencia", "Sin registro")

        st.markdown("---")

        st.markdown(f"""
        <div class="card warning-card">
            <h3>Lectura Técnica MAL</h3>
            <p><b>Gobernanza local:</b> {gobernanza}</p>
            <p><b>Minuta:</b> {minuta} | <b>Asistencia:</b> {asistencia}</p>
            <p>{justificacion}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Ver datos MAL"):
            st.dataframe(mesas_f, use_container_width=True)

# =====================================================
# CONSOLIDADO REGIONAL
# =====================================================

elif pagina == "Consolidado Regional":

    st.header("Consolidado Regional")

    c1, c2, c3 = st.columns(3)

    c1.metric("Registros MAL Región", len(mesas_region))
    c2.metric("Registros OE Región", len(oe_region))
    c3.metric("Registros PAO Región", len(pao_region))

    st.markdown("---")

    delegaciones_region = sorted(
        control[control["Delegación Regional"] == region]["Delegación Policial"]
        .dropna()
        .unique()
    )

    resumen = []

    for d in delegaciones_region:
        mal_d = mesas_region[mesas_region["Delegación Policial"] == d]
        oe_d = oe_region[oe_region["Delegación Policial"] == d]
        pao_d = pao_region[pao_region["Delegación Policial"] == d]

        avance = 0
        if not pao_d.empty and "AVANCE_PAO_%" in pao_d.columns:
            avance = convertir_porcentaje(pao_d["AVANCE_PAO_%"].iloc[0])

        resumen.append({
            "Delegación Policial": d,
            "MAL": len(mal_d),
            "OE": len(oe_d),
            "PAO": len(pao_d),
            "Avance PAO": avance
        })

    resumen = pd.DataFrame(resumen)

    st.subheader("Comparativo Delegacional")

    fig = px.bar(
        resumen,
        x="Delegación Policial",
        y="Avance PAO",
        text="Avance PAO"
    )
    fig.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font_color="white",
        xaxis_tickangle=-45
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Disponibilidad de Información por Componente")

    fig2 = px.bar(
        resumen,
        x="Delegación Policial",
        y=["MAL", "OE", "PAO"],
        barmode="group"
    )
    fig2.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font_color="white",
        xaxis_tickangle=-45
    )
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("Ver tabla regional"):
        st.dataframe(resumen, use_container_width=True)
