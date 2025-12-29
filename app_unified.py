import streamlit as st
import streamlit.components.v1 as components
import uuid
from datetime import datetime
import time
import random
import os
import sys
import requests
import json

try:
    from PIL import Image
    import pytesseract
    from pdf2image import convert_from_bytes
    OCR_AVAILABLE = True
    
    # Windows: Try to find Tesseract if not in PATH
    if sys.platform.startswith('win'):
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.join(os.getenv('LOCALAPPDATA', ''), r"Tesseract-OCR\tesseract.exe")
        ]
        for p in possible_paths:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                break
except ImportError:
    OCR_AVAILABLE = False

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Code Geni AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2. SESSION STATE LOGIC ---

# Initialize logic derived from your code
if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = []

if "active_thread_id" not in st.session_state:
    # Create default thread
    new_id = str(uuid.uuid4())
    st.session_state.chat_threads.append({
        "id": new_id,
        "title": "New Chat",
        "messages": [],
        "created": datetime.now()
    })
    st.session_state.active_thread_id = new_id

# Initialize Settings State
if "settings" not in st.session_state:
    st.session_state.settings = {
        "model": "llama3.2",
        "temperature": 0.7,
        "font_size": "Medium",
        "particles": False,
        "user_name": "You",
        "ai_name": "Code Geni"
    }

# Initialize OCR Context State
if "ocr_context" not in st.session_state:
    st.session_state.ocr_context = {"text": None, "filename": None}

# Helper Functions
def get_active_thread():
    for thread in st.session_state.chat_threads:
        if thread["id"] == st.session_state.active_thread_id:
            return thread
    return st.session_state.chat_threads[0]

def create_new_chat():
    new_id = str(uuid.uuid4())
    new_thread = {
        "id": new_id,
        "title": "New Chat",
        "messages": [],
        "created": datetime.now()
    }
    st.session_state.chat_threads.insert(0, new_thread)
    st.session_state.active_thread_id = new_id

def delete_thread(thread_id):
    st.session_state.chat_threads = [t for t in st.session_state.chat_threads if t["id"] != thread_id]
    if not st.session_state.chat_threads:
        create_new_chat()
    else:
        st.session_state.active_thread_id = st.session_state.chat_threads[0]["id"]

def rename_thread(thread_id, new_name):
    for thread in st.session_state.chat_threads:
        if thread["id"] == thread_id:
            thread["title"] = new_name
            break

def derive_thread_title(thread):
    """Derive a title from the thread's first user message."""
    existing = thread.get("title") or "New Chat"
    messages = thread.get("messages", [])
    for message in reversed(messages):
        if message.get("role") == "user" and message.get("content"):
            snippet = message["content"].splitlines()[0]
            if len(snippet) > 36:
                snippet = snippet[:33] + "..."
            thread["title"] = snippet or existing
            return thread["title"]
    return existing

def generate_title(text):
    """Auto-generate chat title from the first query"""
    # Remove extra whitespace and limit length
    title = " ".join(text.split())
    # Capitalize first letter
    title = title[0].upper() + title[1:] if title else "New Chat"
    # Limit to 40 characters
    return title[:40] + "..." if len(title) > 40 else title

@st.cache_data(ttl=60)
def get_available_models():
    """Fetch available models from the backend (cached for 60 seconds)."""
    # API_KEY is optional for local testing in this setup
    API_KEY = "77d9e9492a0645e197fe948e3d24da4c.tC3UJDhc1Ol_O3wjAZpoj_nP"
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        # Short timeout so UI doesn't freeze if backend is down
        response = requests.get("http://127.0.0.1:8000/api/models", headers=headers, timeout=2)
        if response.status_code == 200:
            return response.json().get("models", [])
    except Exception as e:
        # st.error(f"Connection error: {e}") # Uncomment for debugging
        pass
    return []

