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
# FUNCIONES PERICIALES DE LIMPIEZA Y PROCESAMIENTO
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
    # 1. Limpieza de espacios en los encabezados de columnas
    df.columns = df.columns.astype(str).str.strip()

    # 2. Control profundo sobre columnas clave de control territorial
    for col in ["Delegación Regional", "Delegación Policial", "Trimestre"]:
        if col in df.columns:
            # Elimina saltos de línea internos y limpia espacios en extremos
            df[col] = df[col].astype(str).str.replace(r'[\r\n]+', '', regex=True).str.strip()
            
    # 3. Arreglo definitivo para espacios múltiples intermedios en el texto (ej: "I Trimestre ")
    if "Trimestre" in df.columns:
        df["Trimestre"] = df["Trimestre"].str.replace(r'\s+', ' ', regex=True).str.strip()

    return df


def numero(valor):
    try:
        if isinstance(valor, str):
            # Elimina símbolos de porcentaje y limpia espacios antes de convertir
            valor = valor.replace('%', '').strip()
        return float(valor)
    except Exception:
        return 0.0


def convertir_porcentaje(valor):
    valor = numero(valor)
    # Si viene en formato decimal (ej: 0.85), lo escala a entero (85.0)
    if valor <= 1.0 and valor > 0.0:
        return valor * 100.0
    return valor


def normalizar_texto(texto):
    # Remueve tildes, mayúsculas y espacios para garantizar cruces 100% efectivos
    return (str(texto).lower().strip()
            .replace('á', 'a')
            .replace('é', 'e')
            .replace('í', 'i')
            .replace('ó', 'o')
            .replace('ú', 'u'))


def filtrar(df, delegacion, trimestre):
    if df.empty:
        return df

    # Filtrado tolerante a fallas de digitación o acentos en el Sheets
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
# COMPONENTES VISUALES (PLOTLY)
# =====================================================

