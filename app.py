# app.py
# ---------------------------------------------------------
# App Streamlit: Comparador Exámenes de BASE DE DATOS SIEL
# ---------------------------------------------------------
# Funcionalidad:
# - Subir 2 archivos .xlsx (valida extensión)
# - Normalizar/filtrar columnas según requisitos acordados
# - Convertir "Número" a formato numérico en ambos
# - Anti-join por "Número" (filas del 1º que NO están en el 2º)
# - Excel de salida: "EXAMENES PENDIENTES CARGAR.xlsx"
#   * Hoja1: "EXAMENES PENDIENTES" (orden de columnas del 2º archivo normalizado)
#   * Hoja2: "NOMBRES A ACTUALIZAR" (Número, Nombre exámen del 1º archivo)
# ---------------------------------------------------------

import io
import re
import unicodedata
import pandas as pd
import streamlit as st
from PIL import Image

# ------------------------------
# Configuración de página y cabecera
# ------------------------------
st.set_page_config(page_title="Comparador Exámenes de BASE DE DATOS SIEL", layout="wide")

# Mostrar logo y título
try:
    logo = Image.open("logo_siel.png")
    st.image(logo, width=250)
except Exception:
    st.warning("⚠️ Logo no encontrado. Asegúrate de incluir 'logo_siel.png' en la carpeta de la app.")

st.title("Comparador Exámenes de BASE DE DATOS SIEL")
st.caption("Servicio de Salud Araucanía Sur – Gestión de Información de Laboratorios Clínicos")

# ------------------------------
# Utilidades
# ------------------------------
def strip_accents(s: str) -> str:
    if s is None:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")

