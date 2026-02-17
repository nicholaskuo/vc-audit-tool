import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# Configure file + console logging
log_file = os.path.join(os.path.dirname(__file__), "..", "logs.txt")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="a"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

from backend.api.routes import router

app = FastAPI(title="VC Portfolio Valuation Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

logger.info("VC Portfolio Valuation Engine started")


@app.get("/")
async def root():
    return {"message": "VC Portfolio Valuation Engine API", "docs": "/docs"}
