# app/db.py
import os
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient

DATABASE_URL = os.getenv("DATABASE_URL")
MONGO_URI = os.getenv("MONGO_URI")

engine = None
AsyncSessionLocal = None
mongo_client = None
mongo_db = None


async def init_postgres():
    global engine, AsyncSessionLocal
    if not DATABASE_URL:
        print("DATABASE_URL not set; skipping Postgres init")
        return
    engine = create_async_engine(DATABASE_URL, future=True, echo=False)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    # Optionally create tables here if you import models
    # from .models import Base
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)


async def close_postgres():
    global engine
    if engine:
        await engine.dispose()


async def init_mongo():
    global mongo_client, mongo_db
    if not MONGO_URI:
        print("MONGO_URI not set; skipping Mongo init")
        return
    mongo_client = AsyncIOMotorClient(MONGO_URI)
    # choose DB from URI or env
    dbname = os.getenv("MONGO_DB")
    if dbname:
        mongo_db = mongo_client[dbname]
    else:
        mongo_db = mongo_client.get_default_database()


async def close_mongo():
    global mongo_client
    if mongo_client:
        mongo_client.close()
