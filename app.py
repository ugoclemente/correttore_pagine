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
MODEL_NAME = "gemini-2.5-pro"

# Percorso locale predefinito (usato solo per i test sul tuo PC)
JSON_KEY_PATH = os.path.join(os.path.dirname(__file__), "json", "credentials_ugo983.json")
# ==============================================================================

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Cronache - Revisore AI", layout="centered", page_icon="📰")

# ==============================================================================
# VESTE GRAFICA: INIEZIONE CSS PERSONALIZZATO (TEMA DARK HI-TECH / NEON BLUE FLUID)
# ==============================================================================
st.markdown("""
<style>
    /* 1. Sfondo generale e colore del testo dell'applicazione */
    .stApp {
        background-color: #08090b !important;
        color: #ffffff !important;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }

    /* Centratura del contenitore principale */
    .block-container {
        max-width: 750px !important;
        padding-top: 3rem !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }

    /* 2. Animazione a fluido scorrevole per i bordi */
    @keyframes fluid-flow {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Barra decorativa superiore a scorrimento neon */
    .neon-divider {
        height: 4px;
        width: 100%;
        background: linear-gradient(90deg, #00d2ff, #0066ff, #00d2ff);
        background-size: 200% 200%;
        animation: fluid-flow 3s linear infinite;
        border-radius: 2px;
        box-shadow: 0 0 15px rgba(0, 210, 255, 0.8);
        margin-bottom: 2rem;
    }

    /* Centratura ed estetica del titolo e del sottotitolo */
    h1 {
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 2.2rem !important;
        letter-spacing: -0.5px;
        margin-bottom: 0.5rem !important;
        text-align: center !important;
    }
    p {
        color: #a0aec0 !important;
        font-size: 1.1rem !important;
        margin-bottom: 2rem !important;
        text-align: center !important;
    }

    /* 3. Caricatore file (File Uploader) con bordo a fluido e ombreggiatura glow */
    [data-testid="stFileUploader"] {
        border: 2px solid transparent !important;
        border-radius: 12px !important;
        background-image: linear-gradient(#12151c, #12151c), linear-gradient(90deg, #00d2ff, #0066ff, #00d2ff) !important;
        background-origin: border-box !important;
        background-clip: content-box, border-box !important;
        background-size: 200% 200% !important;
        animation: fluid-flow 4s linear infinite !important;
        box-shadow: 0 0 20px rgba(0, 102, 255, 0.35) !important;
        padding: 12px !important;
        color: #ffffff !important;
        margin-bottom: 2rem !important;
        display: flex;
        justify-content: center;
    }

    /* Centratura dell'interfaccia interna del caricatore */
    [data-testid="stFileUploader"] section {
        background-color: transparent !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        justify-content: center;
    }

    /* Testi interni dell'uploader */
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] p {
        color: #ffffff !important;
        text-align: center !important;
    }

    /* 4. Pulsante "Avvia Analisi" Hi-Tech con animazione fluid e hover */
    div.stButton {
        display: flex;
        justify-content: center;
        width: 100%;
        margin-top: 1.5rem;
        margin-bottom: 2.5rem;
    }
    div.stButton > button {
        background-image: linear-gradient(90deg, #00d2ff, #0066ff, #00d2ff) !important;
        background-size: 200% 200% !important;
        animation: fluid-flow 3s linear infinite !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        letter-spacing: 0.5px;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 2.5rem !important;
        box-shadow: 0 0 15px rgba(0, 102, 255, 0.5) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        cursor: pointer;
    }
    div.stButton > button:hover {
        transform: scale(1.04) !important;
        box-shadow: 0 0 25px rgba(0, 102, 255, 0.8) !important;
        color: #ffffff !important;
    }
    div.stButton > button:active {
        transform: scale(0.98) !important;
    }

    /* 5. Box dei messaggi di stato e avvisi centrati */
    .stAlert {
        background-color: #12151c !important;
        border: 1px solid #1f242e !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        text-align: center !important;
        display: inline-block !important;
        width: 100% !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
    }
    .stAlert div {
        justify-content: center !important;
        text-align: center !important;
    }

    /* 6. Pannello del Report finale stile Terminale */
    .report-card {
        background-color: #0b0c10 !important;
        border: 1px solid #0066ff !important;
        border-radius: 12px !important;
        padding: 2rem !important;
        text-align: left !important; /* Allineamento a sinistra all'interno della scheda per la leggibilità del testo */
        box-shadow: 0 0 25px rgba(0, 102, 255, 0.25) !important;
        margin-top: 1rem;
        width: 100%;
    }
    .report-card h1, .report-card h2, .report-card h3 {
        color: #00d2ff !important;
        text-align: left !important;
        margin-top: 1.5rem;
    }
    .report-card p, .report-card li {
        color: #e2e8f0 !important;
        text-align: left !important;
        font-size: 1rem !important;
        margin-bottom: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Barra neon decorativa superiore
st.markdown('<div class="neon-divider"></div>', unsafe_allow_html=True)

# Titoli centrati (lo stile CSS gestisce la formattazione)
st.markdown("<h1>Revisore delle Pagine AI</h1>", unsafe_allow_html=True)
st.markdown("<p>Rilevamento avanzato di anomalie, refusi tipografici e uniformità stilistica in tempo reale.</p>",
            unsafe_allow_html=True)


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
uploaded_file = st.file_uploader("", type=["pdf", "png", "jpg", "jpeg"])

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
                    "Credenziali Google Cloud mancanti. Configura i Secrets su Streamlit Cloud o inserisci il file JSON nella cartella `./json/`.")

            # Inizializzazione di Vertex AI
            status_box.info("Stabilizzazione del flusso di connessione con Vertex AI...")
            vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)

            # Caricamento del file in memoria
            file_bytes = uploaded_file.getvalue()
            mime_type = uploaded_file.type

            media_part = Part.from_data(
                data=file_bytes,
                mime_type=mime_type
            )

            # Inizializzazione del modello con le istruzioni di sistema
            model = GenerativeModel(
                MODEL_NAME,
                system_instruction=[SYSTEM_PROMPT]
            )

            status_box.info("Analisi morfologica e verifica dell'allineamento visivo in corso...")
            response = model.generate_content([
                media_part,
                "Esegui una revisione approfondita e rigorosa di questa pagina secondo le istruzioni del System Prompt."
            ])

            status_box.empty()

            # Mostra i risultati all'interno della scheda personalizzata "cyber-terminal"
            st.markdown(f'<div class="report-card">{response.text}</div>', unsafe_allow_html=True)

        except Exception as e:
            status_box.empty()
            st.error(f"Errore durante l'analisi: {e}")
        finally:
            # Pulizia sicura della chiave temporanea nel Cloud
            if temp_creds_path and "gcp_service_account" in st.secrets:
                if os.path.exists(temp_creds_path):
                    os.remove(temp_creds_path)