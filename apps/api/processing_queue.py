import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from models import Document, DocumentStatus, get_db
from nlp_service import (
    extract_lease_terms,
    get_extraction_statistics,
    validate_extracted_data,
)
from ocr_service import (
    extract_text_from_document,
    get_text_statistics,
    validate_extracted_text,
)
from sqlalchemy.orm import Session
from summary_service import (
    generate_lease_summary,
    get_summary_statistics,
    validate_summary,
)

logger = logging.getLogger(__name__)


class ProcessingQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.processing_tasks = {}
        self.is_running = False

    async def add_job(
        self, document_id: str, user_id: str, s3_key: str, s3_bucket: str
    ):
        """Add a document processing job to the queue"""
        job = {
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "user_id": user_id,
            "s3_key": s3_key,
            "s3_bucket": s3_bucket,
            "created_at": datetime.utcnow().isoformat(),
            "retry_count": 0,
        }

        await self.queue.put(job)
        logger.info(f"Added processing job {job['id']} for document {document_id}")

        db = next(get_db())
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentStatus.PROCESSING
                document.updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"Updated document {document_id} status to PROCESSING")
        except Exception as e:
            logger.error(f"Failed to update document status: {e}")
            db.rollback()
        finally:
            db.close()

        return job["id"]

    async def start_worker(self):
        """Start the background worker to process jobs"""
        if self.is_running:
            return

        self.is_running = True
        logger.info("Starting processing queue worker")

        while self.is_running:
            try:
                job = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                task = asyncio.create_task(self.process_job(job))
                self.processing_tasks[job["id"]] = task

                completed_tasks = [
                    job_id
                    for job_id, task in self.processing_tasks.items()
                    if task.done()
                ]
                for job_id in completed_tasks:
                    del self.processing_tasks[job_id]

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in queue worker: {e}")
                await asyncio.sleep(1)

    async def process_job(self, job: Dict[str, Any]):
        """Process a single document job with OCR text extraction"""
        document_id = job["document_id"]
        s3_key = job["s3_key"]
        s3_bucket = job["s3_bucket"]
        logger.info(f"Processing job {job['id']} for document {document_id}")

        db = next(get_db())
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"Document {document_id} not found")
                return

            if s3_bucket == "local-storage":
                from s3_service import LOCAL_STORAGE_PATH

                # So we should use it directly with LOCAL_STORAGE_PATH
                file_path = os.path.join(LOCAL_STORAGE_PATH, s3_key)

                if not os.path.exists(file_path):
                    raise FileNotFoundError(
                        f"Local file not found at expected path: {file_path}"
                    )
            else:
                raise NotImplementedError(
                    "S3 file processing not implemented in local development"
                )

            logger.info(f"Extracting text from {file_path}")

            extraction_result = extract_text_from_document(
                file_path, document.mime_type
            )

            if extraction_result["error"]:
                document.status = DocumentStatus.FAILED
                document.extraction_error = extraction_result["error"]
                logger.error(
                    f"Text extraction failed for document {document_id}: {extraction_result['error']}"
                )
            else:
                extracted_text = extraction_result["text"]

                if validate_extracted_text(extracted_text):
                    document.extracted_text = extracted_text
                    document.extraction_error = None

                    stats = get_text_statistics(extracted_text)
                    logger.info(
                        f"Successfully extracted text from document {document_id}: "
                        f"{stats['word_count']} words, {stats['character_count']} characters"
                    )

                    logger.info(f"Starting NLP extraction for document {document_id}")
                    nlp_result = extract_lease_terms(extracted_text)

                    if nlp_result.get("error"):
                        document.nlp_extraction_error = nlp_result["error"]
                        logger.error(
                            f"NLP extraction failed for document {document_id}: {nlp_result['error']}"
                        )
                    else:
                        document.extracted_lease_data = nlp_result
                        document.nlp_extraction_error = None

                        validation = validate_extracted_data(nlp_result)
                        extraction_stats = get_extraction_statistics(nlp_result)

                        logger.info(
                            f"NLP extraction completed for document {document_id}: "
                            f"{validation['confidence_score']:.2%} confidence, "
                            f"{extraction_stats['populated_fields']}/{extraction_stats['total_fields']} fields populated"
                        )

                    logger.info(
                        f"Starting AI summary generation for document {document_id}"
                    )
                    summary_result = generate_lease_summary(extracted_text, nlp_result)

                    if summary_result.get("error"):
                        logger.warning(
                            f"Summary generation had issues for document {document_id}: {summary_result['error']}"
                        )
                        document.ai_summary = "Summary generation failed"
                    else:
                        generated_summary = summary_result.get("summary")
                        if generated_summary:
                            summary_validation = validate_summary(generated_summary)
                            summary_stats = get_summary_statistics(generated_summary)

                            if summary_validation["is_valid"]:
                                document.ai_summary = generated_summary
                                logger.info(
                                    f"AI summary generated for document {document_id}: "
                                    f"{summary_stats['word_count']} words, "
                                    f"quality score: {summary_validation['quality_score']:.2f}"
                                )
                            else:
                                document.ai_summary = (
                                    "Generated summary failed quality validation"
                                )
                                logger.warning(
                                    f"Summary quality validation failed for document {document_id}: {summary_validation['issues']}"
                                )
                        else:
                            document.ai_summary = "No summary could be generated"
                            logger.warning(
                                f"No summary generated for document {document_id}"
                            )

                    document.status = DocumentStatus.COMPLETED
                else:
                    document.status = DocumentStatus.FAILED
                    document.extraction_error = "Extracted text failed quality validation (too short or low quality)"
                    logger.warning(
                        f"Extracted text for document {document_id} failed quality validation"
                    )

            document.updated_at = datetime.utcnow()
            db.commit()
            logger.info(
                f"Completed processing for document {document_id} with status: {document.status.value}"
            )

        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}")

            try:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document:
                    if job["retry_count"] < 3:  # Max 3 retries
                        job["retry_count"] += 1
                        await asyncio.sleep(5)  # Wait before retry
                        await self.queue.put(job)
                        logger.info(
                            f"Retrying job {job['id']} (attempt {job['retry_count']})"
                        )
                    else:
                        document.status = DocumentStatus.FAILED
                        document.extraction_error = (
                            f"Processing failed after max retries: {str(e)}"
                        )
                        document.updated_at = datetime.utcnow()
                        db.commit()
                        logger.error(
                            f"Document {document_id} processing failed after max retries"
                        )
            except Exception as retry_error:
                logger.error(
                    f"Failed to handle retry for document {document_id}: {retry_error}"
                )
                db.rollback()
        finally:
            db.close()

    async def stop_worker(self):
        """Stop the background worker"""
        self.is_running = False

        if self.processing_tasks:
            await asyncio.gather(
                *self.processing_tasks.values(), return_exceptions=True
            )

        logger.info("Processing queue worker stopped")

    def get_queue_size(self) -> int:
        """Get the current queue size"""
        return self.queue.qsize()

    def get_processing_count(self) -> int:
        """Get the number of currently processing jobs"""
        return len(self.processing_tasks)


processing_queue = ProcessingQueue()


async def initialize_processing_queue():
    """Initialize and start the processing queue"""
    await processing_queue.start_worker()


async def shutdown_processing_queue():
    """Shutdown the processing queue"""
    await processing_queue.stop_worker()


def add_document_to_queue(
    document_id: str, user_id: str, s3_key: str, s3_bucket: str
) -> str:
    """Synchronous wrapper to add document to processing queue"""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        task = asyncio.create_task(
            processing_queue.add_job(document_id, user_id, s3_key, s3_bucket)
        )
        return "queued"  # Return immediately, job will be processed async
    else:
        return loop.run_until_complete(
            processing_queue.add_job(document_id, user_id, s3_key, s3_bucket)
        )