def run_ocr_pipeline(uploaded_file):
    """Extract text from an uploaded image or PDF using OCR."""
    if not OCR_AVAILABLE:
        st.error("OCR libraries not found. Please install `pytesseract` and `pdf2image`.")
        return None

    try:
        text = ""
        # Reset file pointer to beginning just in case
        uploaded_file.seek(0)
        
        if uploaded_file.type == "application/pdf":
            # Convert PDF to images (requires poppler installed)
            try:
                images = convert_from_bytes(uploaded_file.read())
                for img in images:
                    text += pytesseract.image_to_string(img) + "\n"
            except Exception as pdf_error:
                if "poppler" in str(pdf_error).lower() or "not found" in str(pdf_error).lower():
                    st.error("❌ Poppler is not installed or not in PATH.")
                    st.info("To fix PDF OCR: Download 'Release-xxx' from https://github.com/oschwartz10612/poppler-windows/releases, extract it, and add the `bin` folder to your System PATH.")
                else:
                    st.error(f"PDF Processing Error: {pdf_error}")
                return None
        else:
            # Handle images
            try:
                image = Image.open(uploaded_file)
                text = pytesseract.image_to_string(image)
            except Exception as img_error:
                st.error(f"Image Processing Error: {img_error}")
                return None
        
        # Cleanup: Normalize whitespace
        cleaned_text = " ".join(text.split())
        if not cleaned_text:
            st.warning("OCR finished but no text was found.")
            return None
            
        return cleaned_text

    except pytesseract.TesseractNotFoundError:
        st.error("❌ Tesseract is not installed or not in PATH.")
        st.info("To fix: Install Tesseract-OCR (https://github.com/UB-Mannheim/tesseract/wiki) and restart the app.")
        return None
    except Exception as e:
        st.error(f"General OCR Error: {e}")
        return None

def call_ollama_backend(prompt: str, conversation_id: str, model: str = "llama3.2") -> str:
    """Call FastAPI backend with Ollama integration or fallback to Mock."""
    
    # API Key Configuration
    API_KEY = "77d9e9492a0645e197fe948e3d24da4c.tC3UJDhc1Ol_O3wjAZpoj_nP"

    # Mock Mode Check (for demo consistency)
    if model == "Mock Mode (Demo)":
        time.sleep(1.2) # Simulate latency
        responses = [
            "That's an interesting question! As Code Geni, I can help you structure that code.",
            "I can certainly help with that. Here is a breakdown of how this architecture works...",
            "Could you provide more details? I want to make sure I generate the perfect snippet for you.",
            "Here's a Python example that demonstrates this concept:\n\n```python\ndef hello_world():\n    print('Hello Code Geni!')\n```",
            "I'm currently running in Demo Mode, but I'm fully operational to help you design your UI."
        ]
        return random.choice(responses)

    try:
        # Added Headers with API Key
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            "http://127.0.0.1:8000/api/chat",
            headers=headers,
            json={
                "message": prompt,
                "conversation_id": conversation_id,
                "model": model
            },
            stream=True,
            timeout=300 # Increased timeout for model loading
        )
        
        if response.status_code == 200:
            full_response = []
            
            # Check content type to decide how to parse
            content_type = response.headers.get('Content-Type', '')
            
            if 'text/event-stream' in content_type:
                # Handle SSE Stream
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data:'):
                            # Handle 'data: ' and 'data:'
                            json_str = line_str[5:].strip()
                            data = json.loads(json_str)
                            
                            if data.get('type') == 'chunk':
                                full_response.append(data.get('content', ''))
                            elif data.get('type') == 'error':
                                return f"⚠️ Ollama Error: {data.get('content')}"
                                
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
            else:
                # Handle standard JSON response (fallback)
                try:
                    data = response.json()
                    if isinstance(data, dict) and 'content' in data:
                        return data['content']
                    # If it's just raw text
                    full_response.append(response.text)
                except:
                    full_response.append(response.text)
            
            result = "".join(full_response)
            return result
        
        # Handle HTTP Errors
        try:
            error_msg = response.json().get("detail", response.text)
        except:
            error_msg = response.text
        return f"⚠️ Backend Error ({response.status_code}): {error_msg}"

    except Exception as e:
        return f"Backend unavailable ({str(e)}). Ensure api.py is running on port 8000."

# --- 3. CUSTOM CSS (VISUAL REPLICA) ---
# Dynamic Font Size Logic
font_size_map = {"Small": "14px", "Medium": "16px", "Large": "18px"}
current_font_size = font_size_map.get(st.session_state.settings["font_size"], "16px")

# Particle CSS (Simple CSS animation)
particle_css = ""
if st.session_state.settings["particles"]:
    particle_css = """
    .stApp::before {
        content: "";
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background-image: radial-gradient(#3b82f6 1px, transparent 1px), radial-gradient(#3b82f6 1px, transparent 1px);
        background-size: 40px 40px;
        background-position: 0 0, 20px 20px;
        opacity: 0.05;
        z-index: -1;
        pointer-events: none;
    }
    """

