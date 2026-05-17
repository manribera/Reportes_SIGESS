import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="SIGESS 2026",
    layout="wide"
)

st.title("SIGESS 2026")
st.subheader("Sistema Integral de Gestión Estratégica")

st.markdown("---")

# =========================
# CARGA TEMPORAL DE DATOS
# =========================
# Primero lo hacemos con CSV o Excel exportado.
# Después lo conectamos directo a Google Sheets.

@st.cache_data
def cargar_datos():
    mesas = pd.read_csv("MESAS_FINAL.csv")
    oe = pd.read_csv("OE_FINAL.csv")
    pao = pd.read_csv("PAO_FINAL.csv")
    return mesas, oe, pao


try:
    mesas, oe, pao = cargar_datos()
except Exception as e:
    st.error("No se pudieron cargar los archivos de datos.")
    st.info("Por ahora colocá en la misma carpeta estos archivos: MESAS_FINAL.csv, OE_FINAL.csv y PAO_FINAL.csv")
    st.stop()


# =========================
# NORMALIZAR COLUMNAS
# =========================

columnas_necesarias = [
    "Delegación Regional",
    "Delegación Policial",
    "Trimestre"
]

for nombre, df in {
    "MESAS": mesas,
    "OE": oe,
    "PAO": pao
}.items():
    faltantes = [col for col in columnas_necesarias if col not in df.columns]
    if faltantes:
        st.error(f"En {nombre} faltan estas columnas: {faltantes}")
        st.stop()


# =========================
# FILTROS GLOBALES
# =========================

st.markdown("### Filtros de consulta")

col1, col2, col3 = st.columns(3)

regiones = sorted(mesas["Delegación Regional"].dropna().unique())

with col1:
    region = st.selectbox("Delegación Regional", regiones)

delegaciones = sorted(
    mesas[mesas["Delegación Regional"] == region]["Delegación Policial"]
    .dropna()
    .unique()
)

with col2:
    delegacion = st.selectbox("Delegación Policial", delegaciones)

with col3:
    trimestre = st.selectbox(
        "Trimestre",
        ["I Trimestre", "II Trimestre", "III Trimestre", "IV Trimestre"]
    )


# =========================
# APLICAR FILTROS
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


st.markdown("---")

# =========================
# RESUMEN EJECUTIVO
# =========================

st.header("Resumen Ejecutivo")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Registros Mesas", len(mesas_f))

with c2:
    st.metric("Registros OE", len(oe_f))

with c3:
    st.metric("Registros PAO", len(pao_f))


# =========================
# SECCIONES
# =========================

st.markdown("---")
st.header("Mesas de Articulación Local")
st.dataframe(mesas_f, use_container_width=True)

st.markdown("---")
st.header("Órdenes de Ejecución")
st.dataframe(oe_f, use_container_width=True)

st.markdown("---")
st.header("Plan Anual Operativo / Despliegue")
st.dataframe(pao_f, use_container_width=True)
