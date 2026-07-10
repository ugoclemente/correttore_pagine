import streamlit as st
import os
import tempfile
import json
import vertexai
from datetime import datetime
from vertexai.generative_models import GenerativeModel, Part

# ==============================================================================
# CONFIGURAZIONE HARDCODED (Modificabile solo qui nel codice sorgente)
# ==============================================================================
GCP_PROJECT_ID = "neon-flare-461910-d6"
GCP_LOCATION = "europe-west8"
MODEL_NAME = "gemini-2.5-pro"  # Sostituire con "gemini-1.5-pro" se non abilitato sul proprio progetto GCP

# Percorso predefinito del file delle credenziali JSON locale (usato solo offline)
JSON_KEY_PATH = os.path.join(os.path.dirname(__file__), "json", "credentials_ugo983.json")
# ==============================================================================

# Configurazione pulita della pagina Streamlit
st.set_page_config(page_title="Cronache - Revisore di bozze AI", layout="centered", page_icon="📰")

st.title("📰 Cronache - Assistente per la correzione delle pagine e la rilevazione degli errori")
st.write("Carica il file pdf per avviare il processo di correzione automatica.")


# Funzione di fallback per rilevare automaticamente la chiave JSON locale (solo sviluppo offline)
def get_local_credentials_path():
    if os.path.exists(JSON_KEY_PATH):
        return JSON_KEY_PATH
    json_dir = os.path.join(os.path.dirname(__file__), "json")
    if os.path.exists(json_dir):
        json_files = [f for f in os.listdir(json_dir) if f.endswith(".json")]
        if json_files:
            return os.path.join(json_dir, json_files[0])
    return None


# Funzione di gestione sicura delle credenziali (Locale e Cloud)
def configure_gcp_credentials():
    # Scenario A: Online su Streamlit Cloud (legge la stringa JSON memorizzata nei Secrets)
    if "gcp_service_account" in st.secrets:
        creds_json_string = st.secrets["gcp_service_account"]
        # Crea un file temporaneo protetto all'interno del container Linux di Streamlit
        temp_creds = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        temp_creds.write(creds_json_string.encode("utf-8"))
        temp_creds.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_creds.name
        return temp_creds.name

    # Scenario B: Sviluppo in locale sul tuo PC (legge il file .json nella cartella)
    local_path = get_local_credentials_path()
    if local_path:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = local_path
        return local_path

    return None


# Generazione dinamica della data odierna in lingua italiana per l'ancoraggio temporale dell'AI
mesi = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre",
        "novembre", "dicembre"]
giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
now = datetime.now()
data_odierna_str = f"{giorni[now.weekday()]} {now.day} {mesi[now.month - 1]} {now.year}"

# Definizione del System Prompt blindato con le nuove regole specifiche
SYSTEM_PROMPT = f"""Sei un correttore di bozze e revisore di testi senior per un quotidiano cartaceo italiano. Il tuo compito è esaminare attentamente le pagine di giornale caricate per identificare anomalie, refusi, incongruenze e proporre correzioni precise.

IMPORTANTE - ANCORAGGIO TEMPORALE:
La data odierna corrente è: {data_odierna_str}. Questa data rappresenta il presente/contemporaneo. Pertanto, qualsiasi data sulla pagina che corrisponda a questo giorno o a questo anno (es. l'anno 2026 o date limitrofe) è corretta e contemporanea. NON segnalarla in nessun caso come errore logico o data futura.

REGOLE TASSATIVE DI ESCLUSIONE (NON CONSIDERARE ERRORI):
1. LE "PARTENZE": La presenza del nome della città, della località o della fonte prima dell'occhiello o del testo di un articolo (es. 'Mondiali I campioni', 'Mondragone Il gruppo', 'Maddaloni Lo stratagemma') è una convenzione stilistica intenzionale dell'impaginazione giornalistica. NON segnalare mai come errore la mancanza di spazi, trattini o punteggiatura tra queste parole e il testo successivo.
2. I RIFERIMENTI AI GIORNALISTI NEI RIMANDI: L'inserimento del cognome del giornalista all'interno dei box di rimando di pagina (es. 'Tallino alle pagine 16 e 17', 'Cicalese a pagina 18', 'Casapulla a pagina 20') è una scelta redazionale voluta. NON considerarla e non segnalarla mai come errore.
3. FALSI POSITIVI DA OCR: Ignora le parole spezzate a fine riga che presentano spazi o mancano graficamente di trattino di unione nel flusso di lettura (es. 'del lo', 'Comu nale', 'Condan na').

FOCUS DI ANALISI (CRITERI DI REVISIONE):
1. Precisione Grammaticale e Lessicale: Concentrati rigorosamente su reali errori ortografici, sintattici, grammaticali o espressioni non idiomatiche in lingua italiana. Sii estremamente rigoroso: ad esempio, l'uso di espressioni come "Non grazie" all'interno di una citazione o discorso diretto (es. 'Io sindaco? Non grazie') costituisce un errore lessicale/idiomatico evidente in italiano e va corretto in "No, grazie" o "No grazie".
2. Ripetizioni nella Titolazione: Segnala ripetizioni non giustificate della stessa parola chiave tra occhiello, titolo e sommario dello stesso articolo, proponendo sinonimi.
3. Coerenza tra Didascalia e Immagine: Verifica che l'immagine corrisponda effettivamente ai soggetti descritti nella didascalia associata (es. se la didascalia cita specifici atleti, verifica che siano effettivamente loro presenti nell'immagine)."""

# Caricamento del file della pagina di giornale
uploaded_file = st.file_uploader("Trascina o seleziona il file della pagina (PDF, PNG, JPG, JPEG)",
                                 type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file:
    st.info(f"File pronto per l'analisi: {uploaded_file.name}")

    if st.button("Avvia Analisi Errori"):
        status_box = st.empty()
        temp_creds_path = None
        try:
            # Configurazione dinamica delle credenziali (Locale o Cloud)
            temp_creds_path = configure_gcp_credentials()
            if not temp_creds_path:
                raise Exception(
                    "Credenziali Google Cloud mancanti. Configura i Secrets su Streamlit Cloud o posiziona il file JSON in ./json/ in locale.")

            # Inizializzazione di Vertex AI
            status_box.info("Inizializzazione della connessione con Vertex AI...")
            vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)

            # Caricamento del file in memoria
            file_bytes = uploaded_file.getvalue()
            mime_type = uploaded_file.type

            media_part = Part.from_data(
                data=file_bytes,
                mime_type=mime_type
            )

            # Inizializzazione del modello con le istruzioni di sistema blindate
            model = GenerativeModel(
                MODEL_NAME,
                system_instruction=[SYSTEM_PROMPT]
            )

            status_box.info("Analisi visiva e testuale in corso sul documento...")
            response = model.generate_content([
                media_part,
                "Esegui una revisione approfondita e rigorosa di questa pagina secondo le istruzioni del System Prompt."
            ])

            status_box.empty()
            st.subheader("📋 Report Revisione Bozze")
            st.markdown(response.text)

        except Exception as e:
            status_box.empty()
            st.error(f"Errore durante l'analisi: {e}")
        finally:
            # Pulizia del file temporaneo se siamo sul cloud
            if temp_creds_path and "gcp_service_account" in st.secrets:
                if os.path.exists(temp_creds_path):
                    os.remove(temp_creds_path)