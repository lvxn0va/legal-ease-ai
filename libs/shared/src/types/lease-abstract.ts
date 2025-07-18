export interface ExtractedLeaseData {
  parties: {
    landlord: string;
    tenant: string;
  };
  leaseTerm: {
    effectiveDate: string;
    expirationDate: string;
    duration: string;
  };
  rentSchedule: {
    baseRent: string;
    escalationClauses: string[];
    paymentTerms: string;
  };
  renewalOptions: string[];
  terminationClauses: string[];
  useClauses: {
    permitted: string[];
    prohibited: string[];
  };
  assignmentSubletting: string;
}

export interface LeaseAbstract {
  id: string;
  documentId: string;
  extractedData: ExtractedLeaseData;
  summary: string;
  createdAt: string;
}
