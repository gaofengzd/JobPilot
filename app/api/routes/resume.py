"""Resume upload endpoint with bounded in-memory parsing."""

from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.dependencies import ApiServices, get_services
from app.core.exceptions import ResumeReadError
from app.schemas.candidate import CandidateProfile
from app.utils.resume_files import MAX_RESUME_BYTES, load_resume_bytes

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("/parse", response_model=CandidateProfile)
async def parse_resume(
    file: UploadFile = File(...),
    services: ApiServices = Depends(get_services),
) -> CandidateProfile:
    data = await file.read(MAX_RESUME_BYTES + 1)
    if len(data) > MAX_RESUME_BYTES:
        raise ResumeReadError("Resume file exceeds the 5 MB limit.")
    document = load_resume_bytes(file.filename or "", data)
    return services.resume_parser.parse_document(document, request_id=str(uuid4()))
