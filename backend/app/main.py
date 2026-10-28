from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.investigations import router

app = FastAPI(title="Anveshi", version="0.1.0", description="Identifier-first application intelligence engine")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
app.include_router(router)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "anveshi"}
