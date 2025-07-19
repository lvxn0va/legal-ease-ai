export type DocumentStatus = 'uploaded' | 'processing' | 'complete' | 'error';

export interface Document {
  id: string;
  userId: string;
  filename: string;
  originalName: string;
  fileSize: number;
  mimeType: string;
  s3Key: string;
  status: DocumentStatus;
  uploadedAt: string;
  processedAt?: string;
  errorMessage?: string;
}

export interface DocumentUploadRequest {
  file: File;
}

export interface DocumentUploadResponse {
  documentId: string;
  uploadUrl: string;
  message: string;
}
