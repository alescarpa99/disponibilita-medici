import streamlit as st
import pandas as pd
import re
from collections import defaultdict

st.set_page_config(page_title="Convertitore Disponibilità Medici", layout="wide")

st.title("Convertitore Disponibilità Medici per Fascia Oraria")

uploaded_file = st.file_uploader("Carica il file Excel delle disponibilità", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    df_raw = xls.parse(xls.sheet_names[0])

    availability_cols = [col for col in df_raw.columns if col.startswith("Disponibilità  [")]
    medico_col = "MEDICO: Nome e Cognome"

    schedule = defaultdict(set)

    for _, row in df_raw.iterrows():
        medico = row[medico_col]
        for col in availability_cols:
            day_match = re.search(r"\[(.+?) (\d{1,2})\]", col)
            if not day_match:
                continue
            day_num = int(day_match.group(2))
            avail_raw = row[col]
            if pd.isna(avail_raw):
                continue
            fasce = [f.strip() for f in re.split(r',\s*', avail_raw)]
            for fascia in fasce:
                schedule[(day_num, fascia)].add(medico)

    days = sorted(set(day for day, _ in schedule.keys()))
    fasce = sorted(set(fascia for _, fascia in schedule.keys()))

    df_schedule = pd.DataFrame(index=days, columns=fasce)
    for (day, fascia), medici in schedule.items():
        df_schedule.at[day, fascia] = ', '.join(sorted(medici))

    st.success("Conversione completata!")

    st.dataframe(df_schedule)

    # Download del file
from io import BytesIO

buffer = BytesIO()
df_schedule.to_excel(buffer, index=True, engine='openpyxl')
buffer.seek(0)

st.download_button(
    "📥 Scarica il file Excel convertito",
    data=buffer,
    file_name="disponibilita_convertita.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