# This CSS transforms Streamlit to look like the dark app screenshots
st.markdown(f"""
<style>
    /* IMPORT FONT */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    /* GLOBAL RESET & DARK THEME */
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
        font-size: {current_font_size};
    }}
    
    {particle_css}
    
    .stApp {{
        background-color: #0f1116; /* Your Deep Dark Background */
        color: #ececec;
    }}

    /* HIDE STREAMLIT CHROME */
    header[data-testid="stHeader"] {{display: none;}}
    footer {{display: none;}}
    #MainMenu {{visibility: hidden;}}
    
    /* SIDEBAR STYLING - Enhanced Modern Design */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #000000 0%, #0a0a0a 100%) !important;
        border-right: 1px solid #2a2a2a !important;
        box-shadow: 4px 0 20px rgba(0,0,0,0.5) !important;
        position: relative !important;
        z-index: 999 !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        transform: translateX(0) !important;
        min-width: 280px !important;
        width: 300px !important;
    }}
    
    /* Sidebar content wrapper */
    section[data-testid="stSidebar"] > div {{
        background: transparent !important;
        padding-top: 2rem !important;
    }}
    
    /* Sidebar scrollbar styling */
    section[data-testid="stSidebar"] ::-webkit-scrollbar {{
        width: 8px;
    }}
    
    section[data-testid="stSidebar"] ::-webkit-scrollbar-track {{
        background: #0a0a0a;
    }}
    
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {{
        background: #333;
        border-radius: 4px;
    }}
    
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover {{
        background: #444;
    }}
    
    /* Sidebar buttons styling */
    section[data-testid="stSidebar"] .stButton > button {{
        background: linear-gradient(135deg, #1a1a1a 0%, #0f0f0f 100%) !important;
        color: #fff !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
        padding: 0.6rem 1rem !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    }}
    
    section[data-testid="stSidebar"] .stButton > button:hover {{
        background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%) !important;
        border-color: #444 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
    }}
    
    /* Primary button (active/new chat) */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%) !important;
        border-color: #1e40af !important;
        box-shadow: 0 2px 12px rgba(37, 99, 235, 0.3) !important;
    }}
    
    section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
        background: linear-gradient(135deg, #1d4ed8 0%, #1e3a8a 100%) !important;
        box-shadow: 0 4px 16px rgba(37, 99, 235, 0.5) !important;
    }}
    
    /* Sidebar text input */
    section[data-testid="stSidebar"] .stTextInput > div > div > input {{
        background-color: #1a1a1a !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
        color: #fff !important;
        padding: 0.6rem 1rem !important;
    }}
    
    section[data-testid="stSidebar"] .stTextInput > div > div > input:focus {{
        border-color: #2563eb !important;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2) !important;
    }}
    
    /* Sidebar popover */
    section[data-testid="stSidebar"] [data-testid="stPopover"] {{
        background: transparent !important;
    }}
    
    section[data-testid="stSidebar"] [data-testid="stPopover"] > button {{
        background: #1a1a1a !important;
        border: 1px solid #333 !important;
        color: #999 !important;
        padding: 0.4rem 0.6rem !important;
        border-radius: 6px !important;
    }}
    
    section[data-testid="stSidebar"] [data-testid="stPopover"] > button:hover {{
        background: #2a2a2a !important;
        color: #fff !important;
        border-color: #444 !important;
    }}
    
    /* History button group styling */
    .history-button-group {{
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
        margin-top: 0.5rem;
    }}
    
    .history-entry {{
        position: relative;
        display: flex;
        width: 100%;
        gap: 0.4rem;
        align-items: stretch;
    }}
    
    .history-entry [data-testid="column"] {{
        padding: 0 !important;
        display: flex;
        align-items: stretch;
    }}
    
    .history-entry [data-testid="column"]:first-child {{
        flex: 1 1 auto;
    }}
    
    .history-entry [data-testid="column"]:first-child button {{
        width: 100% !important;
    }}
    
    .history-entry [data-testid="column"]:last-child {{
        flex: 0 0 auto;
    }}
    
    .history-entry .delete-button {{
        display: flex;
        justify-content: flex-end;
    }}
    
    .history-entry .delete-button button {{
        width: 40px !important;
        height: 40px !important;
        min-width: 40px !important;
        border-radius: 0.8rem !important;
        border: 1px solid var(--border-color, #333) !important;
        background: rgba(255, 50, 50, 0.1) !important;
        color: #ff6b6b !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease !important;
    }}
    
    .history-entry:hover .delete-button button {{
        background: rgba(255, 50, 50, 0.2) !important;
        border-color: #ff6b6b !important;
    }}
    
    .history-entry .delete-button button:hover {{
        background: rgba(255, 50, 50, 0.3) !important;
        transform: scale(1.05) !important;
    }}
    
    /* SIDEBAR SEARCH BAR */
    .sidebar-search {{
        background-color: #1a1a1a;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 10px;
        color: #fff;
        width: 100%;
    }}
    
    /* SIDEBAR SECTION HEADERS */
    .sidebar-section {{
        color: #999;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 20px 0 10px 0;
        font-weight: 600;
    }}
    
    /* CHAT ITEM STYLING */
    .chat-item {{
        background-color: transparent;
        padding: 10px 12px;
        border-radius: 8px;
        margin-bottom: 4px;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .chat-item:hover {{
        background-color: #1a1a1a;
    }}
    .chat-item.active {{
        background-color: #2a2a2a;
        border-left: 3px solid #3b82f6;
    }}
    .chat-item-actions {{
        display: none;
        gap: 8px;
    }}
    .chat-item:hover .chat-item-actions {{
        display: flex;
    }}
    
    /* NEW CHAT BUTTON */
    .new-chat-btn-container {{
        margin-bottom: 20px;
    }}
    div.stButton > button {{
        background-color: transparent;
        border: 1px solid #333;
        color: #fff;
        border-radius: 8px;
        text-align: left;
        width: 100%;
        transition: background 0.2s;
    }}
    div.stButton > button:hover {{
        background-color: #1a1a1a;
        border-color: #555;
    }}
    
    /* MAIN CHAT AREA LAYOUT */
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 8rem; /* Space for fixed input */
        max-width: 850px;
    }}

    /* WELCOME SCREEN */
    .welcome-container {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 60vh;
        color: #888;
        animation: fadeIn 0.5s ease-in;
    }}
    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}

    /* MESSAGE STYLING */
    /* User: Dark Grey Bubble, Right Aligned */
    .user-msg-container {{
        display: flex;
        justify-content: flex-end;
        margin-bottom: 15px;
    }}
    .user-msg-bubble {{
        background-color: #212121; /* Dark grey bubble */
        color: white;
        padding: 10px 18px;
        border-radius: 20px;
        max-width: 80%;
        font-size: 1rem;
        line-height: 1.5;
    }}
    
    /* AI: Transparent, Left Aligned (No bubble, just text) */
    .ai-msg-container {{
        display: flex;
        justify-content: flex-start;
        margin-bottom: 25px;
        padding-right: 10%;
    }}
    .ai-avatar {{
        width: 32px;
        height: 32px;
        margin-right: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        background: #1e40af; /* Blue background for AI */
        border-radius: 50%;
        color: white;
    }}
    .ai-text {{
        color: #ececec;
        font-size: 1rem;
        line-height: 1.6;
        margin-top: 4px;
    }}

    /* OCR UPLOAD CARD */
    .ocr-card {{
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 14px 16px;
        box-shadow: 0 12px 28px -18px rgba(0,0,0,0.6);
        display: flex;
        flex-direction: column;
        gap: 6px;
        position: relative;
        overflow: hidden;
    }}
    .ocr-card::after {{
        content: "";
        position: absolute;
        inset: 0;
        background: radial-gradient(circle at 20% 20%, rgba(59,130,246,0.16), transparent 32%),
                    radial-gradient(circle at 80% 0%, rgba(16,185,129,0.18), transparent 36%);
        pointer-events: none;
    }}
    .ocr-chip {{
        align-self: flex-start;
        padding: 4px 10px;
        border-radius: 999px;
        background: rgba(59,130,246,0.16);
        color: #bfdbfe;
        font-size: 0.82rem;
        border: 1px solid rgba(59,130,246,0.3);
        letter-spacing: 0.04em;
        animation: breathe 3s ease-in-out infinite;
    }}
    .ocr-title {{
        font-weight: 600;
        color: #e2e8f0;
        font-size: 1rem;
        margin: 2px 0;
    }}
    .ocr-hint {{
        color: #94a3b8;
        font-size: 0.9rem;
        margin: 0;
    }}
    .ocr-footnote {{
        color: #cbd5e1;
        font-size: 0.82rem;
        display: inline-flex;
        gap: 6px;
        align-items: center;
    }}
    .ocr-footnote span {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }}
    @keyframes breathe {{
        0% {{ box-shadow: 0 0 0 0 rgba(59,130,246,0.18); }}
        50% {{ box-shadow: 0 0 0 8px rgba(59,130,246,0.06); }}
        100% {{ box-shadow: 0 0 0 0 rgba(59,130,246,0.0); }}
    }}

    /* FLOATING INPUT BAR STYLING */
    /* We target the stChatInput container to make it float */
    div[data-testid="stChatInput"] {{
        position: fixed;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 750px; /* Limit width like the screenshot */
        z-index: 1000;
    }}
    
    div[data-testid="stChatInput"] > div {{
        background-color: #1e1e1e; /* Input pill color */
        border-radius: 25px;
        border: 1px solid #333;
        padding: 5px 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }}
    
    div[data-testid="stChatInput"] textarea {{
        background-color: transparent !important;
        color: white !important;
    }}

    /* POPOVER MENU STYLING (Sidebar History) */
    div[data-testid="stPopover"] > button {{
        border: none;
        padding: 8px 10px;
        color: #999;
    }}
    div[data-testid="stPopover"] > button:hover {{
        background-color: #111;
        color: white;
    }}
</style>
""", unsafe_allow_html=True)

