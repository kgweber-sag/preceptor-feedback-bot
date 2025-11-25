"""
Preceptor Feedback Bot - Streamlit Application
A conversational tool for faculty to provide structured feedback on medical students.
"""

import os
import re
from datetime import datetime

import streamlit as st

from config import Config
from utils import logger
from utils.vertex_ai_client import VertexAIClient


# Authentication check (stubbed for future use)
def check_authentication():
    """
    Check if user is authenticated.
    Currently a stub - returns True to allow all users.

    To enable authentication later:
    1. Set REQUIRE_AUTH=true in environment variables
    2. Deploy Cloud Run with --no-allow-unauthenticated
    3. Implement one of these options:
       - Identity-Aware Proxy (IAP) - reads headers
       - Streamlit auth (if using Streamlit Cloud)
       - Custom OAuth flow
       - Simple password protection

    Returns:
        bool: True if user is authenticated, False otherwise
    """
    if not Config.REQUIRE_AUTH:
        return True

    # TODO: Implement actual authentication
    # Example using IAP headers (when enabled):
    # user_email = st.experimental_get_query_params().get("user_email")
    # if user_email and user_email[0] in Config.ALLOWED_USERS:
    #     return True

    # For now, allow everyone
    logger.debug("Authentication check bypassed (REQUIRE_AUTH=false)")
    return True


def show_authentication_error():
    """Display authentication error page"""
    st.error("🔒 Authentication Required")
    st.write("You must be authenticated to access this application.")
    st.write("Please contact the administrator for access.")
    st.stop()


# Check authentication before rendering app
if not check_authentication():
    show_authentication_error()

