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
st.set_page_config(page_title="Cronache - Revisore di bozze AI", layout="centered")

# ==============================================================================
# VESTE GRAFICA PERSONALIZZATA (TEMA COMPLETAMENTE NERO, BORDI FLUIDI DA 0.5pt)
# ==============================================================================
st.markdown("""
<style>
    /* 1. Rimozione totale della banda bianca e della barra di decorazione superiore di Streamlit */
    header[data-testid="stHeader"] {
        visibility: hidden !important;
        height: 0px !important;
    }
    [data-testid="stDecoration"] {
        display: none !important;
        height: 0px !important;
    }

    /* Sfondo completamente nero per l'applicazione */
    .stApp {
        background-color: #000000 !important;
        color: #ffffff !important;
        font-family: 'Cascadia Mono', 'Consolas', 'Courier New', monospace !important;
    }

    /* Centratura del contenitore principale */
    .block-container {
        max-width: 800px !important;
        padding-top: 1rem !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }

    /* Centratura e colore bianco per tutti i testi */
    h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown, .stMarkdown div {
        text-align: center !important;
        color: #ffffff !important;
        justify-content: center !important;
        font-family: 'Cascadia Mono', 'Consolas', 'Courier New', monospace !important;
    }

    button, input, textarea, select, small, code, pre, li, a, div {
        font-family: 'Cascadia Mono', 'Consolas', 'Courier New', monospace !important;
    }

    .app-masthead {
        width: 100%;
        margin: 0 0 1.35rem 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.2rem;
    }

    .app-name {
        font-family: 'Anton', 'Impact', sans-serif !important;
        margin: 0;
        font-size: 8.75rem !important;
        line-height: 0.9;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0;
    }
    
    /* 3. Regola specifica per cellulari e schermi piccoli (sotto i 768px) */
    @media (max-width: 768px) {
        .app-name {
            font-family: 'Chivo Mono', 'Impact', sans-serif !important;
            font-size: 3.2rem !important; /* Ridimensiona il carattere per farlo stare su un'unica riga */
            font-weight: 700;
            letter-spacing: 0px !important;
        }
    }

    .app-subtitle {
        margin: 0;
        font-size: 1.75rem !important;
        text-transform: normal;
        line-height: 1.1;
        font-weight: 800;
    }

    .app-caption {
        margin: 0 0 0 0;
        font-size: 0.75rem !important;
        line-height: 1;
        color: rgba(255, 255, 255, 0.78) !important;
    }

    /* 2. Animazione fluttuante del colore del bordo (effetto fluido ultra-sottile) */
    @keyframes fluid-border-color {
        0% { 
            border-color: #00d2ff; 
            box-shadow: 0 0 158px rgba(0, 210, 255, 0.6); 
        }
        50% { 
            border-color: #0066ff; 
            box-shadow: 0 0 158px rgba(0, 210, 255, 0.8); 
        }
        100% { 
            border-color: #00d2ff; 
            box-shadow: 0 0 158px rgba(0, 210, 255, 0.6); 
        }
    }

    @keyframes uploader-ambient-shift {
        0% {
            transform: translate3d(-7%, -4%, 0) scale(1);
            opacity: 0.5;
        }
        35% {
            transform: translate3d(6%, 3%, 0) scale(1.08);
            opacity: 0.88;
        }
        70% {
            transform: translate3d(-3%, 7%, 0) scale(1.1);
            opacity: 0.72;
        }
        100% {
            transform: translate3d(7%, -3%, 0) scale(1.05);
            opacity: 0.58;
        }
    }

    @keyframes uploader-scan {
        0% {
            transform: translateY(-38%);
            opacity: 0.05;
        }
        50% {
            opacity: 0.22;
        }
        100% {
            transform: translateY(38%);
            opacity: 0.06;
        }
    }

    @keyframes uploader-surface-drift {
        0% {
            background-position:
                10% 18%,
                88% 74%,
                52% 46%,
                0 0,
                0 0,
                0 0;
        }
        33% {
            background-position:
                18% 28%,
                76% 60%,
                46% 54%,
                10px 0,
                0 12px,
                0 0;
        }
        66% {
            background-position:
                8% 34%,
                84% 56%,
                58% 42%,
                -8px 0,
                0 -10px,
                0 0;
        }
    }

    /* Campo di upload con texture animata minimale e bordo azzurro fluido */
    [data-testid="stFileUploader"] {
        position: relative;
        overflow: hidden;
        isolation: isolate;
        border: 1pt solid #00d2ff !important;
        border-radius: 0px !important;
        animation: fluid-border-color 2s linear infinite, uploader-surface-drift 6.8s ease-in-out infinite alternate !important;
        padding: 10px !important;
        color: #ffffff !important;
        # margin-bottom: 1rem !important;
        display: flex;
        justify-content: center;
        width: 100% !important;
        background:
            radial-gradient(ellipse 140% 110% at 18% 24%, rgba(0, 210, 255, 0.128) 0%, rgba(0, 210, 255, 0.093) 16%, rgba(0, 210, 255, 0.053) 32%, rgba(0, 210, 255, 0.014) 48%, transparent 68%),
            radial-gradient(ellipse 140% 110% at 78% 68%, rgba(0, 210, 255, 0.122) 0%, rgba(0, 210, 255, 0.088) 16%, rgba(0, 210, 255, 0.050) 32%, rgba(0, 210, 255, 0.013) 50%, transparent 70%),
            radial-gradient(ellipse 120% 150% at 50% 50%, rgba(0, 210, 255, 0.032) 0%, rgba(0, 210, 255, 0.018) 22%, rgba(0, 210, 255, 0.006) 40%, transparent 62%),
            repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.025) 0 1px, transparent 1px 22px),
            repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.018) 0 1px, transparent 1px 22px),
            linear-gradient(145deg, #181b22 0%, #0c0f14 52%, #141820 100%) !important;
        background-size: 155% 145%, 155% 145%, 135% 155%, 22px 22px, 22px 22px, 100% 100%;
        background-position: 10% 18%, 88% 74%, 52% 46%, 0 0, 0 0, 0 0;
    }

    [data-testid="stFileUploader"]::before {
        content: "";
        position: absolute;
        inset: -18%;
        z-index: 0;
        pointer-events: none;
        background:
            radial-gradient(ellipse 125% 100% at 24% 30%, rgba(0, 210, 255, 0.128) 0%, rgba(0, 210, 255, 0.090) 20%, rgba(0, 210, 255, 0.038) 38%, transparent 64%),
            radial-gradient(ellipse 125% 100% at 74% 64%, rgba(0, 210, 255, 0.128) 0%, rgba(0, 210, 255, 0.090) 18%, rgba(0, 210, 255, 0.037) 36%, transparent 62%),
            radial-gradient(ellipse 100% 130% at 52% 48%, rgba(0, 210, 255, 0.029) 0%, rgba(0, 210, 255, 0.011) 38%, transparent 62%),
            linear-gradient(120deg, transparent 30%, rgba(255, 255, 255, 0.04) 50%, transparent 70%);
        filter: blur(26px);
        animation: uploader-ambient-shift 7.4s ease-in-out infinite alternate;
    }

    [data-testid="stFileUploader"]::after {
        content: "";
        position: absolute;
        inset: 0;
        z-index: 0;
        pointer-events: none;
        background:
            linear-gradient(180deg, transparent 0%, rgba(0, 210, 255, 0.064) 45%, transparent 100%),
            linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.03) 50%, transparent 100%);
        mix-blend-mode: screen;
        animation: uploader-scan 6.2s ease-in-out infinite alternate;
    }

    /* Centratura dell'interfaccia interna dell'uploader */
    [data-testid="stFileUploader"] section {
        background-color: transparent !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        justify-content: center;
        width: 100% !important;
    }

    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploader"] section > div,
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] p {
        position: relative;
        z-index: 1;
    }

    /* 3. Stilizzazione del pulsante UPLOAD interno (grigio, scritta bianca sempre visibile) */
    [data-testid="stFileUploaderDropzone"] > span > button {
        position: relative;
        background-color: #2b2e3a !important; 
        color: transparent !important;
        border: 0.0pt solid #00d2ff !important;
        border-radius: 0px !important;
        padding: 6px 20px !important;
        font-weight: 600 !important;
        transition: background-color 0.1s ease, transform 0.2s ease !important;
        overflow: hidden;
    }
    [data-testid="stFileUploaderDropzone"] > span > button:hover {
        background-color: #3e4354 !important; /* Grigio leggermente più chiaro in hover */
        color: transparent !important;
        transform: scale(1.02) !important;
    }
    [data-testid="stFileUploaderDropzone"] > span > button * {
        color: transparent !important;
        opacity: 0 !important;
    }
    [data-testid="stFileUploaderDropzone"] > span > button::after {
        content: "Upload";
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ffffff !important;
        font-size: 0.95rem;
        font-weight: 600;
        line-height: 1;
        pointer-events: none;
    }

    [data-testid="stFileChips"] {
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.55rem !important;
        flex-wrap: nowrap !important;
    }

    [data-testid="stFileChip"] {
        background-color: #2b2e3a !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        color: #ffffff !important;
        min-width: 0 !important;
    }

    [data-testid="stFileChip"] [data-testid="stFileChipName"] {
        color: #ffffff !important;
    }

    [data-testid="stFileChip"] div:not([data-testid="stFileChipName"]) {
        color: rgba(255, 255, 255, 0.68) !important;
    }

    [data-testid="stFileChipDeleteBtn"] button {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: rgba(255, 255, 255, 0.72) !important;
        padding: 0 !important;
        min-width: unset !important;
        min-height: unset !important;
        transform: none !important;
        overflow: visible !important;
    }

    [data-testid="stFileChipDeleteBtn"] button * {
        color: rgba(255, 255, 255, 0.72) !important;
        opacity: 1 !important;
    }

    [data-testid="stFileChipDeleteBtn"] button::after {
        content: none !important;
    }

    [data-testid="stFileChipDeleteBtn"] button:hover {
        background-color: transparent !important;
        color: #ffffff !important;
    }

    [data-testid="stFileUploader"] button[aria-label="Add files"] {
        display: none !important;
    }

    /* 4. Pulsante principale "Avvia Analisi" coordinato da 0.5pt */
    [data-testid="stButton"],
    div.stButton {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
        margin-top: 0rem;
        margin-bottom: 2rem;
        margin-left: auto !important;
        margin-right: auto !important;
        text-align: center !important;
        align-self: center !important;
    }
    [data-testid="stButton"] > div,
    div.stButton > div {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
    [data-testid="stButton"] button,
    div.stButton button {
        background-color: #1e1e24 !important;
        border: 0.1pt solid #00d2ff !important;
        border-radius: 8px !important;
        animation: fluid-border-color 4s linear infinite !important;
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 1rem !important;
        padding: 8px 30px !important;
        transition: transform 0.5s ease !important;
        cursor: pointer;
        display: block !important;
        margin: 0 auto !important;
    }
    [data-testid="stButton"] button:hover,
    div.stButton button:hover {
        transform: scale(1.02) !important;
        color: #ffffff !important;
    }

    /* Alert di stato e messaggi */
    .stAlert {
        background-color: transparent !important;
        # opacity: 0.2;
        # border: 0.5pt solid #1f242e !important;
        color: #ffffff !important;
        # border-radius: 8px !important;
        text-align: center !important;
        display: inline-block !important;
        # width: 100% !important;
    }
    .stAlert div {
        padding: 0px !important;
        justify-content: center !important;
        background-color: transparent !important;
        text-align: center !important;
    }
</style>
""", unsafe_allow_html=True)

