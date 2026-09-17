import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '/api',
  timeout: 120000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 || error.response?.status === 403) {
      // Stale or expired token after server restart
      if (localStorage.getItem('token') && !window.location.pathname.includes('/login')) {
        console.warn('Session expired or unauthorized (401/403). Clearing stale token.');
      }
    }
    return Promise.reject(error);
  }
);

// ---- Types ----
export interface LoginResponse {
  token: string;
  officerId: string;
  name: string;
  role: string;
}

export interface ExtractedView {
  name?: string;
  passportNumber?: string;
  nationality?: string;
  dateOfBirth?: string;
  gender?: string;
  issueDate?: string;
  expiryDate?: string;
  mrz?: string;
  ocrConfidence?: number;
  visualZone?: Record<string, unknown>;
  documentCategory?: string;
  documentSubtype?: string;
  applicableFields?: string[];
  applicableChecks?: string[];
}

export interface RealtimeOcrResult {
  mrz?: string | null;
  fields: {
    name?: string;
    passportNumber?: string;
    documentNumber?: string;
    nationality?: string;
    dateOfBirth?: string;
    gender?: string;
    issueDate?: string;
    expiryDate?: string;
    [key: string]: string | undefined;
  };
  fieldConfidences?: Record<string, number>;
  fieldStates?: Record<string, string>;
  visualZone?: {
    rawText?: string;
    detectedDocumentType?: string;
    documentCategory?: string;
    documentSubtype?: string;
    applicableFields?: string[];
    applicableChecks?: string[];
    issuingCountry?: string;
    fatherName?: string;
    address?: string;
    [key: string]: any;
  };
  confidence: number;
  mrzValid: boolean;
  mrzChecks?: Record<string, boolean>;
  notes: string[];
  detectedDocumentType?: string;
  documentCategory?: string;
  documentSubtype?: string;
  applicableFields?: string[];
  applicableChecks?: string[];
  issuingCountry?: string;
  extractionTimeMs?: number;
  qrDetected?: boolean;
  qrDecoded?: boolean;
  qrStatus?: string;
  qrSignatureVerified?: boolean;
  qrSignatureStatus?: string;
  qrOcrMatchStatus?: string;
  qrOcrDiscrepancies?: string[];
  barcodeDetected?: boolean;
  barcodeDecoded?: boolean;
  barcodeStatus?: string;
  barcodeType?: string;
  barcodeData?: any;
  mrzStatus?: string;
}

