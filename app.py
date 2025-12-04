import streamlit as st
import pandas as pd
from io import BytesIO
import altair as alt

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
    "Sube el archivo SIEL",
    type=["xlsx"],
    key="siel"
)
st.caption("Este archivo contiene la información cargada en SIEL.")

archivo_cartera = st.file_uploader(
    "Sube el archivo de la  cartera de prestaciones  SSASUR",
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
# Función auxiliar: DataFrame a Excel (bytes) para descarga simple
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

        # -------------------------------------------------------------------
        # 7. Sección de descargas (comparación SIEL vs cartera)
        # -------------------------------------------------------------------
        st.subheader("Descarga de resultados")

        col1, col2 = st.columns(2)

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

        st.write("")
        st.write("")

        # Resumen de cantidades
        st.markdown("**Resumen rápido:**")
        st.write(f"- Exámenes en SIEL y no en cartera: {len(examenes_siel_no_en_cartera)}")
        st.write(f"- Exámenes en cartera y no en SIEL: {len(examenes_cartera_no_en_siel)}")

        # -------------------------------------------------------------------
        # Análisis por hospitales SSASUR (datos + Excel + gráficos)
        # -------------------------------------------------------------------
        st.subheader("Análisis por hospitales")

        # Asegurar que exista 'Nombre exámen SIEL' en df_bd
        if "Nombre exámen SIEL" not in df_bd.columns and "Nombre exámen" in df_bd.columns:
            df_bd = df_bd.rename(columns={"Nombre exámen": "Nombre exámen SIEL"})

        # Volver al inicio del archivo de cartera para leer todas las hojas
        archivo_cartera.seek(0)
        xls = pd.ExcelFile(archivo_cartera)

        # 1. Cargar hojas de hospitales desde el archivo de cartera
        dfs_hospitales = {
            h: pd.read_excel(xls, sheet_name=h)
            for h in HOSPITALES
        }

        # 2. Matriz base con Número y Nombre exámen SIEL
        df_merged = df_bd[["Número", "Nombre exámen SIEL"]].drop_duplicates().copy()

        # 3. Construcción de matriz hospitalaria
        for h in HOSPITALES:
            df_h = dfs_hospitales[h].copy()

            # Detectar columna Número
            if "Número" in df_h.columns:
                num_col = "Número"
            else:
                num_col = df_h.columns[0]  # Columna A

            # Normalizar Cartera
            df_h["Cartera"] = (
                df_h["Cartera"]
                .astype(str)
                .str.strip()
                .str.upper()
                .replace({"NAN": None, "": None})
            )

            tmp = (
                df_h[[num_col, "Cartera"]]
                .rename(columns={num_col: "Número", "Cartera": h})
                .drop_duplicates(subset="Número", keep="last")
            )

            df_merged = df_merged.merge(tmp, on="Número", how="left")

        # 4. Normalización final de la matriz (SI / NO / NO INFORMADO)
        cartera_norm = df_merged[HOSPITALES].copy()

        for h in HOSPITALES:
            cartera_norm[h] = cartera_norm[h].fillna("NO INFORMADO")
            cartera_norm[h] = cartera_norm[h].replace("", "NO INFORMADO")
            cartera_norm[h] = cartera_norm[h].str.upper().str.strip()

        # Matriz completa final (Número + Nombre exámen SIEL + hospitales)
        df_matriz = pd.concat(
            [df_merged[["Número", "Nombre exámen SIEL"]], cartera_norm],
            axis=1
        )

        # 5. Exámenes que ningún hospital realiza (todos NO)
        mask_nadie = (cartera_norm == "NO").all(axis=1)
        examenes_nadie_realiza = df_matriz.loc[
            mask_nadie, ["Número", "Nombre exámen SIEL"]
        ]

        # 6. Exámenes no informados (algún hospital NO INFORMADO)
        mask_no_inf = (cartera_norm == "NO INFORMADO").any(axis=1)
        df_no_informado = df_matriz.loc[
            mask_no_inf, ["Número", "Nombre exámen SIEL"]
        ].copy()

        def hospitales_no_inf(row):
            return ", ".join([h for h in HOSPITALES if row[h] == "NO INFORMADO"])

        df_no_informado["Hospitales_no_informaron"] = df_matriz.loc[
            mask_no_inf, HOSPITALES
        ].apply(hospitales_no_inf, axis=1)

        # 7. Botón para descargar todo en un único Excel (análisis hospitales)
        def exportar_excel_multi():
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                examenes_nadie_realiza.to_excel(
                    writer, index=False, sheet_name="NINGUN_HOSPITAL_REALIZA"
                )
                df_no_informado.to_excel(
                    writer, index=False, sheet_name="NO_INFORMADO"
                )
                df_matriz.to_excel(
                    writer, index=False, sheet_name="MATRIZ_COMPLETA"
                )
            buffer.seek(0)
            return buffer

        st.download_button(
            label="Descargar análisis por hospitales (Excel)",
            data=exportar_excel_multi(),
            file_name="ANALISIS_HOSPITALES_SSASUR.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # -------------------------------------------------------------------
        # Pestaña de visualización (gráficos)
        # -------------------------------------------------------------------
        st.write("")
        st.write("")
        st.subheader("Visualización")

        tab1, tab2, tab3 = st.tabs([
            "Barras por hospital",
            "Heatmap exámenes vs hospital",
            "Resumen gráfico"
        ])

        # 1) Barras apiladas SI / NO / NO INFORMADO por hospital
        with tab1:
            df_long = (
                cartera_norm
                .reset_index(drop=False)
                .melt(id_vars="index", value_vars=HOSPITALES,
                      var_name="Hospital", value_name="Estado")
            )
            df_counts = (
                df_long
                .groupby(["Hospital", "Estado"])
                .size()
                .reset_index(name="Cantidad")
            )

            chart_barras = (
                alt.Chart(df_counts)
                .mark_bar()
                .encode(
                    x=alt.X("Hospital:N", title="Hospital"),
                    y=alt.Y("Cantidad:Q", title="Cantidad de exámenes"),
                    color=alt.Color("Estado:N", title="Estado"),
                    tooltip=["Hospital", "Estado", "Cantidad"]
                )
                .properties(
                    width=700,
                    height=400,
                    title="Distribución de exámenes por hospital según estado de cartera"
                )
            )
            st.altair_chart(chart_barras, use_container_width=True)

        # 2) Heatmap de exámenes vs hospital
        with tab2:
            # Limitamos a 80 exámenes para que sea legible
            df_heat = df_matriz.head(80).copy()
            heat_long = df_heat.melt(
                id_vars=["Número", "Nombre exámen SIEL"],
                value_vars=HOSPITALES,
                var_name="Hospital",
                value_name="Estado"
            )

            chart_heat = (
                alt.Chart(heat_long)
                .mark_rect()
                .encode(
                    x=alt.X("Hospital:N", title="Hospital"),
                    y=alt.Y("Nombre exámen SIEL:N",
                            title="Examen (primeros 80)",
                            sort="ascending"),
                    color=alt.Color("Estado:N", title="Estado"),
                    tooltip=["Número", "Nombre exámen SIEL", "Hospital", "Estado"]
                )
                .properties(
                    width=700,
                    height=600,
                    title="Mapa de exámenes vs hospital (estado de cartera)"
                )
            )
            st.altair_chart(chart_heat, use_container_width=True)

        # 3) Resumen gráfico (pie chart)
        with tab3:
            total_nadie = len(examenes_nadie_realiza)
            total_no_inf = len(df_no_informado)
            total_siel_no_cart = len(examenes_siel_no_en_cartera)
            total_cart_no_siel = len(examenes_cartera_no_en_siel)

            df_pie = pd.DataFrame({
                "Categoria": [
                    "SIEL no en cartera",
                    "Cartera no en SIEL",
                    "Ningún hospital realiza",
                    "Exámenes con NO INFORMADO"
                ],
                "Valor": [
                    total_siel_no_cart,
                    total_cart_no_siel,
                    total_nadie,
                    total_no_inf
                ]
            })

            chart_pie = (
                alt.Chart(df_pie)
                .mark_arc()
                .encode(
                    theta="Valor:Q",
                    color="Categoria:N",
                    tooltip=["Categoria", "Valor"]
                )
                .properties(
                    width=500,
                    height=400,
                    title="Resumen global de inconsistencias / brechas"
                )
            )
            st.altair_chart(chart_pie, use_container_width=True)

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