# --- 4. SIDEBAR WITH CHATGPT-STYLE UI ---

# Add working sidebar toggle with smooth animation
st.markdown("""
<style>
    /* Force sidebar to be visible and properly styled */
    section[data-testid="stSidebar"] {
        min-width: 280px !important;
        max-width: 320px !important;
        visibility: visible !important;
        display: block !important;
        opacity: 1 !important;
        transition: transform 0.3s ease-in-out !important;
    }
    
    /* Collapsed state */
    section[data-testid="stSidebar"][data-collapsed="true"] {
        transform: translateX(-100%) !important;
    }
    
    /* Toggle button styling */
    .sidebar-toggle-btn {
        position: fixed;
        top: 1rem;
        left: 1rem;
        width: 44px;
        height: 44px;
        background: linear-gradient(135deg, #1a1a1a, #0f0f0f);
        border: 2px solid #333;
        border-radius: 10px;
        color: #fff;
        font-size: 1.3rem;
        cursor: pointer;
        z-index: 999999;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    .sidebar-toggle-btn:hover {
        background: linear-gradient(135deg, #2563eb, #1e40af);
        transform: scale(1.08);
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
    }
    
    /* When sidebar is collapsed, move button */
    .sidebar-collapsed .sidebar-toggle-btn {
        left: 1rem;
    }
    
    /* When sidebar is open, move button to right of sidebar */
    .sidebar-open .sidebar-toggle-btn {
        left: 320px;
    }
</style>

<div id="sidebar-toggle-container"></div>

<script>
(function() {
    // Create toggle button
    const createToggleButton = () => {
        let toggleBtn = document.getElementById('sidebar-toggle-button');
        if (!toggleBtn) {
            toggleBtn = document.createElement('button');
            toggleBtn.id = 'sidebar-toggle-button';
            toggleBtn.className = 'sidebar-toggle-btn';
            toggleBtn.innerHTML = '☰';
            toggleBtn.onclick = toggleSidebar;
            document.body.appendChild(toggleBtn);
        }
        return toggleBtn;
    };
    
    // Toggle sidebar function
    const toggleSidebar = () => {
        const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) return;
        
        const isCollapsed = sidebar.getAttribute('data-collapsed') === 'true';
        
        if (isCollapsed) {
            // Show sidebar
            sidebar.setAttribute('data-collapsed', 'false');
            sidebar.style.transform = 'translateX(0)';
            document.body.classList.remove('sidebar-collapsed');
            document.body.classList.add('sidebar-open');
        } else {
            // Hide sidebar
            sidebar.setAttribute('data-collapsed', 'true');
            sidebar.style.transform = 'translateX(-100%)';
            document.body.classList.remove('sidebar-open');
            document.body.classList.add('sidebar-collapsed');
        }
    };
    
    // Initialize
    setTimeout(() => {
        createToggleButton();
        const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
        if (sidebar) {
            sidebar.setAttribute('data-collapsed', 'false');
            document.body.classList.add('sidebar-open');
        }
    }, 100);
    
    // Re-create button on page updates
    const observer = new MutationObserver(createToggleButton);
    observer.observe(document.body, { childList: true, subtree: true });
})();
</script>
""", unsafe_allow_html=True)