# Page configuration
st.set_page_config(
    page_title="Preceptor Feedback Bot",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize configuration
try:
    Config.validate()
except ValueError as e:
    logger.config_validation_failed(str(e))
    st.error(f"Configuration Error: {e}")
    st.stop()


def initialize_session_state():
    """Initialize Streamlit session state variables"""
    if "client" not in st.session_state:
        st.session_state.client = None
    if "conversation_started" not in st.session_state:
        st.session_state.conversation_started = False
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "feedback_generated" not in st.session_state:
        st.session_state.feedback_generated = False
    if "current_feedback" not in st.session_state:
        st.session_state.current_feedback = ""
    if "student_name" not in st.session_state:
        st.session_state.student_name = ""


def start_conversation():
    """Initialize a new conversation"""
    # Require student name before starting
    if not st.session_state.student_name or not st.session_state.student_name.strip():
        st.error("Please enter a student name before starting the conversation.")
        return

    try:
        st.session_state.client = VertexAIClient()
        st.session_state.client.set_student_name(st.session_state.student_name)

        initial_message = st.session_state.client.start_conversation()

        st.session_state.messages = [{"role": "assistant", "content": initial_message}]
        st.session_state.conversation_started = True
        st.session_state.feedback_generated = False

    except Exception as e:
        logger.error(f"Failed to start conversation: {e}")
        st.error(f"Error starting conversation: {e}")
        st.session_state.conversation_started = False


def on_student_name_change():
    """Callback when student name input changes - auto-captures the value"""
    # Auto-save from the widget to session state
    # The key binding handles this automatically, this is just for logging
    if st.session_state.student_name_input:
        logger.debug(f"Student name captured: {st.session_state.student_name_input}")


def send_message(user_input: str):
    """Send user message and get response"""
    if not st.session_state.client:
        logger.error("send_message called without active client")
        st.error("No active conversation. Please start a new conversation.")
        return

    # Add user message to display
    st.session_state.messages.append({"role": "user", "content": user_input})

    try:
        # Get bot response (now returns tuple)
        response, contains_feedback = st.session_state.client.send_message(user_input)
        st.session_state.messages.append({"role": "assistant", "content": response})

        # If model generated feedback prematurely, flip the flag
        if contains_feedback and not st.session_state.feedback_generated:
            st.session_state.feedback_generated = True
            st.session_state.current_feedback = response
            st.warning(
                "⚠️ The model generated feedback early. You can now review and refine it below."
            )
            logger.feedback_generated(
                student_name=st.session_state.student_name or "unknown", premature=True
            )

        # Check if conversation should conclude
        if st.session_state.client.should_conclude_conversation():
            st.info(
                "🎯 Conversation limit reached or completion indicated. Ready to generate feedback."
            )

    except Exception as e:
        logger.error(
            f"Error in send_message: {e}", student=st.session_state.student_name
        )
        st.error(f"Error sending message: {e}")


def generate_feedback():
    """Generate final feedback summaries"""
    if not st.session_state.client:
        logger.error("generate_feedback called without active client")
        st.error("No active conversation.")
        return

    try:
        feedback = st.session_state.client.generate_feedback()
        st.session_state.current_feedback = feedback
        st.session_state.feedback_generated = True

    except Exception as e:
        logger.error(
            f"Error generating feedback: {e}", student=st.session_state.student_name
        )
        st.error(f"Error generating feedback: {e}")


def refine_feedback(refinement_request: str):
    """Refine the generated feedback"""
    if not st.session_state.client:
        logger.error("refine_feedback called without active client")
        st.error("No active conversation.")
        return

    try:
        refined = st.session_state.client.refine_feedback(refinement_request)
        st.session_state.current_feedback = refined

    except Exception as e:
        logger.error(
            f"Error refining feedback: {e}", student=st.session_state.student_name
        )
        st.error(f"Error refining feedback: {e}")


def save_and_finish():
    """Save conversation log and finish"""
    if st.session_state.client:
        try:
            filename = st.session_state.client.save_conversation_log(
                st.session_state.student_name or "unknown"
            )
            if filename:
                st.success(f"✅ Conversation saved: {filename}")

            # Also save the latest generated/refined feedback
            try:
                feedback_text = st.session_state.current_feedback or ""
                if feedback_text:
                    student_for_fname = st.session_state.student_name or "unknown"
                    # Sanitize filename: allow alnum, dash, underscore
                    safe_student = re.sub(
                        r"[^A-Za-z0-9_-]", "_", student_for_fname.strip()
                    )
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    feedback_fname = f"feedback_{safe_student}_{timestamp}.txt"

                    if Config.IS_CLOUD:
                        # Cloud: Save to Cloud Storage
                        from google.cloud import storage

                        client = storage.Client()
                        bucket = client.bucket(Config.LOG_BUCKET)
                        blob = bucket.blob(feedback_fname)
                        blob.upload_from_string(
                            feedback_text, content_type="text/plain"
                        )
                        feedback_path = f"gs://{Config.LOG_BUCKET}/{feedback_fname}"
                        logger.info(
                            "Feedback saved to Cloud Storage",
                            student=student_for_fname,
                            file=feedback_path,
                        )
                        st.success(f"✅ Feedback saved: {feedback_path}")
                    else:
                        # Local: Save to ./output directory
                        output_dir = os.path.join(".", "output")
                        os.makedirs(output_dir, exist_ok=True)
                        feedback_path = os.path.join(output_dir, feedback_fname)

                        with open(feedback_path, "w") as f:
                            f.write(feedback_text)

                        logger.info(
                            "Feedback saved to local file",
                            student=student_for_fname,
                            file=feedback_path,
                        )
                        st.success(f"✅ Feedback saved: {feedback_path}")

            except Exception as e:
                logger.error(
                    f"Failed to save feedback: {e}",
                    student=st.session_state.student_name,
                )
                st.error(f"Error saving feedback file: {e}")

            # Reset session - INCLUDING student name
            logger.info("Session reset", student=st.session_state.student_name)
            st.session_state.client = None
            st.session_state.conversation_started = False
            st.session_state.messages = []
            st.session_state.feedback_generated = False
            st.session_state.current_feedback = ""
            st.session_state.student_name = ""  # Clear student name

        except Exception as e:
            logger.error(
                f"Error saving conversation: {e}", student=st.session_state.student_name
            )
            st.error(f"Error saving conversation: {e}")
    else:
        logger.error("save_and_finish called without active client")
        st.error("No active conversation.")


# Main UI
def main():
    """Main application UI"""
    initialize_session_state()

    # Log application start once per Streamlit session to avoid noisy repeats
    # (Streamlit re-runs the script on every interaction).
    if not st.session_state.get("app_started_logged"):
        logger.app_started()
        st.session_state.app_started_logged = True

    # Sidebar
    with st.sidebar:
        st.title("⚙️ Configuration")

        st.markdown("### Model Settings")
        st.info(f"**Model**: {Config.get_model_display_name()}")
        st.text(f"Temperature: {Config.TEMPERATURE}")
        st.text(f"Max Tokens: {Config.MAX_OUTPUT_TOKENS}")

        st.markdown("### Conversation Settings")
        st.text(f"Max Turns: {Config.MAX_TURNS}")

        if st.session_state.conversation_started and st.session_state.client:
            st.markdown("### Current Session")
            st.text(f"Turn: {st.session_state.client.turn_count}/{Config.MAX_TURNS}")

        st.markdown("---")

        if st.button(
            "🔄 Start New Conversation", type="primary", use_container_width=True
        ):
            start_conversation()
            st.rerun()

        if st.session_state.conversation_started:
            if st.button("📝 Generate Feedback", use_container_width=True):
                generate_feedback()
                st.rerun()

        st.markdown("---")
        st.caption(f"Project: {Config.GCP_PROJECT_ID}")
        st.caption(f"Region: {Config.GCP_REGION}")
        st.markdown("---")
        with st.expander("ℹ️ Deployment Info"):
            st.caption(f"Environment: {Config.DEPLOYMENT_ENV}")
            st.caption(f"Project: {Config.GCP_PROJECT_ID}")
            st.caption(f"Region: {Config.GCP_REGION}")
            if Config.IS_CLOUD:
                st.caption(f"Logs: gs://{Config.LOG_BUCKET}")
            else:
                st.caption(f"Logs: {Config.LOG_DIRECTORY}")

    # Main content area
    st.title("🩺 Preceptor Feedback Bot")
    st.caption("A conversational tool for providing structured student feedback")

    # Student name input - REQUIRED before conversation starts
    if not st.session_state.conversation_started:
        st.markdown("### 👤 Student Information")
        st.text_input(
            "Student Name *",
            placeholder="e.g., Jane Doe",
            key="student_name_input",
            on_change=on_student_name_change,
            help="Required - This will be included in the feedback report",
        )

        # Auto-sync from widget to session_state.student_name
        if st.session_state.student_name_input:
            st.session_state.student_name = st.session_state.student_name_input

        # Show warning if name is missing
        if not st.session_state.student_name:
            st.warning(
                "⚠️ Please enter the student's name before starting the conversation."
            )
        else:
            st.success(
                f"✓ Ready to provide feedback for: **{st.session_state.student_name}**"
            )

        st.markdown("---")

    # Main conversation area
    if not st.session_state.conversation_started:
        st.info("👈 Click **Start New Conversation** in the sidebar to begin")

        # Instructions
        st.markdown(
            """
        ### How This Works
        
        1. **Start a conversation** - The bot will ask you about your interaction with a medical student
        2. **Answer questions** - Provide observations about the student's performance
        3. **Generate feedback** - The bot creates structured feedback for the clerkship director and student
        4. **Review and refine** - Edit or request changes before finalizing
        5. **Save** - Copy the feedback to your assessment system
        
        This tool organizes your observations according to CWRU's competency framework and generates 
        both a summary for administrators and constructive narrative feedback for the student.
        """
        )

    else:
        # Display conversation
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input (only show if feedback not yet generated)
        if not st.session_state.feedback_generated:
            user_input = st.chat_input("Type your response here...")
            if user_input:
                send_message(user_input)
                st.rerun()

        # Feedback display and refinement
        if st.session_state.feedback_generated:
            st.markdown("---")
            st.markdown("## 📋 Generated Feedback")

            st.markdown(st.session_state.current_feedback)

            st.markdown("---")

            col1, col2 = st.columns([3, 1])

            with col1:
                refinement = st.text_input(
                    "Request changes (optional)",
                    placeholder="e.g., 'Make it more concise' or 'Add more emphasis on teamwork'",
                )
                if refinement and st.button("🔄 Refine Feedback"):
                    refine_feedback(refinement)
                    st.rerun()

            with col2:
                if st.button(
                    "✅ Finish & Save", type="primary", use_container_width=True
                ):
                    save_and_finish()
                    st.success("Conversation completed and saved!")
                    st.rerun()


if __name__ == "__main__":
    main()
