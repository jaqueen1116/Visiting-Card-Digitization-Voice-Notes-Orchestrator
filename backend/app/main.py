from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings, logger
from app.database.mongo import db_manager, init_db
from app.api.sessions import router as sessions_router
from app.api.chat import router as chat_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup database connection initialization and shutdown cleanup.
    """
    logger.info("Starting up FastAPI application lifecycle...")
    import pymongo
    import motor
    logger.info(f"Installed database driver versions - PyMongo: {pymongo.__version__}, Motor: {motor.version}")
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database during startup: {str(e)}")
    
    yield
    
    logger.info("Shutting down FastAPI application lifecycle...")
    db_manager.disconnect()

app = FastAPI(
    title="Visiting Card & Voice Notes Orchestrator API",
    description="Backend API for AI-powered visiting card digitization, state tracking, and notification orchestration.",
    version="1.0.0",
    lifespan=lifespan
)

# Register API Routers
app.include_router(sessions_router)
app.include_router(chat_router)

# Configure CORS for frontend connections
origins = [
    "http://localhost:5173",  # React Vite dev environment
    "http://localhost:3000",  # Standard React build port
    "http://127.0.0.1:5173",  # IP variant for dev
    "http://127.0.0.1:3000",  # IP variant for build
]

# Load production domains dynamically from environment settings
import os
allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
if allowed_origins_env:
    for o in allowed_origins_env.split(","):
        clean_origin = o.strip()
        if clean_origin and clean_origin not in origins:
            origins.append(clean_origin)

# Allow private subnets (10.x.x.x, 192.168.x.x, 172.16.x.x-172.31.x.x) and localhost variants
local_origin_regex = r"https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?"

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=local_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", status_code=200)
async def health_check():
    """
    Health check endpoint to verify system status, check MongoDB and Google Sheets connection health dynamically.
    """
    logger.info("Health check endpoint queried.")
    mongo_status = "unhealthy"
    sheets_status = "unconfigured"
    
    # 1. MongoDB Health Test (Reuses existing client from startup lifecycle)
    if db_manager.client is not None:
        try:
            await db_manager.client.admin.command('ping')
            mongo_status = "healthy"
        except Exception as e:
            logger.error(f"Health check MongoDB connectivity test failed: {str(e)}")
            mongo_status = "unhealthy"
    else:
        mongo_status = "unhealthy"

    # 2. Google Sheets Health Test
    if (settings.GOOGLE_SHEETS_JSON_CREDS_BASE64 or settings.GOOGLE_APPLICATION_CREDENTIALS) and settings.GOOGLE_SHEETS_ID:
        try:
            from app.services.sheets import sheets_service
            sheets_ok = await sheets_service.verify_connection()
            sheets_status = "healthy" if sheets_ok else "unhealthy"
        except Exception as e:
            logger.error(f"Health check Google Sheets connectivity test failed: {str(e)}")
            sheets_status = "unhealthy"

    # 3. WhatsApp Health Test
    whatsapp_status = "unconfigured"
    try:
        from app.services.whatsapp import whatsapp_service
        if whatsapp_service.is_configured:
            whatsapp_ok = await whatsapp_service.verify_connection()
            whatsapp_status = "healthy" if whatsapp_ok else "unhealthy"
    except Exception as e:
        logger.error(f"Health check WhatsApp connectivity test failed: {str(e)}")
        whatsapp_status = "unhealthy"
            
    # System status is degraded if any configured primary database/API service is unhealthy
    overall_status = "healthy"
    if mongo_status == "unhealthy" or sheets_status == "unhealthy" or whatsapp_status == "unhealthy":
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "environment": settings.ENVIRONMENT,
        "services": {
            "mongodb": mongo_status,
            "sheets": sheets_status,
            "whatsapp": whatsapp_status
        },
        "message": "Orchestrator Backend Service is initialized."
    }

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Running uvicorn dev server on port {settings.PORT}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
