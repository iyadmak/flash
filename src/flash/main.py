"""Application Entry Point"""

from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    """Health Check Endpoint"""
    return {"status": "ok"}
