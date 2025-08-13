# Comparador Exámenes de BASE DE DATOS SIEL

Aplicación Streamlit para comparar la **BASE DE DATOS SIEL** con la **CARTERA DE PRESTACIONES SIEL SSAS_EXAMENES_VERSION_GLOBAL_13072025**.

## Funcionalidad
- Carga de dos archivos `.xlsx`.
- Normaliza nombres de columnas y conserva el esquema acordado.
- Convierte **Número** a formato numérico en ambos archivos.
- Genera un Excel: **EXAMENES PENDIENTES CARGAR.xlsx**
  - Hoja **EXAMENES PENDIENTES**: filas del primer archivo cuyo **Número** no está en el segundo (orden de columnas del segundo archivo normalizado).
  - Hoja **NOMBRES A ACTUALIZAR**: casos donde el **Nombre exámen** difiere para el mismo **Número**.

## Uso local
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Estructura
```
app.py
requirements.txt
logo_siel.png
```

> Asegúrate de colocar el logo como **logo_siel.png** en la misma carpeta que `app.py`.
