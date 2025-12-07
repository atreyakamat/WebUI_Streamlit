import streamlit as st
import uuid
from datetime import datetime
import time

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Ollama UI Replica",
    page_icon="🦙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2. CUSTOM CSS (VISUAL REPLICA) ---
# This CSS transforms Streamlit to look like the dark app screenshots
st.markdown("""
<style>
    /* IMPORT FONT */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    /* GLOBAL RESET & DARK THEME */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #0f1116; /* Your Deep Dark Background */
        color: #ececec;
    }

    /* HIDE STREAMLIT CHROME */
    header[data-testid="stHeader"] {display: none;}
    footer {display: none;}
    #MainMenu {visibility: hidden;}
    
    /* SIDEBAR STYLING */
    section[data-testid="stSidebar"] {
        background-color: #000000;
        border-right: 1px solid #222;
        transition: all 0.3s ease;
    }
    
    /* HAMBURGER MENU TOGGLE BUTTON */
    .hamburger-btn {
        position: fixed;
        top: 1rem;
        left: 1rem;
        z-index: 9999;
        background-color: #1a1a1a;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 10px 12px;
        cursor: pointer;
        color: #fff;
        font-size: 1.2rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        width: 44px;
        height: 44px;
    }
    .hamburger-btn:hover {
        background-color: #2a2a2a;
        border-color: #555;
        transform: scale(1.1);
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    .hamburger-btn:active {
        transform: scale(0.95);
    }
    
    /* NEW CHAT BUTTON */
    .new-chat-btn-container {
        margin-bottom: 20px;
    }
    div.stButton > button {
        background-color: transparent;
        border: 1px solid #333;
        color: #fff;
        border-radius: 8px;
        text-align: left;
        width: 100%;
        transition: background 0.2s;
    }
    div.stButton > button:hover {
        background-color: #1a1a1a;
        border-color: #555;
    }
    
    /* MAIN CHAT AREA LAYOUT */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 8rem; /* Space for fixed input */
        max-width: 850px;
    }

    /* WELCOME SCREEN */
    .welcome-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 60vh;
        color: #888;
        animation: fadeIn 0.5s ease-in;
    }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

    /* MESSAGE STYLING */
    /* User: Dark Grey Bubble, Right Aligned */
    .user-msg-container {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 15px;
    }
    .user-msg-bubble {
        background-color: #212121; /* Dark grey bubble */
        color: white;
        padding: 10px 18px;
        border-radius: 20px;
        max-width: 80%;
        font-size: 1rem;
        line-height: 1.5;
    }
    
    /* AI: Transparent, Left Aligned (No bubble, just text) */
    .ai-msg-container {
        display: flex;
        justify-content: flex-start;
        margin-bottom: 25px;
        padding-right: 10%;
    }
    .ai-avatar {
        width: 32px;
        height: 32px;
        margin-right: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
    }
    .ai-text {
        color: #ececec;
        font-size: 1rem;
        line-height: 1.6;
        margin-top: 4px;
    }

    /* FLOATING INPUT BAR STYLING */
    /* We target the stChatInput container to make it float */
    div[data-testid="stChatInput"] {
        position: fixed;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 750px; /* Limit width like the screenshot */
        z-index: 1000;
    }
    
    div[data-testid="stChatInput"] > div {
        background-color: #1e1e1e; /* Input pill color */
        border-radius: 25px;
        border: 1px solid #333;
        padding: 5px 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    
    div[data-testid="stChatInput"] textarea {
        background-color: transparent !important;
        color: white !important;
    }

    /* POPOVER MENU STYLING (Sidebar History) */
    div[data-testid="stPopover"] > button {
        border: none;
        padding: 8px 10px;
        color: #999;
    }
    div[data-testid="stPopover"] > button:hover {
        background-color: #111;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. SESSION STATE LOGIC ---

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

def generate_title(text):
    return text[:25] + "..." if len(text) > 25 else text

def call_ollama_backend(prompt: str, conversation_id: str, model: str = "llama3.2") -> str:
    """Call FastAPI backend with Ollama integration."""
    import requests
    import json
    
    try:
        response = requests.post(
            "http://localhost:8000/api/chat",
            json={
                "message": prompt,
                "conversation_id": conversation_id,
                "model": model
            },
            stream=True,
            timeout=120
        )
        
        if response.status_code == 200:
            full_response = []
            for line in response.iter_lines():
                if line:
                    try:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data = json.loads(line_str[6:])
                            if data.get('type') == 'chunk':
                                full_response.append(data.get('content', ''))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
            return "".join(full_response) if full_response else None
        return None
    except Exception as e:
        st.warning(f"Backend connection failed: {e}")
        return None

# --- 4. SIDEBAR UI ---

# Hamburger Menu Toggle (Fixed position, always visible)
import streamlit.components.v1 as components

components.html(
    """
    <style>
    .hamburger-toggle {
        position: fixed;
        top: 1rem;
        left: 1rem;
        z-index: 9999;
        background-color: #1a1a1a;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 10px 12px;
        cursor: pointer;
        color: #fff;
        font-size: 1.2rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        width: 44px;
        height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .hamburger-toggle:hover {
        background-color: #2a2a2a;
        border-color: #555;
        transform: scale(1.1);
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    </style>
    <div class="hamburger-toggle" id="hamburger-btn">☰</div>
    <script>
    (function() {
        const btn = document.getElementById('hamburger-btn');
        btn.addEventListener('click', function() {
            // Access parent document (Streamlit iframe)
            const parentDoc = window.parent.document;
            
            // Find the collapse button
            const collapseBtn = parentDoc.querySelector('[data-testid="collapsedControl"]');
            
            if (collapseBtn) {
                collapseBtn.click();
            } else {
                // Alternative: try to find sidebar and toggle directly
                const sidebar = parentDoc.querySelector('[data-testid="stSidebar"]');
                if (sidebar) {
                    // Simulate keyboard shortcut for sidebar toggle
                    const event = new KeyboardEvent('keydown', {
                        key: '[',
                        ctrlKey: true,
                        bubbles: true
                    });
                    parentDoc.dispatchEvent(event);
                }
            }
        });
    })();
    </script>
    """,
    height=0,
    width=0,
)

with st.sidebar:
    # 1. New Chat Button
    col_new, col_set = st.columns([0.85, 0.15])
    with col_new:
        if st.button("📝 New Chat", use_container_width=True):
            create_new_chat()
            st.rerun()
    with col_set:
        st.button("⚙️", help="Settings")

    st.markdown("### Today")
    
    # 2. History List
    for thread in st.session_state.chat_threads:
        t_id = thread["id"]
        t_title = thread["title"]
        is_active = (t_id == st.session_state.active_thread_id)
        
        # Visual Styling for Active/Inactive
        label_prefix = "🔹 " if is_active else ""
        label = f"{label_prefix}{t_title}"
        
        # We use a Popover to handle interaction (Click to open, or Rename/Delete)
        # This acts as the "Chat Item"
        with st.popover(label, use_container_width=True):
            st.caption(f"Manage: {t_title}")
            
            # Switch to this chat
            if st.button("📂 Open Chat", key=f"open_{t_id}"):
                st.session_state.active_thread_id = t_id
                st.rerun()
            
            # Rename
            new_name = st.text_input("Rename", value=t_title, key=f"ren_{t_id}")
            if st.button("Save Name", key=f"save_{t_id}"):
                rename_thread(t_id, new_name)
                st.rerun()
                
            # Delete
            if st.button("🗑️ Delete Chat", key=f"del_{t_id}", type="primary"):
                delete_thread(t_id)
                st.rerun()

# --- 5. MAIN CHAT AREA ---

active_thread = get_active_thread()
messages = active_thread["messages"]

# A. WELCOME STATE (Empty Chat)
if not messages:
    st.markdown("""
        <div class="welcome-container">
            <svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M15 6v14"/>
                <path d="M9 6v14"/>
                <rect x="2" y="6" width="20" height="12" rx="4"/>
                <path d="M6 6V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v2"/>
            </svg>
            <h2 style="margin-top:20px; font-weight: 500;">How can I assist you today?</h2>
        </div>
    """, unsafe_allow_html=True)

# B. ACTIVE CHAT STATE
else:
    for msg in messages:
        if msg["role"] == "user":
            # Render User Message (Right Aligned Bubble)
            st.markdown(f"""
                <div class="user-msg-container">
                    <div class="user-msg-bubble">{msg['content']}</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            # Render AI Message (Left Aligned, Icon + Text)
            st.markdown(f"""
                <div class="ai-msg-container">
                    <div class="ai-avatar">🦙</div>
                    <div class="ai-text">
                        {msg['content']}
                        <div style="display: flex; gap: 10px; margin-top: 10px; opacity: 0.5; font-size: 0.8rem;">
                            <span>📄 Copy</span> <span>🔄 Regenerate</span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

# --- 6. FLOATING INPUT ---

# Uses st.chat_input, but styled via CSS above to look like a floating bar
user_input = st.chat_input(placeholder="Message Llama...")

if user_input:
    # 1. Add User Message
    active_thread["messages"].append({"role": "user", "content": user_input})
    
    # 2. Auto-Title if it's the first message
    if len(active_thread["messages"]) == 1:
        rename_thread(active_thread["id"], generate_title(user_input))

    # 3. Call Ollama Backend
    with st.spinner("Thinking..."):
        ai_response = call_ollama_backend(
            prompt=user_input,
            conversation_id=active_thread["id"],
            model="llama3.2"
        )
    
    # Fallback to mock if backend fails
    if not ai_response:
        ai_response = "Sometimes that's just the way it is. If you ever want to chat or need help with something, feel free to reach out. (Using mock - backend unavailable)"
    
    # 4. Add AI Message
    active_thread["messages"].append({"role": "assistant", "content": ai_response})
    
    # Rerun to update UI
    st.rerun()