with st.sidebar:
    # Sidebar Title with Logo
    st.markdown("""
        <div style='text-align: center; padding: 1rem 0; margin-bottom: 1rem; border-bottom: 1px solid #222;'>
            <h2 style='color: #fff; font-size: 1.5rem; margin: 0; display: flex; align-items: center; justify-content: center; gap: 10px;'>
                <span style='font-size: 1.8rem;'>🤖</span>
                <span>Code Geni AI</span>
            </h2>
        </div>
    """, unsafe_allow_html=True)
    
    # New Chat and Settings buttons
    col_new, col_set = st.columns([0.82, 0.18])
    with col_new:
        if st.button("✨ New Chat", use_container_width=True, key="new_chat_btn", type="primary"):
            create_new_chat()
            st.rerun()
    with col_set:
        with st.popover("⚙️", use_container_width=True):
            st.markdown("### ⚙️ Settings")
            
            # Model Selection
            # 1. Try to get models from backend
            detected_models = get_available_models()
            
            # 2. Define options
            if detected_models:
                # If backend is running, use real models + Mock
                model_options = detected_models + ["Mock Mode (Demo)"]
            else:
                # Fallback if backend is down
                model_options = ["llama3.2", "mistral", "codellama", "Mock Mode (Demo)"]

            # 3. Ensure current selection is valid
            current_index = 0
            if st.session_state.settings["model"] in model_options:
                current_index = model_options.index(st.session_state.settings["model"])

            st.session_state.settings["model"] = st.selectbox(
                "Model", 
                model_options, 
                index=current_index,
                key="model_select"
            )
            
            # Temperature
            st.session_state.settings["temperature"] = st.slider(
                "Temperature", 0.0, 2.0, st.session_state.settings["temperature"], key="temp_slider"
            )
            
            st.markdown("---")
            st.markdown("### 🎨 Appearance")
            
            # Font Size
            st.session_state.settings["font_size"] = st.select_slider(
                "Font Size", options=["Small", "Medium", "Large"], value=st.session_state.settings["font_size"], key="font_select"
            )
            
            # Particles Toggle
            st.session_state.settings["particles"] = st.toggle(
                "Background Particles", value=st.session_state.settings["particles"], key="particles_toggle"
            )
            
            # Avatar Names
            st.session_state.settings["user_name"] = st.text_input("User Name", value=st.session_state.settings["user_name"])
            st.session_state.settings["ai_name"] = st.text_input("AI Name", value=st.session_state.settings["ai_name"])

            st.markdown("---")
            if st.button("Clear All Chats", type="primary", key="clear_all_btn"):
                st.session_state.chat_threads = []
                create_new_chat()
                st.rerun()

    st.markdown("---")
    
    # Search Bar
    st.markdown('<div style="padding: 0 0.5rem; margin-bottom: 0.5rem;"><small style="color: #666; font-weight: 600;">🔍 SEARCH</small></div>', unsafe_allow_html=True)
    search_query = st.text_input(
        "Search conversations...", 
        placeholder="Search by message content or title",
        key="search_input",
        label_visibility="collapsed"
    )
    
    st.markdown('<div style="padding: 0.5rem; color: #666; font-size: 0.7rem; font-weight: 600; letter-spacing: 1px; margin-top: 1rem;">CONVERSATIONS</div>', unsafe_allow_html=True)
    
    # Filter threads based on search query
    filtered_threads = st.session_state.chat_threads
    if search_query.strip():
        filtered_threads = []
        query_lower = search_query.lower().strip()
        for thread in st.session_state.chat_threads:
            # Search in thread title
            title_match = query_lower in thread.get("title", "").lower()
            
            # Search in message content
            content_match = False
            for message in thread.get("messages", []):
                if query_lower in message.get("content", "").lower():
                    content_match = True
                    break
            
            if title_match or content_match:
                filtered_threads.append(thread)
    
    if not filtered_threads and search_query.strip():
        st.caption("❌ No conversations found")
    
    # Render conversation list with delete buttons
    st.markdown('<div class="history-button-group">', unsafe_allow_html=True)
    
    for thread in filtered_threads:
        t_id = thread["id"]
        t_title = derive_thread_title(thread)
        is_active = (t_id == st.session_state.active_thread_id)
        
        # Create entry with select and delete columns
        entry = st.container()
        entry.markdown('<div class="history-entry">', unsafe_allow_html=True)
        
        col_chat, col_delete = entry.columns([0.85, 0.15])
        
        with col_chat:
            if st.button(
                f"{'💬' if is_active else '  '} {t_title[:30]}...",
                key=f"chat_{t_id}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
                disabled=is_active,
            ):
                st.session_state.active_thread_id = t_id
                # Update messages for the selected thread
                for thread in st.session_state.chat_threads:
                    if thread["id"] == t_id:
                        st.session_state.messages = thread["messages"]
                        break
                st.rerun()
        
        with col_delete:
            st.markdown('<div class="delete-button">', unsafe_allow_html=True)
            if st.button(
                "🗑",
                key=f"del_{t_id}",
                help="Delete chat",
            ):
                delete_thread(t_id)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        entry.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer info
    st.markdown("---")
    st.caption(f"💬 {len(st.session_state.chat_threads)} conversations | v1.0.0")

