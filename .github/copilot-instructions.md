## Preceptor Feedback Bot — Copilot instructions

Purpose: Help AI coding agents be productive editing and extending this repository. Keep guidance short and actionable, referencing concrete files and patterns.

- Quick start
  - Run locally: create a Python 3.12 venv, install dependencies, then run the Streamlit app:
    - pip install -r requirements.txt
    - streamlit run app.py
  - Configuration lives in `.env` / `config.py`. Set `GCP_CREDENTIALS_PATH` (or `GOOGLE_APPLICATION_CREDENTIALS`) to a Vertex AI service-account JSON if needed.

- Big-picture architecture (what to read first)
  - `app.py` — single-page Streamlit UI and session orchestration. Entry point for interactions and UI wiring.
  - `utils/vertex_ai_client.py` — wrapper around `google-genai` Vertex AI chat. Contains core functions: `start_conversation()`, `send_message()`, `generate_feedback()`, `refine_feedback()`, `save_conversation_log()`.
  - `prompts/system_prompt.txt` — canonical system instruction that determines conversational style, probes, and the crucial rule: do NOT generate formal feedback during the conversation phase.
  - `config.py` — environment-driven configuration (model, temperature, max turns, logging). Changing model happens here.
  - `utils/app_logger.py` — global singleton logger used across the app; follow its conventions when adding telemetry.

- Important behavior & invariants (do not change without tests)
  - The conversation phase must NOT produce final feedback until `generate_feedback()` is explicitly called. See `prompts/system_prompt.txt` for the instruction and `utils/vertex_ai_client.py::_contains_formal_feedback` for detection markers.
  - `send_message()` returns `(response_text, contains_feedback)` and the Streamlit UI treats `contains_feedback` as a premature feedback flag; if you change markers, update both places.
  - Conversation logs are saved to `logs/` via `VertexAIClient.save_conversation_log()` as JSON; keep that schema stable if external tools consume logs.

- Editing generative behavior
  - To alter question style, tone, or probing logic, edit `prompts/system_prompt.txt`. Keep the “only gather information” instruction intact unless also updating the UI flow and tests.
  - If you need to change how we detect premature feedback, update the `feedback_markers` array in `utils/vertex_ai_client.py::_contains_formal_feedback` (example markers are listed in the file).

- Config & deploy notes
  - Models and tokens are configured in `config.py`. Model display names map lives in `Config.get_model_display_name()`.
  - Credentials: `Config.GCP_CREDENTIALS_PATH` is optional; if present the app sets `GOOGLE_APPLICATION_CREDENTIALS` for the genai client.

- Patterns & conventions to follow
  - Use the existing `logger` (from `utils/app_logger.py`) for app-level events (startup, errors, conversation lifecycle). Methods: `info`, `warning`, `error`, and the specialized helpers like `feedback_generated()`.
  - Keep prompts in `prompts/` (not inline in code) so non-devs can iterate on wording.
  - Keep UI logic in `app.py`: small changes to conversation flow should update session state variables there (`st.session_state.client`, `messages`, `feedback_generated`).

- Integration points
  - Vertex AI via `google-genai` (pinned in `requirements.txt`); runtime behavior depends on `Config.MODEL_NAME` and GCP credentials.
  - Filesystem: `logs/` contains both application logs and conversation JSONs — check the timestamped filenames when debugging.

- Examples (where to change for common tasks)
  - Change wording/questions: edit `prompts/system_prompt.txt`.
  - Switch model: update `MODEL_NAME` in `config.py` and, if needed, add mapping in `get_model_display_name()`.
  - Tweak premature-feedback detection: edit `utils/vertex_ai_client.py::_contains_formal_feedback`.

- Safety & guardrails
  - The system prompt reminds users not to include patient identifiers — preserve that reminder when editing prompts.
  - Avoid removing logging around errors and conversation saves; logs are the primary debugging artifact.

If anything here looks incomplete or you want more examples (for instance, a small unit test scaffold for `_contains_formal_feedback`), tell me which area and I will add it.