# Titolo e descrizione principali
st.markdown("""
<div class="app-masthead">
    <p class="app-name">CRONACHE</p>
    <p class="app-subtitle">Correttore di bozze IA</p>
    <p class="app-caption">Carica il file per avviare il processo di correzione automatica.</p>
</div>
""", unsafe_allow_html=True)


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
La data odierna corrente è: {data_odierna_str}. Questa data rappresenta il presente/contemporaneo. Pertanto, qualsiasi data sulla pagina che corrisponda a questo giorno o a questo anno (es. l’anno 2026 o date limitrofe) è corretta e contemporanea. NON segnalarla in nessun caso come errore logico o data futura.

REGOLE TASSATIVE DI ESCLUSIONE (NON CONSIDERARE ERRORI):
1. LE "PARTENZE": La presenza del nome della città, della località o della fonte prima dell'occhiello o del testo di un articolo (es. 'Mondiali I campioni', 'Mondragone Il gruppo', 'Maddaloni Lo stratagemma') è una convenzione stilistica intenzionale dell'impaginazione giornalistica. NON segnalare mai come errore la mancanza di spazi, trattini o punteggiatura tra queste parole e il testo successivo.
2. I RIFERIMENTI AI GIORNALISTI NEI RIMANDI: L'inserimento del cognome del giornalista all'interno dei box di rimando di pagina (es. 'Tallino alle pagine 16 e 17', 'Cicalese a pagina 18', 'Casapulla a pagina 20') è una scelta redazionale voluta. NON considerarla e non segnalarla mai come errore. Non segnalare come errori le forme abbreviate o puntate della firma dei giornalisti.
3. FALSI POSITIVI DA OCR: Ignora le parole spezzate a fine riga che presentano spazi o mancano graficamente di trattino di unione nel flusso di lettura (es. 'del lo', 'Comu nale', 'Condan na').