export async function extractRealtimeOcr(file: File): Promise<RealtimeOcrResult> {
  const form = new FormData();
  form.append('file', file);

  // Try direct /ai/ocr/extract proxy first for ultra-fast response, fallback to backend /api/documents/extract-ocr
  try {
    const res = await axios.post<RealtimeOcrResult>('/ai/ocr/extract', form, {
      timeout: 60000,
    });
    return res.data;
  } catch {
    const res = await api.post<RealtimeOcrResult>('/documents/extract-ocr', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
    return res.data;
  }
}

export interface FieldMismatchView {
  field: string;
  vizValue: string;
  mrzValue: string;
}

export interface VizMrzCrossValidationView {
  status: 'MATCH' | 'MISMATCH' | 'PARTIAL' | 'NOT_APPLICABLE' | 'INCONCLUSIVE';
  matchedFields: string[];
  mismatches: FieldMismatchView[];
  reasons: string[];
}

export interface ExpiryValidationView {
  status: 'VALID' | 'EXPIRED' | 'UNKNOWN' | 'NOT_APPLICABLE';
  expiryDate?: string;
  daysRemaining?: number;
  source?: string;
}

export interface RiskComponentView {
  code: string;
  label: string;
  points: number;
  triggered: boolean;
  reason: string;
}

export interface RiskAssessmentView {
  score: number;
  level: 'LOW' | 'MEDIUM' | 'HIGH';
  components: RiskComponentView[];
  triggeredComponents: RiskComponentView[];
  decision: 'CLEAR' | 'MANUAL_REVIEW' | 'REJECT';
  decisionBasis: string[];
  summary: string;
  securityOverrideTriggered: boolean;
  securityOverrideReason?: string;
}

export interface CandidateStampRegionView {
  bbox: number[];
  inkRatio: number;
  inkType: string;
  suspicious: boolean;
  anomalyReasons: string[];
}

export interface StampForgeryView {
  status: 'NOT_DETECTED' | 'SUSPICIOUS' | 'INCONCLUSIVE' | 'NOT_APPLICABLE' | 'NOT_PERFORMED';
  confidence: number;
  candidateStampRegions?: CandidateStampRegionView[];
  reasons: string[];
}

export interface MetadataAnalysisView {
  status: 'CLEAN' | 'SUSPICIOUS' | 'INCONCLUSIVE' | 'NOT_AVAILABLE';
  confidence: number;
  signals?: string[];
  metadata?: Record<string, unknown>;
  reasons: string[];
}

export interface VisaVerificationView {
  visaNumber?: string;
  visaType?: string;
  entryType?: string;
  stayDuration?: string;
  stayDurationValue?: number;
  stayDurationUnit?: string;
  issueDate?: string;
  expiryDate?: string;
  issuingCountry?: string;
  status: 'VALID' | 'INVALID' | 'PARTIAL' | 'UNKNOWN' | 'NOT_APPLICABLE';
  validationMessages?: string[];
}

export interface DrivingLicenceVerificationView {
  dlNumber?: string;
  holderName?: string;
  dateOfBirth?: string;
  issueDate?: string;
  expiryDate?: string;
  state?: string;
  issuingAuthority?: string;
  vehicleClasses?: string[];
  barcodeStatus?: string;
  status: 'VALID' | 'INVALID' | 'PARTIAL' | 'UNKNOWN' | 'NOT_APPLICABLE';
  validationMessages?: string[];
}

export interface NationalIdVerificationView {
  idNumber?: string;
  holderName?: string;
  dateOfBirth?: string;
  idSubtype?: string;
  issueDate?: string;
  expiryDate?: string;
  address?: string;
  gender?: string;
  nationality?: string;
  qrStatus?: string;
  barcodeStatus?: string;
  status: 'VALID' | 'INVALID' | 'PARTIAL' | 'UNKNOWN' | 'NOT_APPLICABLE';
  validationMessages?: string[];
}

export interface PermitVerificationView {
  permitNumber?: string;
  permitType?: string;
  holderName?: string;
  organizationName?: string;
  issueDate?: string;
  expiryDate?: string;
  issuingAuthority?: string;
  address?: string;
  vehicleAssetIdentifier?: string;
  permitCategory?: string;
  referenceNumber?: string;
  status: 'VALID' | 'INVALID' | 'PARTIAL' | 'UNKNOWN' | 'NOT_APPLICABLE';
  validationMessages?: string[];
}

export interface CrossDocumentCorrelationView {
  status: 'MATCH' | 'MISMATCH' | 'NOT_ENOUGH_EVIDENCE';
  previousDocumentId: number;
  previousDocumentType: string;
  matchedFields: number;
  conflictingFields: number;
  availableFields: number;
  matchedFieldsList: string[];
  conflictingFieldsList: string[];
}

export interface VerificationView {
  verificationId: number;
  documentId: number;
  documentType: string;
  selectedType?: string;
  detectedType?: string;
  detectionConfidence?: number;
  extracted: ExtractedView;
  ocrStatus: string;
  validationStatus: string;
  tamperingScore: number;
  photoTampering: number;
  textTampering: number;
  stampTampering: number;
  photoForgeryStatus?: string;
  photoForgeryConfidence?: number;
  photoForgeryReasons?: string[];
  textManipulationStatus?: string;
  textManipulationConfidence?: number;
  textManipulationFields?: string[];
  textManipulationReasons?: string[];
  stampForgeryStatus?: string;
  stampForgeryConfidence?: number;
  stampForgeryReasons?: string[];
  metadataStatus?: string;
  metadataConfidence?: number;
  metadataReasons?: string[];
  metadataAnalysis?: MetadataAnalysisView;
  vizMrzCrossValidation?: VizMrzCrossValidationView;
  expiryValidation?: ExpiryValidationView;
  visaVerification?: VisaVerificationView;
  drivingLicenceVerification?: DrivingLicenceVerificationView;
  nationalIdVerification?: NationalIdVerificationView;
  permitVerification?: PermitVerificationView;

  riskAssessment?: RiskAssessmentView;
  crossDocumentCorrelations?: CrossDocumentCorrelationView[];

  elaHeatmapBase64?: string;
  faceMatchScore: number;
  faceMatchStatus: string;
  livenessStatus: string;
  blacklistStatus: string;
  storedIdentityMatchStatus?: string;
  storedIdentityMatchDetail?: string;
  riskScore: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  finalResult: 'CLEAR' | 'MANUAL_REVIEW' | 'REJECT';
  securityOverrideTriggered?: boolean;
  securityOverrideReason?: string;
  reasons: string[];
  recordHash: string;
  blockchainTxId?: string;
  createdAt: string;
}

export interface BlacklistEntry {
  id: number;
  documentNumber: string;
  documentType: string;
  name: string;
  dateOfBirth: string;
  reason: string;
  status: string;
  createdAt?: string;
}

export interface AuditLogEntry {
  id: number;
  verificationId: number;
  userId: number;
  action: string;
  ipAddress: string;
  recordHash: string;
  blockchainTxId: string;
  integrityStatus: string;
  timestamp: string;
}

// Redirect to login on auth failure; propagate every other error untouched
// so the UI reflects the real backend/AI-service state instead of a canned
// mock response.
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);
