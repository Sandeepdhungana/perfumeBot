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
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)