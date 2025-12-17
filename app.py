"""ChatGPT-inspired conversational UI built with Streamlit.
"""
from __future__ import annotations

import html
import json
import time
import uuid
import io
from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components
from markdown import markdown as md_to_html
import os
import sys

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

st.set_page_config(
    page_title="ChatGPT Replica",
    page_icon=":speech_balloon:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SYSTEM_PROMPT = (
    "You are a thoughtful, concise, and detail-oriented AI assistant named ChatGPT. "
    "Provide well-structured answers, use markdown when it adds clarity, and be warm and approachable."
)

THEMES: Dict[str, Dict[str, str]] = {
    "dark": {
        "background": "#0f1116",
        "surface": "rgba(25, 27, 32, 0.8)",
        "surface_alt": "rgba(32, 35, 42, 0.85)",
        "border": "rgba(255, 255, 255, 0.08)",
        "user_bubble": "linear-gradient(135deg, #2c7be5, #6c5ce7)",
        "ai_bubble": "rgba(255, 255, 255, 0.07)",
        "label": "#f5f7ff",
        "input_bg": "rgba(22, 24, 30, 0.6)",
    },
    "light": {
        "background": "#f6f7fb",
        "surface": "rgba(255, 255, 255, 0.9)",
        "surface_alt": "rgba(255, 255, 255, 0.85)",
        "border": "rgba(15, 17, 26, 0.08)",
        "user_bubble": "linear-gradient(135deg, #2c7be5, #20c997)",
        "ai_bubble": "rgba(15, 17, 26, 0.05)",
        "label": "#111320",
        "input_bg": "rgba(255, 255, 255, 0.8)",
    },
}

DEFAULT_UI_STATE: Dict[str, object] = {
    "dark_mode": True,
    "font_scale": 1.0,
    "show_particles": True,
    "enable_animations": True,
    "user_avatar": "ME",
    "assistant_avatar": "AI",
    "system_prompt": SYSTEM_PROMPT,
    "show_quick_settings": False,
}


def create_thread(title: str = "New chat") -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "created": datetime.utcnow().isoformat(),
        "messages": [],
    }


def get_active_thread() -> Optional[Dict[str, Any]]:
    active_id = st.session_state.get("active_thread_id")
    for thread in st.session_state.get("chat_threads", []):
        if thread.get("id") == active_id:
            return thread
    return None


def sync_active_messages() -> None:
    active = get_active_thread()
    if not active:
        return
    if st.session_state.get("messages") is not active.get("messages"):
        st.session_state.messages = active.get("messages", [])


def ensure_chat_threads() -> None:
    threads: List[Dict[str, Any]] = st.session_state.setdefault("chat_threads", [])
    if not threads:
        initial_thread = create_thread()
        initial_thread["messages"] = st.session_state.get("messages", [])
        threads.append(initial_thread)
    st.session_state.setdefault("active_thread_id", threads[0]["id"])
    sync_active_messages()


def start_new_thread() -> None:
    thread = create_thread()
    st.session_state.chat_threads.insert(0, thread)
    st.session_state.active_thread_id = thread["id"]
    st.session_state.messages = thread["messages"]


def switch_thread(thread_id: str) -> None:
    if thread_id == st.session_state.get("active_thread_id"):
        return
    current = get_active_thread()
    if current is not None:
        current["messages"] = st.session_state.get("messages", [])
    st.session_state.active_thread_id = thread_id
    target = get_active_thread()
    if not target:
        target = create_thread()
        st.session_state.chat_threads.append(target)
        st.session_state.active_thread_id = target["id"]
    st.session_state.messages = target.get("messages", [])


