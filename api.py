import os
import shutil
import tempfile
import uuid
from threading import Lock

from fastapi.concurrency import run_in_threadpool
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from main import run_pipeline

# FastAPI service that wraps the OCR pipeline and exposes upload/status/download endpoints.

app = FastAPI(title="Electoral Roll OCR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory job state for a single active workflow.
_state_lock = Lock()
_status = {
    "state": "idle",
    "progress": 0,
    "stage": "Idle",  
    "error": None,
}
_downloads = {}


def _set_status(*, state=None, progress=None, stage=None, error=None): 
    """Thread-safe helper to update API-visible pipeline status."""
    with _state_lock:
        if state is not None:
            _status["state"] = state
        if progress is not None:
            _status["progress"] = int(max(0, min(100, progress)))
        if stage is not None:  
            _status["stage"] = stage  
        if error is not None:
            _status["error"] = error


@app.get("/status")
def get_status():
    """Return the latest processing state consumed by the frontend progress UI."""
    with _state_lock:
        return {
            "state": _status["state"],
            "progress": _status["progress"],
            "stage": _status["stage"],  
            "error": _status["error"],
        }


@app.post("/upload")
async def upload_roll(file: UploadFile = File(...)):
    """Accept a roll PDF, run OCR pipeline, and return summary + preview rows."""
    filename = (file.filename or "").lower()
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a valid PDF file")

    _set_status(state="processing", progress=5, stage="Converting PDF to images...", error=None)  # OPTIMIZED

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        def update_progress(pct: int):  
            # Map coarse numeric progress to user-facing stage labels.
            if pct < 15:  
                stage = "Converting PDF to images..."  
            elif pct < 30:  
                stage = "Detecting voter cards..."  
            elif pct < 90:  
                stage = "Extracting voter data..."  
            else:  
                stage = "Generating Excel file..."  
            _set_status(progress=max(5, pct), stage=stage)  

        result = await run_in_threadpool(  
            run_pipeline, 
            pdf_path=tmp_path,  
            progress_callback=update_progress,  
        )  

        records = result.get("records", [])
        output_path = result.get("output_path")
        if not output_path or not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Output file was not generated")

        download_id = uuid.uuid4().hex
        _downloads[download_id] = output_path

        male_count = sum((r.get("Gender") or "").strip().lower() == "male" for r in records)
        female_count = sum((r.get("Gender") or "").strip().lower() == "female" for r in records)

        # Keep API response light by returning only the first few extracted voters.
        preview = []
        for row in records[:10]:
            preview.append(
                {
                    "serial_number": row.get("Serial Number", ""),
                    "epic_number": row.get("EPIC Number", ""),
                    "name": row.get("Name", ""),
                    "relative_name": row.get("Relative Name", ""),
                    "relation_type": row.get("Relation Type", ""),
                    "house_number": row.get("House Number", ""),
                    "age": row.get("Age", ""),
                    "gender": row.get("Gender", ""),
                }
            )

        _set_status(state="completed", progress=100, stage="Completed", error=None)  # OPTIMIZED

        return {
            "total_voters": len(records),
            "total_pages": result.get("pages_processed", 0),
            "male_count": male_count,
            "female_count": female_count,
            "download_id": download_id,
            "preview": preview,
        }
    except HTTPException as exc:
        _set_status(state="failed", progress=0, stage="Failed", error=str(exc.detail))  # OPTIMIZED
        raise
    except Exception as exc:  # pragma: no cover - defensive API wrapper
        _set_status(state="failed", progress=0, stage="Failed", error=str(exc))  # OPTIMIZED
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.get("/download/{download_id}")
def download_output(download_id: str):
    """Serve generated Excel file for a previously returned download token."""
    output_path = _downloads.get(download_id)
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Output file not found")

    return FileResponse(
        path=output_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="voter_output.xlsx",
    )
