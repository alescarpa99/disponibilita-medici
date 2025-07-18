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

    email_col = "Indirizzo email"
    name_col = "MEDICO: Cognome"
    time_col = "Informazioni cronologiche"
    availability_cols = [col for col in df_raw.columns if col.startswith("Disponibilità")]

    # Tieni solo l'ultima risposta per ogni email
    last_responses = df_raw.sort_values(time_col).drop_duplicates(subset=[email_col], keep="last")

    final_disponibilità = defaultdict(set)

    for _, row in last_responses.iterrows():
        nome = row[name_col]
        for col in availability_cols:
            giorno = estrai_giorno(col)
            if giorno is None:
                continue
            cella = row[col]
            if pd.isna(cella):
                continue
            fasce = [f.strip() for f in str(cella).split(",")]
            for fascia in fasce:
                final_disponibilità[(giorno, fascia)].add(nome)

    # Costruzione calendario
    giorni = sorted(set(day for (day, _) in final_disponibilità.keys()))
    fasce_orarie = sorted(set(fascia for (_, fascia) in final_disponibilità.keys()))
    df_schedule = pd.DataFrame(index=giorni, columns=fasce_orarie)

    for (giorno, fascia), nomi in final_disponibilità.items():
        df_schedule.at[giorno, fascia] = ', '.join(sorted(nomi))

    st.success("✅ Conversione completata. È stata usata solo l'ultima risposta di ogni medico.")
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

# Report: conteggio disponibilità per medico
conteggio_medici = defaultdict(int)

# Ogni (giorno, fascia) contiene uno o più medici
for (giorno, fascia), nomi in final_disponibilità.items():
    for nome in nomi:
        conteggio_medici[nome] += 1  # Conta ogni fascia oraria in cui è disponibile

# Converti in DataFrame
df_report = pd.DataFrame(list(conteggio_medici.items()), columns=["Medico", "Numero disponibilità"])
df_report = df_report.sort_values("Numero disponibilità", ascending=False).reset_index(drop=True)

# Mostra in Streamlit
st.markdown("### 📊 Report: Disponibilità Totali per Medico")
st.dataframe(df_report, use_container_width=True)


