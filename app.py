import streamlit as st
import google.generativeai as genai
import tempfile
import os
import json

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

# Input per la chiave API di Google Gemini
api_key = st.text_input("Inserisci la tua Gemini API Key (o configurala nei Secrets):", type="password")
if not api_key:
    # Prova a leggere dai secrets di Streamlit se ospitato online
    api_key = st.secrets.get("GEMINI_API_KEY", "")

if api_key:
    genai.configure(api_key=api_key)
else:
    st.warning("Per favore, inserisci una chiave API di Google Gemini per procedere.")

# Uploader di file
uploaded_file = st.file_uploader(
    "Trascina o seleziona il file della pagina (PDF, PNG, JPG)",
    type=["pdf", "png", "jpg", "jpeg"]
)

if uploaded_file and api_key:
    # Salvataggio temporaneo del file su disco per passarlo all'API di Gemini
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as temp_file:
        temp_file.write(uploaded_file.getvalue())
        temp_path = temp_file.name

    st.info(f"File caricato: {uploaded_file.name}. Analisi avviata...")

    # Esecuzione dell'analisi
    if st.button("Avvia Analisi Errori"):
        with st.spinner("L'intelligenza artificiale sta analizzando la pagina..."):
            try:
                # Caricamento del file tramite File API di Gemini (gestisce PDF nativamente)
                gemini_file = genai.upload_file(path=temp_path)

                # Configurazione del modello con le istruzioni di sistema personalizzate
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-pro",  # Modello raccomandato per compiti complessi di lettura
                    system_instruction=st.session_state.system_prompt
                )

                # Generazione del report di correzione bozze
                response = model.generate_content([
                    gemini_file,
                    "Esegui una revisione completa di questa pagina di giornale seguendo le istruzioni di sistema."
                ])

                # Mostra i risultati nella UI
                st.subheader("📋 Report Revisione Bozze")
                st.markdown(response.text)

                # Pulizia del file caricato sui server Gemini
                genai.delete_file(gemini_file.name)

            except Exception as e:
                st.error(f"Si è verificato un errore durante l'analisi: {e}")
            finally:
                # Rimozione del file temporaneo locale
                if os.path.exists(temp_path):
                    os.remove(temp_path)