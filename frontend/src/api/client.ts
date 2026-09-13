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
      timeout: 35000,
    });
    return res.data;
  } catch {
    const res = await api.post<RealtimeOcrResult>('/documents/extract-ocr', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 35000,
    });
    return res.data;
  }
}

export interface VerificationView {
  verificationId: number;
  documentId: number;
  documentType: string;
  extracted: ExtractedView;
  ocrStatus: string;
  validationStatus: string;
  tamperingScore: number;
  photoTampering: number;
  textTampering: number;
  stampTampering: number;
  elaHeatmapBase64?: string;
  faceMatchScore: number;
  faceMatchStatus: string;
  livenessStatus: string;
  blacklistStatus: string;
  riskScore: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  finalResult: 'CLEAR' | 'MANUAL_REVIEW' | 'REJECT';
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
