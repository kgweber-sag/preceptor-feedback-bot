# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A Streamlit-based conversational AI tool that helps medical school faculty provide structured, competency-based feedback on medical students after clinical encounters. Built with Google Vertex AI (Gemini models).

The application conducts a guided conversation with preceptors (3-5 minutes), then generates two outputs organized by CWRU School of Medicine's core competencies:
1. **Clerkship Director Summary** - Structured bullets (strengths, areas for improvement, developmental suggestions)
2. **Student-Facing Narrative** - Constructive, supportive feedback for the student

## Common Commands

### Local Development
```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your GCP_PROJECT_ID, GCP_REGION, and GCP_CREDENTIALS_PATH

# Run the application
streamlit run app.py
```

### Cloud Deployment
```bash
# Deploy to Cloud Run (one command)
./deploy.sh

# Manual deployment
gcloud run deploy preceptor-feedback-bot \
  --source . \
  --region us-central1 \
  --project your-gcp-project-id
```

## Architecture

### Core Components

**Entry Point:**
- `app.py` - Streamlit UI and session orchestration. All user interactions, conversation state management, and UI flow happen here.

**AI Integration:**
- `utils/vertex_ai_client.py` - Wrapper around `google-genai` Vertex AI chat. Core functions:
  - `start_conversation()` - Initialize chat with system prompt
  - `send_message(user_message)` - Returns `(response_text, contains_feedback)` tuple
  - `generate_feedback()` - Generate structured summaries after conversation
  - `refine_feedback(refinement_request)` - Refine generated feedback
  - `save_conversation_log(student_name)` - Save conversation JSON to logs/ or Cloud Storage

**Configuration:**
- `config.py` - Environment-driven configuration using python-dotenv. All model settings (MODEL_NAME, TEMPERATURE, MAX_OUTPUT_TOKENS), conversation parameters (MAX_TURNS), and deployment settings (DEPLOYMENT_ENV, GCP_PROJECT_ID, LOG_BUCKET) are centralized here.
- Model display names map in `Config.get_model_display_name()`

**Prompting:**
- `prompts/system_prompt.md` - Canonical system instruction that controls conversational style, probing behavior, and competency framework. Contains the critical rule: do NOT generate formal feedback during conversation phase (only after explicit request).

**Logging:**
- `utils/app_logger.py` - Global singleton logger. Use throughout the app for telemetry:
  ```python
  from utils import logger
  logger.info("Message", student=student_name)
  logger.conversation_started(student_name=name, model=model)
  logger.feedback_generated(student_name=name)
  ```

### Critical Behavior Invariant: Premature Feedback Detection

**The conversation phase must NOT produce final feedback until `generate_feedback()` is explicitly called.**

- System prompt in `prompts/system_prompt.md` instructs model to only gather information during conversation
- `utils/vertex_ai_client.py::_contains_formal_feedback()` detects if model ignores instructions and generates feedback early
- Detection checks for markers like `**Clerkship Director Summary`, `**Student-Facing Narrative`, `**Strengths**`, etc.
- `send_message()` returns `(response_text, contains_feedback)` tuple - UI treats `contains_feedback=True` as premature feedback flag
- If markers change, update the `feedback_markers` array in `_contains_formal_feedback()`

### Session State Management

Session state in `app.py` tracks:
- `client` - VertexAIClient instance
- `conversation_started` - Whether conversation has begun
- `messages` - Conversation history for display
- `feedback_generated` - Whether feedback has been generated (blocks chat input when true)
- `current_feedback` - Generated feedback text
- `student_name` - Student name (required before starting conversation)
- `show_survey` - Whether to show post-session survey
- `feedback_timestamp` - Timestamp for feedback file (persists across refinements)

### Conversation Workflow

1. User enters student name (required)
2. Click "Start New Conversation" → calls `VertexAIClient.start_conversation()`
3. Model acknowledges student name in first response
4. Preceptor and AI exchange messages (max MAX_TURNS)
5. Click "Generate Feedback" → calls `VertexAIClient.generate_feedback()`
6. Auto-saves conversation log and feedback draft
7. Optional: refine feedback with text input
8. Click "Finish, Save, and Clear" → saves final versions, shows survey
9. Survey submission resets session state

### Logging and Persistence

**Local Development:**
- Conversation logs: `./logs/conversation_{timestamp}_{student_name}.json`
- Feedback files: `./output/feedback_{timestamp}_{student_name}.txt`
- Survey responses: `./output/survey_{timestamp}.json`
- Application logs: `./logs/app_{date}.log`

**Cloud Deployment:**
- All logs/files saved to Cloud Storage bucket specified by LOG_BUCKET
- Uses Application Default Credentials (Cloud Run service account)
- Path format: `gs://{LOG_BUCKET}/{filename}`

