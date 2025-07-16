import streamlit as st
import pandas as pd
import re
from collections import defaultdict
from io import BytesIO

st.set_page_config(page_title="Disponibilità Medici", layout="wide")
st.title("🩺 Disponibilità Medici (Solo Ultima Risposta + Modifiche Effettive)")

uploaded_file = st.file_uploader("📤 Carica il file Excel con le disponibilità dei medici", type=["xlsx"])

def estrai_giorno(col):
    match = re.search(r"\[(.+?) (\d{1,2})\]", col)
    return int(match.group(2)) if match else None

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    df_raw = xls.parse(xls.sheet_names[0])

    email_col = "Indirizzo email"
    name_col = "MEDICO: Nome e Cognome"
    time_col = "Informazioni cronologiche"
    availability_cols = [col for col in df_raw.columns if col.startswith("Disponibilità")]

    modifiche_report = {}
    final_disponibilità = defaultdict(set)

    grouped = df_raw.groupby(email_col)
    email_counts = df_raw[email_col].value_counts()

    for email, count in email_counts.items():
        group = grouped.get_group(email).sort_values(time_col)
        latest = group.iloc[-1]
        nome = latest[name_col]

        # Ultima risposta
        ultima_risposta = defaultdict(set)
        for col in availability_cols:
            giorno = estrai_giorno(col)
            if giorno is None:
                continue
            cella = latest[col]
            if pd.isna(cella):
                continue
            fasce = [f.strip() for f in str(cella).split(",")]
            for fascia in fasce:
                ultima_risposta[(giorno, fascia)].add(fascia)
                final_disponibilità[(giorno, fascia)].add(nome)

        # Confronta solo se ci sono risposte precedenti
        if count > 1:
            cumulata_precedente = defaultdict(set)
            for _, row in group.iloc[:-1].iterrows():
                for col in availability_cols:
                    giorno = estrai_giorno(col)
                    if giorno is None:
                        continue
                    cella = row[col]
                    if pd.isna(cella):
                        continue
                    fasce = [f.strip() for f in str(cella).split(",")]
                    for fascia in fasce:
                        cumulata_precedente[(giorno, fascia)].add(fascia)

            aggiunte = []
            rimosse = []
            all_keys = set(cumulata_precedente.keys()).union(ultima_risposta.keys())
            for key in all_keys:
                prima = cumulata_precedente.get(key, set())
                dopo = ultima_risposta.get(key, set())
                if dopo > prima:
                    aggiunte.append(key)
                if prima > dopo:
                    rimosse.append(key)

            if aggiunte or rimosse:
                modifiche_report[email] = {
                    "nome": nome,
                    "aggiunte": aggiunte,
                    "rimosse": rimosse
                }

    # Costruzione calendario finale
    giorni = sorted(set(day for (day, _) in final_disponibilità.keys()))
    fasce_orarie = sorted(set(fascia for (_, fascia) in final_disponibilità.keys()))
    df_schedule = pd.DataFrame(index=giorni, columns=fasce_orarie)

    for (giorno, fascia), nomi in final_disponibilità.items():
        df_schedule.at[giorno, fascia] = ', '.join(sorted(nomi))

    st.success("✅ Conversione completata. Solo l'ultima risposta di ciascun medico è considerata.")
    st.dataframe(df_schedule, use_container_width=True)

    # Download Excel
    buffer = BytesIO()
    df_schedule.to_excel(buffer, index=True, engine='openpyxl')
    buffer.seek(0)

    st.download_button(
        "📥 Scarica il file Excel convertito",
        data=buffer,
        file_name="disponibilita_convertita.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Report modifiche vere (solo chi ha inviato più risposte e ha cambiato qualcosa)
    st.subheader("📊 Medici che hanno modificato disponibilità tra una risposta e l'altra")
    if not modifiche_report:
        st.write("✅ Nessun medico ha inviato più di una risposta con differenze.")
    else:
        for email, info in modifiche_report.items():
            nome = info["nome"]
            st.markdown(f"### 🧾 {nome} (`{email}`)")
            if info["aggiunte"]:
                st.write("➕ Fasce aggiunte:")
                for g, f in sorted(info["aggiunte"]):
                    st.write(f"• Giorno {g}, fascia {f}")
            if info["rimosse"]:
                st.write("➖ Fasce rimosse:")
                for g, f in sorted(info["rimosse"]):
                    st.write(f"• Giorno {g}, fascia {f}")