def norm_key(s: str) -> str:
    """
    Normaliza nombre de columna: quita acentos, minúsculas,
    colapsa espacios, y elimina no alfanuméricos (excepto espacio).
    """
    s = strip_accents(s).lower().strip()
    s = re.sub(r"\\s+", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return s

def coerce_numero(series: pd.Series) -> pd.Series:
    """
    Convierte 'Número' a numérico: extrae dígitos, maneja vacíos como NaN.
    """
    cleaned = series.astype(str).str.extract(r"(\\d+)", expand=False)
    return pd.to_numeric(cleaned, errors="coerce")

def ensure_xlsx(file) -> bool:
    name = file.name if file else ""
    return name.lower().endswith(".xlsx")

# ------------------------------
# Esquemas y mapeos de columnas
# ------------------------------

# 1) BASE DE DATOS SIEL -> conservar solo estas columnas (orden final)
BASE_KEEP_CANONICAL = [
    "Número",
    "Nombre exámen",
    "Disponibilidad",
    "Área de trabajo",
    "Sección",
    "Código FONASA",
    "Nombre FONASA",
    "Estado",
    "Analito principal",
    "Contenedor",
    "Tipo muestra",
    "Obtención",
]

# Aliases aceptados para la BASE
BASE_ALIASES = {
    "numero": "Número",
    "número": "Número",

    "nombre examen": "Nombre exámen",
    "nombre exámen": "Nombre exámen",

    "disponibilidad": "Disponibilidad",

    "area de trabajo": "Área de trabajo",
    "área de trabajo": "Área de trabajo",

    "seccion": "Sección",
    "sección": "Sección",

    "codigo fonasa": "Código FONASA",
    "código fonasa": "Código FONASA",

    "nombre fonasa": "Nombre FONASA",

    "estado": "Estado",

    "analito principal": "Analito principal",
    "contenedor": "Contenedor",

    "tipo muestra": "Tipo muestra",
    "obtencion": "Obtención",
    "obtención": "Obtención",

    # Campos que se descartan si aparecen:
    "codigo hca": None,
    "labdate codigo": None,
    "labdate nombre": None,
    "tipo solicitud": None,
    "codigo loinc": None,
    "nombre loinc": None,
    "tiempo de proceso": None,
    "tiempo de recepcion": None,
    "tiempo de recepción": None,
    "usuario creador": None,
    "usuario modificador": None,
    "volumen muestra pediatrica": None,
    "volumen muestra pediátrica": None,
    "volumen muestra adulto": None,
}

# 2) CARTERA DE PRESTACIONES (columnas de entrada y normalización)
CARTERA_INPUT = [
    "Analito principal",
    "Area de trabajo",
    "Código FONASA",
    "Contenedor",
    "Disponibilidad",
    "Estado",
    "Nombre exámen SIEL",
    "Nombre FONASA",
    "Número",
    "Obtención",
    "Sección SIEL",
    "Tipo muestra",
]

# Normalización CARTERA -> canónicas para operar/ordenar
CARTERA_ALIASES = {
    "analito principal": "Analito principal",
    "area de trabajo": "Área de trabajo",
    "área de trabajo": "Área de trabajo",

    "codigo fonasa": "Código FONASA",
    "código fonasa": "Código FONASA",

    "contenedor": "Contenedor",
    "disponibilidad": "Disponibilidad",
    "estado": "Estado",

    "nombre examen siel": "Nombre exámen",
    "nombre exámen siel": "Nombre exámen",

    "nombre fonasa": "Nombre FONASA",

    "numero": "Número",
    "número": "Número",

    "obtencion": "Obtención",
    "obtención": "Obtención",

    "seccion siel": "Sección",
    "sección siel": "Sección",

    "tipo muestra": "Tipo muestra",
}

# Orden final para la hoja de pendientes (del 2º archivo ya normalizado)
OUTPUT_ORDER = [
    "Analito principal",
    "Área de trabajo",
    "Código FONASA",
    "Contenedor",
    "Disponibilidad",
    "Estado",
    "Nombre exámen",
    "Nombre FONASA",
    "Número",
    "Obtención",
    "Sección",
    "Tipo muestra",
]

def normalize_columns(df: pd.DataFrame, aliases: dict, drop_unmapped: bool = False) -> pd.DataFrame:
    """
    Renombra columnas usando 'aliases' (clave normalizada -> nombre canónico).
    Si drop_unmapped=True, descarta columnas no mapeadas.
    """
    col_map = {}
    for c in df.columns:
        key = norm_key(c)
        if key in aliases and aliases[key] is not None:
            col_map[c] = aliases[key]
        elif key in aliases and aliases[key] is None:
            col_map[c] = None  # descartar
        else:
            col_map[c] = c     # conservar sin cambio

    keep_cols = []
    rename_map = {}
    for old, new in col_map.items():
        if new is None:
            continue
        rename_map[old] = new
        keep_cols.append(old)

    df2 = df[keep_cols].rename(columns=rename_map)

    if drop_unmapped:
        allowed = set(v for v in aliases.values() if v is not None)
        df2 = df2[[c for c in df2.columns if c in allowed]]

    return df2

def ensure_columns(df: pd.DataFrame, required_order: list) -> pd.DataFrame:
    """
    Asegura que existan todas las columnas de required_order; si faltan, las crea vacías.
    Reordena según required_order.
    """
    for c in required_order:
        if c not in df.columns:
            df[c] = pd.NA
    return df[required_order]

# ------------------------------
# UI: Carga de archivos
# ------------------------------
st.subheader("1) Subir archivos .xlsx")

col1, col2 = st.columns(2)
with col1:
    file_base = st.file_uploader("BASE DE DATOS SIEL (.xlsx)", type=["xlsx"], key="base")
with col2:
    file_cartera = st.file_uploader("CARTERA DE PRESTACIONES (.xlsx)", type=["xlsx"], key="cartera")

if file_base and not ensure_xlsx(file_base):
    st.error("El archivo de BASE debe ser .xlsx")
if file_cartera and not ensure_xlsx(file_cartera):
    st.error("El archivo de CARTERA debe ser .xlsx")

if file_base and file_cartera:
    try:
        df_base_raw = pd.read_excel(file_base, dtype=str)
        df_cart_raw = pd.read_excel(file_cartera, dtype=str)
    except Exception as e:
        st.error(f"Error al leer los .xlsx: {e}")
        st.stop()

    st.success("Archivos cargados correctamente.")

    # ------------------------------
    # Normalización BASE
    # ------------------------------
    st.subheader("2) Normalización de columnas")
    st.markdown("**BASE DE DATOS SIEL** → conservar columnas definidas, con aliases y acentos normalizados.")
    df_base = normalize_columns(df_base_raw, BASE_ALIASES, drop_unmapped=False)
    df_base = ensure_columns(df_base, BASE_KEEP_CANONICAL)

    # Normalización CARTERA
    st.markdown("**CARTERA DE PRESTACIONES** → normalizar nombres a canónico (Nombre exámen / Sección / Área).")
    df_cart = normalize_columns(df_cart_raw, CARTERA_ALIASES, drop_unmapped=False)

    # ------------------------------
    # Convertir "Número" a numérico en ambos
    # ------------------------------
    st.subheader("3) Conversión de 'Número' a formato numérico")
    if "Número" not in df_base.columns:
        st.error("En BASE DE DATOS SIEL no se encontró la columna 'Número' tras la normalización.")
        st.stop()
    if "Número" not in df_cart.columns:
        st.error("En CARTERA DE PRESTACIONES no se encontró la columna 'Número' tras la normalización.")
        st.stop()

    df_base["Número"] = coerce_numero(df_base["Número"])
    df_cart["Número"] = coerce_numero(df_cart["Número"])

    with st.expander("Ver primeras filas (BASE normalizada)"):
        st.dataframe(df_base.head(10), use_container_width=True)
    with st.expander("Ver primeras filas (CARTERA normalizada)"):
        st.dataframe(df_cart.head(10), use_container_width=True)

    # ------------------------------
    # Anti-join por Número
    # ------------------------------
    st.subheader("4) Pendientes por cargar (anti-join por 'Número')")
    numeros_cartera = set(df_cart["Número"].dropna().unique().tolist())
    mask_pendientes = ~df_base["Número"].isin(numeros_cartera)
    df_pendientes = df_base.loc[mask_pendientes].copy()

    # Orden de salida = OUTPUT_ORDER (del 2º archivo normalizado)
    df_pendientes_out = ensure_columns(df_pendientes.copy(), OUTPUT_ORDER)

    st.write(f"Total pendientes por cargar: **{len(df_pendientes_out)}**")
    with st.expander("Ver primeras filas pendientes"):
        st.dataframe(df_pendientes_out.head(20), use_container_width=True)

    # ------------------------------
    # Comparación de nombres por Número
    # ------------------------------
    st.subheader("5) Nombres a actualizar (coinciden en Número, difieren en 'Nombre exámen')")

    if "Nombre exámen" not in df_base.columns:
        st.error("En BASE falta 'Nombre exámen' después de normalizar.")
        st.stop()
    if "Nombre exámen" not in df_cart.columns:
        st.error("En CARTERA falta 'Nombre exámen' después de normalizar (desde 'Nombre exámen SIEL').")
        st.stop()

    df_join = pd.merge(
        df_base[["Número", "Nombre exámen"]].copy(),
        df_cart[["Número", "Nombre exámen"]].copy(),
        on="Número",
        how="inner",
        suffixes=("_base", "_cart"),
    )

    def clean_str(x):
        return str(x).strip() if pd.notna(x) else x

    neq_mask = df_join.apply(
        lambda r: (clean_str(r["Nombre exámen_base"]) != clean_str(r["Nombre exámen_cart"])),
        axis=1
    )

    df_nombres_actualizar = df_join.loc[neq_mask, ["Número", "Nombre exámen_base"]].copy()
    df_nombres_actualizar.rename(columns={"Nombre exámen_base": "Nombre exámen"}, inplace=True)

    st.write(f"Total nombres a actualizar: **{len(df_nombres_actualizar)}**")
    with st.expander("Ver primeras filas de nombres a actualizar"):
        st.dataframe(df_nombres_actualizar.head(50), use_container_width=True)

    # ------------------------------
    # Generar Excel con dos hojas
    # ------------------------------
    st.subheader("6) Descargar resultado")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_pendientes_out.to_excel(writer, index=False, sheet_name="EXAMENES PENDIENTES")
        df_nombres_actualizar.to_excel(writer, index=False, sheet_name="NOMBRES A ACTUALIZAR")

    st.download_button(
        label="⬇️ Descargar EXAMENES PENDIENTES CARGAR.xlsx",
        data=buffer.getvalue(),
        file_name="EXAMENES PENDIENTES CARGAR.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.success("Listo. Archivo generado con ambas hojas.")
else:
    st.info("Sube ambos archivos .xlsx para continuar.")
