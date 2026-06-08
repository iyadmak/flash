"""Application Entry Point"""

from fastapi import FastAPI
from flash.api.routes import health, item
from flash.config import settings

app = FastAPI(title=settings.app_name)

app.include_router(health.router)
app.include_router(item.router)
