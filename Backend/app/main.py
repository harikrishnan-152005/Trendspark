# main.py
import uvicorn
from fastapi import FastAPI,Depends
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
# Import your models and services
from app.models.models import IdeaInput, ValidationReport
from app.services.pipeline_service import run_validation_pipeline
from app.database.database import SessionLocal, ReportDB,save_report
from app.core.cache import generate_cache_key, get_cache, set_cache
from fastapi import HTTPException
from pydantic import BaseModel
from app.auth.auth import router as auth_router
from app.auth.auth import get_current_user
from app.database.database import Base, engine


# Initialize FastAPI app
app = FastAPI(
    title="TrendSpark Validation Engine",
    description="API for validating startup ideas using AI and real-time data.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    
    
# ───────── LOGIN MODEL ─────────
class LoginInput(BaseModel):
    username: str
    password: str

# ───────── LOGIN ROUTE ─────────



# ─── Enable CORS (fixes OPTIONS 405 errors from browser preflight) ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── AUTH ROUTES ───
app.include_router(auth_router)

# Mount the static folder → /static/index.html
app.mount("/static", StaticFiles(directory="static"), name="static")
"http://127.0.0.1:8000"
# Serve frontend at root path (/)
@app.get("/", include_in_schema=False)
async def serve_frontend():
    index_path = Path("static") / "index.html"
    
    if not index_path.is_file():
        return HTMLResponse(
            content="""
            <h1 style="color: #ff4444; text-align: center; margin-top: 120px; font-family: system-ui;">
                404 - Frontend File Not Found<br>
                <small style="color: #aaa; font-size: 1rem;">
                    Expected location: <code>Backend/static/index.html</code><br>
                    Please make sure the file exists in the 'static' folder.
                </small>
            </h1>
            """,
            status_code=404
        )
    
    return FileResponse(
        path=index_path,
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# Health check
@app.get("/api/v1/health", tags=["Status"])
async def get_health():
    """Health check endpoint to ensure the server is running."""
    return {"status": "ok"}


# Main validation endpoint
@app.post("/api/v1/validate", response_model=ValidationReport)
async def validate_idea(
    idea: IdeaInput,
    current_user=Depends(get_current_user)
):
    report = await run_validation_pipeline(
        idea,
        user_id=current_user.id
    )

    
    save_report(report, current_user.id)

    return report

@app.get("/api/v1/reports")
def get_reports(current_user=Depends(get_current_user)):
    db = SessionLocal()

    reports = db.query(ReportDB)\
        .filter(ReportDB.user_id == current_user.id)\
        .all()

    db.close()

    return [
        {
            "report_id": r.report_id,
            "idea_name": r.idea_name,
            "overall_score": r.overall_score
        }
        for r in reports
    ]

# Run the server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,                # auto-reload on file changes (great for dev)
        reload_dirs=["."],          # watch current directory (Backend)
        # workers=1,                # uncomment only when you need multiple workers
    )