# --- 5. MAIN CHAT AREA ---

active_thread = get_active_thread()
messages = active_thread["messages"]

# OCR UPLOAD IN CHAT AREA (Top Right)
if OCR_AVAILABLE:
    # CSS for Floating Sticky OCR Button
    st.markdown("""
    <style>
    /* 
       Target the specific popover container. 
       We use a more specific selector to ensure we grab the right element 
       and force it out of the normal flow.
    */
    div[data-testid="stPopover"] {
        position: fixed !important;
        top: 3.5rem; /* Adjusted to sit below the header area */
        right: 2rem;
        z-index: 9999999; /* Extremely high z-index */
        width: auto !important;
        display: inline-block !important;
    }
    
    /* Style the button itself to look like a floating pill */
    div[data-testid="stPopover"] > button {
        background: rgba(30, 41, 59, 0.9) !important; /* Dark slate background */
        backdrop-filter: blur(8px);
        border: 1px solid #475569 !important;
        border-radius: 20px !important; /* Pill shape */
        box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
        color: #e2e8f0 !important;
        font-weight: 600 !important;
        padding: 0.4rem 1rem !important;
        transition: all 0.2s ease !important;
        text-transform: uppercase;
        font-size: 0.8rem !important;
        letter-spacing: 0.5px;
    }
    
    div[data-testid="stPopover"] > button:hover {
        background: #3b82f6 !important; /* Blue on hover */
        border-color: #60a5fa !important;
        color: #fff !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4) !important;
    }
    
    /* Ensure the popover content (the dropdown) also appears correctly */
    div[data-testid="stPopoverBody"] {
        z-index: 9999999 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # We place the popover here, but the CSS above will rip it out of flow and pin it
    with st.popover("📎 OCR", use_container_width=False, help="Upload Image/PDF for Text Extraction"):
        st.markdown(
            """
            <div class="ocr-card">
                <div class="ocr-chip">OCR READY</div>
                <div class="ocr-title">Attach an image or PDF</div>
                <p class="ocr-hint">Extracted text is added to this chat so you can ask follow-ups instantly.</p>
                <div class="ocr-footnote">
                    <span>📄 PNG · JPG · PDF</span>
                    <span>⚡ Single file</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "Upload", 
            type=["png", "jpg", "jpeg", "pdf"], 
            key=f"ocr_{active_thread['id']}",
            label_visibility="collapsed"
        )
        
        if uploaded_file:
            if st.button("Attach to Message", key=f"proc_{active_thread['id']}", use_container_width=True):
                with st.spinner("Processing document..."):
                    extracted_text = run_ocr_pipeline(uploaded_file)
                    if extracted_text:
                        st.session_state.ocr_context = {
                            "text": extracted_text,
                            "filename": uploaded_file.name
                        }
                        st.success(f"Attached {uploaded_file.name}! Type your message below.")

