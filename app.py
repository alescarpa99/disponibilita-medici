import streamlit as st
import pandas as pd
import re
from collections import defaultdict
from io import BytesIO

st.set_page_config(page_title="Disponibilità Medici - Convertitore", layout="wide")
st.title("🩺 Convertitore Disponibilità Medici per Fascia Oraria")

uploaded_file = st.file_uploader("📤 Carica il file Excel con le disponibilità dei medici", type=["xlsx"])

def normalizza_nome(nome):
    nome = str(nome).strip().lower()
    cognome = nome.split()[-1]
    return cognome

if uploaded_file:
    # Carica il file
    xls = pd.ExcelFile(uploaded_file)
    df_raw = xls.parse(xls.sheet_names[0])

    # Colonne di disponibilità
    availability_cols = [col for col in df_raw.columns if col.startswith("Disponibilità  [")]
    medico_col = "MEDICO: Nome e Cognome"

    # Dati per ogni medico (normalizzati)
    medici_data = defaultdict(lambda: {
        "nomi_originali": set(),
        "disponibilità": defaultdict(set)
    })

    # Analizza tutte le risposte
    for _, row in df_raw.iterrows():
        nome_originale = row[medico_col]
        nome_norm = normalizza_nome(nome_originale)
        medici_data[nome_norm]["nomi_originali"].add(nome_originale)

        for col in availability_cols:
            match = re.search(r"\[(.+?) (\d{1,2})\]", col)
            if not match:
                continue
            giorno = int(match.group(2))
            cella = row[col]
            if pd.isna(cella):
                continue
            fasce = [f.strip() for f in re.split(r',\s*', cella)]
            for fascia in fasce:
                medici_data[nome_norm]["disponibilità"][(giorno, fascia)].add(nome_originale)

    # Costruzione tabella finale
    schedule = defaultdict(set)
    for medico_norm, dati in medici_data.items():
        for (giorno, fascia), nomi in dati["disponibilità"].items():
            schedule[(giorno, fascia)].update(nomi)

    # Tutti giorni e fasce
    giorni = sorted(set(day for day, _ in schedule.keys()))
    fasce_orarie = sorted(set(fascia for _, fascia in schedule.keys()))

    df_schedule = pd.DataFrame(index=giorni, columns=fasce_orarie)
    for (giorno, fascia), nomi in schedule.items():
        df_schedule.at[giorno, fascia] = ', '.join(sorted(nomi))

    # Mostra il risultato
    st.success("✅ Conversione completata con successo!")
    st.dataframe(df_schedule, use_container_width=True)

    # Download del file Excel
    buffer = BytesIO()
    df_schedule.to_excel(buffer, index=True, engine='openpyxl')
    buffer.seek(0)

    st.download_button(
        "📥 Scarica il file Excel convertito",
        data=buffer,
        file_name="disponibilita_convertita.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
