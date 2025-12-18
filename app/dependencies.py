"""
Dependency injection functions for FastAPI routes.
Provides common dependencies like current user, Firestore client, etc.
"""

from typing import Optional

from fastapi import Request, HTTPException, Depends

from app.services.firestore_service import FirestoreService


def get_current_user(request: Request) -> dict:
    """
    Dependency: Get current authenticated user from request state.
    Raises 401 if not authenticated.

    Args:
        request: FastAPI request with auth middleware applied

    Returns:
        dict: User info from JWT

    Raises:
        HTTPException: 401 if not authenticated
    """
    if not request.state.authenticated or not request.state.user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return request.state.user


def get_current_user_optional(request: Request) -> Optional[dict]:
    """
    Dependency: Get current user if authenticated, None otherwise.
    Does not raise exception for unauthenticated requests.

    Args:
        request: FastAPI request

    Returns:
        dict: User info if authenticated, None otherwise
    """
    if request.state.authenticated and request.state.user:
        return request.state.user
    return None


def get_firestore() -> FirestoreService:
    """
    Dependency: Get Firestore service instance.

    Returns:
        FirestoreService: Initialized Firestore client
    """
    return FirestoreService()


def get_current_user_id(current_user: dict = Depends(get_current_user)) -> str:
    """
    Dependency: Get current user's ID.

    Args:
        current_user: User dict from get_current_user dependency

    Returns:
        str: User ID
    """
    return current_user["user_id"]
