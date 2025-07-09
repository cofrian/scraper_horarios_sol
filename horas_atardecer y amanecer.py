import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import unidecode
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import io

# ------------------------------
# Funciones auxiliares
# ------------------------------

def formatear_texto(texto):
    texto = texto.strip().lower()
    texto = unidecode.unidecode(texto)
    texto = texto.replace(" ", "-")
    return texto

def obtener_datos_mes(ciudad, anio, mes):
    """Scraping con requests + BeautifulSoup"""
    url = f"https://www.sunrise-and-sunset.com/es/sun/espana/{ciudad}/{anio}/{mes}"
    datos = []
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        tabla = soup.find("table", class_="table")
        if not tabla:
            st.warning(f"⚠️ No se encontró tabla en {mes.title()}.")
            return []
        filas = tabla.find_all("tr")[1:]
        for fila in filas:
            cols = [c.text.strip() for c in fila.find_all("td")]
            if len(cols) == 4:
                datos.append({
                    "Fecha": cols[0],
                    "Salida del sol": cols[1],
                    "Puesta del sol": cols[2],
                    "Duración del día": cols[3],
                    "Mes": mes.title()
                })
        return datos
    except Exception as e:
        st.error(f"❌ Error en {mes.title()}: {e}")
        return []

def exportar_excel(df):
    """Crea un archivo Excel en memoria con formato"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Datos")
        workbook = writer.book
        worksheet = writer.sheets["Datos"]

        header_format = workbook.add_format({
            "bold": True,
            "text_wrap": True,
            "valign": "center",
            "align": "center",
            "fg_color": "#FF0000",
            "font_color": "#FFFFFF",
            "border": 1
        })
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        worksheet.set_column("A:A", 25)
        worksheet.set_column("B:D", 15)
        worksheet.set_column("E:E", 10)
    output.seek(0)
    return output

# ------------------------------
# Interfaz Streamlit
# ------------------------------

st.title("🌅 Amaneceres y Atardeceres en España")
st.markdown("Consulta y descarga los horarios de salida y puesta del sol para cualquier ciudad española.")

ciudad_input = st.text_input("📍 Ciudad (ejemplo: Madrid, Sevilla):")
anio_input = st.text_input("📅 Año (opcional, por defecto actual):")

if st.button("Obtener datos"):
    if ciudad_input:
        st.info("🔄 Procesando datos, esto puede tardar unos segundos...")
        ciudad_formateada = formatear_texto(ciudad_input)
        anio_actual = int(anio_input) if anio_input else datetime.now().year
        meses = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]

        all_data = []

        # 🚀 Multihilos para acelerar scraping
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(obtener_datos_mes, ciudad_formateada, anio_actual, mes) for mes in meses]
            for future in futures:
                all_data.extend(future.result())

        if all_data:
            df = pd.DataFrame(all_data)
            st.success("✅ Datos obtenidos correctamente.")
            st.dataframe(df)

            # Botón para descargar Excel
            excel_data = exportar_excel(df)
            st.download_button(
                label="📥 Descargar Excel con formato",
                data=excel_data,
                file_name=f"amaneceres_atardeceres_{ciudad_formateada}_{anio_actual}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("❌ No se encontraron datos para esta ciudad.")
    else:
        st.warning("⚠️ Introduce una ciudad.")
