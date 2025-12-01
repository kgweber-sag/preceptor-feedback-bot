# Preceptor Feedback Bot

A conversational AI tool that helps medical school faculty provide structured, competency-based feedback on medical students after clinical encounters. Built with Streamlit and Google Vertex AI (Gemini models).

## Overview

This application guides preceptors through a brief (3-5 minute) conversation to gather observations about a student's clinical performance. It then generates two structured outputs:

1. **Clerkship Director Summary** - Organized by strengths, areas for improvement, and developmental suggestions
2. **Student-Facing Narrative** - Constructive, supportive feedback framed as opportunities for growth

All feedback is organized according to [CWRU School of Medicine's core competencies](https://case.edu/medicine/curriculum/curriculum-overview/competencies-and-education-program-objectives):
- Professionalism
- Teamwork and Interprofessional Collaboration
- Reflective Practice
- Interpersonal and Communication Skills
- Knowledge for Practice
- Patient Care
- (omitted from the prompt) Research and Scholarship
- (also omitted) Personal and Professional Development
- Systems-based Practice

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Streamlit UI (app.py)                                     │
│  └─> VertexAIClient (utils/vertex_ai_client.py)           │
│       └─> Google Vertex AI (Gemini models)                │
└────────────────────────────────────────────────────────────┘
         │
         └─> Logs & Feedback Output
              - Local: ./logs/ and ./output/
              - Cloud: Cloud Storage bucket
```

## Prerequisites

- **Python 3.12+** (tested with 3.12 and 3.13)
- **Google Cloud Platform account** with:
  - Vertex AI API enabled
  - Service account with Vertex AI User role (for local development)
  - Cloud Storage bucket (for cloud deployment)

## Local Development Setup

### 1. Clone and Install Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd preceptor-feedback-bot

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
```

Required `.env` variables for local development:

```bash
# Deployment
DEPLOYMENT_ENV=local

# GCP Configuration
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1
GCP_CREDENTIALS_PATH=./path-to-your-service-account-key.json

# Model Configuration
MODEL_NAME=gemini-2.0-flash-exp
TEMPERATURE=0.7
MAX_OUTPUT_TOKENS=2048

# Conversation Settings
MAX_TURNS=10

# Logging
LOG_TO_FILE=true
LOG_DIRECTORY=./logs
```

### 3. Get GCP Service Account Credentials

1. Go to [GCP Console → IAM & Admin → Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Create a service account or select existing one
3. Grant **Vertex AI User** role
4. Create and download a JSON key
5. Save the JSON file in your project directory and update `GCP_CREDENTIALS_PATH` in `.env`

### 4. Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Cloud Deployment (Google Cloud Run)

### Prerequisites

1. Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
2. Authenticate:
   ```bash
   gcloud auth login
   gcloud config set project your-gcp-project-id
   ```

### One-Command Deployment

```bash
./deploy.sh
```

This script:
- Builds a Docker container from source
- Deploys to Cloud Run in `us-central1`
- Uses the service account associated with Cloud Run (no JSON key needed)

### Manual Deployment

This command is available as a shell script in `./deploy.sh`

```bash
gcloud run deploy preceptor-feedback-bot \
  --source . \
  --region us-central1 \
  --project your-gcp-project-id \
  --allow-unauthenticated  # Add if you want public access
```

### Environment Variables for Cloud Run

Set these in Cloud Run console or via `gcloud run services update`:

```bash
DEPLOYMENT_ENV=cloud
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1
LOG_BUCKET=your-log-bucket-name
MODEL_NAME=gemini-2.0-flash-exp
```

**Note:** `GCP_CREDENTIALS_PATH` is NOT needed in Cloud Run - it uses Application Default Credentials automatically.

### Setting Up Cloud Storage for Logs

```bash
# Create bucket for logs
gsutil mb -p your-gcp-project-id -l us-central1 gs://your-log-bucket-name

# Grant Cloud Run service account write access
gcloud projects add-iam-policy-binding your-gcp-project-id \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectCreator"
```

## Project Structure

```
preceptor-feedback-bot/
├── app.py                          # Main Streamlit application
├── config.py                       # Configuration management
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Container definition
├── deploy.sh                       # Deployment script
├── .env.example                    # Example environment variables
├── prompts/
│   └── system_prompt.md          # AI system instructions
├── utils/
│   ├── app_logger.py              # Logging utilities
│   └── vertex_ai_client.py        # Vertex AI wrapper
├── logs/                           # Local conversation logs (gitignored)
└── output/                         # Local feedback files (gitignored)
```

## Key Features

### Student Name Workflow
- **Required before starting** - Name input appears before conversation begins
- **Auto-captured** - No "Save" button needed, name captured on input
- **Confirmed by AI** - Model acknowledges student name in first response
- **Logged thoroughly** - All conversation and feedback files include student name

### Conversation Flow
1. Preceptor enters student name
2. Clicks "Start New Conversation"
3. AI asks questions about the clinical encounter
4. AI probes for specifics when responses are vague
5. AI covers key competency domains
6. Preceptor clicks "Generate Feedback"
7. Review and refine feedback if needed
8. Save and finish

### Safeguards
- Reminds preceptors to avoid patient identifiers
- Treats all outputs as FERPA-protected educational records
- Logs all conversations for quality improvement
- Prevents premature feedback generation during conversation phase

## Configuration Options

### Available Models

Edit `MODEL_NAME` in `.env`:

```bash
# Recommended (fast, latest)
MODEL_NAME=gemini-2.0-flash-exp

# Alternative options
MODEL_NAME=gemini-1.5-pro
MODEL_NAME=gemini-1.5-flash
```

See `config.py` for model display name mappings.

### Conversation Parameters

```bash
TEMPERATURE=0.7              # 0.0 (deterministic) to 1.0 (creative)
MAX_OUTPUT_TOKENS=2048       # Max response length
MAX_TURNS=10                 # Max conversation exchanges
```

## Troubleshooting

### "Failed to initialize Vertex AI client"
- Check that Vertex AI API is enabled in your GCP project
- Verify service account has `roles/aiplatform.user` permission
- Confirm `GCP_CREDENTIALS_PATH` points to valid JSON key (local only)

### Student name not appearing in AI responses
- Ensure student name is entered before clicking "Start New Conversation"
- Check `logs/` directory - conversation JSON should include student name
- Verify system prompt includes name confirmation instruction

### Logs not saving to Cloud Storage
- Check bucket exists: `gsutil ls gs://your-bucket-name`
- Verify Cloud Run service account has Storage Object Creator role
- Check `LOG_BUCKET` environment variable is set correctly

### Streamlit app not loading
```bash
# Check Python version
python --version  # Should be 3.12+

# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Clear Streamlit cache
rm -rf ~/.streamlit
```

## Development Guidelines

### Editing Prompts

To modify AI behavior, edit `prompts/system_prompt.md`:
- Conversation style and tone
- Question types and probing logic
- Competency framework
- Output format

**Important:** Do NOT change the instruction about waiting to generate feedback until explicitly asked. This prevents premature feedback generation.

### Detecting Premature Feedback

The system detects if the AI generates formal feedback during conversation phase by checking for markers in `utils/vertex_ai_client.py::_contains_formal_feedback()`. Update the `feedback_markers` array if you modify the output format.

### Logging

All application events use the singleton logger from `utils/app_logger.py`:

```python
from utils import logger

logger.info("Message", student=student_name)
logger.error("Error occurred", student=student_name)
logger.conversation_started(student_name=name, model=model)
logger.feedback_generated(student_name=name)
```

## Security & Privacy

- **FERPA Compliance**: All feedback is treated as educational record
- **No patient identifiers**: Users reminded not to include PHI
- **Authentication**: Currently open access; set `REQUIRE_AUTH=true` to enable (requires additional configuration)
- **Credentials**: Service account keys should NEVER be committed to git (already in `.gitignore`)

## Support & Contribution

For questions or issues related to CWRU medical education workflows, contact your medical education IT team.

### Making Changes

1. Test locally with `streamlit run app.py`
2. Check for errors: Python linting, type checking
3. Update this README if you change deployment procedures
4. Deploy to Cloud Run using `./deploy.sh`

## License

Internal use only - CWRU School of Medicine