# A. WELCOME STATE (Empty Chat)
if not messages:
    st.markdown(f"""
        <div class="welcome-container">
            <div style="background: linear-gradient(135deg, #2563eb, #1e40af); padding: 20px; border-radius: 20px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(37, 99, 235, 0.3);">
                <svg xmlns="http://www.w3.org/2000/svg" width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
                    <path d="M12 12 2.1 12a10.1 10.1 0 0 0 1.6 4.3"/>
                    <path d="M12 12 16.9 16.9a10 10 0 0 0 4.3-1.6"/>
                </svg>
            </div>
            <h2 style="margin-top:10px; font-weight: 600; font-size: 2rem;">Code Geni AI</h2>
            <p style="font-size: 1.1rem; opacity: 0.7;">Your intelligent coding companion</p>
        </div>
    """, unsafe_allow_html=True)

# B. ACTIVE CHAT STATE
else:
    for msg in messages:
        if msg["role"] == "user":
            # Render User Message (Right Aligned Bubble)
            st.markdown(f"""
                <div class="user-msg-container">
                    <div class="user-msg-bubble">
                        <div style="font-size: 0.75rem; opacity: 0.6; margin-bottom: 4px;">{st.session_state.settings['user_name']}</div>
                        {msg['content']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
        elif msg["role"] == "system":
             st.markdown(f"""
                <div style="display: flex; justify-content: center; margin-bottom: 15px; opacity: 0.7;">
                    <div style="font-size: 0.8rem; background: rgba(255, 255, 255, 0.05); padding: 5px 15px; border-radius: 10px; border: 1px dashed #444;">
                        {msg['content']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            # Render AI Message (Left Aligned, Icon + Text)
            # Refactored to use st.columns so Markdown/Code blocks render natively and don't overflow
            with st.container():
                col_avatar, col_text = st.columns([0.06, 0.94])
                with col_avatar:
                    st.markdown('<div class="ai-avatar">🤖</div>', unsafe_allow_html=True)
                with col_text:
                    st.markdown(f'<div style="font-weight: 600; margin-bottom: 4px; color: #3b82f6;">{st.session_state.settings["ai_name"]}</div>', unsafe_allow_html=True)
                    st.markdown(msg['content'])
                    st.markdown("""
                        <div style="display: flex; gap: 10px; margin-top: 10px; opacity: 0.5; font-size: 0.8rem;">
                            <span>📄 Copy</span> <span>🔄 Regenerate</span>
                        </div>
                    """, unsafe_allow_html=True)

# --- 6. FLOATING INPUT ---

# Display attachment indicator if file is staged
if st.session_state.ocr_context["text"]:
    st.markdown(f"""
    <div style="
        position: fixed; 
        bottom: 90px; 
        left: 50%; 
        transform: translateX(-50%); 
        background: #1e293b; 
        border: 1px solid #3b82f6; 
        padding: 8px 16px; 
        border-radius: 20px; 
        color: #bfdbfe; 
        font-size: 0.9rem; 
        z-index: 1001; 
        display: flex; 
        align-items: center; 
        gap: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
        <span>📎 Attached: <b>{st.session_state.ocr_context['filename']}</b></span>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("❌ Clear Attachment", key="clear_attach"):
        st.session_state.ocr_context = {"text": None, "filename": None}
        st.rerun()

# Uses st.chat_input, but styled via CSS above to look like a floating bar
user_input = st.chat_input(placeholder=f"Message {st.session_state.settings['ai_name']}...")

if user_input:
    # 1. Prepare Prompt
    final_prompt = user_input
    
    # 2. Handle Attachment
    if st.session_state.ocr_context["text"]:
        attachment_text = st.session_state.ocr_context["text"]
        filename = st.session_state.ocr_context["filename"]
        
        # Add system note about attachment to history
        active_thread["messages"].append({
            "role": "system", 
            "content": f"📎 Attached File: {filename}"
        })
        
        # Construct augmented prompt for the AI
        final_prompt = (
            f"I have uploaded a document named '{filename}'. Here is its content:\n"
            f"\"\"\"\n{attachment_text}\n\"\"\"\n\n"
            f"Based on this document, please answer the following:\n{user_input}"
        )
        
        # Clear attachment after sending
        st.session_state.ocr_context = {"text": None, "filename": None}

    # 3. Add User Message (Show the user's actual input)
    active_thread["messages"].append({"role": "user", "content": user_input})
    
    # 4. Auto-Title if it's the first message
    if len(active_thread["messages"]) <= 2:
        rename_thread(active_thread["id"], generate_title(user_input))

    # 5. Get selected model from session state
    selected_model = st.session_state.settings.get("model", "llama3.2")
    
    # 6. Call Backend
    with st.spinner(f"{st.session_state.settings['ai_name']} is thinking..."):
        ai_response = call_ollama_backend(
            prompt=final_prompt,
            conversation_id=active_thread["id"],
            model=selected_model
        )
    
    # 7. Add AI Message
    active_thread["messages"].append({"role": "assistant", "content": ai_response})
    
    # Rerun to update UI
    st.rerun()