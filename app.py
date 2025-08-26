import streamlit as st
import pandas as pd
import re
from collections import defaultdict
from io import BytesIO

st.set_page_config(page_title="Disponibilità Medici", layout="wide")
st.title("🩺 Disponibilità Medici DEA")

st.markdown("""
✅ **Nota bene:**  
Questa applicazione considera **solo l'ultima risposta** inviata da ciascun medico (identificato tramite email).  
Se un medico ha inviato più risposte, **le precedenti vengono ignorate**.
""")

uploaded_file = st.file_uploader("📤 Carica il file Excel con le disponibilità dei medici", type=["xlsx"])

def estrai_giorno(col):
    match = re.search(r"\[(.+?) (\d{1,2})\]", col)
    return int(match.group(2)) if match else None

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    df_raw = xls.parse(xls.sheet_names[0])

    # Normalizza colonne
    df_raw.columns = df_raw.columns.str.strip()

    email_col = "Indirizzo email"
    cognome_col = "MEDICO: Cognome"
    time_col = "Informazioni cronologiche"
    availability_cols = [col for col in df_raw.columns if col.startswith("Disponibilità")]

    # Tieni solo l'ultima risposta per ogni email
    last_responses = df_raw.sort_values(time_col).drop_duplicates(subset=[email_col], keep="last")

    final_disponibilita = defaultdict(set)

    for _, row in last_responses.iterrows():
        cognome = str(row[cognome_col]).strip()  # <-- solo cognome
        for col in availability_cols:
            giorno = estrai_giorno(col)
            if giorno is None:
                continue
            cella = row[col]
            if pd.isna(cella):
                continue
            fasce = re.split(r"[;,]\s*", str(cella))
            for fascia in fasce:
                if fascia:
                    final_disponibilita[(giorno, fascia)].add(cognome)

    # Costruzione calendario
    giorni = sorted(set(day for (day, _) in final_disponibilita.keys()))
    # Ordine fasce predefinito
    ordine_fasce = ["Mattina", "Pomeriggio", "Notte"]
    fasce_orarie = [f for f in ordine_fasce if f in {fascia for (_, fascia) in final_disponibilita.keys()}]

    df_schedule = pd.DataFrame(index=giorni, columns=fasce_orarie)

    for (giorno, fascia), cognomi in final_disponibilita.items():
        df_schedule.at[giorno, fascia] = ', '.join(sorted(cognomi))

    st.success("✅ Conversione completata. È stata usata solo l'ultima risposta di ogni medico (solo cognome).")
    st.dataframe(df_schedule, use_container_width=True)

    # Download calendario disponibilità
    buffer = BytesIO()
    df_schedule.to_excel(buffer, index=True, engine='openpyxl')
    buffer.seek(0)
    st.download_button(
        "📥 Scarica il file Excel disponibilità",
        data=buffer,
        file_name="disponibilita_convertita.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Report: conteggio disponibilità per medico
    conteggio_medici = defaultdict(int)
    for (giorno, fascia), cognomi in final_disponibilita.items():
        for cognome in cognomi:
            conteggio_medici[cognome] += 1

    df_report = pd.DataFrame(list(conteggio_medici.items()), columns=["Medico (Cognome)", "Numero disponibilità"])
    df_report = df_report.sort_values("Numero disponibilità", ascending=False).reset_index(drop=True)

    st.markdown("### 📊 Report: Disponibilità Totali per Medico")
    st.dataframe(df_report, use_container_width=True)

    # Download report
    buffer2 = BytesIO()
    df_report.to_excel(buffer2, index=False, engine='openpyxl')
    buffer2.seek(0)
    st.download_button(
        "📥 Scarica il report medici",
        data=buffer2,
        file_name="report_medici.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

