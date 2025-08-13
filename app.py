# app.py (versión minimal con logo)
import io
import re
import unicodedata
import pandas as pd
import streamlit as st
from PIL import Image

st.set_page_config(page_title="Comparador Exámenes de BASE DE DATOS SIEL", layout="wide")

# Mostrar logo y título
try:
    logo = Image.open("logo_siel.png")
    st.image(logo, width=220)
except Exception:
    st.warning("⚠️ Logo no encontrado. Guarda el archivo como 'logo_siel.png' en la misma carpeta que app.py.")

st.title("Comparador Exámenes de BASE DE DATOS SIEL")

# ---------- Funciones auxiliares ----------
def strip_accents(s: str) -> str:
    if s is None:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")

def norm_key(s: str) -> str:
    s = strip_accents(s).lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return s

def coerce_numero(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.extract(r"(\d+)", expand=False)
    return pd.to_numeric(cleaned, errors="coerce")

def normalize_columns(df: pd.DataFrame, aliases: dict) -> pd.DataFrame:
    col_map = {}
    for c in df.columns:
        key = norm_key(c)
        if key in aliases and aliases[key] is not None:
            col_map[c] = aliases[key]
        elif key in aliases and aliases[key] is None:
            col_map[c] = None
        else:
            col_map[c] = c
    keep_cols, rename_map = [], {}
    for old, new in col_map.items():
        if new is None:
            continue
        rename_map[old] = new
        keep_cols.append(old)
    df2 = df[keep_cols].rename(columns=rename_map)
    return df2

def ensure_columns(df: pd.DataFrame, required_order: list) -> pd.DataFrame:
    for c in required_order:
        if c not in df.columns:
            df[c] = pd.NA
    return df[required_order]

# ---------- Configuración de columnas ----------
BASE_KEEP_CANONICAL = [
    "Número","Nombre exámen","Disponibilidad","Área de trabajo","Sección",
    "Código FONASA","Nombre FONASA","Estado","Analito principal","Contenedor",
    "Tipo muestra","Obtención",
]
BASE_ALIASES = {
    "numero":"Número","número":"Número",
    "nombre examen":"Nombre exámen","nombre exámen":"Nombre exámen",
    "disponibilidad":"Disponibilidad",
    "area de trabajo":"Área de trabajo","área de trabajo":"Área de trabajo",
    "seccion":"Sección","sección":"Sección",
    "codigo fonasa":"Código FONASA","código fonasa":"Código FONASA",
    "nombre fonasa":"Nombre FONASA","estado":"Estado",
    "analito principal":"Analito principal","contenedor":"Contenedor",
    "tipo muestra":"Tipo muestra","obtencion":"Obtención","obtención":"Obtención",
    # Descartar:
    "codigo hca":None,"labdate codigo":None,"labdate nombre":None,"tipo solicitud":None,
    "codigo loinc":None,"nombre loinc":None,"tiempo de proceso":None,
    "tiempo de recepcion":None,"tiempo de recepción":None,"usuario creador":None,
    "usuario modificador":None,"volumen muestra pediatrica":None,
    "volumen muestra pediátrica":None,"volumen muestra adulto":None,
}
CARTERA_ALIASES = {
    "analito principal":"Analito principal",
    "area de trabajo":"Área de trabajo","área de trabajo":"Área de trabajo",
    "codigo fonasa":"Código FONASA","código fonasa":"Código FONASA",
    "contenedor":"Contenedor","disponibilidad":"Disponibilidad","estado":"Estado",
    "nombre examen siel":"Nombre exámen","nombre exámen siel":"Nombre exámen",
    "nombre fonasa":"Nombre FONASA",
    "numero":"Número","número":"Número",
    "obtencion":"Obtención","obtención":"Obtención",
    "seccion siel":"Sección","sección siel":"Sección",
    "tipo muestra":"Tipo muestra",
}
OUTPUT_ORDER = [
    "Analito principal","Área de trabajo","Código FONASA","Contenedor",
    "Disponibilidad","Estado","Nombre exámen","Nombre FONASA",
    "Número","Obtención","Sección","Tipo muestra",
]

# ---------- UI: Carga y descarga ----------
col1, col2 = st.columns(2)
with col1:
    file_base = st.file_uploader("BASE DE DATOS SIEL (.xlsx)", type=["xlsx"], key="base")
with col2:
    file_cartera = st.file_uploader("CARTERA DE PRESTACIONES (.xlsx)", type=["xlsx"], key="cartera")

if file_base and file_cartera:
    df_base_raw = pd.read_excel(file_base, dtype=str)
    df_cart_raw = pd.read_excel(file_cartera, dtype=str)

    df_base = normalize_columns(df_base_raw, BASE_ALIASES)
    df_base = ensure_columns(df_base, BASE_KEEP_CANONICAL)
    df_cart = normalize_columns(df_cart_raw, CARTERA_ALIASES)

    df_base["Número"] = coerce_numero(df_base["Número"])
    df_cart["Número"] = coerce_numero(df_cart["Número"])

    numeros_cartera = set(df_cart["Número"].dropna().unique())
    df_pendientes_out = ensure_columns(df_base[~df_base["Número"].isin(numeros_cartera)].copy(), OUTPUT_ORDER)

    df_join = pd.merge(
        df_base[["Número","Nombre exámen"]],
        df_cart[["Número","Nombre exámen"]],
        on="Número", how="inner", suffixes=("_base","_cart")
    )
    def clean_str(x): return str(x).strip() if pd.notna(x) else x
    df_nombres_actualizar = df_join[
        df_join.apply(lambda r: clean_str(r["Nombre exámen_base"]) != clean_str(r["Nombre exámen_cart"]), axis=1)
    ][["Número","Nombre exámen_base"]].rename(columns={"Nombre exámen_base":"Nombre exámen"})

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_pendientes_out.to_excel(writer, index=False, sheet_name="EXAMENES PENDIENTES")
        df_nombres_actualizar.to_excel(writer, index=False, sheet_name="NOMBRES A ACTUALIZAR")

    st.download_button(
        "⬇️ Descargar EXAMENES PENDIENTES CARGAR.xlsx",
        data=buffer.getvalue(),
        file_name="EXAMENES PENDIENTES CARGAR.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Sube ambos archivos .xlsx para generar el resultado.")

