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
from app.api import auth

# Import API routers (to be created)
# from app.api import conversations, feedback, user


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
# To be implemented:
# app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
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
    Dashboard - placeholder for Phase 4.
    Shows authenticated user info for now.
    """
    # Check if authenticated
    if not request.state.authenticated:
        return RedirectResponse(url="/", status_code=302)

    user = request.state.user

    # Simple placeholder dashboard
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - {settings.APP_NAME}</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-50 p-8">
        <div class="max-w-4xl mx-auto bg-white rounded-lg shadow p-8">
            <h1 class="text-3xl font-bold text-blue-600 mb-4">Welcome, {user['name']}!</h1>
            <div class="mb-6">
                <p class="text-gray-600">Email: {user['email']}</p>
                <p class="text-gray-600">Domain: {user['domain']}</p>
                <p class="text-gray-600">User ID: {user['user_id']}</p>
            </div>
            <div class="bg-yellow-50 border border-yellow-200 rounded p-4 mb-4">
                <p class="text-yellow-800">🚧 Dashboard under construction (Phase 4)</p>
            </div>
            <div class="space-x-4">
                <form action="/auth/logout" method="post" class="inline">
                    <button type="submit" class="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">
                        Logout
                    </button>
                </form>
                <a href="/health" class="bg-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-300 inline-block">
                    Health Check
                </a>
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
