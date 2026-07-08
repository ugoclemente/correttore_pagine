import streamlit as st
from google import genai
from google.genai import types
import tempfile
import os
import json
import time

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Revisore Bozze Redazione", layout="wide", page_icon="📰")

st.title("📰 Assistente di Revisione Bozze ed Errori")
st.write("Carica una pagina di giornale (PDF o Immagine) per analizzare refusi, ortografia e impaginazione.")

# File locale per salvare il System Prompt in modo persistente
PROMPT_FILE = "system_prompt.json"
DEFAULT_PROMPT = """Sei un correttore di bozze e revisore di testi senior per un quotidiano cartaceo italiano. Il tuo compito è esaminare attentamente le pagine di giornale caricate in formato PDF o immagine per identificare anomalie, refusi, incongruenze e proporre correzioni precise.

La tua analisi deve focalizzarsi sui seguenti aspetti:
1. Ortografia e Refusi: Errori di battitura, lettere mancanti, invertite o raddoppiate, uso errato di accenti e apostrofi.
2. Grammatica e Sintassi: Errori di concordanza, tempi verbali errati, punteggiatura fuori posto.
3. Ripetizioni nella Titolazione: Verifica che non vi siano ripetizioni della stessa parola chiave tra occhiello, titolo principale e sommario dello stesso articolo.
4. Errori Logici e di Contenuto: Contraddizioni interne, date o dati numerici incoerenti.

ATTENZIONE AI FALSI POSITIVI DA SILLABAZIONE (OCR): Durante l'analisi visiva delle colonne di testo, il motore di estrazione potrebbe convertire le parole spezzate a fine riga in termini separati da uno spazio o apparentemente privi di trattino (es. 'del lo', 'Comu nale', 'Condan na', 'ar- restata'). Ignora sistematicamente queste occorrenze. Non segnalare MAI come errore la mancanza di trattini di unione o la presenza di spazi all'interno di parole divise tra due righe consecutive, poiché si tratta di un artefatto tecnico di lettura e non di un vero refuso sulla pagina stampata."""


# Funzioni per caricare/salvare il prompt modificato
def load_system_prompt():
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("prompt", DEFAULT_PROMPT)
    return DEFAULT_PROMPT


def save_system_prompt(prompt_text):
    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        json.dump({"prompt": prompt_text}, f, ensure_ascii=False, indent=4)


# Inizializzazione del prompt in session state
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = load_system_prompt()

# Barra laterale (Sidebar) per la gestione del System Prompt
with st.sidebar:
    st.header("⚙️ Impostazioni System Prompt")
    st.write("Modifica le istruzioni dell'AI per affinare il comportamento del modello.")

    updated_prompt = st.text_area(
        "System Instruction:",
        value=st.session_state.system_prompt,
        height=450
    )

    if st.button("Salva ed Applica Prompt"):
        st.session_state.system_prompt = updated_prompt
        save_system_prompt(updated_prompt)
        st.success("System Prompt aggiornato con successo!")

# Gestione sicura dei Secrets (Evita il crash se avviato in locale senza secrets.toml)
api_key_env = ""
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key_env = st.secrets["GEMINI_API_KEY"]
except Exception:
    # Ignora l'errore se siamo in locale e il file secrets.toml non esiste
    pass

# Input per la chiave API di Google Gemini
user_key = st.text_input(
    "Inserisci la tua Gemini API Key (lascia vuoto se già configurata sul server):",
    type="password",
    value=api_key_env
)

# La chiave attiva sarà quella inserita dall'utente o, in alternativa, quella nei Secrets
active_key = user_key if user_key else api_key_env

if not active_key:
    st.warning("Per favore, inserisci una chiave API di Google Gemini per procedere.")

# Uploader di file
uploaded_file = st.file_uploader(
    "Trascina o seleziona il file della pagina (PDF, PNG, JPG)",
    type=["pdf", "png", "jpg", "jpeg"]
)

if uploaded_file and active_key:
    # Salvataggio temporaneo del file su disco per passarlo all'API di Gemini
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as temp_file:
        temp_file.write(uploaded_file.getvalue())
        temp_path = temp_file.name

    st.info(f"File locale pronto per l'invio: {uploaded_file.name}")

    # Esecuzione dell'analisi
    if st.button("Avvia Analisi Errori"):
        status_box = st.empty()
        try:
            # Inizializzazione del nuovo client con il pacchetto aggiornato 'google-genai'
            client = genai.Client(api_key=active_key)

            status_box.info("1. Caricamento del file sui server Google in corso...")
            gemini_file = client.files.upload(file=temp_path)

            # Ciclo di polling per verificare che il file sia pronto
            status_box.info("2. File caricato con successo. Google sta elaborando la pagina (OCR)...")
            file_info = client.files.get(name=gemini_file.name)
            while file_info.state.name == "PROCESSING":
                status_box.warning("Elaborazione in corso sui server Google... Attendi qualche secondo...")
                time.sleep(3)
                file_info = client.files.get(name=gemini_file.name)

            if file_info.state.name == "FAILED":
                raise Exception("L'elaborazione del file è fallita sui server Google.")

            status_box.success("3. Elaborazione completata! Avvio dell'analisi dei refusi...")

            # Chiamata di generazione con la nuova sintassi SDK
            response = client.models.generate_content(
                model='gemini-1.5-pro',
                contents=[
                    gemini_file,
                    "Esegui una revisione completa di questa pagina di giornale seguendo le istruzioni di sistema."
                ],
                config=types.GenerateContentConfig(
                    system_instruction=st.session_state.system_prompt,
                ),
            )

            # Rimuoviamo il box dello stato e mostriamo il risultato
            status_box.empty()
            st.subheader("📋 Report Revisione Bozze")
            st.markdown(response.text)

            # Eliminazione sicura del file dai server remoti
            client.files.delete(name=gemini_file.name)

        except Exception as e:
            status_box.empty()
            st.error(f"Si è verificato un errore durante l'analisi: {e}")
        finally:
            # Rimozione del file temporaneo locale
            if os.path.exists(temp_path):
                os.remove(temp_path)