FOCUS DI ANALISI (CRITERI DI REVISIONE):
1. Precisione Grammaticale e Lessicale: Concentrati rigorosamente su reali errori ortografici, sintattici, grammaticali o espressioni non idiomatiche in lingua italiana. Sii estremamente rigoroso: ad esempio, l'uso di espressioni come "Non grazie" all'interno di una citazione o discorso diretto (es. 'Io sindaco? Non grazie') costituisce un errore lessicale/idiomatico evidente in italiano e va corretto in "No, grazie" o "No grazie".
2. Ripetizioni nella Titolazione: Segnala ripetizioni non giustificate della stessa parola chiave tra occhiello, titolo e sommario dello stesso articolo, proponendo sinonimi. Nel computo delle ripetizioni non considerare le parole contenute nell'articolo ma solo quelle contenute in titolo, occhiello e sommario.
3. Coerenza tra Didascalia e Immagine: Verifica che l'immagine corrisponda effettivamente ai soggetti descritti nella didascalia associata (es. se la didascalia cita specifici atleti, verifica che siano effettivamente loro presenti nell'immagine).
Rispondi sempre esordendo con la frase iniziale: "Ho analizzato il file caricato."."""

# Caricamento del file della pagina di giornale
uploaded_file = st.file_uploader("", type=["pdf", "png", "jpg", "jpeg"], label_visibility="collapsed")

if uploaded_file:
    st.info(f"File pronto per l'analisi: {uploaded_file.name}")

    left_spacer, center_action_col, right_spacer = st.columns([1.4, 1.2, 1.4])
    with center_action_col:
        start_analysis = st.button("Avvia analisi", use_container_width=True)

    if start_analysis:
        status_box = st.empty()
        temp_creds_path = None
        try:
            # Configurazione dinamica delle credenziali (Locale o Cloud)
            temp_creds_path = configure_gcp_credentials()
            if not temp_creds_path:
                raise Exception(
                    "Credenziali Google Cloud mancanti. Configura i Secrets su Streamlit Cloud o inserisci il file JSON nella cartella `./json/`.")

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

            # Inizializzazione del modello con le istruzioni di sistema
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
            st.subheader("Report Revisione Bozze")
            st.markdown(response.text)

        except Exception as e:
            status_box.empty()
            st.error(f"Errore durante l'analisi: {e}")
        finally:
            # Pulizia sicura del file temporaneo nel Cloud
            if temp_creds_path and "gcp_service_account" in st.secrets:
                if os.path.exists(temp_creds_path):
                    os.remove(temp_creds_path)
