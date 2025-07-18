import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import HTTPException
import uuid
from typing import Optional
import shutil
from pathlib import Path

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "legal-ease-ai-documents")
LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "/tmp/legal-ease-ai-documents")

try:
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    s3_client.list_buckets()
    USE_S3 = True
    print("AWS S3 credentials found, using S3 for storage")
except (NoCredentialsError, ClientError) as e:
    s3_client = None
    USE_S3 = False
    print(f"AWS credentials not found ({e}), using local storage for development")
    Path(LOCAL_STORAGE_PATH).mkdir(parents=True, exist_ok=True)

def generate_presigned_upload_url(
    filename: str, 
    content_type: str, 
    user_id: str,
    expires_in: int = 3600
) -> dict:
    """
    Generate a presigned URL for uploading a file to S3 or local storage
    """
    try:
        file_extension = filename.split('.')[-1] if '.' in filename else ''
        unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
        s3_key = f"documents/local/{unique_filename}"
        
        if USE_S3:
            s3_key = f"documents/{user_id}/{unique_filename}"
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': S3_BUCKET_NAME,
                    'Key': s3_key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
            
            return {
                'upload_url': presigned_url,
                's3_key': s3_key,
                's3_bucket': S3_BUCKET_NAME,
                'unique_filename': unique_filename
            }
        else:
            local_upload_url = f"http://localhost:8000/documents/local-upload/{s3_key}"
            
            return {
                'upload_url': local_upload_url,
                's3_key': s3_key,
                's3_bucket': 'local-storage',
                'unique_filename': unique_filename
            }
        
    except ClientError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate upload URL: {str(e)}"
        )

def generate_presigned_download_url(
    s3_key: str,
    expires_in: int = 3600
) -> str:
    """
    Generate a presigned URL for downloading a file from S3 or local storage
    """
    try:
        if USE_S3:
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': S3_BUCKET_NAME,
                    'Key': s3_key
                },
                ExpiresIn=expires_in
            )
            return presigned_url
        else:
            return f"http://localhost:8000/documents/local-download/{s3_key}"
        
    except ClientError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate download URL: {str(e)}"
        )

def delete_file_from_s3(s3_key: str) -> bool:
    """
    Delete a file from S3 or local storage
    """
    try:
        if USE_S3:
            s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        else:
            local_file_path = Path(LOCAL_STORAGE_PATH) / s3_key
            if local_file_path.exists():
                local_file_path.unlink()
        return True
        
    except (ClientError, OSError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )

def validate_file_type(content_type: str, filename: str) -> bool:
    """
    Validate that the file is a PDF or DOCX
    """
    allowed_types = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword'
    ]
    
    allowed_extensions = ['.pdf', '.docx', '.doc']
    
    if content_type in allowed_types:
        return True
    
    filename_lower = filename.lower()
    for ext in allowed_extensions:
        if filename_lower.endswith(ext):
            return True
    
    return False

def get_file_size_mb(content_length: Optional[int]) -> Optional[str]:
    """
    Convert content length to MB string
    """
    if content_length is None:
        return None
    
    size_mb = content_length / (1024 * 1024)
    return f"{size_mb:.2f} MB"
