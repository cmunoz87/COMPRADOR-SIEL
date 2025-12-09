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
# Carga de archivos (en 2 columnas, más compacto)
# -------------------------------------------------------------------
st.subheader("Carga de archivos")

col_siel, col_cartera = st.columns(2)

with col_siel:
    st.markdown("**Sube el archivo SIEL**")
    archivo_siel = st.file_uploader(
        " ",
        type=["xlsx"],
        key="siel"
    )
    st.caption("Este archivo contiene la información cargada en SIEL.")

with col_cartera:
    st.markdown("**Sube el archivo de la cartera de prestaciones SSASUR**")
    archivo_cartera = st.file_uploader(
        "  ",
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

        tab1, = st.tabs([
            "Barras por hospital",
        ])

        # 1) Barras apiladas SI / NO / NO INFORMADO por hospital
        with tab1:
            # Selector de hospital
            opcion_hosp = st.selectbox(
                "Selecciona hospital para visualizar",
                ["Todos los hospitales"] + HOSPITALES
            )

            # Pasar matriz a formato largo
            df_long = (
                cartera_norm
                .reset_index(drop=False)
                .melt(
                    id_vars="index",
                    value_vars=HOSPITALES,
                    var_name="Hospital",
                    value_name="Estado"
                )
            )

            # Agrupar por hospital y estado
            df_counts = (
                df_long
                .groupby(["Hospital", "Estado"])
                .size()
                .reset_index(name="Cantidad")
            )

            # Filtrar según elección del usuario
            if opcion_hosp != "Todos los hospitales":
                df_counts_plot = df_counts[df_counts["Hospital"] == opcion_hosp]
                titulo = f"Distribución de exámenes en {opcion_hosp}"
            else:
                df_counts_plot = df_counts
                titulo = "Distribución de exámenes por hospital según estado de cartera"

            # Gráfico
            chart_barras = (
                alt.Chart(df_counts_plot)
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
                    title=titulo
                )
            )
            st.altair_chart(chart_barras, use_container_width=True)

        # -------------------------------------------------------------------
        # Análisis por Nodo y nivel de complejidad (por examen)
        # -------------------------------------------------------------------
        st.write("")
        st.write("")
        st.subheader("Análisis por Nodo y nivel de complejidad (por examen)")

        # Definición de Nodos (según estructura entregada)
        NODOS = {
            "CENTRO": ["CAPLC", "HCUNCO"],
            "COSTERO": ["HINI", "HCARAH", "HSAAVE"],
            "SUR": ["HPITRU", "HTOLTE", "HGORBE"],
            "NORTE": ["HLAUTA", "HGALVA", "HVILCU"],
            "LACUSTRE": ["HVILLA", "HLONCO"],
        }

        # Definición de complejidad por hospital
        COMPLEJIDAD = {
            "HHHA": "ALTA",
            "CAPLC": "MEDIANA",
            "HINI": "MEDIANA",
            "HPITRU": "MEDIANA",
            "HLAUTA": "MEDIANA",
            "HVILLA": "MEDIANA",
            "HCARAH": "BAJA",
            "HCUNCO": "BAJA",
            "HTOLTE": "BAJA",
            "HGALVA": "BAJA",
            "HLONCO": "BAJA",
            "HGORBE": "BAJA",
            "HSAAVE": "BAJA",
            "HVILCU": "BAJA",
        }

        # Selector de examen a partir de df_matriz
        opciones_examen = df_matriz[["Número", "Nombre exámen SIEL"]].copy()
        opciones_examen["label"] = (
            opciones_examen["Número"].astype(str)
            + " - "
            + opciones_examen["Nombre exámen SIEL"].astype(str)
        )
        opciones_examen = opciones_examen.drop_duplicates(subset=["label"])

        examen_seleccionado = st.selectbox(
            "Selecciona un examen para analizar por Nodo y complejidad:",
            opciones_examen["label"].sort_values().tolist(),
        )

        if examen_seleccionado:
            fila_sel = opciones_examen.loc[
                opciones_examen["label"] == examen_seleccionado
            ].iloc[0]

            numero_sel = fila_sel["Número"]
            nombre_sel = fila_sel["Nombre exámen SIEL"]

            # Buscamos la fila correspondiente en df_matriz
            fila_examen = df_matriz[
                (df_matriz["Número"] == numero_sel)
                & (df_matriz["Nombre exámen SIEL"] == nombre_sel)
            ]

            if not fila_examen.empty:
                fila_examen = fila_examen.iloc[0]

                # Estados por hospital para ese examen
                estados_por_hospital = {
                    h: fila_examen[h] for h in HOSPITALES if h in fila_examen.index
                }

                # ------------------------------------------
                # 1) Resumen por NODO
                # ------------------------------------------
                datos_nodos = []
                for nodo, lista_hosp in NODOS.items():
                    estados = [
                        estados_por_hospital[h]
                        for h in lista_hosp
                        if h in estados_por_hospital
                    ]

                    total_hosp_nodo = len(estados)
                    if total_hosp_nodo == 0:
                        continue

                    n_si = sum(e == "SI" for e in estados)
                    n_no = sum(e == "NO" for e in estados)
                    n_no_inf = sum(e == "NO INFORMADO" for e in estados)

                    # Regla de estado del Nodo
                    if n_si >= 1:
                        estado_nodo = "SI"
                    elif n_si == 0 and n_no_inf > 0:
                        estado_nodo = "NO INFORMADO"
                    else:
                        estado_nodo = "NO"

                    porcentaje_si = round((n_si / total_hosp_nodo) * 100, 1)

                    datos_nodos.append(
                        {
                            "Nodo": nodo,
                            "Total_hospitales_nodo": total_hosp_nodo,
                            "Hospitales_SI": n_si,
                            "Hospitales_NO": n_no,
                            "Hospitales_NO_INFORMADO": n_no_inf,
                            "%_hospitales_SI": porcentaje_si,
                            "Estado_nodo": estado_nodo,
                        }
                    )

                df_nodos = pd.DataFrame(datos_nodos)

                # ------------------------------------------
                # 2) Resumen por nivel de COMPLEJIDAD
                # ------------------------------------------
                grupos_complejidad = {}
                for hosp, comp in COMPLEJIDAD.items():
                    if hosp in estados_por_hospital:
                        grupos_complejidad.setdefault(comp, []).append(hosp)

                datos_complejidad = []
                for comp, lista_hosp in grupos_complejidad.items():
                    estados = [estados_por_hospital[h] for h in lista_hosp]

                    total_hosp_comp = len(estados)
                    n_si = sum(e == "SI" for e in estados)
                    n_no = sum(e == "NO" for e in estados)
                    n_no_inf = sum(e == "NO INFORMADO" for e in estados)

                    porcentaje_si = round((n_si / total_hosp_comp) * 100, 1)

                    datos_complejidad.append(
                        {
                            "Complejidad": comp,
                            "Total_hospitales": total_hosp_comp,
                            "Hospitales_SI": n_si,
                            "Hospitales_NO": n_no,
                            "Hospitales_NO_INFORMADO": n_no_inf,
                            "%_hospitales_SI": porcentaje_si,
                        }
                    )

                df_complejidad = pd.DataFrame(datos_complejidad)

                # ------------------------------------------
                # Mostrar tablas resumen
                # ------------------------------------------
                st.markdown(
                    f"**Examen seleccionado:** `{numero_sel}` - {nombre_sel}"
                )

                col_tab1, col_tab2 = st.columns(2)
                with col_tab1:
                    st.markdown("**Resumen por Nodo**")
                    st.dataframe(df_nodos, use_container_width=True)

                with col_tab2:
                    st.markdown("**Resumen por nivel de complejidad**")
                    st.dataframe(df_complejidad, use_container_width=True)

                # ------------------------------------------
                # Gráfico de porcentaje de hospitales que realizan el examen
                # por Nodo
                # ------------------------------------------
                st.markdown("**Porcentaje de hospitales que realizan el examen por Nodo**")
                chart_nodos = (
                    alt.Chart(df_nodos)
                    .mark_bar()
                    .encode(
                        x=alt.X("Nodo:N", title="Nodo"),
                        y=alt.Y("%_hospitales_SI:Q", title="% hospitales que realizan el examen"),
                        tooltip=[
                            "Nodo",
                            "%_hospitales_SI",
                            "Hospitales_SI",
                            "Total_hospitales_nodo",
                            "Estado_nodo",
                        ],
                    )
                    .properties(
                        width=600,
                        height=300,
                    )
                )
                st.altair_chart(chart_nodos, use_container_width=True)

                # ------------------------------------------
                # Gráfico de porcentaje de hospitales que realizan el examen
                # por nivel de complejidad
                # ------------------------------------------
                st.markdown("**Porcentaje de hospitales que realizan el examen por nivel de complejidad**")
                chart_comp = (
                    alt.Chart(df_complejidad)
                    .mark_bar()
                    .encode(
                        x=alt.X("Complejidad:N", title="Nivel de complejidad"),
                        y=alt.Y("%_hospitales_SI:Q", title="% hospitales que realizan el examen"),
                        tooltip=[
                            "Complejidad",
                            "%_hospitales_SI",
                            "Hospitales_SI",
                            "Total_hospitales",
                        ],
                    )
                    .properties(
                        width=600,
                        height=300,
                    )
                )
                st.altair_chart(chart_comp, use_container_width=True)
            else:
                st.warning("No se encontró el examen seleccionado en la matriz.")

        # -------------------------------------------------------------------
        # Carteras agregadas (básica, nodos, alta, baja complejidad)
        # -------------------------------------------------------------------
        st.write("")
        st.write("")
        st.subheader("Carteras agregadas (estándar básica, nodos, alta y baja complejidad)")

        # 1) Cartera estándar básica: exámenes que TODOS los hospitales realizan
        mask_cartera_basica = (cartera_norm[HOSPITALES] == "SI").all(axis=1)
        cartera_basica = df_matriz.loc[
            mask_cartera_basica,
            ["Número", "Nombre exámen SIEL"]
        ].drop_duplicates()

        # 2) Cartera nodos: exámenes realizados por TODOS los laboratorios de mediana complejidad (nodos)
        hospitales_mediana = ["CAPLC", "HINI", "HPITRU", "HLAUTA", "HVILLA"]
        mask_cartera_nodos = (cartera_norm[hospitales_mediana] == "SI").all(axis=1)
        cartera_nodos = df_matriz.loc[
            mask_cartera_nodos,
            ["Número", "Nombre exámen SIEL"]
        ].drop_duplicates()

        # 3) Cartera alta complejidad (HHHA)
        mask_alta = cartera_norm["HHHA"] == "SI"
        cartera_alta = df_matriz.loc[
            mask_alta,
            ["Número", "Nombre exámen SIEL"]
        ].drop_duplicates()

        # 4) Cartera baja complejidad: exámenes realizados por TODOS los hospitales de baja complejidad
        hospitales_baja = [h for h, comp in COMPLEJIDAD.items() if comp == "BAJA"]
        mask_baja = (cartera_norm[hospitales_baja] == "SI").all(axis=1)
        cartera_baja = df_matriz.loc[
            mask_baja,
            ["Número", "Nombre exámen SIEL"]
        ].drop_duplicates()

        # Botón de descarga Excel con 4 hojas
        def exportar_carteras_excel():
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                cartera_basica.to_excel(writer, index=False, sheet_name="CARTERA_BASICA")
                cartera_nodos.to_excel(writer, index=False, sheet_name="CARTERA_NODOS")
                cartera_alta.to_excel(writer, index=False, sheet_name="ALTA_COMPLEJIDAD")
                cartera_baja.to_excel(writer, index=False, sheet_name="BAJA_COMPLEJIDAD")
            buffer.seek(0)
            return buffer

        st.download_button(
            label="Descargar carteras agregadas (Excel)",
            data=exportar_carteras_excel(),
            file_name="CARTERAS_AGREGADAS_SSASUR.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Gráfico con la cantidad de exámenes en cada cartera
        df_resumen_carteras = pd.DataFrame({
            "Tipo_cartera": [
                "Cartera estándar básica (todos los hospitales)",
                "Cartera nodos (todos los nodos de mediana complejidad)",
                "Alta complejidad (HHHA)",
                "Baja complejidad (hospitales baja complejidad)"
            ],
            "Cantidad_examenes": [
                len(cartera_basica),
                len(cartera_nodos),
                len(cartera_alta),
                len(cartera_baja)
            ]
        })

        st.markdown("**Cantidad de exámenes por tipo de cartera**")
        chart_carteras = (
            alt.Chart(df_resumen_carteras)
            .mark_bar()
            .encode(
                x=alt.X("Tipo_cartera:N", title="Tipo de cartera"),
                y=alt.Y("Cantidad_examenes:Q", title="Cantidad de exámenes"),
                tooltip=["Tipo_cartera", "Cantidad_examenes"]
            )
            .properties(
                width=700,
                height=400
            )
        )
        st.altair_chart(chart_carteras, use_container_width=True)

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
