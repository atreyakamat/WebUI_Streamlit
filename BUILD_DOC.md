# WebUI_Streamlit — Build & Implementation Notes

This document describes how the Streamlit Chat-UI replica was built, key design and implementation decisions, development notes, and hardships encountered. It also contains instructions to convert this Markdown into a PDF on Windows (PowerShell).

---

## Project Overview

- Repository: `WebUI_Streamlit`
- Main file: `app.py`
- Purpose: Frontend-only Streamlit application that mimics ChatGPT-style UI, supports multiple conversation threads, per-thread message storage (in-memory via `st.session_state`), a sidebar with chat history and quick actions, and UX niceties (animations, copy buttons, search, hover-delete, fixed gear for settings).

Key features implemented:
- Chat feed with user/assistant bubbles and simple mock AI replies.
- Thread management: create, switch, and delete conversations (threads) kept in `st.session_state.chat_threads`.
- Automatic chat title derivation: each thread title is derived from the most recent user prompt.
- Sidebar search: text input that filters conversations by title or message content.
- Hover-delete: per-thread delete button that appears when hovering the conversation row.
- Fixed gear button: settings toggle placed in the sidebar and kept fixed (doesn't move on scroll).
- Custom CSS + client-side JS injected using `st.markdown(..., unsafe_allow_html=True)` and `components.html(...)`.

---

## Files and Structure

- `app.py` — single-file Streamlit app. Contains all logic and styling.
  - Top-level constants: `SYSTEM_PROMPT`, `THEMES`, `DEFAULT_UI_STATE`.
  - Session state initialisation: `init_session_state()`.
  - Thread helpers: `create_thread`, `start_new_thread`, `switch_thread`, `delete_thread`, `derive_thread_title`, `refresh_active_thread_title`.
  - Message helpers: `create_message`, `find_message`, `update_message_content`, `delete_message`, `build_plaintext_transcript`.
  - UI rendering: `inject_global_styles`, `inject_particle_layer`, `inject_client_scripts`, `render_chat_feed`, `render_message_html`, `sidebar_actions`, `quick_settings_panel`, `render_header`, `main`.

No server-side LLM integration is present; there is a `call_custom_llm` hook and a `mock_ai_response` fallback.

---

## How It Was Built (Step-by-step)

1. Initialize Streamlit page config:
   - `st.set_page_config(... layout='wide', initial_sidebar_state='collapsed')` for a ChatGPT-like layout.

2. Session-state-first architecture:
   - All conversation and UI state is stored in `st.session_state` so the Streamlit rerun model can keep everything consistent.
   - A list of threads is stored as `st.session_state.chat_threads` where each thread is a dict `{id, title, created, messages}`.

3. Chat thread lifecycle:
   - `create_thread()` creates a thread object with a GUID and empty messages list.
   - `start_new_thread()` inserts a new thread at the front and selects it.
   - `switch_thread(thread_id)` persists the current thread's messages and switches to the target.
   - `delete_thread(thread_id)` removes the selected thread and reassigns active thread safely.

4. Deriving chat titles:
   - `derive_thread_title(thread)` now walks the thread messages in reverse (most recent first) to find the latest user message, and uses its first line (truncated) as the chat title. This makes the chat name reflect the most recent user prompt automatically.

5. UI & styling:
   - `inject_global_styles(theme)` injects CSS with careful escaping of braces so Streamlit's f-string and `unsafe_allow_html` behavior are respected.
   - Chat bubbles, avatars, and meta are styled to match modern translucent surfaces and to be responsive.
   - The gear button was placed using `position: fixed` so it stays at a fixed location in the sidebar.

6. Sidebar history and controls:
   - Built as a vertical list of interactive entries.
   - Added a small search box (text input) that filters threads by title or message content.
   - Each conversation row is a flex block with two columns: a wide button for selecting the thread, and a narrow column containing the delete button. The delete button is only visible (opacity changes) when hovering the chat row.

7. Client-side enhancements:
   - Small JS injected via `components.html(...)` to wire copy-to-clipboard buttons, and to scroll the feed to the latest message.
   - Optional particle background layer added by `inject_particle_layer` (toggleable via quick settings).

8. Behavior on user prompt:
   - When a user submits text via `st.chat_input`, the app creates a user message, appends it to the active thread, renders a placeholder, produces a mock AI response, streams the assistant message (simulated typing), then updates session state and reruns.

---

## Development Notes & Implementation Details

- CSS formatting and Streamlit:
  - Because the CSS is embedded in a Python f-string, every `{` and `}` used by CSS must be escaped properly in the Python literal (double braces `{{`, `}}`) to avoid format interpolation. This trick was repeatedly needed when editing `inject_global_styles`.

- Streamlit column behavior in the sidebar:
  - Streamlit automatically wraps columns in generated HTML containers with test IDs. To ensure the hover effect and inline layout for delete buttons, CSS targets the column containers and forces padding to `0` and explicit flex sizing.

- Copy buttons:
  - The assistant messages contain a small `Copy` button that uses the Navigator clipboard API wired via client-side JS. The JS attaches event listeners to buttons with `data-copy` and visually toggles a `.copied` class.

- Mock LLM:
  - `call_custom_llm` is a placeholder hook to integrate an external model later. Currently, `mock_ai_response` provides a deterministic, human-readable fallback.

---

## Hardships & How We Solved Them

1. CSS interpolation problems inside Python f-strings
   - Symptom: Format errors or broken CSS when embedding braces.
   - Fix: Use double braces `{{` and `}}` where CSS requires braces inside the f-string. Careful editing and testing were required.

2. Positioning the gear button reliably in the Streamlit sidebar
   - Symptom: `position: absolute` placed it relative to the nearest positioned ancestor; it moved when scrolling or when the sidebar layout changed.
   - Fix: Use `position: fixed` and place the gear in a container at the top of the sidebar. This keeps it visually fixed relative to the browser viewport.

3. Hover-only delete button alignment
   - Symptom: Streamlit's generated markup for columns made it hard to align the delete button inline at the right edge and to reveal it only on hover.
   - Fix: Wrap each conversation entry in a `.history-entry` container, use two columns with flex sizing (`flex: 1 1 auto` for the main button and `flex: 0 0 auto` for the delete column), and reveal the delete button by toggling its opacity on `.history-entry:hover` via CSS.

4. Keeping session state consistent when switching and deleting threads
   - Symptom: Deleted threads could leave `active_thread_id` referencing a missing thread, or messages could get out of sync between the UI and thread objects.
   - Fix: The `delete_thread` helper ensures that we reassign `active_thread_id` and `st.session_state.messages` to a valid thread; when none remain, we create a fresh thread.

5. Streamlit `unsafe_allow_html` limitations and DOM access
   - Symptom: Relying on direct DOM manipulation via injected HTML/JS can be brittle across Streamlit versions.
   - Fix: Minimize direct DOM assumptions, scope injected selectors carefully (`window.parent.document`), and wrap scripts to check for existing elements before injecting.

6. Testing visual changes quickly
   - Symptom: Each CSS tweak required re-running Streamlit to verify layout across wide and narrow viewports.
   - Fix: Iterative small edits, using responsive media queries and resizing the browser during testing.

---

## How to Run the App (Development)

1. Create a virtual environment (recommended) and install dependencies. Example (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run the Streamlit app:

```powershell
python -m streamlit run app.py
```

3. The app opens in your default browser (usually `http://localhost:8501`).

---

## How to Convert This Markdown to PDF (Windows / PowerShell)

Below are multiple options. Pick the one that fits your environment.

### Option A — Pandoc + LaTeX (best-quality PDF)

1. Install Pandoc (https://pandoc.org/) and a TeX engine (e.g., TinyTeX, TeX Live, or MiKTeX).
   - You can install Pandoc with Chocolatey: `choco install pandoc`.
   - Install TinyTeX via R or use MiKTeX installer.

2. Convert to PDF:

```powershell
# If you have xelatex installed
pandoc .\BUILD_DOC.md -o .\BUILD_DOC.pdf --pdf-engine=xelatex
```

Pros: high fidelity, full control over fonts and pagination. Cons: requires a TeX engine installation.

### Option B — Pandoc + wkhtmltopdf (HTML -> PDF)

1. Install Pandoc and `wkhtmltopdf`.
2. Convert:

```powershell
pandoc .\BUILD_DOC.md -o .\BUILD_DOC.pdf --from markdown --pdf-engine=wkhtmltopdf
```

Pros: Simpler than LaTeX, can produce visually pleasing output with CSS. Cons: wkhtmltopdf may have limits with complex CSS.

### Option C — VSCode `Markdown PDF` extension

1. Open `BUILD_DOC.md` in VSCode.
2. Install the `markdown-pdf` or `Markdown PDF` extension.
3. Use the command palette `Markdown PDF: Export (pdf)`.

Pros: Quick and easy for developers using VSCode.

### Option D — Use Python with `weasyprint` (HTML -> PDF)

1. Install packages:

```powershell
pip install markdown weasyprint
```

2. Convert using a small Python script (PowerShell example):

```powershell
python - <<'PY'
import markdown, weasyprint
html = markdown.markdown(open('BUILD_DOC.md', encoding='utf-8').read(), extensions=['fenced_code', 'tables'])
weasyprint.HTML(string=html).write_pdf('BUILD_DOC.pdf')
PY
```

Pros: Pure Python, scriptable. Cons: you may need additional system dependencies for weasyprint (Cairo, Pango).

---

## Suggestions / Next Steps

- Add a small `docs/` folder and keep this document plus screenshots demonstrating the hover-delete and gear placement.
- Add a small automated `make` or `invoke` task to generate a PDF using your preferred toolchain (Pandoc/LaTeX or WeasyPrint).
- Consider extracting CSS into a separate static resource if you plan to expand the UI further, or move more client-side behavior into an iframe component for isolation.

---

## Contact / Notes

If you want, I can:
- Generate the PDF here (if you allow installing necessary dependencies in this environment), or
- Add a small `scripts/make_pdf.ps1` that runs the recommended conversion command on your machine.

File created: `BUILD_DOC.md` in the repository root.
