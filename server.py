from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from app.chatbot.routes import router as chatbot_router

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Perfume Chatbot API",
    description="A FastAPI application for perfume recommendations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include chatbot routes with /api prefix
app.include_router(chatbot_router, prefix="/api")

# Mount static files (for serving CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the main HTML file at root
@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")

# Serve favicon to prevent 404 errors
@app.get("/favicon.ico")
async def serve_favicon():
    return {"message": "No favicon"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Perfume Chatbot API is running"}

if __name__ == "__main__":
    import uvicorn
    import sys
    import platform
    
    # Check if running on Windows
    is_windows = platform.system() == "Windows"
    
    if is_windows:
        # Windows-specific configuration (single worker with threading)
        print("Running on Windows - using single worker with threading optimization")
        uvicorn.run(
            "server:app", 
            host="0.0.0.0", 
            port=8000, 
            workers=1,  # Single worker for Windows compatibility
            reload=False,
            access_log=True,
            log_level="info",
            # Enable threading within single worker
            loop="asyncio",
            # Use threading for better concurrency on Windows
            log_config={
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    },
                },
                "handlers": {
                    "default": {
                        "formatter": "default",
                        "class": "logging.FileHandler",
                        "filename": "uvicorn.log",
                        "mode": "a",
                    },
                    "console": {
                        "formatter": "default",
                        "class": "logging.StreamHandler",
                        "stream": "ext://sys.stdout",
                    },
                },
                "root": {
                    "level": "INFO",
                    "handlers": ["console", "default"]
                },
                "loggers": {
                    "uvicorn": {
                        "level": "INFO",
                        "handlers": ["console", "default"], 
                        "propagate": False
                    },
                    "uvicorn.access": {
                        "level": "INFO", 
                        "handlers": ["console", "default"], 
                        "propagate": False
                    },
                    "uvicorn.error": {
                        "level": "INFO",
                        "handlers": ["console", "default"], 
                        "propagate": False
                    }
                }
            }
        )
    else:
        # Unix/Linux configuration (multi-worker)
        print("Running on Unix/Linux - using multi-worker configuration")
        uvicorn.run(
            "server:app", 
            host="0.0.0.0", 
            port=8000, 
            workers=4,  # Multiple workers for Unix/Linux
            reload=False,
            access_log=True,
            log_level="info",
            log_config={
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    },
                },
                "handlers": {
                    "default": {
                        "formatter": "default",
                        "class": "logging.FileHandler",
                        "filename": "uvicorn.log",
                        "mode": "a",
                    },
                    "console": {
                        "formatter": "default",
                        "class": "logging.StreamHandler",
                        "stream": "ext://sys.stdout",
                    },
                },
                "root": {
                    "level": "INFO",
                    "handlers": ["console", "default"]
                },
                "loggers": {
                    "uvicorn": {
                        "level": "INFO",
                        "handlers": ["console", "default"], 
                        "propagate": False
                    },
                    "uvicorn.access": {
                        "level": "INFO", 
                        "handlers": ["console", "default"], 
                        "propagate": False
                    },
                    "uvicorn.error": {
                        "level": "INFO",
                        "handlers": ["console", "default"], 
                        "propagate": False
                    }
                }
            }
        )