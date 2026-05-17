import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================

st.set_page_config(
    page_title="SIGESS 2026",
    layout="wide"
)

st.title("SIGESS 2026")
st.subheader("Sistema Integral de Gestión Estratégica")

# =====================================================
# CONEXIÓN GOOGLE SHEETS
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

    columnas_base = [
        "Delegación Regional",
        "Delegación Policial",
        "Trimestre"
    ]

    for col in columnas_base:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


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
# VALIDACIÓN DE COLUMNAS
# =====================================================

columnas_necesarias = [
    "Delegación Regional",
    "Delegación Policial",
    "Trimestre"
]

for nombre, df in {
    "MESAS_FINAL": mesas,
    "OE_FINAL": oe,
    "PAO_FINAL": pao,
    "CONTROL_FILTROS": control
}.items():

    faltantes = [c for c in columnas_necesarias if c not in df.columns]

    if faltantes:
        st.error(f"La hoja {nombre} no tiene estas columnas: {faltantes}")
        st.stop()


# =====================================================
# FILTROS GENERALES
# =====================================================

st.markdown("---")
st.header("Filtros de consulta")

col1, col2, col3 = st.columns(3)

with col1:
    region = st.selectbox(
        "Delegación Regional",
        sorted(control["Delegación Regional"].dropna().unique())
    )

with col2:
    delegaciones_filtradas = control[
        control["Delegación Regional"] == region
    ]["Delegación Policial"].dropna().unique()

    delegacion = st.selectbox(
        "Delegación Policial",
        sorted(delegaciones_filtradas)
    )

with col3:
    trimestre = st.selectbox(
        "Trimestre",
        ["I Trimestre", "II Trimestre", "III Trimestre", "IV Trimestre"]
    )


# =====================================================
# FUNCIÓN DE FILTRO
# =====================================================
# Importante:
# No se filtra por región en las bases operativas,
# porque algunas hojas pueden almacenar datos poco a poco.
# La región solo sirve para ordenar la selección de delegación.

def filtrar_por_delegacion_trimestre(df):
    return df[
        (df["Delegación Policial"] == delegacion) &
        (df["Trimestre"] == trimestre)
    ]


mesas_f = filtrar_por_delegacion_trimestre(mesas)
oe_f = filtrar_por_delegacion_trimestre(oe)
pao_f = filtrar_por_delegacion_trimestre(pao)


# =====================================================
# RESUMEN EJECUTIVO
# =====================================================

st.markdown("---")
st.header("Resumen Ejecutivo")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Registros Mesas", len(mesas_f))

with c2:
    st.metric("Registros OE", len(oe_f))

with c3:
    st.metric("Registros PAO", len(pao_f))


# =====================================================
# MESAS DE ARTICULACIÓN
# =====================================================

st.markdown("---")
st.header("Mesas de Articulación Local")

if mesas_f.empty:
    st.info("Sin registros de Mesas para esta delegación y trimestre.")
else:
    st.dataframe(mesas_f, use_container_width=True)


# =====================================================
# ÓRDENES DE EJECUCIÓN
# =====================================================

st.markdown("---")
st.header("Órdenes de Ejecución")

if oe_f.empty:
    st.info("Sin registros de OE para esta delegación y trimestre.")
else:
    st.dataframe(oe_f, use_container_width=True)


# =====================================================
# PAO / DESPLIEGUE
# =====================================================

st.markdown("---")
st.header("Plan Anual Operativo / Despliegue")

if pao_f.empty:
    st.info("Sin registros de PAO para esta delegación y trimestre.")
else:
    st.dataframe(pao_f, use_container_width=True)


# =====================================================
# DEPURACIÓN OPCIONAL
# =====================================================

with st.expander("Verificación técnica"):
    st.write("Región seleccionada:", region)
    st.write("Delegación seleccionada:", delegacion)
    st.write("Trimestre seleccionado:", trimestre)

    st.write("Columnas MESAS:", list(mesas.columns))
    st.write("Columnas OE:", list(oe.columns))
    st.write("Columnas PAO:", list(pao.columns))
