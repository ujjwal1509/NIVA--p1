# app/main.py
# app/main.py
import os
import asyncio
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

load_dotenv()

from .api_routes import router as api_router
from .db import init_postgres, init_mongo, close_postgres, close_mongo

app = FastAPI(title="NIVA Symptom Analysis Service")

app.include_router(api_router, prefix="/api")


@app.on_event("startup")
async def startup():
    await init_postgres()
    await init_mongo()


@app.on_event("shutdown")
async def shutdown():
    await close_postgres()
    await close_mongo()


@app.get("/")
async def root():
    return {"service": "niva-symptom-bot", "status": "ok"}
