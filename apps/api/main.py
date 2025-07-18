import asyncio
import io
import logging
import os
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import uvicorn
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user_cognito,
    create_access_token,
    get_password_hash,
    register_user_cognito,
    verify_token,
)
from document_generator import document_generator
from models import (
    Document,
    DocumentFeedback,
    DocumentStatus,
    FeedbackType,
    User,
    create_tables,
    get_db,
)
from processing_queue import (
    add_document_to_queue,
    initialize_processing_queue,
    processing_queue,
    shutdown_processing_queue,
)
from s3_service import (
    generate_presigned_download_url,
    generate_presigned_upload_url,
    get_file_size_mb,
    validate_file_type,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LegalEase AI API",
    description="AI-powered lease document analysis and abstraction service",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


@app.on_event("startup")
async def startup_event():
    create_tables()
    asyncio.create_task(initialize_processing_queue())


@app.on_event("shutdown")
async def shutdown_event():
    await shutdown_processing_queue()


@app.get("/")
async def root():
    return {"message": "LegalEase AI API is running"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "legal-ease-ai-api",
        "queue_size": processing_queue.get_queue_size(),
        "processing_count": processing_queue.get_processing_count(),
    }


@app.post("/auth/register")
async def register(
    email: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    db: Session = Depends(get_db),
):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    try:
        await register_user_cognito(email, password, first_name, last_name)
    except HTTPException:
        pass

    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(password)

    db_user = User(
        id=user_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        hashed_password=hashed_password,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )

    return {
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "firstName": db_user.first_name,
            "lastName": db_user.last_name,
            "createdAt": db_user.created_at.isoformat(),
        },
        "accessToken": access_token,
        "tokenType": "bearer",
    }


@app.post("/auth/login")
async def login(
    email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    try:
        await authenticate_user_cognito(email, password)
    except HTTPException:
        pass

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )

    user.last_login_at = datetime.utcnow()
    db.commit()

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "createdAt": user.created_at.isoformat(),
            "lastLoginAt": (
                user.last_login_at.isoformat() if user.last_login_at else None
            ),
        },
        "accessToken": access_token,
        "tokenType": "bearer",
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token_data = verify_token(credentials.credentials)
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


@app.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "firstName": current_user.first_name,
        "lastName": current_user.last_name,
        "createdAt": current_user.created_at.isoformat(),
        "lastLoginAt": (
            current_user.last_login_at.isoformat()
            if current_user.last_login_at
            else None
        ),
    }


