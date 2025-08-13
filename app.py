# app.py (versión minimal con logo y hoja 'BD')
import io, re, unicodedata
import pandas as pd
import streamlit as st
from PIL import Image

st.set_page_config(page_title="Comparador Exámenes de BASE DE DATOS SIEL", layout="wide")

# Logo y título
try:
    st.image("logo_siel.png", width=220)
except Exception:
    st.warning("⚠️ Logo no encontrado. Guarda 'logo_siel.png' junto a app.py.")
st.title("Comparador Exámenes de BASE DE DATOS SIEL")

# Utilidades
def strip_accents(s): 
    return "" if s is None else "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")
def norm_key(s):
    s = strip_accents(s).lower().strip()
    s = re.sub(r"\s+", " ", s);  s = re.sub(r"[^a-z0-9 ]", "", s);  return s
def coerce_numero(s): 
    return pd.to_numeric(s.astype(str).str.extract(r"(\d+)", expand=False), errors="coerce")
def normalize_columns(df, aliases):
    col_map = {c: (aliases.get(norm_key(c)) if norm_key(c) in aliases else c) for c in df.columns}
    keep, ren = [], {}
    for old, new in col_map.items():
        if new is None: continue
        keep.append(old); ren[old] = new
    return df[keep].rename(columns=ren)
def ensure_columns(df, order):
    for c in order:
        if c not in df.columns: df[c] = pd.NA
    return df[order]

# Esquemas
BASE_KEEP = ["Número","Nombre exámen","Disponibilidad","Área de trabajo","Sección","Código FONASA",
             "Nombre FONASA","Estado","Analito principal","Contenedor","Tipo muestra","Obtención"]
BASE_ALIASES = {
    "numero":"Número","número":"Número","nombre examen":"Nombre exámen","nombre exámen":"Nombre exámen",
    "disponibilidad":"Disponibilidad","area de trabajo":"Área de trabajo","área de trabajo":"Área de trabajo",
    "seccion":"Sección","sección":"Sección","codigo fonasa":"Código FONASA","código fonasa":"Código FONASA",
    "nombre fonasa":"Nombre FONASA","estado":"Estado","analito principal":"Analito principal","contenedor":"Contenedor",
    "tipo muestra":"Tipo muestra","obtencion":"Obtención","obtención":"Obtención",
    # descartar extras
    "codigo hca":None,"labdate codigo":None,"labdate nombre":None,"tipo solicitud":None,"codigo loinc":None,
    "nombre loinc":None,"tiempo de proceso":None,"tiempo de recepcion":None,"tiempo de recepción":None,
    "usuario creador":None,"usuario modificador":None,"volumen muestra pediatrica":None,
    "volumen muestra pediátrica":None,"volumen muestra adulto":None,
}
CARTERA_ALIASES = {
    "analito principal":"Analito principal","area de trabajo":"Área de trabajo","área de trabajo":"Área de trabajo",
    "codigo fonasa":"Código FONASA","código fonasa":"Código FONASA","contenedor":"Contenedor",
    "disponibilidad":"Disponibilidad","estado":"Estado",
    "nombre examen siel":"Nombre exámen","nombre exámen siel":"Nombre exámen",
    "nombre fonasa":"Nombre FONASA","numero":"Número","número":"Número",
    "obtencion":"Obtención","obtención":"Obtención","seccion siel":"Sección","sección siel":"Sección",
    "tipo muestra":"Tipo muestra",
}
OUTPUT_ORDER = ["Analito principal","Área de trabajo","Código FONASA","Contenedor","Disponibilidad","Estado",
                "Nombre exámen","Nombre FONASA","Número","Obtención","Sección","Tipo muestra"]

# UI mínima
c1, c2 = st.columns(2)
with c1: file_base = st.file_uploader("BASE DE DATOS SIEL (.xlsx)", type=["xlsx"], key="base")
with c2: file_cartera = st.file_uploader("CARTERA DE PRESTACIONES (.xlsx, hoja BD)", type=["xlsx"], key="cartera")

if file_base and file_cartera:
    # Base: primera hoja; Cartera: hoja BD
    df_base_raw = pd.read_excel(file_base, dtype=str)
    df_cart_raw = pd.read_excel(file_cartera, sheet_name="BD", dtype=str)

    # Normalizar + asegurar columnas
    df_base = ensure_columns(normalize_columns(df_base_raw, BASE_ALIASES), BASE_KEEP)
    df_cart = normalize_columns(df_cart_raw, CARTERA_ALIASES)

    # Número a numérico
    df_base["Número"] = coerce_numero(df_base["Número"]); df_cart["Número"] = coerce_numero(df_cart["Número"])

    # Anti-join (pendientes)
    numeros_cartera = set(df_cart["Número"].dropna().unique())
    df_pendients = ensure_columns(df_base[~df_base["Número"].isin(numeros_cartera)].copy(), OUTPUT_ORDER)

    # Nombres a actualizar
    df_join = pd.merge(df_base[["Número","Nombre exámen"]],
                       df_cart[["Número","Nombre exámen"]],
                       on="Número", how="inner", suffixes=("_base","_cart"))
    clean = lambda x: str(x).strip() if pd.notna(x) else x
    neq = df_join.apply(lambda r: clean(r["Nombre exámen_base"]) != clean(r["Nombre exámen_cart"]), axis=1)
    df_names = df_join.loc[neq, ["Número","Nombre exámen_base"]].rename(columns={"Nombre exámen_base":"Nombre exámen"})

    # Excel final
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df_pendients.to_excel(w, index=False, sheet_name="EXAMENES PENDIENTES")
        df_names.to_excel(w, index=False, sheet_name="NOMBRES A ACTUALIZAR")

    st.download_button("⬇️ Descargar EXAMENES PENDIENTES CARGAR.xlsx",
                       data=buf.getvalue(),
                       file_name="EXAMENES PENDIENTES CARGAR.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("Sube ambos archivos .xlsx (segundo: hoja 'BD') para generar el resultado.")

