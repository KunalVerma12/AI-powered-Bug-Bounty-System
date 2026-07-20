from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from backend.app.routes.auth import router as auth_router
    from backend.app.routes.github import router as github_router
    from backend.app.routes.scans import router as scans_router
except ModuleNotFoundError:
    from app.routes.auth import router as auth_router
    from app.routes.github import router as github_router
    from app.routes.scans import router as scans_router


app = FastAPI(
    title="Autonomous Multi-Agent Bug Bounty Hunter API",
    version="1.0.0",
    summary="AI-powered vulnerability scanning service for GitHub repositories.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(github_router)
app.include_router(scans_router)
app.include_router(auth_router, prefix="/api")
app.include_router(github_router, prefix="/api")
app.include_router(scans_router, prefix="/api")


@app.get("/")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": "autonomous-multi-agent-bug-bounty-hunter"}
