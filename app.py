import streamlit as st
import os
import json
import tempfile
import vertexai
from vertexai.generative_models import GenerativeModel, Part

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Revisore Bozze Redazione", layout="wide", page_icon="📰")

st.title("📰 Assistente di Revisione Bozze ed Errori - Vertex AI")
st.write("Analisi professionale delle pagine di giornale basata sulla configurazione aziendale Vertex AI.")

# File locale per salvare il System Prompt in modo persistente
PROMPT_FILE = "system_prompt.json"
DEFAULT_PROMPT = """Sei un correttore di bozze e revisore di testi senior per un quotidiano cartaceo italiano. Il tuo compito è esaminare attentamente le pagine di giornale caricate in formato PDF o immagine per identificare anomalie, refusi, incongruenze e proporre correzioni precise.

La tua analisi deve focalizzarsi sui seguenti aspetti:
1. Ortografia e Refusi: Errori di battitura, lettere mancanti, invertite o raddoppiate, uso errato di accenti e apostrofi.
2. Grammatica e Sintassi: Errori di concordanza, tempi verbali errati, punteggiatura fuori posto.
3. Ripetizioni nella Titolazione: Verifica che non vi siano ripetizioni della stessa parola chiave tra occhiello, titolo principale e sommario dello stesso articolo.
4. Errori Logici e di Contenuto: Contraddizioni interne, date o dati numerici incoerenti.

ATTENZIONE AI FALSI POSITIVI DA SILLABAZIONE (OCR): Durante l’analisi visiva delle colonne di testo, il motore di estrazione potrebbe convertire le parole spezzate a fine riga in termini separati da uno spazio o apparentemente privi di trattino (es. 'del lo', 'Comu nale', 'Condan na', 'ar- restata'). Ignora sistematicamente queste occorrenze. Non segnalare MAI come errore la mancanza di trattini di unione o la presenza di spazi all'interno di parole divise tra due righe consecutive, poiché si tratta di un artefatto tecnico di lettura e non di un vero refuso sulla pagina stampata."""


# Funzioni per caricare/salvare il prompt
def load_system_prompt():
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("prompt", DEFAULT_PROMPT)
    return DEFAULT_PROMPT


def save_system_prompt(prompt_text):
    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        json.dump({"prompt": prompt_text}, f, ensure_ascii=False, indent=4)


if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = load_system_prompt()

# Configurazione del progetto tramite Sidebar (Allineato a vertex_init)
with st.sidebar:
    st.header("⚙️ Configurazione Google Cloud")

    # ID Progetto e Regione impostati di default sui tuoi valori attivi
    gcp_project = st.text_input("GCP Project ID:", value="pagine-automatiche-project")
    gcp_location = st.text_input("GCP Location (Regione):", value="us-central1")

    st.write("---")
    st.subheader("🔑 Credenziali Service Account")

    # Rilevamento automatico delle chiavi JSON nella tua cartella locale "json" (come nel tuo codice)
    json_dir = os.path.join(os.path.dirname(__file__), "json")
    json_files = []
    if os.path.exists(json_dir):
        json_files = [f for f in os.listdir(json_dir) if f.endswith(".json")]

    # Seleziona la chiave dal menu a discesa se presente, altrimenti permette il caricamento manuale
    if json_files:
        selected_key = st.selectbox("Seleziona chiave JSON trovata in ./json/:", json_files)
        json_key_path = os.path.join(json_dir, selected_key)
    else:
        st.warning("Nessuna chiave JSON rilevata in `./json/`. Puoi caricarne una qui sotto:")
        json_key_path = None

    uploaded_key = st.file_uploader("Carica file credenziali JSON:", type=["json"])

    st.write("---")
    st.subheader("🤖 Modello Generativo")
    # Menu di scelta per utilizzare gemini-1.5-pro o il nuovo gemini-2.5-pro del tuo modulo
    model_name = st.selectbox("Modello LLM:", ["gemini-1.5-pro", "gemini-2.5-pro"])

    st.write("---")
    st.header("✍️ Impostazioni System Prompt")
    updated_prompt = st.text_area("System Instruction:", value=st.session_state.system_prompt, height=350)

    if st.button("Salva ed Applica Prompt"):
        st.session_state.system_prompt = updated_prompt
        save_system_prompt(updated_prompt)
        st.success("System Prompt aggiornato!")

# Uploader per il documento (PDF o Immagine)
uploaded_file = st.file_uploader("Carica la pagina del giornale (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file:
    st.info(f"File pronto per l'analisi: {uploaded_file.name}")

    if st.button("Avvia Analisi Errori"):
        with st.spinner("Inizializzazione Vertex AI e analisi del layout in corso..."):
            try:
                # Gestione dinamica delle credenziali
                final_key_path = ""
                if uploaded_key is not None:
                    # Se l'utente carica una chiave al volo, la salviamo temporaneamente
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_key:
                        temp_key.write(uploaded_key.getvalue())
                        final_key_path = temp_key.name
                elif json_key_path:
                    final_key_path = json_key_path
                else:
                    raise Exception(
                        "Credenziali JSON non trovate. Carica un file o posizionalo nella cartella `./json/`.")

                # Configurazione ambiente (Stessa identica logica del tuo vertex_init.py)
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = final_key_path
                vertexai.init(project=gcp_project, location=gcp_location)

                # Lettura del file in memoria ed estrazione dei byte
                file_bytes = uploaded_file.getvalue()
                mime_type = uploaded_file.type

                # Creazione del blocco multimediale inline per Vertex AI (massima velocità)
                media_part = Part.from_data(
                    data=file_bytes,
                    mime_type=mime_type
                )

                # Istanziazione del modello con le istruzioni di sistema
                model = GenerativeModel(
                    model_name,
                    system_instruction=[st.session_state.system_prompt]
                )

                # Richiesta diretta senza polling asincrono esterno
                response = model.generate_content([
                    media_part,
                    "Esegui una revisione completa di questa pagina di giornale seguendo le istruzioni di sistema."
                ])

                st.subheader(f"📋 Report Revisione Bozze (Vertex AI - {model_name})")
                st.markdown(response.text)

                # Rimozione del file temporaneo se è stata usata una chiave caricata al volo
                if uploaded_key is not None and os.path.exists(final_key_path):
                    os.remove(final_key_path)

            except Exception as e:
                st.error(f"Errore durante l'analisi: {e}")