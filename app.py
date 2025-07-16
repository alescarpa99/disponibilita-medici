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

    # Trova le colonne di disponibilità
    availability_cols = [col for col in df_raw.columns if col.startswith("Disponibilità  [")]
    medico_col = "MEDICO: Nome e Cognome"

    # Salva le risposte multiple per medico
    medici_data = defaultdict(lambda: {"risposte": []})

    for _, row in df_raw.iterrows():
        nome_originale = row[medico_col]
        nome_norm = normalizza_nome(nome_originale)

        risposta = {
            "nome": nome_originale,
            "disponibilità": defaultdict(set)
        }

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
                risposta["disponibilità"][(giorno, fascia)].add(fascia)

        medici_data[nome_norm]["risposte"].append(risposta)

    # Costruisci il calendario finale unendo le risposte
    schedule = defaultdict(set)

    for medico_norm, dati in medici_data.items():
        tutte_disponibilità = defaultdict(set)
        for risposta in dati["risposte"]:
            for (giorno, fascia), fasce in risposta["disponibilità"].items():
                tutte_disponibilità[(giorno, fascia)].add(risposta["nome"])
        for key, nomi in tutte_disponibilità.items():
            schedule[key].update(nomi)

    giorni = sorted(set(day for day, _ in schedule.keys()))
    fasce_orarie = sorted(set(fascia for _, fascia in schedule.keys()))
    df_schedule = pd.DataFrame(index=giorni, columns=fasce_orarie)

    for (giorno, fascia), nomi in schedule.items():
        cella_nomi = set()
        for nome in nomi:
            norm = normalizza_nome(nome)
            nomi_possibili = {r["nome"] for r in medici_data[norm]["risposte"]}
            nome_finale = max(nomi_possibili, key=len)
            cella_nomi.add(nome_finale)
        df_schedule.at[giorno, fascia] = ', '.join(sorted(cella_nomi))

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

    # Report medici con più risposte
    st.subheader("📤 Medici che hanno inviato più risposte")

    for norm, data in medici_data.items():
        risposte = data["risposte"]
        if len(risposte) <= 1:
            continue

        st.markdown(f"### 🔁 `{norm.upper()}` ha inviato {len(risposte)} risposte")
        nomi = {r['nome'] for r in risposte}
        st.write(f"🧾 Nomi usati: {', '.join(nomi)}")

        # Confronto con la prima risposta
        prima = risposte[0]["disponibilità"]
        for i, r in enumerate(risposte[1:], start=2):
            st.markdown(f"**🆚 Confronto con risposta #{i}:**")
            differenze = []
            for key, fasce in r["disponibilità"].items():
                if key not in prima or fasce != prima[key]:
                    giorno, fascia = key
                    differenze.append(f"Giorno {giorno}, fascia {fascia}")
            if differenze:
                st.write("🔍 Fasce aggiunte o modificate:")
                for d in differenze:
                    st.write(f"• {d}")
            else:
                st.write("✅ Nessuna differenza rilevata rispetto alla prima risposta.")
