'use client';

import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

interface DocumentUploadProps {
  onUploadSuccess?: (document: any) => void;
  onUploadError?: (error: string) => void;
}

export default function DocumentUpload({ onUploadSuccess, onUploadError }: DocumentUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');

  const validateFile = (file: File): string | null => {
    const allowedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword'
    ];
    
    const allowedExtensions = ['.pdf', '.docx', '.doc'];
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
      return 'Only PDF and DOCX files are allowed';
    }
    
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      return 'File size must be less than 50MB';
    }
    
    return null;
  };

  const uploadFile = async (file: File) => {
    setUploading(true);
    setUploadProgress(0);
    setError('');

    try {
      const token = localStorage.getItem('accessToken');
      if (!token) {
        throw new Error('No authentication token found');
      }

      const uploadUrlFormData = new FormData();
      uploadUrlFormData.append('filename', file.name);
      uploadUrlFormData.append('content_type', file.type);

      const uploadUrlResponse = await fetch('http://localhost:8000/documents/upload-url', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: uploadUrlFormData
      });

      if (uploadUrlResponse.ok) {
        const uploadData = await uploadUrlResponse.json();
        setUploadProgress(25);

        const uploadResponse = await fetch(uploadData.uploadUrl, {
          method: 'PUT',
          headers: {
            'Content-Type': file.type
          },
          body: file
        });

        if (!uploadResponse.ok) {
          throw new Error('Failed to upload file to storage');
        }

        setUploadProgress(75);

        const documentFormData = new FormData();
        documentFormData.append('filename', uploadData.uniqueFilename);
        documentFormData.append('original_filename', file.name);
        documentFormData.append('file_size', `${(file.size / (1024 * 1024)).toFixed(2)} MB`);
        documentFormData.append('mime_type', file.type);
        documentFormData.append('s3_key', uploadData.s3Key);
        documentFormData.append('s3_bucket', uploadData.s3Bucket);

        const documentResponse = await fetch('http://localhost:8000/documents', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: documentFormData
        });

        if (!documentResponse.ok) {
          const errorData = await documentResponse.json();
          throw new Error(errorData.detail || 'Failed to create document record');
        }

        const document = await documentResponse.json();
        setUploadProgress(100);

        if (onUploadSuccess) {
          onUploadSuccess(document);
        }
      } else {
        const fileExtension = file.name.split('.').pop() || '';
        const uniqueFilename = `${Date.now()}-${Math.random().toString(36).substring(2)}.${fileExtension}`;
        const s3Key = `documents/local/${uniqueFilename}`;
        
        setUploadProgress(25);

        const uploadFormData = new FormData();
        uploadFormData.append('file', file);

        const localUploadResponse = await fetch(`http://localhost:8000/documents/local-upload/${s3Key}`, {
          method: 'PUT',
          body: uploadFormData
        });

        if (!localUploadResponse.ok) {
          throw new Error('Failed to upload file to local storage');
        }

        setUploadProgress(75);

        const documentFormData = new FormData();
        documentFormData.append('filename', uniqueFilename);
        documentFormData.append('original_filename', file.name);
        documentFormData.append('file_size', `${(file.size / (1024 * 1024)).toFixed(2)} MB`);
        documentFormData.append('mime_type', file.type);
        documentFormData.append('s3_key', s3Key);
        documentFormData.append('s3_bucket', 'local-storage');

        const documentResponse = await fetch('http://localhost:8000/documents', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: documentFormData
        });

        if (!documentResponse.ok) {
          const errorData = await documentResponse.json();
          throw new Error(errorData.detail || 'Failed to create document record');
        }

        const document = await documentResponse.json();
        setUploadProgress(100);

        if (onUploadSuccess) {
          onUploadSuccess(document);
        }
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      setError(errorMessage);
      if (onUploadError) {
        onUploadError(errorMessage);
      }
    } finally {
      setUploading(false);
      setTimeout(() => setUploadProgress(0), 2000);
    }
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    const validationError = validateFile(file);
    
    if (validationError) {
      setError(validationError);
      if (onUploadError) {
        onUploadError(validationError);
      }
      return;
    }

    await uploadFile(file);
  }, [uploadFile, onUploadSuccess, onUploadError]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc']
    },
    multiple: false,
    disabled: uploading
  });

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
          ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        <div className="space-y-4">
          <div className="text-6xl text-gray-400">📄</div>
          
          {uploading ? (
            <div className="space-y-2">
              <p className="text-lg font-medium text-gray-700">Uploading...</p>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <p className="text-sm text-gray-500">{uploadProgress}% complete</p>
            </div>
          ) : isDragActive ? (
            <p className="text-lg font-medium text-blue-600">Drop the file here...</p>
          ) : (
            <div className="space-y-2">
              <p className="text-lg font-medium text-gray-700">
                Drag & drop a lease document here, or click to select
              </p>
              <p className="text-sm text-gray-500">
                Supports PDF and DOCX files up to 50MB
              </p>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}
    </div>
  );
}
