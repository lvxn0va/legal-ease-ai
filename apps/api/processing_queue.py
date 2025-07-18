import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from models import Document, DocumentStatus, get_db
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

class ProcessingQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.processing_tasks = {}
        self.is_running = False
        
    async def add_job(self, document_id: str, user_id: str, s3_key: str, s3_bucket: str):
        """Add a document processing job to the queue"""
        job = {
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "user_id": user_id,
            "s3_key": s3_key,
            "s3_bucket": s3_bucket,
            "created_at": datetime.utcnow().isoformat(),
            "retry_count": 0
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
                    job_id for job_id, task in self.processing_tasks.items() 
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
        """Process a single document job"""
        document_id = job["document_id"]
        logger.info(f"Processing job {job['id']} for document {document_id}")
        
        db = next(get_db())
        try:
            await asyncio.sleep(2)
            
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentStatus.COMPLETED
                document.updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"Completed processing for document {document_id}")
            else:
                logger.error(f"Document {document_id} not found")
                
        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}")
            
            try:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document:
                    if job["retry_count"] < 3:  # Max 3 retries
                        job["retry_count"] += 1
                        await asyncio.sleep(5)  # Wait before retry
                        await self.queue.put(job)
                        logger.info(f"Retrying job {job['id']} (attempt {job['retry_count']})")
                    else:
                        document.status = DocumentStatus.FAILED
                        document.updated_at = datetime.utcnow()
                        db.commit()
                        logger.error(f"Document {document_id} processing failed after max retries")
            except Exception as retry_error:
                logger.error(f"Failed to handle retry for document {document_id}: {retry_error}")
                db.rollback()
        finally:
            db.close()
    
    async def stop_worker(self):
        """Stop the background worker"""
        self.is_running = False
        
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks.values(), return_exceptions=True)
        
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

def add_document_to_queue(document_id: str, user_id: str, s3_key: str, s3_bucket: str) -> str:
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
