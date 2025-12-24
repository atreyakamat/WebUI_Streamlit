import streamlit as st
import requests
import json
import speech_recognition as sr
from PIL import Image
import pytesseract

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Code Gen AI", layout="wide", page_icon="💻")

# -----------------------------
# SESSION STATE FOR THEME
# -----------------------------
if "theme" not in st.session_state:
    st.session_state["theme"] = "light"

# -----------------------------
# SESSION STATE FOR MODEL
# -----------------------------
if "selected_model" not in st.session_state:
    st.session_state["selected_model"] = "llama3"

# -----------------------------
# CUSTOM CSS FOR NEAT LOOK WITH THEMES (VERY COMPACT SIDEBAR)
# -----------------------------
def apply_theme():
    if st.session_state["theme"] == "dark":
        bg_color = "#0f172a"
        text_color = "#f8fafc"
        sidebar_bg = "rgba(30, 41, 59, 0.9)"
        card_bg = "rgba(30, 41, 59, 0.8)"
        border_color = "#475569"
        accent_color = "#6366f1"
        hover_bg = "#4f46e5"
        input_bg = "rgba(30, 41, 59, 0.8)"
        scrollbar_track = "#1e293b"
        scrollbar_thumb = "#6366f1"
    else:
        bg_color = "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #f1f5f9 100%)"
        text_color = "#1e293b"
        sidebar_bg = "rgba(255, 255, 255, 0.9)"
        card_bg = "rgba(255, 255, 255, 0.8)"
        border_color = "#e2e8f0"
        accent_color = "#6366f1"
        hover_bg = "#4f46e5"
        input_bg = "rgba(255, 255, 255, 0.8)"
        scrollbar_track = "#f1f5f9"
        scrollbar_thumb = "#6366f1"

    css = f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {{
            font-family: 'Inter', sans-serif;
        }}
        
        .stApp {{
            background: {bg_color};
            color: {text_color};
        }}
        
        .stTitle {{
            color: {accent_color};
            font-weight: 700;
            text-align: center;
            margin-bottom: 2rem;
        }}
        
        .stSidebar {{
            background: {sidebar_bg};
            backdrop-filter: blur(10px);
            border-right: 1px solid {border_color};
            width: 220px !important;  /* Even narrower */
            font-size: 0.8rem;  /* Smaller font */
            padding: 0.25rem;  /* Minimal padding */
            max-height: 100vh;  /* Limit height to viewport */
            overflow: hidden;  /* Hide overflow to prevent scrolling */
        }}
        
        .stSidebar .stMarkdown {{
            font-size: 0.75rem;  /* Very small markdown text */
            margin: 0.1rem 0;  /* Minimal margins */
            line-height: 1.2;  /* Tighter line height */
        }}
        
        .stSidebar .stButton>button {{
            border-radius: 4px;  /* Smaller radius */
            border: 1px solid {accent_color};
            background: {accent_color};
            color: white;
            font-weight: 500;
            font-size: 0.7rem;  /* Very small button text */
            padding: 0.15rem 0.3rem;  /* Minimal padding */
            margin: 0.1rem 0;  /* Minimal margin */
            height: auto;  /* Allow height to adjust */
            transition: all 0.3s ease;
        }}
        
        .stSidebar .stButton>button:hover {{
            background: {hover_bg};
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(99, 102, 241, 0.3);
        }}
        
        .stSidebar .stTextInput>div>div>input {{
            border-radius: 4px;
            border: 1px solid {border_color};
            padding: 0.15rem;  /* Minimal padding */
            font-size: 0.8rem;
            background: {input_bg};
            color: {text_color};
        }}
        
        .stSidebar .stTextInput>div>div>input:focus {{
            border-color: {accent_color};
            box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.2);
        }}
        
        .stChatMessage {{
            background: {card_bg};
            border-radius: 12px;
            border: 1px solid {border_color};
            padding: 1rem;
            margin: 0.5rem 0;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            color: {text_color};
        }}
        
        .stSpinner {{
            color: {accent_color};
        }}
        
        .stFileUploader {{
            border: 2px dashed {accent_color};
            border-radius: 8px;
            padding: 1rem;
            background: {card_bg};
        }}
        
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
            color: {text_color};
            font-size: 0.9rem;  /* Smaller headers */
        }}
        
        .stColumns {{
            gap: 0.25rem;  /* Smaller gap */
        }}
        
        .stSidebar .stSelectbox {{
            font-size: 0.75rem;  /* Very small selectbox */
        }}
        
        .stSidebar .stSelectbox div[role="combobox"] {{
            padding: 0.1rem;  /* Minimal padding */
        }}
        
        /* Hide scrollbar completely */
        .stSidebar ::-webkit-scrollbar {{
            display: none;
        }}
        .stSidebar {{
            -ms-overflow-style: none;  /* IE and Edge */
            scrollbar-width: none;  /* Firefox */
        }}
        """

    # Dark mode specific overrides
    if st.session_state["theme"] == "dark":
        css += """
        .stApp, .stMarkdown, .stChatMessage, .stFileUploader label {
            color: #ffffff !important;  /* Ensure all text is white */
        }
        .stFileUploader {
            background: #ffffff !important;  /* White background for drag and drop */
            color: #808080 !important;  /* Ash color for the folder input box text */
        }
        .stFileUploader input[type="file"]::file-selector-button {
            color: #808080 !important;  /* Ash color for file selector button text */
        }
        """

    css += """
        </style>
    """

    st.markdown(css, unsafe_allow_html=True)

apply_theme()

st.title("💻 Code Gen AI")

# -----------------------------
# SESSION STATE
# -----------------------------
if "chats" not in st.session_state:
    st.session_state["chats"] = {"Chat 1": []}

if "current_chat" not in st.session_state:
    st.session_state["current_chat"] = "Chat 1"

if "user_msg" not in st.session_state:
    st.session_state["user_msg"] = ""

if "ocr_done" not in st.session_state:
    st.session_state["ocr_done"] = False

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

# -----------------------------
# OLLAMA SETTINGS
# -----------------------------
OLLAMA_URL = "http://localhost:11434/api/chat"
model_name = st.session_state["selected_model"]

# -----------------------------
# OCR SETUP (WINDOWS)
# -----------------------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -----------------------------
# FUNCTIONS
# -----------------------------
def ask_llama(messages):
    # System prompt to enforce code-focused responses
    system_prompt = {
        "role": "system",
        "content": "You are Code Gen AI, a specialized assistant for fixing, enhancing, and upgrading code projects. Always focus on code-related queries. If the user asks something unrelated to coding, such as greetings or off-topic questions, respond politely with something like 'Hey coder, how can I help fix or improve your code today?' and encourage them to ask about code."
    }
    full_messages = [system_prompt] + messages
    payload = {"model": model_name, "messages": full_messages}
    reply = ""
    try:
        r = requests.post(OLLAMA_URL, json=payload, stream=True)
        for line in r.iter_lines():
            if line:
                data = json.loads(line.decode())
                if "message" in data:
                    reply += data["message"]["content"]
                if data.get("done"):
                    break
    except Exception as e:
        reply = f"❌ Error: {e}"
    return reply

def extract_text_from_image(image):
    try:
        return pytesseract.image_to_string(image).strip()
    except:
        return ""

def save_user_message(text):
    if not text.strip():
        return
    st.session_state["chats"][st.session_state["current_chat"]].append(
        {"role": "user", "content": text}
    )
    st.session_state["user_msg"] = ""

def recognize_speech():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            audio = r.listen(source, phrase_time_limit=5)
            return r.recognize_google(audio)
    except:
        return None

def get_ollama_models():
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            data = response.json()
            available_models = [model["name"] for model in data.get("models", [])]
            # Add common models if not present
            common_models = ["llama3", "llama2", "codellama", "mistral", "gemma", "phi", "orca-mini"]
            for model in common_models:
                if model not in available_models:
                    available_models.append(model)
            return available_models
        else:
            return ["llama3", "llama2", "codellama", "mistral", "gemma", "phi", "orca-mini"]  # Fallback with more models
    except:
        return ["llama3", "llama2", "codellama", "mistral", "gemma", "phi", "orca-mini"]  # Fallback with more models

# =====================================================
# 🔝 AUTO OCR IMAGE UPLOAD (NO BUTTON, NO DISPLAY)
# =====================================================
uploaded_image = st.file_uploader(
    "📷 Upload image (auto OCR)",
    type=["png", "jpg", "jpeg"],
    key=f"uploader_{st.session_state['uploader_key']}"
)

if uploaded_image and not st.session_state["ocr_done"]:
    with st.spinner("Reading image..."):
        image = Image.open(uploaded_image)
        ocr_text = extract_text_from_image(image)

        if ocr_text:
            save_user_message(ocr_text)

    st.session_state["ocr_done"] = True
    st.session_state["uploader_key"] += 1
    st.rerun()

# -----------------------------
# SIDEBAR (VERY COMPACT FRAME)
# -----------------------------
with st.sidebar:
    st.markdown("**📁 Chats**")  # Smaller title
    
    # Theme Selector (compact)
    col1, col2 = st.columns(2)
    if col1.button("☀️", use_container_width=True):  # Icon only for compactness
        st.session_state["theme"] = "light"
        st.rerun()
    if col2.button("🌙", use_container_width=True):
        st.session_state["theme"] = "dark"
        st.rerun()
    
    st.markdown("---")
    
    # Function to get display name for a chat (shorter truncation)
    def get_display_name(chat_key):
        chat_data = st.session_state["chats"][chat_key]
        if chat_data:
            last_user_msg = next((msg["content"] for msg in reversed(chat_data) if msg["role"] == "user"), None)
            if last_user_msg:
                # Truncate to 20 characters for more compactness
                return last_user_msg[:20] + (".." if len(last_user_msg) > 20 else "")
        return chat_key  # Fallback to key like "Chat 1"
    
    for name in list(st.session_state["chats"].keys()):
        display_name = get_display_name(name)
        if st.button(display_name, use_container_width=True):
            st.session_state["current_chat"] = name
            st.session_state["ocr_done"] = False
            st.rerun()
    
    if st.button("🆕 New", use_container_width=True):  # Shorter label
        name = f"Chat {len(st.session_state['chats']) + 1}"
        st.session_state["chats"][name] = []
        st.session_state["current_chat"] = name
        st.session_state["ocr_done"] = False
        st.rerun()
    
    if st.button("🗑 Del All", use_container_width=True):  # Shorter label
        st.session_state.clear()
        st.session_state["chats"] = {"Chat 1": []}
        st.session_state["current_chat"] = "Chat 1"
        st.session_state["user_msg"] = ""
        st.session_state["ocr_done"] = False
        st.session_state["uploader_key"] = 0
        st.rerun()
    
    # Export Chat Button (compact)
    current_chat_data = st.session_state["chats"][st.session_state["current_chat"]]
    chat_json = json.dumps(current_chat_data, indent=4)
    st.download_button(
        label="📤 Export",
        data=chat_json,
        file_name=f"{st.session_state['current_chat'].replace(' ', '_')}.json",
        mime="application/json",
        use_container_width=True
    )
    
    st.markdown("---")
    # Display the display name for the active chat (compact)
    active_display = get_display_name(st.session_state["current_chat"])
    st.markdown(f"**Active:** {active_display}")
    st.markdown(f"**Model:** {st.session_state['selected_model']}")
    
    # Model Selection Dropdown at the bottom (compact)
    models = get_ollama_models()
    selected_model = st.selectbox(
        "",
        models,
        index=models.index(st.session_state["selected_model"]) if st.session_state["selected_model"] in models else 0,
        label_visibility="collapsed"
    )
    if selected_model != st.session_state["selected_model"]:
        st.session_state["selected_model"] = selected_model
        st.rerun()

# -----------------------------
# CHAT DISPLAY
# -----------------------------
chat = st.session_state["chats"][st.session_state["current_chat"]]

for msg in chat:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# -----------------------------
# ASSISTANT RESPONSE (ONCE)
# -----------------------------
if chat and chat[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Code Gen AI is thinking..."):
            reply = ask_llama(chat)
            st.write(reply)
    chat.append({"role": "assistant", "content": reply})

# -----------------------------
# SPACING TO MOVE INPUT BAR DOWN
# -----------------------------
st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)

# -----------------------------
# USER INPUT (BOTTOM)
# -----------------------------
col1, col2 = st.columns([4, 1])

with col1:
    st.text_input(
        "Type your message",
        key="user_msg",
        on_change=lambda: (
            save_user_message(st.session_state["user_msg"]),
            st.session_state.update(user_msg="")
        ),
        label_visibility="collapsed"
    )

with col2:
    st.button(
        "🎤 Speak",
        on_click=lambda: (
            lambda t=recognize_speech(): save_user_message(t) if t else None
        )(),
        use_container_width=True
    )