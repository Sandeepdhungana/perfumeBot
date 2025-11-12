"""
Windows-optimized FastAPI server with threading support.
This version uses threading within a single process for better Windows compatibility.
"""
import asyncio
import concurrent.futures
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("uvicorn_windows.log"),
        logging.StreamHandler()
    ]
)

# Thread pool for CPU-intensive operations
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=8)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan with thread pool."""
    logging.info("Starting Windows-optimized FastAPI server with thread pool...")
    logging.info(f"Thread pool initialized with {thread_pool._max_workers} workers")
    yield
    # Shutdown thread pool
    thread_pool.shutdown(wait=True)
    logging.info("Thread pool shutdown complete")

# Load environment variables
load_dotenv()

# Create FastAPI app with lifespan management
app = FastAPI(
    title="Perfume Chatbot API (Windows Optimized)",
    description="A FastAPI application for perfume recommendations with Windows threading optimization",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include chatbot routes with threading support
from app.chatbot.routes import router as chatbot_router
app.include_router(chatbot_router, prefix="/api")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_frontend():
    """Serve the main HTML file at root."""
    return FileResponse("index.html")

@app.get("/favicon.ico")
async def serve_favicon():
    """Serve favicon to prevent 404 errors."""
    return {"message": "No favicon"}

@app.get("/health")
async def health_check():
    """Health check endpoint with thread pool status."""
    return {
        "status": "healthy", 
        "message": "Perfume Chatbot API is running (Windows optimized)",
        "thread_pool_workers": thread_pool._max_workers,
        "active_threads": threading.active_count()
    }

@app.get("/stats")
async def server_stats():
    """Get server performance stats."""
    return {
        "platform": "Windows",
        "optimization": "Threading within single process",
        "thread_pool_max_workers": thread_pool._max_workers,
        "active_threads": threading.active_count(),
        "asyncio_tasks": len(asyncio.all_tasks())
    }

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Windows-optimized FastAPI server...")
    print("🧵 Using threading optimization for better Windows performance")
    print("📝 Logs will be written to uvicorn_windows.log")
    
    uvicorn.run(
        "server_windows_optimized:app",
        host="0.0.0.0",
        port=8000,
        workers=1,  # Single worker for Windows
        reload=False,
        access_log=True,
        log_level="info",
        loop="asyncio",
        # Windows-compatible configuration
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
                },
                "access": {
                    "format": "%(asctime)s [%(process)d] [ACCESS] %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.FileHandler",
                    "filename": "uvicorn_windows.log",
                    "mode": "a",
                },
                "access": {
                    "formatter": "access", 
                    "class": "logging.FileHandler",
                    "filename": "uvicorn_windows_access.log",
                    "mode": "a",
                },
                "console": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                }
            },
            "loggers": {
                "uvicorn": {"handlers": ["console", "default"], "level": "INFO", "propagate": False},
                "uvicorn.error": {"level": "INFO"},
                "uvicorn.access": {"handlers": ["access", "console"], "level": "INFO", "propagate": False},
            }
        }
    )