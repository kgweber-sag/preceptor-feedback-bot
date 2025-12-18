"""
Firestore service for database operations.
Handles user profiles, conversations, and feedback storage/retrieval.
"""

import os
from datetime import datetime
from typing import List, Optional

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.config import settings
from app.models.user import User, UserCreate
from app.models.conversation import Conversation, ConversationSummary, ConversationStatus
from app.models.feedback import Feedback, FeedbackVersion


class FirestoreService:
    """Service for Firestore database operations"""

    def __init__(self):
        """Initialize Firestore client"""
        # Set credentials if running locally
        if not settings.IS_CLOUD and settings.GCP_CREDENTIALS_PATH:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GCP_CREDENTIALS_PATH

        self.db = firestore.Client(
            project=settings.GCP_PROJECT_ID,
            database=settings.FIRESTORE_DATABASE,
        )

    # ===== User Operations =====

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User email

        Returns:
            User object if found, None otherwise
        """
        users_ref = self.db.collection(settings.USERS_COLLECTION)
        query = users_ref.where(filter=FieldFilter("email", "==", email)).limit(1)

        docs = list(query.stream())
        if not docs:
            return None

        doc = docs[0]
        data = doc.to_dict()
        data["user_id"] = doc.id
        return User(**data)

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create new user in Firestore.

        Args:
            user_data: User creation data

        Returns:
            Created User object
        """
        users_ref = self.db.collection(settings.USERS_COLLECTION)

        user_dict = {
            "email": user_data.email,
            "name": user_data.name,
            "domain": user_data.domain,
            "picture_url": user_data.picture_url,
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow(),
        }

        # Create document with auto-generated ID
        doc_ref = users_ref.add(user_dict)[1]

        # Return User object with ID
        user_dict["user_id"] = doc_ref.id
        return User(**user_dict)

    async def update_user_last_login(self, user_id: str) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: User document ID
        """
        user_ref = self.db.collection(settings.USERS_COLLECTION).document(user_id)
        user_ref.update({"last_login": datetime.utcnow()})

    async def get_or_create_user(self, user_data: UserCreate) -> User:
        """
        Get existing user or create new one.

        Args:
            user_data: User data

        Returns:
            User object
        """
        existing_user = await self.get_user_by_email(user_data.email)

        if existing_user:
            # Update last login
            await self.update_user_last_login(existing_user.user_id)
            return existing_user
        else:
            # Create new user
            return await self.create_user(user_data)

    # ===== Conversation Operations =====

    async def create_conversation(
        self, user_id: str, student_name: str, model: str
    ) -> Conversation:
        """
        Create new conversation.

        Args:
            user_id: User document ID
            student_name: Student being evaluated
            model: AI model name

        Returns:
            Created Conversation object
        """
        conversations_ref = self.db.collection(settings.CONVERSATIONS_COLLECTION)

        conv_dict = {
            "user_id": user_id,
            "student_name": student_name,
            "status": ConversationStatus.ACTIVE.value,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "metadata": {
                "model": model,
                "total_turns": 0,
                "project_id": settings.GCP_PROJECT_ID,
                "environment": settings.DEPLOYMENT_ENV,
            },
            "messages": [],
        }

        doc_ref = conversations_ref.add(conv_dict)[1]
        conv_dict["conversation_id"] = doc_ref.id

        return Conversation(**conv_dict)

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get conversation by ID.

        Args:
            conversation_id: Conversation document ID

        Returns:
            Conversation object if found, None otherwise
        """
        doc_ref = self.db.collection(settings.CONVERSATIONS_COLLECTION).document(
            conversation_id
        )
        doc = doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        data["conversation_id"] = doc.id
        return Conversation(**data)

    async def update_conversation_messages(
        self, conversation_id: str, messages: list, total_turns: int
    ) -> None:
        """
        Update conversation messages and turn count.

        Args:
            conversation_id: Conversation document ID
            messages: List of message dicts
            total_turns: Updated turn count
        """
        conv_ref = self.db.collection(settings.CONVERSATIONS_COLLECTION).document(
            conversation_id
        )

        conv_ref.update({
            "messages": messages,
            "metadata.total_turns": total_turns,
            "updated_at": datetime.utcnow(),
        })

    async def update_conversation_status(
        self, conversation_id: str, status: ConversationStatus
    ) -> None:
        """
        Update conversation status.

        Args:
            conversation_id: Conversation document ID
            status: New status
        """
        conv_ref = self.db.collection(settings.CONVERSATIONS_COLLECTION).document(
            conversation_id
        )

        conv_ref.update({
            "status": status.value,
            "updated_at": datetime.utcnow(),
        })

    async def list_conversations(
        self,
        user_id: str,
        status: Optional[ConversationStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ConversationSummary]:
        """
        List conversations for a user.

        Args:
            user_id: User document ID
            status: Optional status filter
            limit: Max conversations to return
            offset: Pagination offset

        Returns:
            List of ConversationSummary objects
        """
        conversations_ref = self.db.collection(settings.CONVERSATIONS_COLLECTION)

        # Base query: user's conversations
        query = conversations_ref.where(filter=FieldFilter("user_id", "==", user_id))

        # Optional status filter
        if status:
            query = query.where(filter=FieldFilter("status", "==", status.value))

        # Order by updated_at descending
        query = query.order_by("updated_at", direction=firestore.Query.DESCENDING)

        # Pagination
        query = query.offset(offset).limit(limit)

        # Execute query
        docs = list(query.stream())

        summaries = []
        for doc in docs:
            data = doc.to_dict()
            messages = data.get("messages", [])
            last_message = messages[-1]["content"] if messages else ""

            summary = ConversationSummary(
                conversation_id=doc.id,
                student_name=data["student_name"],
                status=ConversationStatus(data["status"]),
                total_turns=data["metadata"]["total_turns"],
                last_message_preview=last_message[:100] if last_message else None,
                created_at=data["created_at"],
                updated_at=data["updated_at"],
            )
            summaries.append(summary)

        return summaries

    # ===== Feedback Operations =====

    async def create_feedback(
        self,
        conversation_id: str,
        user_id: str,
        student_name: str,
        initial_content: str,
    ) -> Feedback:
        """
        Create new feedback document.

        Args:
            conversation_id: Associated conversation ID
            user_id: User document ID
            student_name: Student being evaluated
            initial_content: Initial feedback content

        Returns:
            Created Feedback object
        """
        feedback_ref = self.db.collection(settings.FEEDBACK_COLLECTION)

        initial_version = FeedbackVersion(
            version=1,
            timestamp=datetime.utcnow(),
            type="initial",
            content=initial_content,
            request=None,
        )

        feedback_dict = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "student_name": student_name,
            "generated_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "versions": [initial_version.model_dump()],
            "current_version": 1,
        }

        doc_ref = feedback_ref.add(feedback_dict)[1]
        feedback_dict["feedback_id"] = doc_ref.id

        return Feedback(**feedback_dict)

    async def add_feedback_refinement(
        self, feedback_id: str, refinement_content: str, refinement_request: str
    ) -> Feedback:
        """
        Add refinement version to existing feedback.

        Args:
            feedback_id: Feedback document ID
            refinement_content: Refined feedback content
            refinement_request: User's refinement request

        Returns:
            Updated Feedback object
        """
        feedback_ref = self.db.collection(settings.FEEDBACK_COLLECTION).document(
            feedback_id
        )
        doc = feedback_ref.get()

        if not doc.exists:
            raise ValueError(f"Feedback {feedback_id} not found")

        data = doc.to_dict()
        current_version = data["current_version"]
        new_version = current_version + 1

        new_version_obj = FeedbackVersion(
            version=new_version,
            timestamp=datetime.utcnow(),
            type="refinement",
            content=refinement_content,
            request=refinement_request,
        )

        # Update document
        feedback_ref.update({
            "versions": firestore.ArrayUnion([new_version_obj.model_dump()]),
            "current_version": new_version,
            "updated_at": datetime.utcnow(),
        })

        # Return updated feedback
        data["versions"].append(new_version_obj.model_dump())
        data["current_version"] = new_version
        data["feedback_id"] = doc.id
        return Feedback(**data)

    async def get_feedback_by_conversation(
        self, conversation_id: str
    ) -> Optional[Feedback]:
        """
        Get feedback for a conversation.

        Args:
            conversation_id: Conversation document ID

        Returns:
            Feedback object if found, None otherwise
        """
        feedback_ref = self.db.collection(settings.FEEDBACK_COLLECTION)
        query = feedback_ref.where(
            filter=FieldFilter("conversation_id", "==", conversation_id)
        ).limit(1)

        docs = list(query.stream())
        if not docs:
            return None

        doc = docs[0]
        data = doc.to_dict()
        data["feedback_id"] = doc.id
        return Feedback(**data)