### Credentials Handling

**Local:** Set `GCP_CREDENTIALS_PATH` in `.env` to point to service account JSON. The app sets `GOOGLE_APPLICATION_CREDENTIALS` environment variable.

**Cloud:** Set `DEPLOYMENT_ENV=cloud`. No credentials path needed - uses Application Default Credentials automatically.

## Common Modification Patterns

### Change conversational behavior, questions, or tone
Edit `prompts/system_prompt.md`. Keep the "only gather information" instruction intact unless also updating UI flow.

### Switch model
Update `MODEL_NAME` in `.env` or environment variables. If needed, add display name mapping in `config.py::get_model_display_name()`.

### Modify premature feedback detection
Update `feedback_markers` array in `utils/vertex_ai_client.py::_contains_formal_feedback()`.

### Add logging
Use the singleton logger from `utils/app_logger.py`:
```python
from utils import logger
logger.info("Event", student=student_name, extra_field=value)
```
Available methods: `info()`, `warning()`, `error()`, `debug()`, plus specialized helpers like `conversation_started()`, `feedback_generated()`, etc.

### Modify UI flow
Update session state variables and button callbacks in `app.py`. The conversation flow is controlled by boolean flags (`conversation_started`, `feedback_generated`, `show_survey`).

## Safeguards and Privacy

- System prompt reminds preceptors not to include patient identifiers (PHI)
- All feedback treated as FERPA-protected educational records
- Student and preceptor names preserved in all outputs
- Service account credentials never committed to git (in `.gitignore`)
- Logs contain full conversation transcripts for quality improvement and debugging

## Integration Points

**Vertex AI:** Uses `google-genai` SDK (pinned in requirements.txt) with Gemini models. Runtime behavior depends on `Config.MODEL_NAME` and GCP credentials.

**Cloud Storage:** Used for logs and feedback files in cloud deployment. Requires Storage Object Creator role for Cloud Run service account.

**Streamlit:** UI framework. Session state persists across reruns. Chat input pins to bottom of page.

## Conversation Logs Schema

Conversation logs (JSON) contain:
```json
{
  "metadata": {
    "timestamp": "ISO 8601",
    "model": "model-name",
    "student_name": "name",
    "total_turns": 10,
    "project_id": "gcp-project",
    "environment": "local|cloud"
  },
  "conversation": [
    {
      "timestamp": "ISO 8601",
      "turn": 1,
      "role": "user|assistant|system",
      "content": "message text",
      "response_time_ms": 1234.56
    }
  ]
}
```

Special turn markers: `"turn": "feedback_generation"`, `"turn": "feedback_refinement"` (not numbered conversation turns).

## Error Handling

**Rate Limits (429):** `_call_with_backoff()` in `VertexAIClient` implements exponential backoff with jitter (~2s, ~4s, ~8s, ~16s, ~32s) with max 5 retries for up to ~60 seconds total wait time.

**Empty Responses:** Logged and raised as `ValueError("No response received from model")`.

**Logging Failures:** Cloud Storage logging failures fall back to stderr.

## Critical Configuration Requirements

### Avoiding RESOURCE_EXHAUSTED Errors

**Region Configuration:**
- **MUST use a specific region** (e.g., `us-central1`, `us-east4`, `europe-west4`)
- **NEVER use `GCP_REGION=global`** - causes unpredictable routing and rate limit issues
- Quota limits are region-specific; "global" may use shared/restricted quota pools
- Ensure Cloud Run and `.env` both specify the same region

**Model Selection:**
- **Use stable model versions** (e.g., `gemini-2.0-flash-001`)
- **Avoid experimental models** (suffix `-exp`) unless necessary
- Experimental models have drastically lower rate limits (2-10 RPM vs 60+ RPM)
- Can trigger 429 errors even with very low usage (5-6 calls in a few minutes)

**Example of correct configuration:**
```bash
GCP_REGION=us-central1          # NOT "global"
MODEL_NAME=gemini-2.0-flash-001 # NOT "gemini-2.0-flash-exp"
```

## Deployment Environments

**Local (`DEPLOYMENT_ENV=local`):**
- Reads `.env` file
- Requires `GCP_CREDENTIALS_PATH`
- Logs to `./logs/` directory
- Output to `./output/` directory

**Cloud (`DEPLOYMENT_ENV=cloud`):**
- Environment variables set in Cloud Run
- Uses Application Default Credentials (no JSON key)
- Logs to Cloud Storage bucket specified by `LOG_BUCKET`
- `CLOUD_RUN_TIMEOUT` controls session timeout (default 600s / 10 min)
