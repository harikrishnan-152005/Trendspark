import json
import uuid
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.auth.auth import get_current_user
from app.auth.auth import router as auth_router
from app.core.cache import generate_cache_key, get_cache, set_cache
from app.database.database import Base, ReportDB, SessionLocal, engine, save_report
from app.models.models import IdeaInput, ValidationReport
from app.services.pipeline_service import generate_pdf, run_validation_pipeline

BACKEND_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BACKEND_DIR / "static"
REPORTS_DIR = BACKEND_DIR / "reports"

app = FastAPI(
    title="TrendSpark Validation Engine",
    description="API for validating startup ideas using AI and real-time data.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


class LoginInput(BaseModel):
    username: str
    password: str


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    index_path = STATIC_DIR / "index.html"

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
            status_code=404,
        )

    return FileResponse(
        path=index_path,
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/api/v1/health", tags=["Status"])
async def get_health():
    return {"status": "ok"}


def _deserialize_saved_report(report_row: ReportDB) -> ValidationReport:
    data = json.loads(report_row.full_json)
    data["report_id"] = report_row.report_id
    data["idea_name"] = report_row.idea_name
    data["overall_score"] = report_row.overall_score
    return ValidationReport(**data)


def _find_report_by_internal_id(user_id: str, requested_report_id: str):
    db = SessionLocal()
    try:
        reports = db.query(ReportDB).filter(ReportDB.user_id == user_id).all()
    finally:
        db.close()

    for report in reports:
        try:
            data = json.loads(report.full_json)
        except Exception:
            continue

        if data.get("report_id") == requested_report_id:
            return report

    return None


@app.post("/api/v1/validate", response_model=ValidationReport)
async def validate_idea(
    idea: IdeaInput,
    current_user=Depends(get_current_user),
):
    idea_dict = idea.model_dump()
    cache_key = generate_cache_key(idea_dict)

    cached = get_cache(cache_key)
    if cached:
        print("CACHE HIT")
        cached_report = (
            cached
            if isinstance(cached, ValidationReport)
            else ValidationReport(**cached)
        )

        db = SessionLocal()
        try:
            existing_report = db.query(ReportDB).filter(
                ReportDB.report_id == cached_report.report_id,
                ReportDB.user_id == current_user.id,
            ).first()

            conflicting_report = db.query(ReportDB).filter(
                ReportDB.report_id == cached_report.report_id,
            ).first()
        finally:
            db.close()

        if existing_report:
            file_path = REPORTS_DIR / f"{cached_report.report_id}.pdf"
            if not file_path.exists():
                generate_pdf(cached_report)
            return cached_report

        if conflicting_report or not existing_report:
            cached_report = cached_report.model_copy(
                update={"report_id": str(uuid.uuid4())}
            )

        save_report(cached_report, current_user.id)
        generate_pdf(cached_report)
        set_cache(cache_key, cached_report)
        return cached_report

    print("CACHE MISS")

    report = await run_validation_pipeline(
        idea,
        user_id=current_user.id,
    )

    set_cache(cache_key, report)
    return report


@app.get("/api/v1/reports")
def get_reports(current_user=Depends(get_current_user)):
    db = SessionLocal()

    reports = (
        db.query(ReportDB)
        .filter(ReportDB.user_id == current_user.id)
        .all()
    )

    db.close()

    return [
        {
            "report_id": r.report_id,
            "idea_name": r.idea_name,
            "overall_score": r.overall_score,
        }
        for r in reports
    ]


@app.get("/api/v1/report/{report_id}")
def preview_report(
    report_id: str,
    current_user=Depends(get_current_user),
):
    db = SessionLocal()

    report = db.query(ReportDB).filter(
        ReportDB.report_id == report_id,
        ReportDB.user_id == current_user.id,
    ).first()

    db.close()

    if not report:
        report = _find_report_by_internal_id(current_user.id, report_id)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        return _deserialize_saved_report(report)
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid report data")


@app.get("/api/v1/report/{report_id}/pdf")
def download_report_pdf(
    report_id: str,
    current_user=Depends(get_current_user),
):
    db = SessionLocal()

    report = db.query(ReportDB).filter(
        ReportDB.report_id == report_id,
        ReportDB.user_id == current_user.id,
    ).first()

    db.close()

    if not report:
        report = _find_report_by_internal_id(current_user.id, report_id)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    validation_report = _deserialize_saved_report(report)
    generated_path = generate_pdf(validation_report)
    file_path = Path(generated_path) if generated_path else REPORTS_DIR / f"{validation_report.report_id}.pdf"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        path=file_path,
        filename=f"{validation_report.idea_name}.pdf",
        media_type="application/pdf",
    )


@app.delete("/api/v1/report/{report_id}")
def delete_report(report_id: str, current_user=Depends(get_current_user)):
    db = SessionLocal()

    report = db.query(ReportDB).filter(
        ReportDB.report_id == report_id,
        ReportDB.user_id == current_user.id,
    ).first()

    if not report:
        db.close()
        raise HTTPException(status_code=404, detail="Report not found")

    db.delete(report)
    db.commit()
    db.close()

    pdf_path = REPORTS_DIR / f"{report_id}.pdf"
    if pdf_path.exists():
        pdf_path.unlink()

    return {"message": "Report + PDF deleted successfully"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(BACKEND_DIR)],
    )
