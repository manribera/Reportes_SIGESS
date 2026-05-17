import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# =========================
# CONFIGURACIÓN
# =========================

st.set_page_config(
    page_title="SIGESS 2026",
    layout="wide"
)

st.title("SIGESS 2026")
st.subheader("Sistema Integral de Gestión Estratégica")

# =========================
# GOOGLE SHEETS
# =========================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

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

# =========================
# URL LIBRO MAESTRO
# =========================

URL_MASTER = "https://docs.google.com/spreadsheets/d/1cl2OeKSqtt4YvOkVM90uHa6Xa4zGuknjUsYpsrXzL_c/edit?usp=sharing"

# =========================
# CARGAR HOJAS
# =========================

mesas = cargar_hoja(URL_MASTER, "MESAS_FINAL")
oe = cargar_hoja(URL_MASTER, "OE_FINAL")
pao = cargar_hoja(URL_MASTER, "PAO_FINAL")

# =========================
# VALIDAR COLUMNAS
# =========================

columnas = [
    "Delegación Regional",
    "Delegación Policial",
    "Trimestre"
]

for nombre, df in {
    "MESAS": mesas,
    "OE": oe,
    "PAO": pao
}.items():

    faltantes = [c for c in columnas if c not in df.columns]

    if faltantes:
        st.error(f"{nombre} no tiene columnas: {faltantes}")
        st.stop()

# =========================
# FILTROS
# =========================

st.markdown("---")
st.header("Filtros")

col1, col2, col3 = st.columns(3)

with col1:
    region = st.selectbox(
        "Delegación Regional",
        sorted(mesas["Delegación Regional"].dropna().unique())
    )

with col2:
    delegacion = st.selectbox(
        "Delegación Policial",
        sorted(
            mesas[
                mesas["Delegación Regional"] == region
            ]["Delegación Policial"].dropna().unique()
        )
    )

with col3:
    trimestre = st.selectbox(
        "Trimestre",
        sorted(mesas["Trimestre"].dropna().unique())
    )

# =========================
# FILTRAR
# =========================

def filtrar(df):

    return df[
        (df["Delegación Regional"] == region) &
        (df["Delegación Policial"] == delegacion) &
        (df["Trimestre"] == trimestre)
    ]

mesas_f = filtrar(mesas)
oe_f = filtrar(oe)
pao_f = filtrar(pao)

# =========================
# DASHBOARD
# =========================

st.markdown("---")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Registros Mesas", len(mesas_f))

with c2:
    st.metric("Registros OE", len(oe_f))

with c3:
    st.metric("Registros PAO", len(pao_f))

# =========================
# TABLAS
# =========================

st.markdown("---")
st.header("Mesas de Articulación")
st.dataframe(mesas_f, use_container_width=True)

st.markdown("---")
st.header("Órdenes de Ejecución")
st.dataframe(oe_f, use_container_width=True)

st.markdown("---")
st.header("PAO")
st.dataframe(pao_f, use_container_width=True)
