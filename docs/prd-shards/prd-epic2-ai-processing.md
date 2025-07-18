# Epic 2: AI Processing & Abstract Generation

**Expanded Goal:** This epic delivers the core "magic" of the application. It will implement the backend AI pipeline that takes an uploaded document, performs OCR and text extraction, analyzes the content to identify key terms, and generates both a structured abstract and a concise summary. This epic culminates in presenting the processed information to the user in a clear and intuitive interface, fully realizing the app's primary value proposition.

## Story 2.1: Trigger Asynchronous Document Processing

**As a Developer, I want to automatically trigger an asynchronous AI processing pipeline when a document is uploaded, so that heavy processing does not block the user interface and can scale efficiently.**

### Acceptance Criteria:
1. A successful document upload from Story 1.3 adds a new job message to a processing queue (e.g., AWS SQS).  
2. The document's record in the database is updated to a "Processing" status immediately after being queued.  
3. A serverless function (e.g., AWS Lambda) is configured to be automatically triggered by new messages in the queue.  
4. The user's dashboard (from Story 1.4) correctly reflects the "Processing" status for the document.

## Story 2.2: Extract Text Content from Lease Document

**As the System, I want to perform Optical Character Recognition (OCR) and text extraction on an uploaded document, so that its content is available as clean, machine-readable text for analysis.**

### Acceptance Criteria:
1. The processing function retrieves the correct document from cloud storage (e.g., S3) based on the job message.  
2. The system calls a cloud AI service (e.g., Amazon Textract) to process the document.  
3. The full, raw text content of the document is successfully extracted into a structured format (e.g., lines, pages).  
4. The system correctly handles and logs potential errors from the extraction service (e.g., a password-protected or unreadable file).

## Story 2.3: Extract Key Lease Terms using AI

**As the System, I want to analyze the extracted text using Natural Language Processing (NLP) to identify and extract key lease terms, so that a structured abstract can be created.**

### Acceptance Criteria:
1. The system sends the extracted text to an NLP service (e.g., Amazon Comprehend or other language model).  
2. The system successfully extracts the predefined key data points (e.g., Parties, Term, Rent) as outlined in FR3.  
3. The extracted data points are saved in a structured format (e.g., JSON) and associated with the document record in the database.  
4. The system gracefully handles cases where a specific key data point is not found in the text.

## Story 2.4: Generate AI-Powered Lease Summary

**As the System, I want to generate a concise summary of the lease's main provisions, so that users can quickly grasp the document's overall purpose.**

### Acceptance Criteria:
1. The system uses a language model to generate a multi-sentence summary of the lease.  
2. The generated summary is saved and associated with the document record in the database.  
3. The summary is objective and accurately reflects the core content of the document.  
4. After all processing steps (extraction, summarization) are complete, the document's status is updated to "Complete".

## Story 2.5: Display Lease Abstract and Summary

**As a logged-in User, I want to click a completed document in my dashboard and view its generated abstract and summary, so that I can review the key details of my lease.**

### Acceptance Criteria:
1. Documents with a "Complete" status on the dashboard are presented as clickable links.  
2. Clicking a link navigates the user to a new "Document Abstract View" page, unique to that document.  
3. This view displays the AI-generated summary prominently.  
4. The view also displays the full, structured abstract, with key terms clearly labeled and organized into logical categories.  
5. The user can easily navigate back to their main dashboard.

## Epic 2 Deliverables

Upon completion of Epic 2, the system will have:
- Asynchronous AI processing pipeline with queue management
- OCR and text extraction capabilities using AWS Textract
- NLP-powered key term extraction using AWS Comprehend
- AI-generated lease summaries
- User interface for viewing processed results
- Complete document processing workflow from upload to display

## Technical Dependencies

- AWS SQS for message queuing
- AWS Lambda for serverless processing functions
- Amazon Textract for OCR and document analysis
- Amazon Comprehend for NLP and entity extraction
- Database schema for storing extracted data and summaries
- Frontend components for displaying structured lease data

## Development Reference Materials

**Sample Files**: Use `/samples/` directory for development and testing:
- **Input Testing**: Process sample lease documents (`/samples/lease-documents/`) to validate OCR and text extraction
- **Output Validation**: Compare AI-generated abstracts against professional samples (`/samples/lease-abstracts/`)
- **Accuracy Benchmarking**: Ensure extracted data matches the quality standards demonstrated in sample abstracts

## Key Data Points to Extract (FR3)

- **Parties:** Landlord and Tenant information
- **Lease Term:** Effective date, expiration date, duration
- **Rent Schedule:** Base rent, escalation clauses, payment terms
- **Renewal Options:** Extension terms and conditions
- **Termination Clauses:** Early termination rights and conditions
- **Use Clauses:** Permitted and prohibited uses of the property
- **Assignment/Subletting:** Transfer rights and restrictions
