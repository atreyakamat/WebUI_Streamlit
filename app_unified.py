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
    
    /* SIDEBAR STYLING - Enhanced Modern Design */
    section[data-testid="stSidebar"] {
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
    }
    
    /* Sidebar content wrapper */
    section[data-testid="stSidebar"] > div {
        background: transparent !important;
        padding-top: 2rem !important;
    }
    
    /* Sidebar scrollbar styling */
    section[data-testid="stSidebar"] ::-webkit-scrollbar {
        width: 8px;
    }
    
    section[data-testid="stSidebar"] ::-webkit-scrollbar-track {
        background: #0a0a0a;
    }
    
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
        background: #333;
        border-radius: 4px;
    }
    
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover {
        background: #444;
    }
    
    /* Sidebar buttons styling */
    section[data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, #1a1a1a 0%, #0f0f0f 100%) !important;
        color: #fff !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
        padding: 0.6rem 1rem !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%) !important;
        border-color: #444 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
    }
    
    /* Primary button (active/new chat) */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%) !important;
        border-color: #1e40af !important;
        box-shadow: 0 2px 12px rgba(37, 99, 235, 0.3) !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e3a8a 100%) !important;
        box-shadow: 0 4px 16px rgba(37, 99, 235, 0.5) !important;
    }
    
    /* Sidebar text input */
    section[data-testid="stSidebar"] .stTextInput > div > div > input {
        background-color: #1a1a1a !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
        color: #fff !important;
        padding: 0.6rem 1rem !important;
    }
    
    section[data-testid="stSidebar"] .stTextInput > div > div > input:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2) !important;
    }
    
    /* Sidebar popover */
    section[data-testid="stSidebar"] [data-testid="stPopover"] {
        background: transparent !important;
    }
    
    section[data-testid="stSidebar"] [data-testid="stPopover"] > button {
        background: #1a1a1a !important;
        border: 1px solid #333 !important;
        color: #999 !important;
        padding: 0.4rem 0.6rem !important;
        border-radius: 6px !important;
    }
    
    section[data-testid="stSidebar"] [data-testid="stPopover"] > button:hover {
        background: #2a2a2a !important;
        color: #fff !important;
        border-color: #444 !important;
    }
    
    /* History button group styling */
    .history-button-group {
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
        margin-top: 0.5rem;
    }
    
    .history-entry {
        position: relative;
        display: flex;
        width: 100%;
        gap: 0.4rem;
        align-items: stretch;
    }
    
    .history-entry [data-testid="column"] {
        padding: 0 !important;
        display: flex;
        align-items: stretch;
    }
    
    .history-entry [data-testid="column"]:first-child {
        flex: 1 1 auto;
    }
    
    .history-entry [data-testid="column"]:first-child button {
        width: 100% !important;
    }
    
    .history-entry [data-testid="column"]:last-child {
        flex: 0 0 auto;
    }
    
    .history-entry .delete-button {
        display: flex;
        justify-content: flex-end;
    }
    
    .history-entry .delete-button button {
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
    }
    
    .history-entry:hover .delete-button button {
        background: rgba(255, 50, 50, 0.2) !important;
        border-color: #ff6b6b !important;
    }
    
    .history-entry .delete-button button:hover {
        background: rgba(255, 50, 50, 0.3) !important;
        transform: scale(1.05) !important;
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
                <span style='font-size: 2rem;'>🦙</span>
                <span>Ollama Chat</span>
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