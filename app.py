"""
Preceptor Feedback Bot - Streamlit Application
A conversational tool for faculty to provide structured feedback on medical students.
"""

from datetime import datetime

import streamlit as st

from config import Config
from utils import logger  # Add this import
from utils.vertex_ai_client import VertexAIClient

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
    logger.app_started()  # Log app startup
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
    if "student_name_set" not in st.session_state:  # Track if name has been set
        st.session_state.student_name_set = False


def start_conversation():
    """Initialize a new conversation"""
    try:
        st.session_state.client = VertexAIClient()
        initial_message = st.session_state.client.start_conversation()
        
        st.session_state.messages = [
            {"role": "assistant", "content": initial_message}
        ]
        st.session_state.conversation_started = True
        st.session_state.feedback_generated = False
        
    except Exception as e:
        logger.error(f"Failed to start conversation: {e}")
        st.error(f"Error starting conversation: {e}")
        st.session_state.conversation_started = False


def update_student_name():
    """Update student name in active conversation"""
    if st.session_state.client and st.session_state.student_name:
        st.session_state.client.set_student_name(st.session_state.student_name)
        st.session_state.student_name_set = True


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
            
            # Reset session - INCLUDING student name
            logger.info("Session reset", student=st.session_state.student_name)
            st.session_state.client = None
            st.session_state.conversation_started = False
            st.session_state.messages = []
            st.session_state.feedback_generated = False
            st.session_state.current_feedback = ""
            st.session_state.student_name = ""  # Clear student name
            st.session_state.student_name_set = False  # Reset flag
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}", student=st.session_state.student_name)
            st.error(f"Error saving conversation: {e}")
    else:
        logger.error("save_and_finish called without active client")
        st.error("No active conversation.")




# Main UI
def main():
    """Main application UI"""
    initialize_session_state()

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

    # Main content area
    st.title("🩺 Preceptor Feedback Bot")
    st.caption("A conversational tool for providing structured student feedback")

    # Student name input - appears BEFORE conversation starts or if not yet set
    if st.session_state.conversation_started and not st.session_state.student_name_set:
        col1, col2 = st.columns([3, 1])
        with col1:
            student_input = st.text_input(
                "Student Name (optional - for logging)",
                placeholder="e.g., Jane Doe",
                key="student_name_input"
            )
        with col2:
            if st.button("Set Name", type="secondary"):
                st.session_state.student_name = student_input
                update_student_name()
                st.rerun()
        
        st.info("👆 You can set the student name now, or skip and continue the conversation")


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
