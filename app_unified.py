import streamlit as st
import streamlit.components.v1 as components
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
        background-color: #000000 !important;
        border-right: 1px solid #222 !important;
        transition: all 0.3s ease !important;
        position: fixed !important;
        left: 0 !important;
        top: 0 !important;
        height: 100vh !important;
        z-index: 999 !important;
    }
    
    /* Sidebar content */
    section[data-testid="stSidebar"] > div {
        background-color: #000000 !important;
    }
    
    /* Make main content adjust when sidebar is visible */
    section[data-testid="stSidebar"][style*="margin-left: 0px"] ~ div[data-testid="stAppViewContainer"] {
        margin-left: 336px;
        transition: margin-left 0.3s ease;
    }
    
    /* SIDEBAR SEARCH BAR */
    .sidebar-search {
        background-color: #1a1a1a;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 10px;
        color: #fff;
        width: 100%;
    }
    
    /* SIDEBAR SECTION HEADERS */
    .sidebar-section {
        color: #999;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 20px 0 10px 0;
        font-weight: 600;
    }
    
    /* CHAT ITEM STYLING */
    .chat-item {
        background-color: transparent;
        padding: 10px 12px;
        border-radius: 8px;
        margin-bottom: 4px;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .chat-item:hover {
        background-color: #1a1a1a;
    }
    .chat-item.active {
        background-color: #2a2a2a;
        border-left: 3px solid #3b82f6;
    }
    .chat-item-actions {
        display: none;
        gap: 8px;
    }
    .chat-item:hover .chat-item-actions {
        display: flex;
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
    """Auto-generate chat title from the first query"""
    # Remove extra whitespace and limit length
    title = " ".join(text.split())
    # Capitalize first letter
    title = title[0].upper() + title[1:] if title else "New Chat"
    # Limit to 40 characters
    return title[:40] + "..." if len(title) > 40 else title

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

# --- 4. SIDEBAR UI WITH HAMBURGER TOGGLE ---

# Hamburger Toggle Button (Always Visible) - Using components for better control
components.html("""
<!DOCTYPE html>
<html>
<head>
<style>
    body {
        margin: 0;
        padding: 0;
        overflow: hidden;
    }
    .hamburger-btn {
        position: absolute;
        top: 0;
        left: 0;
        background-color: #1a1a1a;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 10px 12px;
        cursor: pointer;
        color: #fff;
        font-size: 1.5rem;
        width: 44px;
        height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    .hamburger-btn:hover {
        background-color: #2a2a2a;
        border-color: #555;
        transform: scale(1.1);
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
</style>
</head>
<body>
<button class="hamburger-btn" onclick="toggleSidebar()">☰</button>
<script>
    // Position the iframe container in parent
    const iframe = window.frameElement;
    if (iframe) {
        iframe.style.position = 'fixed';
        iframe.style.top = '1rem';
        iframe.style.left = '1rem';
        iframe.style.zIndex = '999999';
        iframe.style.width = '60px';
        iframe.style.height = '60px';
        iframe.style.border = 'none';
        iframe.style.pointerEvents = 'auto';
    }
    
    let sidebarCollapsed = false;
    let forcedState = null;
    
    function toggleSidebar() {
        const parent = window.parent.document;
        const sidebar = parent.querySelector('[data-testid="stSidebar"]');
        const mainContent = parent.querySelector('[data-testid="stAppViewContainer"]');
        
        if (!sidebar) {
            console.log('Sidebar not found');
            return;
        }
        
        sidebarCollapsed = !sidebarCollapsed;
        forcedState = sidebarCollapsed;
        
        // Force sidebar to left side and make it visible
        sidebar.style.setProperty('position', 'fixed', 'important');
        sidebar.style.setProperty('left', '0', 'important');
        sidebar.style.setProperty('top', '0', 'important');
        sidebar.style.setProperty('height', '100vh', 'important');
        sidebar.style.setProperty('width', '336px', 'important');
        sidebar.style.setProperty('z-index', '999', 'important');
        sidebar.style.setProperty('background-color', '#000000', 'important');
        sidebar.style.setProperty('border-right', '1px solid #222', 'important');
        sidebar.style.setProperty('overflow-y', 'auto', 'important');
        
        if (sidebarCollapsed) {
            // Collapse sidebar - move it off screen to the left
            sidebar.style.setProperty('transform', 'translateX(-100%)', 'important');
            sidebar.style.setProperty('margin-left', '0px', 'important');
            if (mainContent) {
                mainContent.style.setProperty('margin-left', '0', 'important');
            }
            console.log('Collapsing sidebar');
        } else {
            // Expand sidebar - bring it back
            sidebar.style.setProperty('transform', 'translateX(0)', 'important');
            sidebar.style.setProperty('margin-left', '0px', 'important');
            if (mainContent) {
                mainContent.style.setProperty('margin-left', '336px', 'important');
            }
            console.log('Expanding sidebar');
        }
    }
    
    // Keep the sidebar in the forced state and ensure left positioning
    setInterval(() => {
        const parent = window.parent.document;
        const sidebar = parent.querySelector('[data-testid="stSidebar"]');
        const mainContent = parent.querySelector('[data-testid="stAppViewContainer"]');
        
        if (sidebar) {
            // Always ensure sidebar is on the left
            sidebar.style.setProperty('position', 'fixed', 'important');
            sidebar.style.setProperty('left', '0', 'important');
            sidebar.style.setProperty('right', 'auto', 'important');
            sidebar.style.setProperty('top', '0', 'important');
            sidebar.style.setProperty('height', '100vh', 'important');
            sidebar.style.setProperty('width', '336px', 'important');
            sidebar.style.setProperty('background-color', '#000000', 'important');
            
            if (forcedState !== null) {
                const currentTransform = window.getComputedStyle(sidebar).transform;
                
                if (forcedState) {
                    // Keep collapsed
                    if (!currentTransform.includes('matrix') || !currentTransform.includes('-336')) {
                        sidebar.style.setProperty('transform', 'translateX(-100%)', 'important');
                        if (mainContent) {
                            mainContent.style.setProperty('margin-left', '0', 'important');
                        }
                    }
                } else {
                    // Keep expanded
                    if (currentTransform.includes('-336') || currentTransform.includes('-100')) {
                        sidebar.style.setProperty('transform', 'translateX(0)', 'important');
                        if (mainContent) {
                            mainContent.style.setProperty('margin-left', '336px', 'important');
                        }
                    }
                }
            }
        }
    }, 50);
</script>
</body>
</html>
""", height=60)

with st.sidebar:
    # Header with New Chat and Settings
    col_new, col_set = st.columns([0.85, 0.15])
    with col_new:
        if st.button("✨ New Chat", use_container_width=True, key="new_chat_btn"):
            create_new_chat()
            st.rerun()
    with col_set:
        with st.popover("⚙️", use_container_width=True):
            st.markdown("### ⚙️ Settings")
            model_choice = st.selectbox("Model", ["llama3.2", "mistral", "codellama"], key="model_select")
            temperature = st.slider("Temperature", 0.0, 2.0, 0.7, key="temp_slider")
            st.markdown("---")
            st.caption("Theme: Dark Mode")
            if st.button("Clear All Chats", type="primary", key="clear_all_btn"):
                st.session_state.chat_threads = []
                create_new_chat()
                st.rerun()

    st.markdown("---")
    
    # Search Bar
    search_query = st.text_input("🔍 Search chats...", key="search_input", label_visibility="collapsed", placeholder="Search chats...")
    
    st.markdown('<div class="sidebar-section">Conversations</div>', unsafe_allow_html=True)
    
    # 2. Chat History List with Search Filter
    filtered_threads = [
        t for t in st.session_state.chat_threads 
        if search_query.lower() in t["title"].lower()
    ] if search_query else st.session_state.chat_threads
    
    if not filtered_threads:
        st.caption("No chats found")
    
    for thread in filtered_threads:
        t_id = thread["id"]
        t_title = thread["title"]
        is_active = (t_id == st.session_state.active_thread_id)
        
        # Create a container for each chat item
        col_chat, col_menu = st.columns([0.85, 0.15])
        
        with col_chat:
            if st.button(
                f"{'💬' if is_active else '  '} {t_title[:30]}...",
                key=f"chat_{t_id}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.active_thread_id = t_id
                st.rerun()
        
        with col_menu:
            with st.popover("⋮", use_container_width=True):
                st.caption(f"**{t_title}**")
                st.markdown("---")
                
                # Rename option
                with st.expander("✏️ Rename"):
                    new_name = st.text_input("New name", value=t_title, key=f"ren_{t_id}", label_visibility="collapsed")
                    if st.button("Save", key=f"save_{t_id}", use_container_width=True):
                        rename_thread(t_id, new_name)
                        st.rerun()
                
                # Delete option
                st.markdown("")
                if st.button("🗑️ Delete", key=f"del_{t_id}", use_container_width=True, type="primary"):
                    delete_thread(t_id)
                    st.rerun()
    
    # Footer info
    st.markdown("---")
    st.caption(f"💬 {len(st.session_state.chat_threads)} conversations")

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

    # 3. Get selected model from session state (default to llama3.2)
    selected_model = st.session_state.get("model_select", "llama3.2")
    
    # 4. Call Ollama Backend
    with st.spinner("Thinking..."):
        ai_response = call_ollama_backend(
            prompt=user_input,
            conversation_id=active_thread["id"],
            model=selected_model
        )
    
    # Fallback to mock if backend fails
    if not ai_response:
        ai_response = "Sometimes that's just the way it is. If you ever want to chat or need help with something, feel free to reach out. (Using mock - backend unavailable)"
    
    # 4. Add AI Message
    active_thread["messages"].append({"role": "assistant", "content": ai_response})
    
    # Rerun to update UI
    st.rerun()