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

# =====================================================
# ESTILO
# =====================================================

st.markdown("""
<style>
.main {
    background-color: #111827;
}
.block-container {
    padding-top: 1.5rem;
}
h1, h2, h3 {
    color: #F9FAFB;
}
.stMetric {
    background-color: #1F2937;
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #374151;
}
div[data-testid="stMetricValue"] {
    color: #F9FAFB;
}
div[data-testid="stMetricLabel"] {
    color: #D1D5DB;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# GOOGLE SHEETS
# =====================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

URL_MASTER = "https://docs.google.com/spreadsheets/d/1cl2OeKSqtt4YvOkVM90uHa6Xa4zGuknjUsYpsrXzL_c/edit?usp=sharing"


@st.cache_data(ttl=300)
def cargar_hoja(sheet_url, nombre_hoja):
    creds_dict = st.secrets["gcp_service_account"]

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES
    )

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


def obtener_columna_numerica(df, posibles):
    for col in posibles:
        if col in df.columns:
            return col
    return None


# =====================================================
# CARGA
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
st.sidebar.caption("Sistema Integral de Gestión Estratégica")

pagina = st.sidebar.radio(
    "Navegación",
    [
        "Resumen Ejecutivo",
        "Consolidado Regional",
        "Mesas de Articulación",
        "Órdenes de Ejecución",
        "PAO / Despliegue"
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
st.sidebar.caption("Fuente: Libro maestro SIGESS 2026")

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
# ENCABEZADO
# =====================================================

st.title("SIGESS 2026")
st.caption(f"{region} | {delegacion} | {trimestre}")
st.markdown("---")

# =====================================================
# PÁGINA 1: RESUMEN EJECUTIVO
# =====================================================

if pagina == "Resumen Ejecutivo":

    st.header("Resumen Ejecutivo Delegacional")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Mesas registradas", len(mesas_f))

    with c2:
        st.metric("Órdenes de Ejecución", len(oe_f))

    with c3:
        st.metric("Registros PAO", len(pao_f))

    with c4:
        total_registros = len(mesas_f) + len(oe_f) + len(pao_f)
        st.metric("Registros totales", total_registros)

    st.markdown("---")

    col1, col2 = st.columns(2)

    resumen = pd.DataFrame({
        "Componente": ["Mesas", "OE", "PAO"],
        "Registros": [len(mesas_f), len(oe_f), len(pao_f)]
    })

    with col1:
        st.subheader("Distribución de registros")
        fig = px.bar(
            resumen,
            x="Componente",
            y="Registros",
            text="Registros",
            title=""
        )
        fig.update_layout(
            paper_bgcolor="#111827",
            plot_bgcolor="#111827",
            font_color="white"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Estado de información")
        fig = px.pie(
            resumen,
            names="Componente",
            values="Registros",
            hole=0.55
        )
        fig.update_layout(
            paper_bgcolor="#111827",
            plot_bgcolor="#111827",
            font_color="white"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Lectura ejecutiva")

    if total_registros == 0:
        st.info("No se registran datos para la delegación y trimestre seleccionados.")
    else:
        st.success(
            "La delegación presenta información registrada en al menos uno de los componentes SIGESS. "
            "Revise los apartados específicos para valorar trazabilidad, ejecución operativa y avance del PAO."
        )

# =====================================================
# PÁGINA 2: CONSOLIDADO REGIONAL
# =====================================================

elif pagina == "Consolidado Regional":

    st.header("Consolidado Regional")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Mesas en la región", len(mesas_region))

    with c2:
        st.metric("OE en la región", len(oe_region))

    with c3:
        st.metric("PAO en la región", len(pao_region))

    st.markdown("---")

    st.subheader("Registros por delegación")

    delegaciones_region = sorted(
        control[control["Delegación Regional"] == region]["Delegación Policial"]
        .dropna()
        .unique()
    )

    resumen_regional = []

    for d in delegaciones_region:
        resumen_regional.append({
            "Delegación Policial": d,
            "Mesas": len(mesas_region[mesas_region["Delegación Policial"] == d]),
            "OE": len(oe_region[oe_region["Delegación Policial"] == d]),
            "PAO": len(pao_region[pao_region["Delegación Policial"] == d])
        })

    resumen_regional = pd.DataFrame(resumen_regional)

    fig = px.bar(
        resumen_regional,
        x="Delegación Policial",
        y=["Mesas", "OE", "PAO"],
        barmode="group"
    )
    fig.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font_color="white",
        xaxis_tickangle=-45
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Ver tabla consolidada regional"):
        st.dataframe(resumen_regional, use_container_width=True)

# =====================================================
# PÁGINA 3: MESAS
# =====================================================

elif pagina == "Mesas de Articulación":

    st.header("Mesas de Articulación Local")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Registros MAL", len(mesas_f))

    col_cumplimiento = obtener_columna_numerica(
        mesas_f,
        ["% Cumplimiento Integral", "Cumplimiento Integral", "Porcentaje", "Cumplimiento"]
    )

    with c2:
        if col_cumplimiento and not mesas_f.empty:
            valor = pd.to_numeric(mesas_f[col_cumplimiento], errors="coerce").mean()
            st.metric("Cumplimiento promedio", f"{valor:.1f}%")
        else:
            st.metric("Cumplimiento promedio", "N/D")

    with c3:
        st.metric("Trimestre", trimestre)

    st.markdown("---")

    if mesas_f.empty:
        st.info("Sin registros de Mesas para esta delegación y trimestre.")
    else:
        if col_cumplimiento:
            valor = pd.to_numeric(mesas_f[col_cumplimiento], errors="coerce").mean()

            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=valor,
                title={"text": "Cumplimiento MAL"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "green"},
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
                height=320
            )
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("Ver detalle de Mesas"):
            st.dataframe(mesas_f, use_container_width=True)

# =====================================================
# PÁGINA 4: OE
# =====================================================

elif pagina == "Órdenes de Ejecución":

    st.header("Órdenes de Ejecución")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Registros OE", len(oe_f))

    col_total_oe = obtener_columna_numerica(
        oe_f,
        ["Total OE", "OE", "Cantidad OE"]
    )

    with c2:
        if col_total_oe and not oe_f.empty:
            total_oe = pd.to_numeric(oe_f[col_total_oe], errors="coerce").sum()
            st.metric("Total OE", int(total_oe))
        else:
            st.metric("Total OE", "N/D")

    col_acciones = obtener_columna_numerica(
        oe_f,
        ["Total acciones ejecutadas", "Acciones ejecutadas"]
    )

    with c3:
        if col_acciones and not oe_f.empty:
            total_acciones = pd.to_numeric(oe_f[col_acciones], errors="coerce").sum()
            st.metric("Acciones ejecutadas", int(total_acciones))
        else:
            st.metric("Acciones ejecutadas", "N/D")

    st.markdown("---")

    if oe_f.empty:
        st.info("Sin registros de OE para esta delegación y trimestre.")
    else:
        columnas_grafico = []

        for col in [
            "Total OE",
            "Total acciones ejecutadas",
            "OE con cumplimiento parcial",
            "OE no válidas",
            "OE sin planificación en MAL"
        ]:
            if col in oe_f.columns:
                columnas_grafico.append(col)

        if columnas_grafico:
            datos_oe = oe_f[columnas_grafico].apply(
                pd.to_numeric,
                errors="coerce"
            ).sum().reset_index()

            datos_oe.columns = ["Indicador", "Valor"]

            fig = px.bar(
                datos_oe,
                x="Indicador",
                y="Valor",
                text="Valor"
            )
            fig.update_layout(
                paper_bgcolor="#111827",
                plot_bgcolor="#111827",
                font_color="white",
                xaxis_tickangle=-25
            )
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("Ver detalle de Órdenes de Ejecución"):
            st.dataframe(oe_f, use_container_width=True)

# =====================================================
# PÁGINA 5: PAO
# =====================================================

elif pagina == "PAO / Despliegue":

    st.header("PAO / Despliegue")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Registros PAO", len(pao_f))

    col_avance = obtener_columna_numerica(
        pao_f,
        ["Porcentaje de Avance", "Avance", "% Avance"]
    )

    with c2:
        if col_avance and not pao_f.empty:
            avance = pd.to_numeric(pao_f[col_avance], errors="coerce").mean()
            st.metric("Avance PAO", f"{avance:.1f}%")
        else:
            st.metric("Avance PAO", "N/D")

    with c3:
        st.metric("Trimestre", trimestre)

    st.markdown("---")

    if pao_f.empty:
        st.info("Sin registros de PAO para esta delegación y trimestre.")
    else:
        componentes_pao = [
            "Val.Instrumentos de Recolección DR",
            "Val.Instrumentos de Recolección DP",
            "Recolección de Muestras",
            "MIC-MAC",
            "Triángulo de las Violencias",
            "Val.Líneas de Acción",
            "Val.Informe Territorial"
        ]

        columnas_existentes = [c for c in componentes_pao if c in pao_f.columns]

        if columnas_existentes:
            datos_pao = pao_f[columnas_existentes].apply(
                pd.to_numeric,
                errors="coerce"
            ).sum().reset_index()

            datos_pao.columns = ["Componente", "Puntaje"]

            fig = px.bar(
                datos_pao,
                x="Componente",
                y="Puntaje",
                text="Puntaje"
            )
            fig.update_layout(
                paper_bgcolor="#111827",
                plot_bgcolor="#111827",
                font_color="white",
                xaxis_tickangle=-35
            )
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("Ver detalle PAO"):
            st.dataframe(pao_f, use_container_width=True)
