import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

router = APIRouter()

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".xls", ".pptx",
    ".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm",
}

MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다: {suffix}. 지원 형식: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="파일 크기가 50MB를 초과합니다.")

    save_name = f"{uuid.uuid4().hex}{suffix}"
    save_path = UPLOAD_DIR / save_name
    save_path.write_bytes(content)

    return {"path": str(save_path), "filename": file.filename}
