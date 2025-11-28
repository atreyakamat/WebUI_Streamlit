"""ChatGPT-inspired conversational UI built with Streamlit.
"""
from __future__ import annotations

import html
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components
from markdown import markdown as md_to_html

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


def init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "ui" not in st.session_state:
        st.session_state.ui = DEFAULT_UI_STATE.copy()
    else:
        for key, value in DEFAULT_UI_STATE.items():
            st.session_state.ui.setdefault(key, value)


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
    st.session_state.messages = []


def clear_messages() -> None:
    st.session_state.messages = []


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
        st.header("Chat Actions")
        st.caption("Manage this conversation from a single place.")
        if st.button("Clear chat", use_container_width=True):
            clear_messages()
            st.rerun()
        if st.button("New chat", use_container_width=True):
            reset_conversation()
            st.rerun()
        st.download_button(
            "Export (JSON)",
            data=json_payload,
            file_name=f"chat-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )
        if st.button("Settings panel", use_container_width=True):
            st.session_state.ui["show_quick_settings"] = not st.session_state.ui.get("show_quick_settings", False)

        st.divider()
        st.subheader("Message Manager")
        st.caption("Create, edit, or delete manual entries.")

        with st.form("add-message-form"):
            role = st.radio(
                "Message role",
                ("user", "assistant"),
                horizontal=True,
                key="add-role",
            )
            add_content = st.text_area(
                "Message content",
                placeholder="Type the text you want to inject...",
                height=120,
                key="add-content",
            )
            if st.form_submit_button("Add message"):
                if add_content.strip():
                    st.session_state.messages.append(create_message(role, add_content))
                    st.success("Message added to the chat feed.")
                    st.rerun()
                else:
                    st.warning("Content cannot be empty.")

        choices = [choice for choice in list_message_choices() if choice["id"]]
        if not choices:
            st.info("No messages are available to edit or delete yet.")
            return

        label_map = {choice["id"]: choice["label"] for choice in choices}

        with st.form("edit-message-form"):
            edit_id = st.selectbox(
                "Select a message to edit",
                options=[choice["id"] for choice in choices],
                format_func=lambda option: label_map.get(option, option),
                key="edit-select",
            )
            target = find_message(edit_id) if edit_id else None
            target_content = target.get("content", "") if target else ""
            new_content = st.text_area(
                "Updated content",
                value=target_content,
                height=150,
                key=f"edit-content-{edit_id or 'none'}",
            )
            if st.form_submit_button("Save changes"):
                if edit_id and update_message_content(edit_id, new_content):
                    st.success("Message updated.")
                    st.rerun()
                else:
                    st.warning("Select a message and provide new content before saving.")

        with st.form("delete-message-form"):
            delete_id = st.selectbox(
                "Select a message to delete",
                options=[choice["id"] for choice in choices],
                format_func=lambda option: label_map.get(option, option),
                key="delete-select",
            )
            confirm = st.checkbox("Yes, remove this message", key="delete-confirm")
            if st.form_submit_button("Delete message"):
                if confirm and delete_id and delete_message(delete_id):
                    st.success("Message removed from the chat feed.")
                    st.rerun()
                elif not confirm:
                    st.warning("Confirm the deletion before proceeding.")
                else:
                    st.warning("Unable to delete the selected message.")
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
    user_prompt = st.chat_input("Message ChatGPT", key="chat-input")

    if user_prompt:
        user_message = create_message("user", user_prompt)
        st.session_state.messages.append(user_message)
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

    st.caption("Need ideas? Try asking for UX critiques, summaries, or code reviews.")


if __name__ == "__main__":
    main()
