'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ArrowLeftIcon, DocumentTextIcon, CalendarIcon, CurrencyDollarIcon, UserGroupIcon, ClockIcon, ArrowDownTrayIcon, HandThumbUpIcon, HandThumbDownIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface Document {
  id: string;
  filename: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  extractedText?: string;
  extractedLeaseData?: any;
  aiSummary?: string;
}

interface ExtractedLeaseData {
  parties?: {
    landlord: string;
    tenant: string;
  };
  dates?: {
    effectiveDate: string;
    expirationDate: string;
  };
  rent?: {
    baseRent: string;
    escalationClauses?: string[];
  };
  options?: {
    renewalOptions?: string[];
    terminationClauses?: string[];
  };
  use_clauses?: string[];
  assignment?: any;
}

export default function DocumentAbstractPage() {
  const [documentData, setDocumentData] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<string | null>(null);
  const router = useRouter();
  const params = useParams();
  const documentId = params.id as string;

  useEffect(() => {
    const fetchDocument = async () => {
      try {
        const token = localStorage.getItem('accessToken');
        if (!token) {
          router.push('/login');
          return;
        }

        const response = await fetch(`http://localhost:8000/documents/${documentId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          if (response.status === 401) {
            router.push('/login');
            return;
          }
          throw new Error(`Failed to fetch document: ${response.status}`);
        }

        const data = await response.json();
        setDocumentData(data);
      } catch (err) {
        console.error('Error fetching document:', err);
        setError(err instanceof Error ? err.message : 'Failed to load document');
      } finally {
        setLoading(false);
      }
    };

    if (documentId) {
      fetchDocument();
    }
  }, [documentId, router]);

  const handleBackToDashboard = () => {
    router.push('/dashboard');
  };

  const handleDownloadPDF = async () => {
    try {
      const token = localStorage.getItem('accessToken');
      const response = await fetch(`http://localhost:8000/documents/${documentId}/download/pdf`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to download PDF');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `${documentData?.filename || 'lease-abstract'}.pdf`;
      window.document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading PDF:', error);
      alert('Failed to download PDF. Please try again.');
    }
  };

  const handleDownloadMarkdown = async () => {
    try {
      const token = localStorage.getItem('accessToken');
      const response = await fetch(`http://localhost:8000/documents/${documentId}/download/markdown`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to download Markdown');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `${documentData?.filename || 'lease-abstract'}.md`;
      window.document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading Markdown:', error);
      alert('Failed to download Markdown. Please try again.');
    }
  };

  const handleFeedback = async (feedbackType: 'thumbs_up' | 'thumbs_down', isPositive: boolean) => {
    try {
      const token = localStorage.getItem('accessToken');
      const response = await fetch(`http://localhost:8000/documents/${documentId}/feedback`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: feedbackType,
          is_positive: isPositive,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      const result = await response.json();
      setFeedbackSubmitted(result.message);
      
      setTimeout(() => {
        setFeedbackSubmitted(null);
      }, 3000);
    } catch (error) {
      console.error('Error submitting feedback:', error);
      alert('Failed to submit feedback. Please try again.');
    }
  };

  const handleErrorReport = async () => {
    const comment = prompt('Please describe the error or inaccuracy you found:');
    if (!comment) return;

    try {
      const token = localStorage.getItem('accessToken');
      const response = await fetch(`http://localhost:8000/documents/${documentId}/feedback`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: 'error_report',
          comment: comment,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to submit error report');
      }

      const result = await response.json();
      setFeedbackSubmitted(result.message);
      
      setTimeout(() => {
        setFeedbackSubmitted(null);
      }, 3000);
    } catch (error) {
      console.error('Error submitting error report:', error);
      alert('Failed to submit error report. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading document...</p>
        </div>
      </div>
    );
  }

  if (error || !documentData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <DocumentTextIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Document Not Found</h2>
          <p className="text-gray-600 mb-4">{error || 'The requested document could not be found.'}</p>
          <button
            onClick={handleBackToDashboard}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const extractedData: ExtractedLeaseData = documentData.extractedLeaseData || {};

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <button
                onClick={handleBackToDashboard}
                className="flex items-center text-gray-600 hover:text-gray-900 mr-4"
              >
                <ArrowLeftIcon className="h-5 w-5 mr-2" />
                Back to Dashboard
              </button>
              <h1 className="text-xl font-semibold text-gray-900">
                Document Abstract
              </h1>
            </div>
            <div className="flex items-center space-x-3">
              <div className="relative inline-block text-left">
                <button
                  type="button"
                  className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  onClick={() => {
                    const dropdown = window.document.getElementById('download-dropdown');
                    dropdown?.classList.toggle('hidden');
                  }}
                >
                  <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
                  Download
                  <svg className="-mr-1 ml-2 h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
                <div id="download-dropdown" className="hidden absolute right-0 z-10 mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5">
                  <div className="py-1">
                    <button
                      onClick={handleDownloadPDF}
                      className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <DocumentTextIcon className="h-4 w-4 mr-3 text-red-500" />
                      Download as PDF
                      <span className="ml-auto text-xs text-gray-500">Professional format</span>
                    </button>
                    <button
                      onClick={handleDownloadMarkdown}
                      className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <DocumentTextIcon className="h-4 w-4 mr-3 text-blue-500" />
                      Download as Markdown
                      <span className="ml-auto text-xs text-gray-500">Plain text format</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="bg-white overflow-hidden shadow rounded-lg mb-6">
            <div className="px-4 py-5 sm:p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-medium text-gray-900">
                  {documentData.filename}
                </h2>
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  documentData.status === 'completed' 
                    ? 'bg-green-100 text-green-800'
                    : documentData.status === 'processing'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {documentData.status.charAt(0).toUpperCase() + documentData.status.slice(1)}
                </span>
              </div>
              <div className="text-sm text-gray-500">
                <p>Uploaded: {new Date(documentData.createdAt).toLocaleString()}</p>
                <p>Last Updated: {new Date(documentData.updatedAt).toLocaleString()}</p>
              </div>
            </div>
          </div>

          {documentData.aiSummary && (
            <div className="bg-white overflow-hidden shadow rounded-lg mb-6">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                  <DocumentTextIcon className="h-5 w-5 mr-2 text-blue-600" />
                  AI-Generated Summary
                </h3>
                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-md">
                  <p className="text-gray-800 leading-relaxed">{documentData.aiSummary}</p>
                </div>
              </div>
            </div>
          )}

          {feedbackSubmitted && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-green-800">{feedbackSubmitted}</p>
                </div>
              </div>
            </div>
          )}

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-medium text-gray-900">Lease Abstract Details</h3>
                
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-gray-600">Was this helpful?</span>
                    <button
                      onClick={() => handleFeedback('thumbs_up', true)}
                      className="p-2 text-gray-400 hover:text-green-500 transition-colors duration-200"
                      title="This abstract is accurate and helpful"
                    >
                      <HandThumbUpIcon className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => handleFeedback('thumbs_down', false)}
                      className="p-2 text-gray-400 hover:text-red-500 transition-colors duration-200"
                      title="This abstract has issues"
                    >
                      <HandThumbDownIcon className="h-5 w-5" />
                    </button>
                    <button
                      onClick={handleErrorReport}
                      className="p-2 text-gray-400 hover:text-orange-500 transition-colors duration-200"
                      title="Report an error or inaccuracy"
                    >
                      <ExclamationTriangleIcon className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {extractedData.parties && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="text-md font-medium text-gray-900 mb-3 flex items-center">
                      <UserGroupIcon className="h-5 w-5 mr-2 text-gray-600" />
                      Parties
                    </h4>
                    <dl className="space-y-2">
                      {extractedData.parties.landlord && (
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Landlord</dt>
                          <dd className="text-sm text-gray-900">{extractedData.parties.landlord}</dd>
                        </div>
                      )}
                      {extractedData.parties.tenant && (
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Tenant</dt>
                          <dd className="text-sm text-gray-900">{extractedData.parties.tenant}</dd>
                        </div>
                      )}
                    </dl>
                  </div>
                )}

                {extractedData.dates && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="text-md font-medium text-gray-900 mb-3 flex items-center">
                      <CalendarIcon className="h-5 w-5 mr-2 text-gray-600" />
                      Lease Term
                    </h4>
                    <dl className="space-y-2">
                      {extractedData.dates.effectiveDate && (
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Effective Date</dt>
                          <dd className="text-sm text-gray-900">{extractedData.dates.effectiveDate}</dd>
                        </div>
                      )}
                      {extractedData.dates.expirationDate && (
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Expiration Date</dt>
                          <dd className="text-sm text-gray-900">{extractedData.dates.expirationDate}</dd>
                        </div>
                      )}
                    </dl>
                  </div>
                )}

                {extractedData.rent && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="text-md font-medium text-gray-900 mb-3 flex items-center">
                      <CurrencyDollarIcon className="h-5 w-5 mr-2 text-gray-600" />
                      Rent Information
                    </h4>
                    <dl className="space-y-2">
                      {extractedData.rent.baseRent && (
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Base Rent</dt>
                          <dd className="text-sm text-gray-900">{extractedData.rent.baseRent}</dd>
                        </div>
                      )}
                      {extractedData.rent.escalationClauses && extractedData.rent.escalationClauses.length > 0 && (
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Escalation Clauses</dt>
                          <dd className="text-sm text-gray-900">
                            <ul className="list-disc list-inside space-y-1">
                              {extractedData.rent.escalationClauses.map((clause, index) => (
                                <li key={index}>{clause}</li>
                              ))}
                            </ul>
                          </dd>
                        </div>
                      )}
                    </dl>
                  </div>
                )}

                {extractedData.options && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="text-md font-medium text-gray-900 mb-3 flex items-center">
                      <ClockIcon className="h-5 w-5 mr-2 text-gray-600" />
                      Options & Terms
                    </h4>
                    <dl className="space-y-2">
                      {extractedData.options.renewalOptions && extractedData.options.renewalOptions.length > 0 && (
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Renewal Options</dt>
                          <dd className="text-sm text-gray-900">
                            <ul className="list-disc list-inside space-y-1">
                              {extractedData.options.renewalOptions.map((option, index) => (
                                <li key={index}>{option}</li>
                              ))}
                            </ul>
                          </dd>
                        </div>
                      )}
                      {extractedData.options.terminationClauses && extractedData.options.terminationClauses.length > 0 && (
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Termination Clauses</dt>
                          <dd className="text-sm text-gray-900">
                            <ul className="list-disc list-inside space-y-1">
                              {extractedData.options.terminationClauses.map((clause, index) => (
                                <li key={index}>{clause}</li>
                              ))}
                            </ul>
                          </dd>
                        </div>
                      )}
                    </dl>
                  </div>
                )}
              </div>

              {extractedData.use_clauses && extractedData.use_clauses.length > 0 && (
                <div className="mt-6 bg-gray-50 rounded-lg p-4">
                  <h4 className="text-md font-medium text-gray-900 mb-3">Permitted Use</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-gray-900">
                    {extractedData.use_clauses.map((clause, index) => (
                      <li key={index}>{clause}</li>
                    ))}
                  </ul>
                </div>
              )}

              {(!extractedData.parties && !extractedData.dates && !extractedData.rent && !extractedData.options && !extractedData.use_clauses) && (
                <div className="text-center py-8">
                  <DocumentTextIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                  <h4 className="text-lg font-medium text-gray-900 mb-2">No Extracted Data Available</h4>
                  <p className="text-gray-600">
                    {documentData.status === 'completed' 
                      ? 'The document was processed but no structured data could be extracted.'
                      : 'The document is still being processed. Please check back later.'}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
