import streamlit as st
import pandas as pd
import re
from collections import defaultdict
from io import BytesIO

st.set_page_config(page_title="Disponibilità Medici - Convertitore", layout="wide")
st.title("🩺 Convertitore Disponibilità Medici per Fascia Oraria")

uploaded_file = st.file_uploader("📤 Carica il file Excel con le disponibilità dei medici", type=["xlsx"])

def estrai_giorno(col):
    match = re.search(r"\[(.+?) (\d{1,2})\]", col)
    return int(match.group(2)) if match else None

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    df_raw = xls.parse(xls.sheet_names[0])

    email_col = "Indirizzo email"
    name_col = "MEDICO: Nome e Cognome"
    availability_cols = [col for col in df_raw.columns if col.startswith("Disponibilità")]

    grouped = df_raw.groupby(email_col)
    medici_info = {}

    for email, group in grouped:
        nome_set = set(group[name_col])
        risposte = []
        disponibilita_unificate = defaultdict(set)

        for _, row in group.iterrows():
            risposta = defaultdict(set)
            for col in availability_cols:
                giorno = estrai_giorno(col)
                if giorno is None:
                    continue
                cella = row[col]
                if pd.isna(cella):
                    continue
                fasce = [f.strip() for f in str(cella).split(",")]
                for fascia in fasce:
                    risposta[(giorno, fascia)].add(fascia)
                    nome = row[name_col]
                    disponibilita_unificate[(giorno, fascia)].add(nome)
            risposte.append(risposta)

        medici_info[email] = {
            "nomi": list(set(group[name_col])),
            "risposte": risposte,
            "disponibilità_fusa": disponibilita_unificate
        }

    # Costruzione calendario unificato
    schedule = defaultdict(set)
    for email, info in medici_info.items():
        for (giorno, fascia), nomi in info["disponibilità_fusa"].items():
            schedule[(giorno, fascia)].update(nomi)

    giorni = sorted(set(day for (day, _) in schedule.keys()))
    fasce_orarie = sorted(set(fascia for (_, fascia) in schedule.keys()))
    df_schedule = pd.DataFrame(index=giorni, columns=fasce_orarie)

    for (giorno, fascia), nomi in schedule.items():
        df_schedule.at[giorno, fascia] = ', '.join(sorted(nomi))

    # Mostra il calendario
    st.success("✅ Conversione completata con successo!")
    st.dataframe(df_schedule, use_container_width=True)

    # Download del file
    buffer = BytesIO()
    df_schedule.to_excel(buffer, index=True, engine='openpyxl')
    buffer.seek(0)

    st.download_button(
        "📥 Scarica il file Excel convertito",
        data=buffer,
        file_name="disponibilita_convertita.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Report delle modifiche
    st.subheader("📤 Medici che hanno inviato più risposte e modifiche rilevate")

    for email, info in medici_info.items():
        risposte = info["risposte"]
        if len(risposte) <= 1:
            continue

        nomi = ', '.join(info["nomi"])
        st.markdown(f"### 🔁 {nomi} (`{email}`) ha inviato {len(risposte)} risposte")

        prima = risposte[0]
        for i, nuova in enumerate(risposte[1:], start=2):
            differenze = []
            for key, value in nuova.items():
                if key not in prima or value != prima[key]:
                    giorno, fascia = key
                    differenze.append(f"Giorno {giorno}, fascia {fascia}")
            if differenze:
                st.write(f"🆚 Risposta #{i} ha modificato o aggiunto:")
                for d in differenze:
                    st.write(f"• {d}")
            else:
                st.write(f"✅ Risposta #{i} identica alla prima.")