@app.post("/documents/upload-url")
async def get_upload_url(
    filename: str = Form(...),
    content_type: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    if not validate_file_type(content_type, filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are allowed",
        )

    try:
        upload_data = generate_presigned_upload_url(
            filename=filename, content_type=content_type, user_id=current_user.id
        )

        return {
            "uploadUrl": upload_data["upload_url"],
            "s3Key": upload_data["s3_key"],
            "s3Bucket": upload_data["s3_bucket"],
            "uniqueFilename": upload_data["unique_filename"],
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {str(e)}",
        )


@app.post("/documents")
async def create_document(
    file: UploadFile = File(None),
    filename: str = Form(...),
    original_filename: str = Form(...),
    file_size: str = Form(None),
    mime_type: str = Form(...),
    s3_key: str = Form(...),
    s3_bucket: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document_id = str(uuid.uuid4())

    if s3_bucket == "local-storage":
        if file is not None:
            try:
                from s3_service import LOCAL_STORAGE_PATH

                uploads_dir = Path(LOCAL_STORAGE_PATH)
                uploads_dir.mkdir(parents=True, exist_ok=True)

                local_file_path = uploads_dir / filename
                with open(local_file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                print(f"Saved file to local storage: {local_file_path}")

            except Exception as e:
                print(f"Failed to save file to local storage: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to save file: {str(e)}",
                )
        else:
            print(f"File already uploaded to local storage at: {s3_key}")

    db_document = Document(
        id=document_id,
        user_id=current_user.id,
        filename=filename,
        original_filename=original_filename,
        file_size=file_size,
        mime_type=mime_type,
        s3_key=s3_key,
        s3_bucket=s3_bucket,
        status=DocumentStatus.UPLOADED,
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    try:
        job_id = add_document_to_queue(
            document_id=db_document.id,
            user_id=current_user.id,
            s3_key=s3_key,
            s3_bucket=s3_bucket,
        )
        print(
            f"Added document {db_document.id} to processing queue with job ID: {job_id}"
        )
    except Exception as e:
        print(f"Failed to add document to processing queue: {e}")

    return {
        "id": db_document.id,
        "filename": db_document.filename,
        "originalFilename": db_document.original_filename,
        "fileSize": db_document.file_size,
        "mimeType": db_document.mime_type,
        "status": db_document.status.value,
        "createdAt": db_document.created_at.isoformat(),
        "updatedAt": db_document.updated_at.isoformat(),
    }


@app.get("/documents")
async def get_user_documents(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "originalFilename": doc.original_filename,
            "fileSize": doc.file_size,
            "mimeType": doc.mime_type,
            "status": doc.status.value,
            "createdAt": doc.created_at.isoformat(),
            "updatedAt": doc.updated_at.isoformat(),
        }
        for doc in documents
    ]


@app.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    extracted_lease_data = None
    if document.extracted_lease_data:
        try:
            import json

            extracted_lease_data = json.loads(document.extracted_lease_data)
        except (json.JSONDecodeError, TypeError):
            extracted_lease_data = None

    return {
        "id": document.id,
        "filename": document.filename,
        "originalFilename": document.original_filename,
        "fileSize": document.file_size,
        "mimeType": document.mime_type,
        "status": document.status.value,
        "createdAt": document.created_at.isoformat(),
        "updatedAt": document.updated_at.isoformat(),
        "extractedText": document.extracted_text,
        "extractedLeaseData": extracted_lease_data,
        "aiSummary": document.ai_summary,
    }


@app.get("/documents/{document_id}/download")
async def get_document_download_url(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    try:
        download_url = generate_presigned_download_url(document.s3_key)
        return {"downloadUrl": download_url}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}",
        )


@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    try:
        from s3_service import delete_file_from_s3

        delete_file_from_s3(document.s3_key)

        db.delete(document)
        db.commit()

        return {"message": "Document deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )


@app.get("/documents/{document_id}/download/pdf")
async def download_document_pdf(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download document abstract as PDF"""
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.status != DocumentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Document processing not completed")

    try:
        pdf_buffer = document_generator.generate_pdf(document)

        filename = f"{document.original_filename or document.filename}_abstract.pdf"

        return StreamingResponse(
            io.BytesIO(pdf_buffer.read()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.error(f"Failed to generate PDF for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF")


@app.get("/documents/{document_id}/download/markdown")
async def download_document_markdown(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download document abstract as Markdown"""
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.status != DocumentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Document processing not completed")

    try:
        markdown_content = document_generator.generate_markdown(document)

        filename = f"{document.original_filename or document.filename}_abstract.md"

        return StreamingResponse(
            io.BytesIO(markdown_content.encode("utf-8")),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.error(f"Failed to generate Markdown for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate Markdown")


@app.put("/documents/local-upload/{s3_key:path}")
async def local_upload(s3_key: str, request: Request):
    """
    Handle local file uploads for development
    """
    try:
        from fastapi import Request

        from s3_service import LOCAL_STORAGE_PATH

        local_file_path = Path(LOCAL_STORAGE_PATH) / s3_key
        local_file_path.parent.mkdir(parents=True, exist_ok=True)

        file_data = await request.body()

        with open(local_file_path, "wb") as buffer:
            buffer.write(file_data)

        print(f"Successfully uploaded file to: {local_file_path}")
        return {"message": "File uploaded successfully"}

    except Exception as e:
        print(f"Failed to upload file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        )


@app.get("/documents/local-download/{s3_key:path}")
async def local_download(s3_key: str):
    """
    Handle local file downloads for development
    """
    try:
        from s3_service import LOCAL_STORAGE_PATH

        local_file_path = Path(LOCAL_STORAGE_PATH) / s3_key

        if not local_file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        return FileResponse(path=str(local_file_path), filename=local_file_path.name)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}",
        )


@app.post("/documents/{document_id}/feedback")
async def submit_feedback(
    document_id: str,
    feedback_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    feedback_type_str = feedback_data.get("type")
    is_positive = feedback_data.get("is_positive")
    comment = feedback_data.get("comment", "")

    if feedback_type_str not in ["thumbs_up", "thumbs_down", "error_report"]:
        raise HTTPException(status_code=400, detail="Invalid feedback type")

    feedback_type = FeedbackType(feedback_type_str)

    existing_feedback = (
        db.query(DocumentFeedback)
        .filter(
            DocumentFeedback.document_id == document_id,
            DocumentFeedback.user_id == current_user.id,
            DocumentFeedback.feedback_type == feedback_type,
        )
        .first()
    )

    if existing_feedback:
        existing_feedback.is_positive = is_positive
        existing_feedback.comment = comment
        existing_feedback.created_at = datetime.utcnow()
        feedback = existing_feedback
    else:
        feedback = DocumentFeedback(
            id=str(uuid.uuid4()),
            document_id=document_id,
            user_id=current_user.id,
            feedback_type=feedback_type,
            is_positive=is_positive,
            comment=comment,
        )
        db.add(feedback)

    try:
        db.commit()
        db.refresh(feedback)

        return {
            "message": "Thank you for your feedback!",
            "feedback_id": feedback.id,
            "created_at": feedback.created_at.isoformat(),
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to save feedback")


@app.get("/documents/{document_id}/feedback")
async def get_document_feedback(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    feedback_list = (
        db.query(DocumentFeedback)
        .filter(
            DocumentFeedback.document_id == document_id,
            DocumentFeedback.user_id == current_user.id,
        )
        .all()
    )

    feedback_summary = {"thumbs_up": None, "thumbs_down": None, "error_reports": []}

    for feedback in feedback_list:
        if feedback.feedback_type == FeedbackType.THUMBS_UP:
            feedback_summary["thumbs_up"] = {
                "is_positive": feedback.is_positive,
                "created_at": feedback.created_at.isoformat(),
            }
        elif feedback.feedback_type == FeedbackType.THUMBS_DOWN:
            feedback_summary["thumbs_down"] = {
                "is_positive": feedback.is_positive,
                "created_at": feedback.created_at.isoformat(),
            }
        elif feedback.feedback_type == FeedbackType.ERROR_REPORT:
            feedback_summary["error_reports"].append(
                {
                    "comment": feedback.comment,
                    "created_at": feedback.created_at.isoformat(),
                }
            )

    return feedback_summary


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
