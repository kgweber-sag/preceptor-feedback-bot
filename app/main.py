"""
FastAPI Main Application - Preceptor Feedback Bot
Entry point for the FastAPI application with OAuth authentication and Firestore persistence.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.middleware.auth_middleware import AuthMiddleware
from app.api import auth, conversations

# Import API routers (to be created)
# from app.api import feedback, user


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup: Initialize services
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Environment: {settings.DEPLOYMENT_ENV}")
    print(f"Model: {settings.get_model_display_name()}")
    print(f"OAuth enabled: {bool(settings.OAUTH_CLIENT_ID)}")

    # Validate configuration
    try:
        settings.validate_config()
        print("Configuration validated successfully")
    except ValueError as e:
        print(f"Configuration error: {e}")
        raise

    yield

    # Shutdown: Cleanup
    print("Shutting down application")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered feedback tool for medical education",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# Add middleware
app.add_middleware(AuthMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

# Add custom template filters
templates.env.filters["timeago"] = lambda dt: "just now"  # Placeholder for timeago filter


# Include API routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
# To be implemented:
# app.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
# app.include_router(user.router, tags=["user"])


# ===== Root Routes =====


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Root endpoint - redirects to dashboard if authenticated, otherwise shows login page.
    """
    # Check if user is authenticated (via middleware)
    if request.state.authenticated and request.state.user:
        # Redirect to dashboard
        return RedirectResponse(url="/dashboard", status_code=302)

    # Show login page
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
        },
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Dashboard - start new conversations or view history.
    """
    # Check if authenticated
    if not request.state.authenticated:
        return RedirectResponse(url="/", status_code=302)

    user = request.state.user

    # Simple dashboard with new conversation form
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - {settings.APP_NAME}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/htmx.org@1.9.10"></script>
        <script src="https://unpkg.com/htmx.org@1.9.10/dist/ext/json-enc.js"></script>
    </head>
    <body class="bg-gray-50 p-8">
        <div class="max-w-4xl mx-auto">
            <!-- Header -->
            <div class="bg-white rounded-lg shadow-sm p-6 mb-6">
                <h1 class="text-3xl font-bold text-blue-600 mb-2">Welcome, {user['name']}!</h1>
                <p class="text-gray-600">Start a new feedback conversation below</p>
            </div>

            <!-- New Conversation Form -->
            <div class="bg-white rounded-lg shadow-sm p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Start New Conversation</h2>
                <form
                    hx-post="/conversations"
                    hx-headers='{{"Content-Type": "application/json"}}'
                    hx-ext="json-enc"
                    class="space-y-4">

                    <div>
                        <label for="student_name" class="block text-sm font-medium text-gray-700 mb-2">
                            Student Name *
                        </label>
                        <input
                            type="text"
                            id="student_name"
                            name="student_name"
                            required
                            placeholder="Enter student's full name"
                            class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                        <p class="text-xs text-gray-500 mt-1">
                            This will be used to personalize the feedback conversation
                        </p>
                    </div>

                    <button
                        type="submit"
                        class="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium">
                        🩺 Start Feedback Session
                    </button>
                </form>
            </div>

            <!-- Recent Conversations (Phase 4) -->
            <div class="bg-white rounded-lg shadow-sm p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Recent Conversations</h2>
                <div class="bg-yellow-50 border border-yellow-200 rounded p-4">
                    <p class="text-yellow-800">🚧 Conversation history coming in Phase 4</p>
                </div>
            </div>

            <!-- User Info & Actions -->
            <div class="bg-white rounded-lg shadow-sm p-6">
                <h2 class="text-lg font-semibold mb-3">Account</h2>
                <div class="mb-4">
                    <p class="text-sm text-gray-600">Email: {user['email']}</p>
                    <p class="text-sm text-gray-600">Domain: {user['domain']}</p>
                </div>
                <form action="/auth/logout" method="post" class="inline">
                    <button type="submit" class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors text-sm">
                        Logout
                    </button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """)


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.DEPLOYMENT_ENV,
    }


@app.get("/config")
async def config_info():
    """Configuration info endpoint (for debugging)"""
    return settings.get_deployment_info()


# ===== Error Handlers =====


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors"""
    # Check if it's an HTMX request
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            '<div class="text-red-600 p-4">Page not found</div>', status_code=404
        )

    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "error_message": "Page not found",
            "status_code": 404,
        },
        status_code=404,
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors"""
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            '<div class="text-red-600 p-4">Internal server error</div>',
            status_code=500,
        )

    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "error_message": "Internal server error",
            "status_code": 500,
        },
        status_code=500,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.DEBUG,
    )