def delete_thread(thread_id: str) -> None:
    threads = st.session_state.get("chat_threads", [])
    if not threads:
        return
    remaining = [thread for thread in threads if thread.get("id") != thread_id]
    if len(remaining) == len(threads):
        return
    if not remaining:
        fresh = create_thread()
        st.session_state.chat_threads = [fresh]
        st.session_state.active_thread_id = fresh["id"]
        st.session_state.messages = fresh["messages"]
        return
    st.session_state.chat_threads = remaining
    active_id = st.session_state.get("active_thread_id")
    if active_id == thread_id or active_id not in {thread.get("id") for thread in remaining}:
        st.session_state.active_thread_id = remaining[0]["id"]
        st.session_state.messages = remaining[0].get("messages", [])
    else:
        sync_active_messages()


def derive_thread_title(thread: Dict[str, Any]) -> str:
    existing = thread.get("title") or "New chat"
    messages: List[Dict[str, str]] = thread.get("messages", [])
    for message in reversed(messages):
        if message.get("role") == "user" and message.get("content"):
            snippet = message["content"].splitlines()[0]
            if len(snippet) > 36:
                snippet = snippet[:33] + "..."
            thread["title"] = snippet or existing
            return thread["title"]
    return existing


def refresh_active_thread_title() -> None:
    thread = get_active_thread()
    if not thread:
        return
    if thread.get("messages"):
        derive_thread_title(thread)
    else:
        thread["title"] = "New chat"


def init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "ui" not in st.session_state:
        st.session_state.ui = DEFAULT_UI_STATE.copy()
    else:
        for key, value in DEFAULT_UI_STATE.items():
            st.session_state.ui.setdefault(key, value)
    ensure_chat_threads()


def create_message(role: str, content: str) -> Dict[str, str]:
    return {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content.strip(),
        "timestamp": datetime.utcnow().isoformat(),
    }


def readable_timestamp(raw: str) -> str:
    try:
        ts = datetime.fromisoformat(raw)
    except ValueError:
        ts = datetime.utcnow()
    return ts.strftime("%b %d | %I:%M %p")


def current_theme() -> Dict[str, str]:
    mode = "dark" if st.session_state.ui.get("dark_mode", True) else "light"
    return THEMES[mode]


