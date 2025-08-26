import streamlit as st
import pandas as pd
import re
from collections import defaultdict
from io import BytesIO

st.set_page_config(page_title="Disponibilità Medici", layout="wide")
st.title("🩺 Disponibilità Medici DEA")

st.markdown("""
✅ **Nota bene:**  
Appena carichi il file Excel, **tutti i valori di testo e gli header vengono convertiti in MAIUSCOLO**.  
L'app considera **solo l'ultima risposta** inviata da ciascun medico (identificato tramite email).
""")

uploaded_file = st.file_uploader("📤 Carica il file Excel con le disponibilità dei medici", type=["xlsx"])

def estrai_giorno(col):
    match = re.search(r"\[(.+?) (\d{1,2})\]", col)
    return int(match.group(2)) if match else None

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    df_raw = xls.parse(xls.sheet_names[0])

    # ---- CONVERSIONE IMMEDIATA IN MAIUSCOLO ----
    # Normalizza e mette in maiuscolo gli header
    df_raw.columns = [col.strip().upper() if isinstance(col, str) else col for col in df_raw.columns]
    # Converte tutte le celle di tipo stringa in MAIUSCOLO (senza toccare numeri/datetime)
    df_raw = df_raw.applymap(lambda x: x.strip().upper() if isinstance(x, str) else x)
    # -------------------------------------------

    # Nomi colonne (ORA in MAIUSCOLO)
    email_col   = "INDIRIZZO EMAIL"
    cognome_col = "MEDICO: COGNOME"
    time_col    = "INFORMAZIONI CRONOLOGICHE"

    # Trova colonne di disponibilità (gestisce sia DISPONIBILITA che DISPONIBILITÀ)
    availability_cols = [col for col in df_raw.columns if isinstance(col, str) and col.startswith("DISPONIBILIT")]

    # Controlli minimi
    missing = [c for c in (email_col, cognome_col, time_col) if c not in df_raw.columns]
    if missing:
        st.error(f"Colonne mancanti nel file (dopo uppercase): {missing}. Controlla gli header del tuo Excel.")
    elif not availability_cols:
        st.error("Non trovate colonne di disponibilità (header che iniziano con 'Disponibilit...').")
    else:
        # Tieni solo l'ultima risposta per ogni email (time_col può essere stringa o datetime)
        last_responses = df_raw.sort_values(time_col).drop_duplicates(subset=[email_col], keep="last")

        final_disponibilita = defaultdict(set)

        for _, row in last_responses.iterrows():
            cognome_raw = str(row.get(cognome_col, "")).strip()
            if not cognome_raw:
                continue

            for col in availability_cols:
                giorno = estrai_giorno(col)
                if giorno is None:
                    continue
                cella = row[col]
                if pd.isna(cella):
                    continue
                # Fasce già uppercase grazie ad applymap
                fasce = re.split(r"[;,]\s*", str(cella).strip())
                for fascia in fasce:
                    if fascia:
                        final_disponibilita[(giorno, fascia)].add(cognome_raw)

        # Costruzione calendario
        giorni = sorted({day for (day, _) in final_disponibilita.keys()})
        fasce_presenti = {fascia for (_, fascia) in final_disponibilita.keys()}
        # Ordine fasce definito in MAIUSCOLO
        ordine_fasce = ["MATTINA", "POMERIGGIO", "NOTTE"]
        fasce_orarie = [f for f in ordine_fasce if f in fasce_presenti] + sorted([f for f in fasce_presenti if f not in ordine_fasce])

        df_schedule = pd.DataFrame(index=giorni, columns=fasce_orarie)

        for (giorno, fascia), cognomi in final_disponibilita.items():
            df_schedule.at[giorno, fascia] = ", ".join(sorted(cognomi))

        st.success("✅ File caricato e tutto convertito in MAIUSCOLO. Conversione e report generati (solo ultima risposta per email).")
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

        # Report: conteggio disponibilità per medico (cognome già uppercase)
        conteggio_medici = defaultdict(int)
        for (giorno, fascia), cognomi in final_disponibilita.items():
            for cognome in cognomi:
                key = str(cognome).strip().upper()
                if key:
                    conteggio_medici[key] += 1

        df_report = pd.DataFrame(list(conteggio_medici.items()), columns=["Medico (COGNOME)", "Numero disponibilità"])
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
