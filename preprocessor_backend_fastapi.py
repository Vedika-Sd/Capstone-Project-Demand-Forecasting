"""
Standalone FastAPI backend for the preprocessor pipeline.

It imports the existing pipeline and exposes it as HTTP endpoints.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from preprocessor_backend import PipelineResult, run_pipeline


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


def _resolve_festivals_path(custom_path: Optional[str] = None) -> Path:
    """Resolve the festival CSV path from form input or environment."""
    candidate_paths = []

    if custom_path:
        candidate_paths.append(Path(custom_path).expanduser())

    env_path = os.getenv("FESTIVALS_PATH")
    if env_path:
        candidate_paths.append(Path(env_path).expanduser())

    candidate_paths.extend(
        [
            BASE_DIR / "data" / "all_festivals.csv",
            BASE_DIR / "all_festivals.csv",
        ]
    )

    for path in candidate_paths:
        resolved = path.resolve()
        if resolved.is_file():
            return resolved

    searched_paths = ", ".join(str(path.resolve()) for path in candidate_paths) or "none"
    raise HTTPException(
        status_code=500,
        detail=(
            "Festival CSV not found. Set `FESTIVALS_PATH`, place `all_festivals.csv` "
            f"in the project folder, or send `festivals_path` in the request. Searched: {searched_paths}"
        ),
    )


def _validate_upload(filename: str) -> None:
    if not filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    if not filename.lower().endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only .xls and .xlsx files are accepted.")


class HealthResponse(BaseModel):
    status: str
    upload_dir: str
    output_dir: str


class PreprocessResponse(BaseModel):
    status: str
    message: str
    uploaded_file: str
    output_file: str
    download_path: str
    festivals_path: str
    sheets_merged: int
    rows_input: int
    rows_output: int
    unmapped_products: list[str]
    warnings: list[str]


app = FastAPI(
    title="Preprocessor API",
    description="Upload an XLS/XLSX file and run the existing preprocessing pipeline.",
    version="1.0.0",
)


@app.get("/", response_model=HealthResponse, summary="Health check")
@app.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        upload_dir=str(UPLOAD_DIR),
        output_dir=str(OUTPUT_DIR),
    )


@app.post("/preprocess", response_model=PreprocessResponse, summary="Upload and preprocess a sales file")
async def preprocess_sales_file(
    file: UploadFile = File(...),
    festivals_path: Optional[str] = Form(default=None),
) -> PreprocessResponse:
    _validate_upload(file.filename or "")

    resolved_festivals_path = _resolve_festivals_path(festivals_path)
    unique_id = uuid.uuid4().hex[:8]
    safe_name = Path(file.filename).name
    upload_path = UPLOAD_DIR / f"{unique_id}_{safe_name}"
    output_filename = f"{unique_id}_processed.csv"
    output_path = OUTPUT_DIR / output_filename

    contents = await file.read()
    upload_path.write_bytes(contents)

    result: PipelineResult = run_pipeline(
        xls_path=str(upload_path),
        festivals_path=str(resolved_festivals_path),
        output_path=str(output_path),
    )

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.error or "Pipeline failed to process the file.",
        )

    return PreprocessResponse(
        status="success",
        message="File processed successfully.",
        uploaded_file=str(upload_path),
        output_file=str(output_path),
        download_path=f"/download/{output_filename}",
        festivals_path=str(resolved_festivals_path),
        sheets_merged=result.sheets_merged,
        rows_input=result.rows_input,
        rows_output=result.rows_output,
        unmapped_products=result.unmapped_products,
        warnings=result.warnings,
    )


@app.get("/download/{filename}", summary="Download processed CSV")
async def download_file(filename: str) -> FileResponse:
    safe_filename = Path(filename).name
    file_path = OUTPUT_DIR / safe_filename

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Processed file not found.")

    return FileResponse(
        path=str(file_path),
        media_type="text/csv",
        filename=safe_filename,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("preprocessor_backend_fastapi:app", reload=True)