def inject_global_styles(theme: Dict[str, str]) -> None:
    css = f"""
    <style>
    :root {{
        --surface: {theme['surface']};
        --surface-alt: {theme['surface_alt']};
        --border-color: {theme['border']};
        --user-bubble: {theme['user_bubble']};
        --ai-bubble: {theme['ai_bubble']};
        --label-color: {theme['label']};
        --input-bg: {theme['input_bg']};
        --font-scale: {st.session_state.ui.get('font_scale', 1.0)};
    }}
    .message-row.system {{
        justify-content: center;
        padding: 0.5rem 0;
        opacity: 0.7;
        animation: floatIn 0.4s ease;
    }}
    .message-content.system-msg {{
        font-size: 0.8rem;
        background: rgba(255, 255, 255, 0.05);
        padding: 0.4rem 1rem;
        border-radius: 1rem;
        font-style: italic;
        text-align: center;
        border: 1px dashed var(--border-color);
    }}
    body {{
        font-family: "Space Grotesk", "Segoe UI", sans-serif;
        background: {theme['background']};
        color: var(--label-color);
        transition: background 0.8s ease, color 0.4s ease;
    }}
    #root .block-container {{
        padding-top: 3vh;
        padding-bottom: 4vh;
        max-width: min(860px, 92vw);
        margin: 0 auto;
    }}
    .welcome-wrap {{
        width: 100%;
        min-height: 28vh;
        padding: 1rem 0;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .welcome-heading {{
        text-align: center;
        font-size: 2rem;
        margin: 0;
        letter-spacing: -0.01em;
    }}
    .history-label {{
        margin: 1rem 0 0.3rem;
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        opacity: 0.75;
    }}
    .history-button-group {{
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
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
        width: 100%;
    }}
    .history-entry [data-testid="column"]:last-child {{
        flex: 0 0 auto;
    }}
    .history-entry .delete-button {{
        display: flex;
        justify-content: flex-end;
    }}
    .history-entry .delete-button button {{
        width: 40px;
        height: 40px;
        border-radius: 0.8rem;
        border: 1px solid var(--border-color);
        background: rgba(255, 255, 255, 0.04);
        color: inherit;
        opacity: 0;
        transition: opacity 0.2s ease;
    }}
    .history-entry:hover .delete-button button {{
        opacity: 1;
    }}
    .history-button-group button {{
        justify-content: flex-start;
        border-radius: 0.9rem;
        border: 1px solid var(--border-color);
        background: rgba(255, 255, 255, 0.02);
        color: inherit;
        font-weight: 500;
        transition: border 0.2s ease, background 0.2s ease;
        padding: 0.35rem 0.9rem;
    }}
    .history-button-group button:hover {{
        border-color: rgba(32, 201, 151, 0.7);
        background: rgba(32, 201, 151, 0.08);
    }}
    .history-button-group button:disabled {{
        border-color: #20c997;
        color: #20c997;
        background: rgba(32, 201, 151, 0.12);
    }}
    .chat-feed {{
        width: 100%;
        max-width: min(820px, 92vw);
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        padding: 0.4rem 0 0;
    }}
    .message-row {{
        display: flex;
        width: 100%;
        align-items: flex-start;
        gap: 0.8rem;
        animation: floatIn 0.4s ease;
    }}
    .message-row.user {{
        flex-direction: row-reverse;
        justify-content: flex-end;
    }}
    .message-row.user .message-card {{
        margin-left: auto;
    }}
    .message-row.assistant {{
        justify-content: flex-start;
    }}
    .message-row.assistant .message-card {{
        margin-right: auto;
    }}
    .avatar-circle {{
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: var(--surface-alt);
        border: 1px solid var(--border-color);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 0.9rem;
    }}
    .message-card {{
        flex: 0 1 auto;
        max-width: min(620px, 90vw);
        width: fit-content;
        padding: 0.6rem 1rem;
        border-radius: 1rem;
        backdrop-filter: blur(16px);
        border: 1px solid var(--border-color);
        box-shadow: 0 18px 40px -24px rgba(0, 0, 0, 0.6);
        display: inline-flex;
        flex-direction: column;
    }}
    .message-card.user-bubble {{
        background: var(--user-bubble);
        color: #fff;
    }}
    .message-card.ai-bubble {{
        background: var(--ai-bubble);
    }}
    .message-meta {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        opacity: 0.8;
        margin-bottom: 0.4rem;
        gap: 0.6rem;
    }}
    .message-content {{
        font-size: calc(1rem * var(--font-scale));
        line-height: 1.45;
    }}
    .message-content pre {{
        background: rgba(0, 0, 0, 0.3);
        padding: 0.8rem;
        border-radius: 0.8rem;
        border: 1px solid var(--border-color);
        overflow-x: auto;
    }}
    .message-content code {{
        font-family: "JetBrains Mono", "SFMono-Regular", monospace;
        font-size: 0.85rem;
    }}
    .copy-btn {{
        background: transparent;
        color: inherit;
        border: none;
        cursor: pointer;
        padding: 0;
        font-size: 0.75rem;
        opacity: 0.7;
        transition: opacity 0.2s ease;
    }}
    .copy-btn:hover {{
        opacity: 1;
    }}
    .copy-btn.copied {{
        color: #20c997;
        opacity: 1;
    }}
    [data-testid="stChatInput"] {{
        background: transparent;
        max-width: min(820px, 92vw);
        margin: 0 auto;
        display: flex;
        justify-content: flex-end;
    }}
    [data-testid="stChatInput"] > div {{
        background: var(--surface);
        border: 1px solid var(--border-color);
        border-radius: 1.5rem;
        padding: 0.6rem 1rem;
        box-shadow: 0 18px 40px -28px rgba(0, 0, 0, 0.8);
        backdrop-filter: blur(18px);
        width: min(620px, 100%);
    }}
    [data-testid="stSidebar"] {{
        position: relative;
    }}
    .sidebar-gear-space {{
        height: 2rem;
    }}
    .sidebar-gear {{
        position: fixed;
        left: 1rem;
        top: 8rem;
        z-index: 200;
    }}
    .sidebar-gear button {{
        width: 46px;
        height: 46px;
        border-radius: 999px;
        border: 1px solid var(--border-color);
        background: var(--surface);
        font-size: 1.2rem;
        box-shadow: 0 8px 24px -12px rgba(0, 0, 0, 0.6);
    }}
    @keyframes floatIn {{
        from {{
            transform: translateY(14px);
            opacity: 0;
        }}
        to {{
            transform: translateY(0);
            opacity: 1;
        }}
    }}
    @media (max-width: 768px) {{
        #root .block-container {{
            padding-top: 1.4rem;
            padding-bottom: 3rem;
            max-width: 100%;
            padding-left: 1rem;
            padding-right: 1rem;
        }}
        .welcome-wrap {{
            min-height: 20vh;
        }}
        .chat-feed {{
            max-width: 100%;
        }}
        [data-testid="stChatInput"] {{
            max-width: 100%;
        }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def inject_particle_layer(enabled: bool) -> None:
    if not enabled:
        return
    components.html(
        """
        <div id="sparkle-layer"></div>
        <style>
        #sparkle-layer {{
            position: fixed;
            inset: 0;
            background: transparent;
            pointer-events: none;
            z-index: -1;
        }}
        .sparkle {{
            position: absolute;
            width: 4px;
            height: 4px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.25);
            animation: shimmer 6s linear infinite;
        }}
        @keyframes shimmer {{
            0% {{ opacity: 0; transform: scale(0.6); }}
            20% {{ opacity: 1; }}
            100% {{ opacity: 0; transform: translateY(-40px) scale(1.4); }}
        }}
        </style>
        <script>
        const doc = window.parent.document;
        const layerId = 'sparkle-overlay';
        if (!doc.getElementById(layerId)) {{
            const layer = doc.createElement('div');
            layer.id = layerId;
            layer.style.position = 'fixed';
            layer.style.inset = '0';
            layer.style.pointerEvents = 'none';
            layer.style.zIndex = '-1';
            doc.body.appendChild(layer);
            for (let i = 0; i < 30; i += 1) {{
                const dot = doc.createElement('div');
                dot.className = 'sparkle';
                dot.style.left = `${Math.random() * 100}%`;
                dot.style.top = `${Math.random() * 100}%`;
                dot.style.animationDelay = `${Math.random() * 4}s`;
                layer.appendChild(dot);
            }}
        }}
        </script>
        """,
        height=0,
        width=0,
    )


def inject_client_scripts() -> None:
    components.html(
        """
        <script>
        const doc = window.parent.document;
        function wireCopyButtons() {{
            const buttons = doc.querySelectorAll('button[data-copy]');
            buttons.forEach((btn) => {{
                if (btn.dataset.bound === 'true') {{
                    return;
                }}
                btn.dataset.bound = 'true';
                btn.addEventListener('click', async (event) => {{
                    event.stopPropagation();
                    try {{
                        await navigator.clipboard.writeText(btn.dataset.copy || '');
                        btn.classList.add('copied');
                        setTimeout(() => btn.classList.remove('copied'), 1200);
                    }} catch (err) {{
                        console.warn('Clipboard unavailable', err);
                    }}
                }});
            }});
        }}
        function scrollToLatest() {{
            const feed = doc.querySelector('#chat-feed');
            if (feed) {{
                feed.scrollTo({{ top: feed.scrollHeight, behavior: 'smooth' }});
            }}
        }}
        setTimeout(() => {{
            wireCopyButtons();
            scrollToLatest();
        }}, 100);
        </script>
        """,
        height=0,
        width=0,
    )


def run_ocr_pipeline(uploaded_file) -> Optional[str]:
    """Extract text from an uploaded image or PDF using OCR."""
    if not OCR_AVAILABLE:
        st.error("OCR libraries not found. Please install `pytesseract` and `pdf2image`.")
        return None

    try:
        text = ""
        uploaded_file.seek(0)
        
        if uploaded_file.type == "application/pdf":
            # Convert PDF to images (requires poppler installed)
            images = convert_from_bytes(uploaded_file.read())
            for img in images:
                text += pytesseract.image_to_string(img) + "\n"
        else:
            # Handle images
            image = Image.open(uploaded_file)
            text = pytesseract.image_to_string(image)
        
        # Cleanup: Normalize whitespace
        cleaned_text = " ".join(text.split())
        return cleaned_text
    except pytesseract.TesseractNotFoundError:
        st.error("Tesseract is not installed or not in PATH. Please install Tesseract-OCR.")
        return None
    except Exception as e:
        st.error(f"OCR Error: {e}")
        if "poppler" in str(e).lower():
             st.info("For PDFs, `poppler` must be installed and in your PATH.")
        return None


def call_custom_llm(prompt_text: str) -> Optional[str]:
    """Hook for integrating a bespoke LLM or API later on."""

    _ = prompt_text  # placeholder until wired up
    return None


def generate_ai_reply(prompt_text: str) -> str:
    """Return the assistant response, falling back to a mock typing effect."""

    custom_reply = call_custom_llm(prompt_text)
    if custom_reply:
        return custom_reply.strip()
    return mock_ai_response(prompt_text)


def mock_ai_response(prompt_text: str) -> str:
    snippet = prompt_text[:160].strip() or "your prompt"
    return (
        f"Summary: I captured the essence of '{snippet}'.\n"
        "Suggestion: Consider breaking it into smaller deliverables.\n"
        "Next step: Let me know if you want code, visuals, or bullet notes."
    )


def find_message(message_id: str) -> Optional[Dict[str, str]]:
    for message in st.session_state.messages:
        if message.get("id") == message_id:
            return message
    return None


def format_message_label(message: Dict[str, str]) -> str:
    role = message.get("role", "assistant").title()
    content = message.get("content", "").replace("\n", " ")
    snippet = (content[:42] + "...") if len(content) > 45 else content
    return f"{role} | {snippet or 'Empty message'}"


def list_message_choices() -> List[Dict[str, str]]:
    return [
        {"id": message.get("id", ""), "label": format_message_label(message)}
        for message in st.session_state.messages
    ]


def update_message_content(message_id: str, new_content: str) -> bool:
    target = find_message(message_id)
    if not target or not new_content.strip():
        return False
    target["content"] = new_content.strip()
    target["timestamp"] = datetime.utcnow().isoformat()
    return True


def delete_message(message_id: str) -> bool:
    before = len(st.session_state.messages)
    st.session_state.messages = [
        message for message in st.session_state.messages if message.get("id") != message_id
    ]
    return len(st.session_state.messages) < before


def render_message_html(message: Dict[str, str]) -> str:
    role = message.get("role", "assistant")
    
    # Handle system messages distinctively
    if role == "system":
        content = html.escape(message.get("content", ""))
        return (
            f"<div class=\"message-row system\">"
            f"<div class=\"message-content system-msg\">{content}</div>"
            "</div>"
        )

    avatar = (
        st.session_state.ui.get("assistant_avatar", "AI")
        if role == "assistant"
        else st.session_state.ui.get("user_avatar", "ME")
    )
    avatar = html.escape(avatar or ("AI" if role == "assistant" else "ME"))
    label = "Assistant" if role == "assistant" else "You"
    copy_payload = html.escape(message.get("content", ""))
    body_html = md_to_html(
        message.get("content", ""),
        extensions=["fenced_code", "tables"],
    )
    bubble_class = "ai-bubble" if role == "assistant" else "user-bubble"
    copy_button = (
        f"<button class=\"copy-btn\" data-copy=\"{copy_payload}\">Copy</button>"
        if role == "assistant"
        else ""
    )
    return (
        "<div class=\"message-row {role}\">"
        f"<div class=\"avatar-circle\">{avatar}</div>"
        f"<div class=\"message-card {bubble_class}\">"
        f"<div class=\"message-meta\"><span>{label}</span>{copy_button}</div>"
        f"<div class=\"message-content\">{body_html}</div>"
        "</div></div>"
    ).format(role=role)


def render_chat_feed(container, include_placeholder: bool = False):
    container.markdown('<div id="chat-feed" class="chat-feed">', unsafe_allow_html=True)
    for message in st.session_state.messages:
        container.markdown(render_message_html(message), unsafe_allow_html=True)
    placeholder = container.empty() if include_placeholder else None
    container.markdown('</div>', unsafe_allow_html=True)
    return placeholder


def stream_ai_response(placeholder, message: Dict[str, str], animate: bool = True) -> None:
    text = message["content"]
    if not animate:
        placeholder.markdown(render_message_html(message), unsafe_allow_html=True)
        return
    buffer = []
    tokens = text.split()
    for token in tokens:
        buffer.append(token)
        partial = " ".join(buffer)
        temp_message = {**message, "content": partial + " _"}
        placeholder.markdown(render_message_html(temp_message), unsafe_allow_html=True)
        time.sleep(0.04)
    placeholder.markdown(render_message_html(message), unsafe_allow_html=True)


def build_plaintext_transcript(messages: List[Dict[str, str]]) -> str:
    lines: List[str] = []
    for message in messages:
        ts = readable_timestamp(message.get("timestamp", datetime.utcnow().isoformat()))
        role = message.get("role", "assistant").title()
        lines.append(f"[{ts}] {role}:\n{message.get('content', '')}")
    return "\n\n".join(lines)


def export_payloads() -> Dict[str, str]:
    json_payload = json.dumps(st.session_state.messages, indent=2)
    text_payload = build_plaintext_transcript(st.session_state.messages)
    return {"json": json_payload, "text": text_payload}


def reset_conversation() -> None:
    start_new_thread()


def clear_messages() -> None:
    fresh: List[Dict[str, str]] = []
    st.session_state.messages = fresh
    thread = get_active_thread()
    if thread:
        thread["messages"] = fresh
        thread["title"] = "New chat"


def quick_settings_panel() -> None:
    if not st.session_state.ui.get("show_quick_settings"):
        return
    with st.expander("Quick Settings", expanded=True):
        ui = st.session_state.ui
        font_scale = st.slider(
            "Font scale (quick)",
            0.85,
            1.3,
            value=float(ui.get("font_scale", 1.0)),
            step=0.05,
            key="quick-font",
        )
        ui["font_scale"] = font_scale
        animations = st.checkbox(
            "Enable animations",
            value=bool(ui.get("enable_animations", True)),
            key="quick-anim",
        )
        ui["enable_animations"] = animations
        particles = st.checkbox(
            "Sparkle background",
            value=bool(ui.get("show_particles", True)),
            key="quick-particles",
        )
        ui["show_particles"] = particles


def sidebar_actions(json_payload: str) -> None:
    with st.sidebar:
        with st.container():
            st.markdown('<div class="sidebar-gear">', unsafe_allow_html=True)
            if st.button("⚙️", key="gear-settings-btn"):
                st.session_state.ui["show_quick_settings"] = not st.session_state.ui.get("show_quick_settings", False)
            st.markdown('</div>', unsafe_allow_html=True)
            
        st.subheader("Conversations")
        if st.button("➕ New chat", use_container_width=True, key="new-chat-btn"):
            reset_conversation()
            st.rerun()
        if st.button("🧹 Clear chat", use_container_width=True, key="clear-chat-btn"):
            clear_messages()
            st.rerun()

        # Search bar for conversations
        search_query = st.text_input(
            "Search conversations...", 
            placeholder="Search by message content or title",
            key="chat-search",
            label_visibility="collapsed"
        )

        thread_ids = [thread["id"] for thread in st.session_state.chat_threads]
        current_id = st.session_state.get("active_thread_id", thread_ids[0] if thread_ids else None)
        thread_labels = {thread["id"]: derive_thread_title(thread) or "New chat" for thread in st.session_state.chat_threads}
        
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
        
        st.markdown('<p class="history-label">Chats</p>', unsafe_allow_html=True)
        st.markdown('<div class="history-button-group">', unsafe_allow_html=True)

        if not filtered_threads and search_query.strip():
            st.markdown('<p style="opacity: 0.6; font-size: 0.85rem; padding: 0.5rem;">No conversations found</p>', unsafe_allow_html=True)

        for thread in filtered_threads:
            thread_id = thread["id"]
            label = thread_labels.get(thread_id, "New chat")
            disabled = thread_id == current_id
            entry = st.container()
            entry.markdown('<div class="history-entry">', unsafe_allow_html=True)
            select_col, delete_col = entry.columns([1, 0.12], gap="small")
            with select_col:
                if st.button(
                    label,
                    use_container_width=True,
                    key=f"thread-btn-{thread_id}",
                    disabled=disabled,
                    help="Current conversation" if disabled else None,
                ) and not disabled:
                    switch_thread(thread_id)
                    st.rerun()
            with delete_col:
                st.markdown('<div class="delete-button">', unsafe_allow_html=True)
                if st.button(
                    "🗑",
                    key=f"delete-thread-{thread_id}",
                    help="Delete chat",
                ):
                    delete_thread(thread_id)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            entry.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
def render_header() -> None:
    st.markdown(
        '<div class="welcome-wrap"><h1 class="welcome-heading">Welcome</h1></div>',
        unsafe_allow_html=True,
    )


def main() -> None:
    init_session_state()
    render_header()
    theme = current_theme()
    inject_global_styles(theme)
    inject_particle_layer(bool(st.session_state.ui.get("show_particles", True)))
    inject_client_scripts()

    chat_feed = st.container()
    
    # OCR Upload Area (Main Column)
    if OCR_AVAILABLE:
        with st.expander("📎 Attach Image/PDF for OCR", expanded=False):
            uploaded_file = st.file_uploader(
                "Upload an image or scanned PDF",
                type=["png", "jpg", "jpeg", "pdf"],
                accept_multiple_files=False,
                key="ocr_uploader_main"
            )
            
            if uploaded_file and st.button("Extract & Ask", key="ocr_trigger_main"):
                with st.spinner("Scanning document..."):
                    extracted_text = run_ocr_pipeline(uploaded_file)
                    
                    if extracted_text:
                        # 1. Inject system notice
                        st.session_state.messages.append(create_message(
                            "system", 
                            f"System: OCR extracted text from {uploaded_file.name}"
                        ))
                        
                        # 2. Inject the content as user prompt
                        ocr_prompt = (
                            "The following text was extracted using OCR from a user-uploaded document.\n"
                            "The text may contain formatting or recognition errors.\n\n"
                            f"Extracted Content:\n\"\"\"\n{extracted_text}\n\"\"\"\n"
                        )
                        st.session_state.messages.append(create_message("user", ocr_prompt))
                        
                        # 3. Generate AI Reply
                        with st.spinner("Analyzing extracted text..."):
                            ai_text = generate_ai_reply(ocr_prompt)
                        
                        st.session_state.messages.append(create_message("assistant", ai_text))
                        st.rerun()

    user_prompt = st.chat_input("Message ChatGPT", key="chat-input")

    if user_prompt:
        user_message = create_message("user", user_prompt)
        st.session_state.messages.append(user_message)
        refresh_active_thread_title()
        placeholder = render_chat_feed(chat_feed, include_placeholder=True)
        with st.spinner("Thinking through the best reply..."):
            ai_text = generate_ai_reply(user_prompt)
        ai_message = create_message("assistant", ai_text)
        stream_ai_response(
            placeholder,
            ai_message,
            animate=bool(st.session_state.ui.get("enable_animations", True)),
        )
        st.session_state.messages.append(ai_message)
        st.session_state.ui["last_response"] = ai_text
        st.rerun()
    else:
        render_chat_feed(chat_feed)

    payloads = export_payloads()
    sidebar_actions(payloads["json"])
    quick_settings_panel()


if __name__ == "__main__":
    main()
