import streamlit as st
import pandas as pd
from io import BytesIO

# -------------------------------------------------------------------
# Configuración básica de la página
# -------------------------------------------------------------------
st.set_page_config(
    page_title="CARTERA DE PRESTACIONES, REVISIÓN",
    layout="centered"
)

# -------------------------------------------------------------------
# Encabezado: logo + título
# -------------------------------------------------------------------
# El archivo de imagen debe llamarse "logo_siel.png"
# y estar en la misma carpeta que este app.py
col_izq, col_centro, col_der = st.columns([1, 2, 1])
with col_centro:
    st.image("logo_siel.png", width=220)

st.markdown(
    "<h1 style='text-align:center;'>CARTERA DE PRESTACIONES, REVISIÓN</h1>",
    unsafe_allow_html=True
)

st.write("")  # pequeño espacio

# -------------------------------------------------------------------
# Carga de archivos
# -------------------------------------------------------------------
st.subheader("Carga de archivos")

archivo_siel = st.file_uploader(
    "Sube el archivo SIEL (LABORATORIOHOSPITALHERNANHENRIQUEZARAVENA_EXAMENES_VERSION_GLOBAL_04122025.xlsx)",
    type=["xlsx"],
    key="siel"
)
st.caption("Este archivo contiene la información cargada en SIEL.")

archivo_cartera = st.file_uploader(
    "Sube el archivo de cartera SSASUR (CARTERA DE PRESTACIONES SIEL SSAS_EXAMENES_VERSION_GLOBAL_2025-2026.xlsx)",
    type=["xlsx"],
    key="cartera"
)
st.caption("Este archivo contiene la información de la cartera de prestaciones disponible en SSASUR.")

st.write("")  # espacio

# Lista de hojas de hospitales en la cartera
HOSPITALES = [
    "HHHA", "CAPLC", "HINI", "HPITRU", "HLAUTA", "HVILLA",
    "HCARAH", "HCUNCO", "HTOLTE", "HGALVA", "HLONCO",
    "HGORBE", "HSAAVE", "HVILCU"
]

# -------------------------------------------------------------------
# Función auxiliar: DataFrame a Excel (bytes) para descarga
# -------------------------------------------------------------------
def df_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Hoja1") -> BytesIO:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    buffer.seek(0)
    return buffer

# -------------------------------------------------------------------
# Lógica principal (solo si ambos archivos fueron cargados)
# -------------------------------------------------------------------
if archivo_siel is not None and archivo_cartera is not None:
    try:
        # -------------------------
        # 1. Cargar dataframes base
        # -------------------------
        df_siel = pd.read_excel(archivo_siel)
        df_bd = pd.read_excel(archivo_cartera, sheet_name="BD")  # cartera base

        # --------------------------------------------
        # 2. Homologar nombres de columnas en SIEL
        # --------------------------------------------
        rename_map = {}
        if "Nombre exámen" in df_siel.columns:
            rename_map["Nombre exámen"] = "Nombre exámen SIEL"
        if "Sección" in df_siel.columns:
            rename_map["Sección"] = "Sección SIEL"
        if rename_map:
            df_siel = df_siel.rename(columns=rename_map)

        # -------------------------------------------------
        # 3. Alinear columnas de df_siel con las de df_bd
        # -------------------------------------------------
        df_siel = df_siel[df_bd.columns]

        # Normalización de Número para comparaciones
        siel_num = df_siel["Número"].astype(str).str.strip()
        bd_num = df_bd["Número"].astype(str).str.strip()

        # -------------------------------------------------
        # 4. Exámenes en SIEL y no en cartera (BD)
        # -------------------------------------------------
        mask_siel_no_en_bd = ~siel_num.isin(bd_num)
        examenes_siel_no_en_cartera = df_siel[mask_siel_no_en_bd].copy()

        # -------------------------------------------------
        # 5. Exámenes en cartera (BD) y no en SIEL
        # -------------------------------------------------
        mask_bd_no_en_siel = ~bd_num.isin(siel_num)
        examenes_cartera_no_en_siel = df_bd[mask_bd_no_en_siel].copy()

        # -------------------------------------------------
        # 6. Exámenes de BD que ningún hospital realiza
        # -------------------------------------------------
        # Cargar hojas de hospitales
        dfs_hospitales = {
            h: pd.read_excel(archivo_cartera, sheet_name=h) for h in HOSPITALES
        }

        # Base con todos los exámenes de BD por Número
        df_merged = df_bd[["Número"]].drop_duplicates().copy()

        # Unir la columna "Cartera" de cada hospital usando Número
        for h in HOSPITALES:
            df_h = dfs_hospitales[h]

            # Si existe "Número", la usamos; si no, usamos la primera columna como Número
            if "Número" in df_h.columns:
                num_col = "Número"
            else:
                num_col = df_h.columns[0]  # columna A

            tmp = (
                df_h[[num_col, "Cartera"]]
                .rename(columns={num_col: "Número", "Cartera": h})
                .drop_duplicates(subset="Número", keep="last")
            )

            df_merged = df_merged.merge(tmp, on="Número", how="left")

        # Al menos un hospital realiza el examen si tiene "SI" en alguna columna
        mask_alguno_si = (df_merged[HOSPITALES] == "SI").any(axis=1)
        numeros_no_nadie = df_merged.loc[~mask_alguno_si, "Número"]

        examenes_no_realiza_nadie = df_bd[df_bd["Número"].isin(numeros_no_nadie)].copy()

        # -------------------------------------------------------------------
        # 7. Sección de descargas
        # -------------------------------------------------------------------
        st.subheader("Descarga de resultados")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.download_button(
                label="SIEL no en cartera",
                data=df_to_excel_bytes(
                    examenes_siel_no_en_cartera,
                    sheet_name="SIEL_no_en_cartera"
                ),
                file_name="examenes_siel_no_en_cartera.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with col2:
            st.download_button(
                label="Cartera no en SIEL",
                data=df_to_excel_bytes(
                    examenes_cartera_no_en_siel,
                    sheet_name="cartera_no_en_SIEL"
                ),
                file_name="examenes_cartera_no_en_siel.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with col3:
            st.download_button(
                label="Exámenes que nadie realiza",
                data=df_to_excel_bytes(
                    examenes_no_realiza_nadie,
                    sheet_name="no_realiza_nadie"
                ),
                file_name="examenes_no_realiza_nadie.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        st.write("")
        st.write("")

        # Resumen de cantidades
        st.markdown("**Resumen rápido:**")
        st.write(f"- Exámenes en SIEL y no en cartera: {len(examenes_siel_no_en_cartera)}")
        st.write(f"- Exámenes en cartera y no en SIEL: {len(examenes_cartera_no_en_siel)}")
        st.write(f"- Exámenes en cartera que ningún hospital realiza: {len(examenes_no_realiza_nadie)}")

    except Exception as e:
        st.error(f"Ocurrió un error al procesar los archivos: {e}")

else:
    st.info("Sube ambos archivos para habilitar los resultados y las descargas.")

# -------------------------------------------------------------------
# Pie de página
# -------------------------------------------------------------------
st.write("")
st.write("")
st.markdown(
    "<p style='text-align:center; font-size:0.8rem;'>"
    "Realizado por TM. Camilo Muñoz, Diciembre 2025."
    "</p>",
    unsafe_allow_html=True
)