def grafico_gauge(valor, titulo):
    valor = convertir_porcentaje(valor)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        title={"text": titulo, "font": {"size": 18}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "white"},
            "bar": {"color": "#3B82F6"}, # Azul estructural de barra
            "steps": [
                {"range": [0, 69], "color": "#7F1D1D"},   # Rojo Crítico
                {"range": [70, 84], "color": "#92400E"},  # Amarillo / Naranja Regular
                {"range": [85, 100], "color": "#14532D"}  # Verde Óptimo
            ]
        }
    ))

    fig.update_layout(
        paper_bgcolor="#111827",
        font_color="white",
        height=260,
        margin=dict(l=30, r=30, t=50, b=20)
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
    fig.update_traces(marker_color='#3B82F6', textposition='outside')
    return fig


# =====================================================
# EXTRACCIÓN Y LIMPIEZA DE SÁBANAS DESDE GOOGLE
# =====================================================

try:
    mesas = limpiar_df(cargar_hoja(URL_MASTER, "MESAS_FINAL"))
    oe = limpiar_df(cargar_hoja(URL_MASTER, "OE_FINAL"))
    pao = limpiar_df(cargar_hoja(URL_MASTER, "PAO_FINAL"))
    control = limpiar_df(cargar_hoja(URL_MASTER, "CONTROL_FILTROS"))
except Exception as e:
    st.error("Error Crítico: No se pudieron extraer los datos desde Google Sheets.")
    st.exception(e)
    st.stop()


# =====================================================
# MENÚ LATERAL DE FILTROS (SIDEBAR)
# =====================================================

st.sidebar.title("SIGESS 2026")
st.sidebar.caption("Centro de Monitoreo Estratégico")

pagina = st.sidebar.radio(
    "Navegación Módulos",
    [
        "Inicio Ejecutivo",
        "PAO Estratégico",
        "Órdenes de Ejecución",
        "Mesas de Articulación",
        "Consolidado Regional"
    ]
)

st.sidebar.markdown("---")

# Carga dinámica de filtros regionales sin duplicados
regiones_disponibles = sorted(control["Delegación Regional"].dropna().unique())
region = st.sidebar.selectbox("Delegación Regional", regiones_disponibles)

# Carga de delegaciones vinculadas estrictamente a la región seleccionada
delegaciones_vinculadas = sorted(
    control[control["Delegación Regional"].apply(normalizar_texto) == normalizar_texto(region)]["Delegación Policial"]
    .dropna()
    .unique()
)
delegacion = st.sidebar.selectbox("Delegación Policial", delegaciones_vinculadas)

trimestre = st.sidebar.selectbox(
    "Trimestre de Auditoría",
    ["I Trimestre", "II Trimestre", "III Trimestre", "IV Trimestre"]
)

st.sidebar.markdown("---")
st.sidebar.caption("Estrategia Sembremos Seguridad")


# =====================================================
# EJECUCIÓN DE FILTROS OPERACIONALES
# =====================================================

mesas_f = filtrar(mesas, delegacion, trimestre)
oe_f = filtrar(oe, delegacion, trimestre)
pao_f = filtrar(pao, delegacion, trimestre)

mesas_region = filtrar_region(mesas, region, trimestre)
oe_region = filtrar_region(oe, region, trimestre)
pao_region = filtrar_region(pao, region, trimestre)


# =====================================================
# ENCABEZADO GENERAL DE LA PLATAFORMA
# =====================================================

st.markdown('<div class="big-title">SIGESS 2026 — CENTRO DE CONTROL</div>', unsafe_allow_html=True)
st.caption(f"Área Operativa: {region} | Unidad: {delegacion} | Temporalidad: {trimestre}")
st.markdown("---")


# =====================================================
# MÓDULO 1: INICIO EJECUTIVO (PANTALLA PRINCIPAL)
# =====================================================

if pagina == "Inicio Ejecutivo":

    st.header("Resumen del Estado Policial")

    # Blindaje contra índices vacíos para evitar caídas del sistema
    total_mesas = len(mesas_f) if not mesas_f.empty else 0
    total_oe = len(oe_f) if not oe_f.empty else 0
    total_pao = len(pao_f) if not pao_f.empty else 0

    avance_pao = 0.0
    if not pao_f.empty and "AVANCE_PAO_%" in pao_f.columns:
        avance_pao = convertir_porcentaje(pao_f["AVANCE_PAO_%"].iloc[0])

    cumplimiento_mal = 0.0
    if not mesas_f.empty and "% Cumplimiento Integral" in mesas_f.columns:
        cumplimiento_mal = convertir_porcentaje(mesas_f["% Cumplimiento Integral"].iloc[0])

    # FÓRMULA DE PROYECCIÓN ANUAL ABSOLUTA (Basada en los 4 periodos obligatorios)
    # Suma las notas reales registradas del año de esa delegación y las divide estrictamente entre 4
    df_todas_mesas_anio = mesas[mesas["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(delegacion)]
    nota_anual_absoluta = 0.0
    if not df_todas_mesas_anio.empty:
        nota_anual_absoluta = df_todas_mesas_anio["% Cumplimiento Integral"].apply(numero).sum() / 4.0
        nota_anual_absoluta = convertir_porcentaje(nota_anual_absoluta)

    # Bloque de KPIs Principales en fila
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros en Mesas (MAL)", total_mesas)
    c2.metric("Órdenes de Ejecución (OE)", total_oe)
    c3.metric("Plan Operativo (PAO)", total_pao)
    c4.metric("Porcentaje Avance PAO", f"{avance_pao:.1f}%")

    st.markdown("---")

    # Despliegue de Tacómetros de Medición
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Cumplimiento M.A.L.")
        st.plotly_chart(grafico_gauge(cumplimiento_mal, "Trimestral"), use_container_width=True)
    with col2:
        st.subheader("Avance del PAO")
        st.plotly_chart(grafico_gauge(avance_pao, "Trimestral"), use_container_width=True)
    with col3:
        st.subheader("Proyección Cumplimiento Anual")
        # Medidor calibrado con la fórmula estricta de acumulación anual absoluta (esfuerzo/4)
        st.plotly_chart(grafico_gauge(nota_anual_absoluta, "Fórmula Absoluta Anual"), use_container_width=True)

    st.markdown("---")

    # Cuadro de estado dinámico institucional
    estado, clase = clasificar_estado(cumplimiento_mal)
    st.markdown(f"""
    <div class="card {clase}">
        <h3>Lectura Ejecutiva de Control Mando</h3>
        <p>La unidad policial presenta un estado de rendimiento de: <b>{estado}</b> en el eje de Mesas de Articulación.</p>
        <p class="small-text">
        <b>Nota de Fiscalización:</b> Conforme a las directrices de la Dirección de Operaciones, la Proyección de Cumplimiento Anual calcula de forma estricta la constancia institucional. 
        Si una delegación obtiene un 100% en el primer trimestre pero no registra actividad el resto del año, su nota final absoluta será del 25%.
        </p>
    </div>
    """, unsafe_allow_html=True)


# =====================================================
# MÓDULO 2: PLAN ANUAL OPERATIVO (PAO ESTRATÉGICO)
# =====================================================

elif pagina == "PAO Estratégico":

    st.header("PAO Estratégico / Despliegue de Diagnóstico")

    if pao_f.empty:
        st.info("No se registran auditorías del PAO para esta delegación en el periodo seleccionado.")
    else:
        fila = pao_f.iloc[0]

        avance = convertir_porcentaje(fila.get("AVANCE_PAO_%", 0))
        total_pao = numero(fila.get("TOTAL_PAO_100", 0))
        despliegue = numero(fila.get("DESPLIEGUE_10", 0))
        estado_pao = fila.get("ESTADO_AVANCE_PAO", "Sin estado")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Avance PAO Acumulado", f"{avance:.1f}%")
        c2.metric("Puntaje PAO Bruto", f"{total_pao:.0f} / 100")
        c3.metric("Nivel Despliegue", f"{despliegue:.1f} / 10")
        c4.metric("Estado Administrativo", estado_pao)

        st.markdown("---")
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("Semáforo Técnico PAO")
            st.plotly_chart(grafico_gauge(avance, "Progreso PAO"), use_container_width=True)

        with col2:
            st.subheader("Desglose Metodológico de Puntajes")
            componentes = {
                "Validación DR": fila.get("INSTR_DR_5", 0),
                "Validación Delegación": fila.get("INSTR_DELEG_5", 0),
                "Recolección Datos": fila.get("RECOLECCION_15", 0),
                "Análisis MIC-MAC": fila.get("MICMAC_15", 0),
                "Triángulo Violencia": fila.get("TRIANGULO_10", 0),
                "Líneas de Acción": fila.get("LINEAS_25", 0),
                "Informe Territorial": fila.get("INFORME_25", 0),
            }

            df_componentes = pd.DataFrame({
                "Componente": list(componentes.keys()),
                "Puntaje Asignado": [numero(v) for v in componentes.values()]
            })
            st.plotly_chart(grafico_barras(df_componentes, "Componente", "Puntaje Asignado"), use_container_width=True)

        st.markdown("---")
        st.subheader("Estado Fino de Soportes Metodológicos")
        cols = st.columns(4)

        for i, row in df_componentes.iterrows():
            comp = row["Componente"]
            puntaje = row["Puntaje Asignado"]
            clase_card = "success-card" if puntaje > 0 else "danger-card"
            estado_txt = "Consolidado / Válido" if puntaje > 0 else "Pendiente de Procesar"

            with cols[i % 4]:
                st.markdown(f"""
                <div class="card {clase_card}">
                    <b>{comp}</b><br>
                    <span class="small-text">{estado_txt}</span><br>
                    <b>Puntos: {puntaje}</b>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        diagnostico = fila.get("DIAGNOSTICO_PAO", "Sin diagnóstico registrado en la sábana.")
        observaciones = fila.get("OBSERVACIONES", "Sin observaciones registradas.")

        st.markdown(f"""
        <div class="card info-card">
            <h3>Diagnóstico pericial del PAO</h3>
            <p>{diagnostico}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="card warning-card">
            <h3>Observaciones Técnicas de Fiscalización</h3>
            <p>{observaciones}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Ver Matriz de Datos Originales PAO"):
            st.dataframe(pao_f, use_container_width=True)


# =====================================================
# MÓDULO 3: ÓRDENES DE EJECUCIÓN (O.E.)
# =====================================================

elif pagina == "Órdenes de Ejecución":

    st.header("Cumplimiento de Órdenes de Ejecución (ORDOP-0022-2026)")

    if oe_f.empty:
        st.info("La unidad seleccionada no registra datos de Órdenes de Ejecución en este trimestre.")
    else:
        fila = oe_f.iloc[0]

        total_oe = numero(fila.get("Total OE", 0))
        acciones = numero(fila.get("Total acciones ejecutadas", 0))
        articulacion = numero(fila.get("OE con articulación", 0))
        validas = numero(fila.get("OE válidas", 0))
        parciales = numero(fila.get("OE con cumplimiento parcial", 0))
        sin_mal = numero(fila.get("OE sin planificación en MAL", 0))
        pct_cumplimiento = convertir_porcentaje(fila.get("% cumplimiento", 0))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Volumen Total OE", int(total_oe))
        c2.metric("Acciones en Campo", int(acciones))
        c3.metric("OE con Articulación", int(articulacion))
        c4.metric("OE Fuera de M.A.L.", int(sin_mal))

        st.markdown("---")
        
        col_graf_1, col_graf_2 = st.columns(2)
        with col_graf_1:
            st.subheader("Rendimiento de Gestión OE")
            st.plotly_chart(grafico_gauge(pct_cumplimiento, "Cumplimiento OE"), use_container_width=True)
            
        with col_graf_2:
            st.subheader("Distribución de Indicadores Operativos")
            df_indicadores_oe = pd.DataFrame({
                "Métrica Operativa": ["Total OE", "Acciones Ejecutadas", "Con Articulación", "Válidas", "Parciales", "Sin M.A.L."],
                "Cantidad": [total_oe, acciones, articulacion, validas, parciales, sin_mal]
            })
            st.plotly_chart(grafico_barras(df_indicadores_oe, "Métrica Operativa", "Cantidad"), use_container_width=True)

        st.markdown("---")
        
        # Extracción segura salvando el espacio en blanco del final ("Validación Final ")
        informe = fila.get("Informe automático (justificación técnica operativa)", "Sin informe registrado.")
        sintesis = fila.get("Acciones y Resultados (síntesis de acciones)", "Sin detalle de acciones.")
        criterio = fila.get("Criterio Técnico (sustento técnico)", "Sin criterio técnico.")
        validacion_final = fila.get("Validación Final", fila.get("Validación Final ", "Pendiente de Validar"))

        st.markdown(f"""
        <div class="card info-card">
            <h3>Justificación Técnica Automatizada</h3>
            <p>{informe}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="card success-card">
            <h3>Síntesis de Acciones Operacionales y Resultados</h3>
            <p>{sintesis}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="card warning-card">
            <h3>Criterio y Dictamen Técnico de la Dirección</h3>
            <p>{criterio}</p>
            <p><b>Estado de Validación de Evidencia:</b> {validacion_final}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Ver Matriz de Datos Originales OE"):
            st.dataframe(oe_f, use_container_width=True)


# =====================================================
# MÓDULO 4: MESAS DE ARTICULACIÓN LOCAL (M.A.L.)
# =====================================================

elif pagina == "Mesas de Articulación":

    st.header("Módulo de Mesas de Articulación Local (M.A.L.)")

    if mesas_f.empty:
        st.info("Sin evidencias o registros consolidados para esta Mesa de Articulación en el periodo.")
    else:
        fila = mesas_f.iloc[0]

        cumplimiento = convertir_porcentaje(fila.get("% Cumplimiento Integral", 0))
        total_envios = numero(fila.get("Total Envíos", 0))
        trazabilidad = fila.get("Nivel de Trazabilidad", "Sin registro")
        fase = fila.get("Fase de Madurez Operativa", "Sin registro")
        estado_gestion = fila.get("Estado de Gestión", "Sin estado")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Nota del Trimestre", f"{cumplimiento:.1f}%")
        c2.metric("Formularios Transmitidos", int(total_envios))
        c3.metric("Alineamiento Territorial", trazabilidad)
        c4.metric("Estado de la Mesa", estado_gestion)

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Calibración Integral de la Mesa")
            st.plotly_chart(grafico_gauge(cumplimiento, "Índice de Madurez"), use_container_width=True)

        with col2:
            st.subheader("Ciclo de Despliegue en Territorio")
            st.markdown(f"""
            <div class="card info-card">
                <h3>{fase}</h3>
                <p><b>Nivel de Trazabilidad ORDOP-0022:</b> {trazabilidad}</p>
                <p><b>Condición Actual de Auditoría:</b> {estado_gestion}</p>
            </div>
            """, unsafe_allow_html=True)

        justificacion = fila.get("Justificación Técnica Operativa", "Sin redacción registrada.")
        gobernanza = fila.get("Índice Gobernanza Local", "Sin datos")
        minuta = fila.get("Minuta", "No")
        asistencia = fila.get("Asistencia", "No")

        st.markdown("---")
        st.markdown(f"""
        <div class="card warning-card">
            <h3>Dictamen Pericial de Articulación Colectiva</h3>
            <p><b>Gobernanza e Impacto de Actores:</b> {gobernanza}</p>
            <p><b>Cumplimiento Formal:</b> Acta/Minuta Levantada: <b>{minuta}</b> | Control de Firmas Asistencia: <b>{asistencia}</b></p>
            <hr style="border-color:#374151;">
            <p>{justificacion}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Ver Matriz de Datos Originales M.A.L."):
            st.dataframe(mesas_f, use_container_width=True)


# =====================================================
# MÓDULO 5: CONSOLIDADO REGIONAL (VISTA DE COMPARATIVAS)
# =====================================================

elif pagina == "Consolidado Regional":

    st.header(f"Diagnóstico Comparativo de Mandos — {region}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Registros M.A.L. en la Región", len(mesas_region))
    c2.metric("Órdenes de Ejecución Regionales", len(oe_region))
    c3.metric("Hojas de Ruta PAO Validadas", len(pao_region))

    st.markdown("---")

    # Extrae el mapa completo de unidades de la región actual
    mask_cantones = control["Delegación Regional"].apply(normalizar_texto) == normalizar_texto(region)
    cantones_region = sorted(control[mask_cantones]["Delegación Policial"].dropna().unique())

    datos_resumen_regional = []

    for c in cantones_region:
        # Filtra cada componente por unidad policial para armar la tabla cruzada de la región
        df_mal_c = mesas_region[mesas_region["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(c)]
        df_oe_c = oe_region[oe_region["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(c)]
        df_pao_c = pao_region[pao_region["Delegación Policial"].apply(normalizar_texto) == normalizar_texto(c)]

        pct_avance_pao_regional = 0.0
        if not df_pao_c.empty and "AVANCE_PAO_%" in df_pao_c.columns:
            pct_avance_pao_regional = convertir_porcentaje(df_pao_c["AVANCE_PAO_%"].iloc[0])

        datos_resumen_regional.append({
            "Delegación Policial": c,
            "Envíos M.A.L.": len(df_mal_c),
            "Volumen O.E.": len(df_oe_c),
            "Auditorías PAO": len(df_pao_c),
            "Eficiencia PAO %": pct_avance_pao_regional
        })

    df_resumen_regional = pd.DataFrame(datos_resumen_regional)

    st.subheader("Gráfico de Eficiencia del Despliegue del PAO por Comandancia")
    fig_regional_pao = px.bar(
        df_resumen_regional,
        x="Delegación Policial",
        y="Eficiencia PAO %",
        text="Eficiencia PAO %"
    )
    fig_regional_pao.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font_color="white",
        xaxis_tickangle=-45
    )
    fig_regional_pao.update_traces(marker_color='#10B981', texttemplate='%{text:.1f}%', textposition='outside')
    st.plotly_chart(fig_regional_pao, use_container_width=True)

    st.markdown("---")

    st.subheader("Volumen de Actividad Transmitida por Unidad Policial")
    fig_regional_actividad = px.bar(
        df_resumen_regional,
        x="Delegación Policial",
        y=["Envíos M.A.L.", "Volumen O.E.", "Auditorías PAO"],
        barmode="group",
        labels={"value": "Cantidad de Registros", "variable": "Componente ESTRATEGIA"}
    )
    fig_regional_actividad.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font_color="white",
        xaxis_tickangle=-45
    )
    st.plotly_chart(fig_regional_actividad, use_container_width=True)

    with st.expander("Ver Matriz de Datos del Consolidado Regional de Comandancias"):
        st.dataframe(df_resumen_regional, use_container_width=True)
