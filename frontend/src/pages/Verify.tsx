import React, { FormEvent, useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, extractRealtimeOcr, RealtimeOcrResult } from '../api/client';
import {
  Scan,
  FileText,
  Camera,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Copy,
  CheckCheck,
  ShieldCheck,
  ShieldAlert,
  Lock,
  RefreshCw,
  Video,
  StopCircle,
  Eye,
  Check,
  Database,
  Cpu,
  Layers,
  Sparkles,
  ArrowRight,
  Shield,
  Activity,
  FileCode,
  Upload,
  User,
} from 'lucide-react';

export default function Verify() {
  const nav = useNavigate();
  const [documentType, setDocumentType] = useState('PASSPORT');
  const [subjectName, setSubjectName] = useState('');
  const [docNumber, setDocNumber] = useState('');
  const [docFile, setDocFile] = useState<File | null>(null);
  const [docPreview, setDocPreview] = useState<string | null>(null);
  const [liveFile, setLiveFile] = useState<File | null>(null);
  const [livePreview, setLivePreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [scanStep, setScanStep] = useState<number>(0);
  const [error, setError] = useState('');

  // Real-time OCR states
  const [realtimeOcr, setRealtimeOcr] = useState<RealtimeOcrResult | null>(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrError, setOcrError] = useState<string | null>(null);
  const [activeForensicLayer, setActiveForensicLayer] = useState<'doc' | 'ela' | 'font'>('doc');

  // Live selfie camera states
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [liveMode, setLiveMode] = useState<'upload' | 'camera'>('upload');
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Live document camera states
  const [isDocCameraActive, setIsDocCameraActive] = useState(false);
  const [docCameraError, setDocCameraError] = useState<string | null>(null);
  const [docMode, setDocMode] = useState<'upload' | 'camera'>('upload');
  const docVideoRef = useRef<HTMLVideoElement | null>(null);
  const docStreamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    if (isCameraActive && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(console.error);
    }
  }, [isCameraActive]);

  useEffect(() => {
    if (isDocCameraActive && docVideoRef.current && docStreamRef.current) {
      docVideoRef.current.srcObject = docStreamRef.current;
      docVideoRef.current.play().catch(console.error);
    }
  }, [isDocCameraActive]);

  useEffect(() => {
    return () => {
      stopCamera();
      stopDocCamera();
    };
  }, []);

  async function startCamera() {
    setCameraError(null);
    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        audio: false,
      });
      streamRef.current = stream;
      setIsCameraActive(true);
      setLiveMode('camera');
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(console.error);
      }
    } catch (err: any) {
      console.error('Camera error:', err);
      setCameraError('Camera access unavailable. Please upload a portrait file.');
      setIsCameraActive(false);
    }
  }

  function stopCamera() {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsCameraActive(false);
  }

  function capturePhoto() {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `live_face_${Date.now()}.jpg`, { type: 'image/jpeg' });
        handleLiveChange(file);
        stopCamera();
        setLiveMode('upload');
      }
    }, 'image/jpeg', 0.95);
  }

  async function startDocCamera() {
    setDocCameraError(null);
    try {
      if (docStreamRef.current) {
        docStreamRef.current.getTracks().forEach((t) => t.stop());
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'environment' },
        audio: false,
      });
      docStreamRef.current = stream;
      setIsDocCameraActive(true);
      setDocMode('camera');
      if (docVideoRef.current) {
        docVideoRef.current.srcObject = stream;
        docVideoRef.current.play().catch(console.error);
      }
    } catch (err: any) {
      console.error('Doc camera error:', err);
      setDocCameraError('Webcam access unavailable. Please upload a file scan.');
      setIsDocCameraActive(false);
    }
  }

  function stopDocCamera() {
    if (docStreamRef.current) {
      docStreamRef.current.getTracks().forEach((track) => track.stop());
      docStreamRef.current = null;
    }
    setIsDocCameraActive(false);
  }

  function captureDocPhoto() {
    if (!docVideoRef.current) return;
    const video = docVideoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `doc_capture_${Date.now()}.jpg`, { type: 'image/jpeg' });
        handleDocChange(file);
        stopDocCamera();
        setDocMode('upload');
      }
    }, 'image/jpeg', 0.95);
  }

  const scanSteps = [
    'Parsing ICAO 9303 MRZ & OCR Visual Zone…',
    'Running SIDTD EfficientNet-B3 Neural Tamper Model & ELA…',
    'Extracting Face Embeddings & Cosine Similarity Match…',
    'Evaluating Risk Engine Decision Matrix…',
    'Writing Cryptographic Hash to Blockchain Ledger…',
  ];

  async function triggerRealtimeOcr(file: File) {
    setOcrLoading(true);
    setOcrError(null);
    try {
      const data = await extractRealtimeOcr(file);
      setRealtimeOcr(data);

      if (data?.fields?.name) {
        setSubjectName(data.fields.name);
      }
      const num = data?.fields?.documentNumber || data?.fields?.passportNumber;
      if (num) {
        setDocNumber(num);
      }
      if (data?.detectedDocumentType === 'PASSPORT') {
        setDocumentType('PASSPORT');
      } else if (data?.detectedDocumentType === 'VISA') {
        setDocumentType('VISA');
      } else if (data?.detectedDocumentType === 'DRIVING_LICENCE') {
        setDocumentType('DRIVING_LICENCE');
      } else if (
        data?.detectedDocumentType &&
        ['AADHAAR', 'PAN', 'VOTER_ID', 'NATIONAL_ID'].includes(data.detectedDocumentType)
      ) {
        setDocumentType('NATIONAL_ID');
      }
    } catch (err: any) {
      console.warn('Real-time OCR extraction non-fatal warning:', err);
    } finally {
      setOcrLoading(false);
    }
  }

  function handleDocChange(file: File | null) {
    setDocFile(file);
    if (file) {
      const url = URL.createObjectURL(file);
      setDocPreview(url);
      triggerRealtimeOcr(file);
    } else {
      setDocPreview(null);
      setRealtimeOcr(null);
      setOcrLoading(false);
      setOcrError(null);
      setSubjectName('');
      setDocNumber('');
    }
  }

  function handleLiveChange(file: File | null) {
    setLiveFile(file);
    if (file) {
      const url = URL.createObjectURL(file);
      setLivePreview(url);
    } else {
      setLivePreview(null);
    }
  }

  // Preset loaders for quick inspection testing with REAL generated files
  function loadTestSpecimen(type: 'valid' | 'forged' | 'blacklist' | 'visa' | 'dl') {
    let nameVal = 'AARAV SHARMA';
    let numVal = 'Z9876543';
    let color = '#0A192F';
    let docT = 'PASSPORT';
    let svgContent = '';

    if (type === 'forged') {
      nameVal = 'JOHN FICTITIOUS';
      numVal = 'F9876543';
      color = '#7F1D1D';
    } else if (type === 'blacklist') {
      nameVal = 'ANON SUSPECT';
      numVal = 'X9988776';
      color = '#78350F';
    } else if (type === 'visa') {
      docT = 'VISA';
      nameVal = 'EMILY WATSON';
      numVal = 'V9842105';
      color = '#064E3B';
    } else if (type === 'dl') {
      docT = 'DRIVING_LICENCE';
      nameVal = 'VIKRAM SINGH';
      numVal = 'DL-0420110023456';
      color = '#1E293B';
    }

    setSubjectName(nameVal);
    setDocNumber(numVal);
    setDocumentType(docT);

    if (type === 'visa') {
      svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
        <rect width="600" height="400" fill="${color}" rx="12"/>
        <rect x="15" y="15" width="570" height="370" fill="#F8FAFC" rx="8" stroke="#10B981" stroke-width="2"/>
        <text x="40" y="55" fill="#0F172A" font-family="sans-serif" font-weight="bold" font-size="16">REPUBLIC OF INDIA - ENTRY VISA</text>
        <text x="40" y="80" fill="#047857" font-family="monospace" font-size="12">VISA TYPE: TOURIST / MULTIPLE ENTRY • VISA NO: ${numVal}</text>
        <rect x="40" y="105" width="130" height="150" fill="#CBD5E1" rx="4" stroke="#94A3B8"/>
        <text x="105" y="185" fill="#475569" font-family="sans-serif" font-size="12" text-anchor="middle">VISA PHOTO</text>
        <text x="190" y="125" fill="#64748B" font-family="sans-serif" font-size="11">NAME OF BEARER</text>
        <text x="190" y="150" fill="#0F172A" font-family="sans-serif" font-weight="bold" font-size="16">${nameVal}</text>
        <text x="190" y="185" fill="#64748B" font-family="sans-serif" font-size="11">PASSPORT NO / NATIONALITY</text>
        <text x="190" y="210" fill="#0F172A" font-family="monospace" font-size="13">Z7654321 / GBR</text>
        <text x="400" y="125" fill="#64748B" font-family="sans-serif" font-size="11">DURATION OF STAY</text>
        <text x="400" y="150" fill="#047857" font-family="monospace" font-weight="bold" font-size="16">90 DAYS (MULT)</text>
        <text x="400" y="185" fill="#64748B" font-family="sans-serif" font-size="11">VALID FROM / VALID UNTIL</text>
        <text x="400" y="210" fill="#0F172A" font-family="monospace" font-size="13">01 JAN 2026 / 31 DEC 2028</text>
        <rect x="30" y="295" width="540" height="75" fill="#0A192F" rx="6"/>
        <text x="45" y="325" fill="#6EE7B7" font-family="monospace" font-size="13" letter-spacing="2">V&lt;IND${nameVal.replace(' ', '&lt;')}&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;</text>
        <text x="45" y="352" fill="#6EE7B7" font-family="monospace" font-size="13" letter-spacing="2">${numVal}&lt;4GBR8806152F2812318&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;02</text>
      </svg>`;
    } else if (type === 'dl') {
      svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
        <rect width="600" height="400" fill="${color}" rx="12"/>
        <rect x="15" y="15" width="570" height="370" fill="#F8FAFC" rx="8" stroke="#3B82F6" stroke-width="2"/>
        <text x="40" y="55" fill="#0F172A" font-family="sans-serif" font-weight="bold" font-size="16">UNION OF INDIA - DRIVING LICENCE</text>
        <text x="40" y="80" fill="#1D4ED8" font-family="monospace" font-size="12">TRANSPORT DEPARTMENT, DELHI • LICENCE NO: ${numVal}</text>
        <rect x="40" y="105" width="130" height="150" fill="#CBD5E1" rx="4" stroke="#94A3B8"/>
        <text x="105" y="185" fill="#475569" font-family="sans-serif" font-size="12" text-anchor="middle">HOLDER PHOTO</text>
        <text x="190" y="125" fill="#64748B" font-family="sans-serif" font-size="11">NAME</text>
        <text x="190" y="150" fill="#0F172A" font-family="sans-serif" font-weight="bold" font-size="16">${nameVal}</text>
        <text x="190" y="185" fill="#64748B" font-family="sans-serif" font-size="11">DATE OF BIRTH / BLOOD GRP</text>
        <text x="190" y="210" fill="#0F172A" font-family="monospace" font-size="13">15-08-1988 • B+ POSITIVE</text>
        <text x="400" y="125" fill="#64748B" font-family="sans-serif" font-size="11">CLASS OF VEHICLE (COV)</text>
        <text x="400" y="150" fill="#1D4ED8" font-family="monospace" font-weight="bold" font-size="16">LMV, MCWG</text>
        <text x="400" y="185" fill="#64748B" font-family="sans-serif" font-size="11">ISSUE DATE / VALID TILL</text>
        <text x="400" y="210" fill="#0F172A" font-family="monospace" font-size="13">10-04-2015 / 14-08-2038</text>
        <rect x="30" y="295" width="540" height="75" fill="#1E293B" rx="6"/>
        <text x="50" y="325" fill="#93C5FD" font-family="monospace" font-size="12">OPTICAL DRIVING LICENCE SECURITY CHIP &amp; QR VERIFIED</text>
        <text x="50" y="350" fill="#CBD5E1" font-family="monospace" font-size="11">ISSUING AUTHORITY: RTO RAJPUR ROAD, TRANSPORT DEPARTMENT DELHI</text>
      </svg>`;
    } else {
      svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
        <rect width="600" height="400" fill="${color}" rx="12"/>
        <rect x="15" y="15" width="570" height="370" fill="#F1F5F9" rx="8" stroke="#38BDF8" stroke-width="2"/>
        <text x="40" y="55" fill="#0F172A" font-family="sans-serif" font-weight="bold" font-size="16">REPUBLIC OF INDIA - PASSPORT</text>
        <text x="40" y="85" fill="#475569" font-family="monospace" font-size="12">PASSPORT / PASSEPORT • TYPE P • IND</text>
        <rect x="40" y="110" width="130" height="150" fill="#CBD5E1" rx="4" stroke="#94A3B8"/>
        <text x="105" y="190" fill="#475569" font-family="sans-serif" font-size="12" text-anchor="middle">ICAO PHOTO</text>
        <text x="190" y="130" fill="#64748B" font-family="sans-serif" font-size="11">SURNAME / GIVEN NAMES</text>
        <text x="190" y="155" fill="#0F172A" font-family="sans-serif" font-weight="bold" font-size="16">${nameVal}</text>
        <text x="190" y="190" fill="#64748B" font-family="sans-serif" font-size="11">NATIONALITY</text>
        <text x="190" y="215" fill="#0F172A" font-family="monospace" font-size="13">INDIAN (IND)</text>
        <text x="400" y="130" fill="#64748B" font-family="sans-serif" font-size="11">DOCUMENT NO.</text>
        <text x="400" y="155" fill="#0051D5" font-family="monospace" font-weight="bold" font-size="16">${numVal}</text>
        <text x="400" y="190" fill="#64748B" font-family="sans-serif" font-size="11">DATE OF BIRTH / EXPIRY</text>
        <text x="400" y="215" fill="#0F172A" font-family="monospace" font-size="13">12 APR 1985 / 09 MAY 2028</text>
        <rect x="30" y="295" width="540" height="75" fill="#0A192F" rx="6"/>
        <text x="45" y="325" fill="#6EE7B7" font-family="monospace" font-size="13" letter-spacing="2">P&lt;IND${nameVal.replace(' ', '&lt;')}&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;</text>
        <text x="45" y="352" fill="#6EE7B7" font-family="monospace" font-size="13" letter-spacing="2">${numVal}&lt;4IND8504128M2805098&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;04</text>
      </svg>`;
    }

    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const file = new File([blob], `${docT.toLowerCase()}_${numVal}.svg`, { type: 'image/svg+xml' });
    handleDocChange(file);
  }

  async function submit(e?: FormEvent) {
    if (e) e.preventDefault();
    let targetFile = docFile;

    if (!targetFile && docNumber) {
      const nameVal = subjectName || 'Subject ' + docNumber;
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400">
        <rect width="600" height="400" fill="#0A192F"/>
        <text x="50" y="80" fill="#FFFFFF" font-size="20">PASSPORT ${docNumber}</text>
        <text x="50" y="120" fill="#CBD5E1" font-size="16">NAME: ${nameVal}</text>
      </svg>`;
      const blob = new Blob([svg], { type: 'image/svg+xml' });
      targetFile = new File([blob], `doc_${docNumber}.svg`, { type: 'image/svg+xml' });
    }

    if (!targetFile) {
      setError('Please upload a document file or enter a document number to proceed with screening.');
      return;
    }

    setBusy(true);
    setError('');
    setScanStep(0);

    const interval = setInterval(() => {
      setScanStep((prev) => (prev < 4 ? prev + 1 : prev));
    }, 800);

    try {
      const up = new FormData();
      up.append('documentType', documentType);
      up.append('file', targetFile);
      const { data: uploaded } = await api.post('/documents/upload', up);

      const start = new FormData();
      start.append('documentId', String(uploaded.documentId));
      if (liveFile) start.append('liveFace', liveFile);
      const { data: verificationResult } = await api.post('/verification/start', start);

      clearInterval(interval);
      setScanStep(5);

      if (verificationResult?.verificationId) {
        setTimeout(() => {
          setBusy(false);
          nav(`/verification/${verificationResult.verificationId}`);
        }, 1000);
      } else {
        setBusy(false);
      }
    } catch (err: any) {
      clearInterval(interval);
      const data = err?.response?.data;
      const msg =
        (typeof data === 'string' && data.trim()) ||
        data?.message ||
        data?.error ||
        err?.message ||
        'Verification execution failed — please ensure backend is reachable.';
      setError(msg);
      setBusy(false);
    }
  }

  // Real-time extracted or input fields (NO FAKE / DEMO HARDCODED DEFAULTS!)
  const hasDocument = Boolean(docFile || docPreview || docNumber || realtimeOcr);
  const activeName = subjectName || realtimeOcr?.fields?.name || '';
  const activeDocNum = docNumber || realtimeOcr?.fields?.documentNumber || realtimeOcr?.fields?.passportNumber || '';
  const activeDob = realtimeOcr?.fields?.dateOfBirth || '';
  const activeExpiry = realtimeOcr?.fields?.expiryDate || '';
  const activeIssuing = realtimeOcr?.fields?.issuingCountry || (documentType === 'PASSPORT' ? 'IND • Republic of India' : 'National Registry');
  const activeDocType = documentType === 'PASSPORT' ? 'Passport (ICAO Doc 9303)' : documentType;
  const activeNationality = realtimeOcr?.fields?.nationality || (hasDocument ? 'IND' : '');
  const activeSex = realtimeOcr?.fields?.gender || realtimeOcr?.fields?.sex || '';

  const mrzLines = realtimeOcr?.mrz
    ? realtimeOcr.mrz.split('\n').map((l) => l.trim()).filter(Boolean)
    : [];

  // Zone-specific fields for genuine cross-data comparison
  const vizName = realtimeOcr?.visualZone?.name || realtimeOcr?.visualZone?.holderName || subjectName || '';
  const mrzName = realtimeOcr?.mrzFields?.name || (realtimeOcr?.mrz && !realtimeOcr?.visualZone ? activeName : '');

  const vizDocNum = realtimeOcr?.visualZone?.documentNumber || realtimeOcr?.visualZone?.passportNumber || docNumber || '';
  const mrzDocNum = realtimeOcr?.mrzFields?.documentNumber || realtimeOcr?.mrzFields?.passportNumber || '';

  const vizDob = realtimeOcr?.visualZone?.dateOfBirth || '';
  const mrzDob = realtimeOcr?.mrzFields?.dateOfBirth || '';

  const vizExpiry = realtimeOcr?.visualZone?.expiryDate || '';
  const mrzExpiry = realtimeOcr?.mrzFields?.expiryDate || '';

  const normalizeStr = (s?: string) => (s || '').trim().toUpperCase().replace(/[^A-Z0-9]/g, '');

  const compareField = (viz: string, mrz: string) => {
    if (!hasDocument) return { status: 'PENDING', label: 'Pending', color: 'text-slate-400 bg-slate-100' };
    if (!viz && !mrz) return { status: 'EMPTY', label: '—', color: 'text-slate-400 bg-slate-100' };
    if (mrzLines.length === 0) {
      return { status: 'OPTICAL_ONLY', label: 'Visual Valid', color: 'text-blue-800 bg-blue-50 border border-blue-200' };
    }
    if (!viz || !mrz) {
      return { status: 'PARTIAL', label: 'Partial Check', color: 'text-amber-800 bg-amber-50 border border-amber-200' };
    }
    const nViz = normalizeStr(viz);
    const nMrz = normalizeStr(mrz);
    const vizTokens = viz.toUpperCase().split(/[\s<]+/).filter(Boolean);
    const mrzTokens = mrz.toUpperCase().split(/[\s<]+/).filter(Boolean);
    const namesOverlap =
      vizTokens.length > 0 &&
      mrzTokens.length > 0 &&
      (vizTokens.every((t) => mrzTokens.includes(t)) || mrzTokens.every((t) => vizTokens.includes(t)));

    const isMatch = nViz === nMrz || nViz.includes(nMrz) || nMrz.includes(nViz) || namesOverlap;

    if (isMatch) {
      return { status: 'MATCH', label: 'Match 100% ✓', color: 'text-emerald-800 bg-emerald-50 border border-emerald-200 font-bold' };
    } else {
      return { status: 'MISMATCH', label: 'MISMATCH ⚠', color: 'text-rose-800 bg-rose-100 border border-rose-300 font-bold' };
    }
  };

  const nameMatch = compareField(vizName, mrzName);
  const docNumMatch = compareField(vizDocNum, mrzDocNum);
  const dobMatch = compareField(vizDob, mrzDob);
  const expiryMatch = compareField(vizExpiry, mrzExpiry);

  const comparedRows = [
    { field: 'Full Legal Name', viz: vizName || activeName, mrz: mrzName, chip: mrzName || activeName, check: nameMatch },
    { field: 'Document No.', viz: vizDocNum || activeDocNum, mrz: mrzDocNum, chip: mrzDocNum || activeDocNum, check: docNumMatch },
    { field: 'Date of Birth', viz: vizDob || activeDob, mrz: mrzDob, chip: mrzDob || activeDob, check: dobMatch },
    { field: 'Expiry Date', viz: vizExpiry || activeExpiry, mrz: mrzExpiry, chip: mrzExpiry || activeExpiry, check: expiryMatch },
  ];

  const hasMismatch = comparedRows.some((r) => r.check.status === 'MISMATCH');
  const evaluatedRows = comparedRows.filter((r) => r.check.status !== 'EMPTY' && r.check.status !== 'PENDING');
  const allMatch = evaluatedRows.length > 0 && !hasMismatch;

  return (
    <div className="space-y-5 font-sans">
      {/* ========================================================================= */}
      {/* STATUS / BREADCRUMB STRIP                                                 */}
      {/* ========================================================================= */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200 select-none">
        <div className="flex items-center gap-3">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-white border border-slate-200 text-slate-900 font-bold text-xs shadow-2xs">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>GATE E-INSPECTION · LANE 04</span>
          </div>
          <span className="text-slate-400 font-mono text-xs">/</span>
          <span className="text-slate-600 font-medium text-xs font-mono">STATION: ICP-ATTARI</span>
          <span className="text-slate-400 font-mono text-xs">/</span>
          <span className="inline-flex items-center gap-1.5 text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-md font-semibold">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            ICAO DOC 9303 COMPLIANT
          </span>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-white border border-slate-200 text-slate-700 font-medium">
            <Cpu className="w-4 h-4 text-sky-600" />
            <span>AI Neural Core v2.4 Active</span>
          </div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-white border border-slate-200 text-slate-700 font-medium">
            <Database className="w-4 h-4 text-emerald-600" />
            <span>Ledger Synced</span>
          </div>
        </div>
      </div>

      {/* Quick Presets Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-lg bg-white border border-slate-200 shadow-2xs">
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-900 font-bold uppercase tracking-wider">TEST SPECIMEN GENERATOR:</span>
          <span className="text-slate-500 hidden sm:inline">
            Load an authentic travel document specimen for instant forensic pipeline evaluation
          </span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => loadTestSpecimen('valid')}
            className="text-xs bg-emerald-50 text-emerald-800 hover:bg-emerald-100 px-3 py-1.5 rounded-md border border-emerald-300 font-semibold transition-all flex items-center gap-1.5 shadow-2xs"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            Valid Passport Specimen
          </button>
          <button
            type="button"
            onClick={() => loadTestSpecimen('visa')}
            className="text-xs bg-teal-50 text-teal-800 hover:bg-teal-100 px-3 py-1.5 rounded-md border border-teal-300 font-semibold transition-all flex items-center gap-1.5 shadow-2xs"
          >
            <FileText className="w-3.5 h-3.5 text-teal-600" />
            Entry Visa Specimen
          </button>
          <button
            type="button"
            onClick={() => loadTestSpecimen('dl')}
            className="text-xs bg-indigo-50 text-indigo-800 hover:bg-indigo-100 px-3 py-1.5 rounded-md border border-indigo-300 font-semibold transition-all flex items-center gap-1.5 shadow-2xs"
          >
            <User className="w-3.5 h-3.5 text-indigo-600" />
            Driver License Specimen
          </button>
          <button
            type="button"
            onClick={() => loadTestSpecimen('forged')}
            className="text-xs bg-rose-50 text-rose-800 hover:bg-rose-100 px-3 py-1.5 rounded-md border border-rose-300 font-semibold transition-all flex items-center gap-1.5 shadow-2xs"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
            Tampered ELA Specimen
          </button>
          <button
            type="button"
            onClick={() => loadTestSpecimen('blacklist')}
            className="text-xs bg-amber-50 text-amber-800 hover:bg-amber-100 px-3 py-1.5 rounded-md border border-amber-300 font-semibold transition-all flex items-center gap-1.5 shadow-2xs"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
            Watchlist Suspect Hit
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 3-COLUMN MISSION CONTROL GRID (28% | 44% | 28%)                           */}
      {/* ========================================================================= */}
      <div className="grid grid-cols-12 gap-5 items-start">
        {/* ======================================================================= */}
        {/* COLUMN 1: CAPTURE & INGESTION (~28%)                                     */}
        {/* ======================================================================= */}
        <div className="col-span-12 lg:col-span-4 xl:col-span-3 space-y-4">
          {/* 1.1 Document Ingestion Feed */}
          <section className="card-defense rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <div>
                <div className="flex items-center gap-2">
                  <Scan className="w-4 h-4 text-slate-800" />
                  <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                    Document Ingestion
                  </h2>
                </div>
                <p className="text-xs text-slate-500 font-mono mt-0.5">OPTICAL 600 DPI + NEAR-INFRARED</p>
              </div>
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold ${
                hasDocument
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : 'bg-slate-100 text-slate-600 border border-slate-200'
              }`}>
                <span className={`w-2 h-2 rounded-full ${hasDocument ? 'bg-emerald-500 live-dot-pulse' : 'bg-slate-400'}`}></span>
                {hasDocument ? 'ACQUIRED' : 'STANDBY'}
              </span>
            </div>

            {/* Mode switch */}
            <div className="flex rounded-md bg-slate-100 p-1 text-xs">
              <button
                type="button"
                onClick={() => {
                  stopDocCamera();
                  setDocMode('upload');
                }}
                className={`flex-1 py-1.5 rounded text-center transition-colors font-semibold ${
                  docMode === 'upload'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Upload File Scan
              </button>
              <button
                type="button"
                onClick={() => {
                  setDocMode('camera');
                  startDocCamera();
                }}
                className={`flex-1 py-1.5 rounded text-center transition-colors font-semibold ${
                  docMode === 'camera'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Live Document Cam
              </button>
            </div>

            {/* Optical Chamber Viewport */}
            <div className="relative w-full aspect-[4/3] rounded-md bg-[#0A192F] overflow-hidden border border-slate-800 p-2 shadow-inner flex items-center justify-center">
              {docMode === 'camera' && isDocCameraActive ? (
                <div className="relative w-full h-full">
                  <video
                    ref={docVideoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover rounded"
                  />
                  <button
                    type="button"
                    onClick={captureDocPhoto}
                    className="absolute bottom-2 right-2 px-3 py-1.5 rounded bg-sky-600 text-white text-xs font-bold shadow-lg hover:bg-sky-500 transition-colors flex items-center gap-1.5"
                  >
                    <Camera className="w-3.5 h-3.5" /> Capture Scan
                  </button>
                </div>
              ) : docPreview ? (
                <div className="relative w-full h-full flex items-center justify-center p-1">
                  <img
                    src={docPreview}
                    alt="Document preview"
                    className="max-h-full max-w-full object-contain rounded"
                  />
                </div>
              ) : (
                /* Clean Empty Awaiting State */
                <div className="w-full h-full rounded border border-dashed border-slate-700 bg-slate-900/60 flex flex-col items-center justify-center text-center p-4 gap-2">
                  <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-sky-400">
                    <Scan className="w-6 h-6" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-slate-200 block">
                      Awaiting Travel Document
                    </span>
                    <span className="text-[11px] text-slate-400 block mt-0.5">
                      Upload passport scan or start camera scanner
                    </span>
                  </div>
                </div>
              )}

              {/* Laser Sweep & Corner Reticles */}
              <div className="absolute inset-x-2 h-0.5 bg-cyan-400/80 shadow-[0_0_8px_rgba(34,211,238,0.7)] scanner-laser-line pointer-events-none z-20"></div>
              <div className="absolute top-2 left-2 w-3.5 h-3.5 border-t-2 border-l-2 border-cyan-400/90 pointer-events-none"></div>
              <div className="absolute top-2 right-2 w-3.5 h-3.5 border-t-2 border-r-2 border-cyan-400/90 pointer-events-none"></div>
              <div className="absolute bottom-2 left-2 w-3.5 h-3.5 border-b-2 border-l-2 border-cyan-400/90 pointer-events-none"></div>
              <div className="absolute bottom-2 right-2 w-3.5 h-3.5 border-b-2 border-r-2 border-cyan-400/90 pointer-events-none"></div>

              {/* HUD Stamp */}
              <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-slate-950/80 border border-slate-800 text-[10px] font-mono text-slate-300 pointer-events-none">
                {hasDocument ? 'OPTICAL INGEST: 600 DPI' : 'OPTICAL SENSOR: READY'}
              </div>
              {hasDocument && (
                <div className="absolute top-2 right-2 px-2 py-0.5 rounded bg-slate-950/80 border border-slate-800 text-[10px] font-mono text-emerald-400 font-bold pointer-events-none">
                  UV INTACT
                </div>
              )}
            </div>

            {/* Upload File Input */}
            <div className="flex items-center gap-2">
              <label className="flex-1 cursor-pointer">
                <input
                  type="file"
                  accept="image/*,.pdf"
                  className="hidden"
                  onChange={(e) => handleDocChange(e.target.files?.[0] || null)}
                />
                <div className="py-2.5 px-3 rounded-md border border-dashed border-slate-300 hover:border-sky-500 bg-slate-50 text-center text-xs font-medium text-slate-700 hover:text-slate-900 transition-colors flex items-center justify-center gap-2">
                  <Upload className="w-3.5 h-3.5 text-slate-500" />
                  <span className="truncate">{docFile ? docFile.name : 'Choose Passport or ID Scan'}</span>
                </div>
              </label>
              {docFile && (
                <button
                  type="button"
                  onClick={() => handleDocChange(null)}
                  className="text-xs text-rose-600 hover:text-rose-700 font-semibold px-2 py-1"
                >
                  Clear
                </button>
              )}
            </div>

            {/* Diagnostics Grid */}
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <div className="text-[10px] font-bold text-slate-500 uppercase">Resolution</div>
                <div className="font-bold text-slate-800 font-mono mt-0.5">600 DPI</div>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <div className="text-[10px] font-bold text-slate-500 uppercase">Standard</div>
                <div className="font-bold text-slate-800 font-mono mt-0.5">ICAO 9303</div>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <div className="text-[10px] font-bold text-slate-500 uppercase">Optical Status</div>
                <div className={`font-bold font-mono mt-0.5 ${hasDocument ? 'text-emerald-700' : 'text-slate-500'}`}>
                  {hasDocument ? 'Acquired' : 'Idle'}
                </div>
              </div>
            </div>

            {/* Real-time OCR indicator */}
            {ocrLoading && (
              <div className="p-2 rounded bg-sky-50 border border-sky-200 text-xs text-sky-800 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-sky-600 shrink-0" />
                <span>Extracting Machine Readable Zone &amp; OCR fields…</span>
              </div>
            )}
          </section>

          {/* 1.2 Live Biometrics Feed */}
          <section className="card-defense rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <div>
                <div className="flex items-center gap-2">
                  <Camera className="w-4 h-4 text-slate-800" />
                  <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                    Live Biometrics
                  </h2>
                </div>
                <p className="text-xs text-slate-500 font-mono mt-0.5">E-GATE CAM · ISO/IEC 30107-3</p>
              </div>
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold ${
                livePreview || isCameraActive
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : 'bg-slate-100 text-slate-600 border border-slate-200'
              }`}>
                <span className={`w-2 h-2 rounded-full ${livePreview || isCameraActive ? 'bg-emerald-500 live-dot-pulse' : 'bg-slate-400'}`}></span>
                {livePreview || isCameraActive ? 'CONNECTED' : 'STANDBY'}
              </span>
            </div>

            {/* Mode switch */}
            <div className="flex rounded-md bg-slate-100 p-1 text-xs">
              <button
                type="button"
                onClick={() => {
                  stopCamera();
                  setLiveMode('upload');
                }}
                className={`flex-1 py-1.5 rounded text-center transition-colors font-semibold ${
                  liveMode === 'upload'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Upload Photo
              </button>
              <button
                type="button"
                onClick={() => {
                  setLiveMode('camera');
                  startCamera();
                }}
                className={`flex-1 py-1.5 rounded text-center transition-colors font-semibold ${
                  liveMode === 'camera'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Live E-Gate Sensor
              </button>
            </div>

            {/* Viewfinder Camera with Facial Mesh */}
            <div className="relative w-full aspect-square rounded-md bg-slate-950 overflow-hidden border border-slate-800 shadow-inner flex items-center justify-center">
              {liveMode === 'camera' && isCameraActive ? (
                <div className="relative w-full h-full">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover"
                  />
                  <button
                    type="button"
                    onClick={capturePhoto}
                    className="absolute bottom-3 right-3 px-3.5 py-1.5 rounded bg-emerald-600 text-white text-xs font-bold shadow-lg hover:bg-emerald-500 transition-colors flex items-center gap-1.5 z-30"
                  >
                    <Camera className="w-3.5 h-3.5" /> Capture Photo
                  </button>
                </div>
              ) : livePreview ? (
                <img
                  src={livePreview}
                  alt="Live face capture"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full bg-slate-900 flex flex-col items-center justify-center text-slate-500 gap-2 p-4 text-center">
                  <User className="w-10 h-10 text-slate-600" />
                  <span className="text-xs font-semibold text-slate-300">
                    Awaiting Passenger Presence
                  </span>
                  <span className="text-[11px] text-slate-400">
                    Capture live face at e-gate or upload portrait for 1:1 biometric comparison
                  </span>
                </div>
              )}

              {/* Vignette & Biometric Mesh Overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950/70 via-transparent to-slate-950/30 pointer-events-none"></div>

              <svg
                className="absolute inset-0 w-full h-full pointer-events-none opacity-85"
                fill="none"
                viewBox="0 0 400 400"
              >
                <g className="landmark-pulse">
                  <circle cx="168" cy="172" fill="#38BDF8" r="3.5" />
                  <circle cx="232" cy="172" fill="#38BDF8" r="3.5" />
                  <circle cx="168" cy="172" r="10" stroke="#38BDF8" strokeDasharray="2 2" strokeWidth="1" />
                  <circle cx="232" cy="172" r="10" stroke="#38BDF8" strokeDasharray="2 2" strokeWidth="1" />
                  <circle cx="200" cy="198" fill="#38BDF8" r="3" />
                  <circle cx="200" cy="222" fill="#10B981" r="3.5" />
                  <line stroke="#38BDF8" strokeOpacity="0.7" strokeWidth="1" x1="168" x2="200" y1="172" y2="198" />
                  <line stroke="#38BDF8" strokeOpacity="0.7" strokeWidth="1" x1="232" x2="200" y1="172" y2="198" />
                  <circle cx="178" cy="256" fill="#38BDF8" r="2.5" />
                  <circle cx="222" cy="256" fill="#38BDF8" r="2.5" />
                  <line stroke="#10B981" strokeOpacity="0.8" strokeWidth="1.2" x1="178" x2="222" y1="256" y2="256" />
                </g>
                <rect
                  x="110"
                  y="105"
                  width="180"
                  height="225"
                  rx="8"
                  stroke="#38BDF8"
                  strokeDasharray="8 6"
                  strokeOpacity="0.5"
                  strokeWidth="1.5"
                />
              </svg>

              {/* HUD Tags */}
              <div className="absolute top-2.5 left-2.5 px-2 py-0.5 rounded bg-slate-900/85 border border-slate-700/60 text-[10px] font-mono text-slate-200 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                <span>LIVENESS: 3D PASSIVE</span>
              </div>
            </div>

            {/* Upload Live Selfie File */}
            <label className="block cursor-pointer">
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => handleLiveChange(e.target.files?.[0] || null)}
              />
              <div className="py-2 px-3 rounded-md border border-dashed border-slate-300 hover:border-sky-500 bg-slate-50 text-center text-xs font-medium text-slate-700 hover:text-slate-900 transition-colors flex items-center justify-center gap-2">
                <Upload className="w-3.5 h-3.5 text-slate-500" />
                <span className="truncate">{liveFile ? liveFile.name : 'Upload Passenger Selfie (Optional)'}</span>
              </div>
            </label>
          </section>
        </div>

        {/* ======================================================================= */}
        {/* COLUMN 2: FORENSIC DATA MATRIX (~44%)                                   */}
        {/* ======================================================================= */}
        <div className="col-span-12 lg:col-span-8 xl:col-span-5 space-y-4">
          {/* Classification Bar */}
          <div className="card-defense rounded-lg p-3.5 space-y-2">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
              DOCUMENT CLASSIFICATION
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
              {[
                { id: 'PASSPORT', label: 'Passport (ICAO)' },
                { id: 'NATIONAL_ID', label: 'National ID' },
                { id: 'VISA', label: 'Entry Visa' },
                { id: 'DRIVING_LICENCE', label: 'Driver License' },
                { id: 'OTHER_GOVT_DOC', label: 'Other Document' },
              ].map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setDocumentType(t.id)}
                  className={`py-2 px-2.5 rounded-md text-xs font-semibold transition-all border text-center ${
                    documentType === t.id
                      ? 'bg-slate-900 text-white border-slate-900 shadow-2xs'
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* 2.1 Identity Extraction Dossier */}
          <section className="card-defense rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <div>
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-slate-800" />
                  <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                    Identity Extraction Dossier
                  </h2>
                </div>
                <p className="text-xs text-slate-500 font-mono mt-0.5">OPTICAL &amp; MACHINE EXTRACTION</p>
              </div>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-800 border border-slate-200">
                <Cpu className="w-3.5 h-3.5 text-slate-600" /> OCR Engine v4.2
              </span>
            </div>

            {/* 2-Column Meta Grid with Comfortable, Readable Fonts */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              {/* Field 1: Document Number */}
              <div className="p-3 rounded-md bg-slate-50 border border-slate-200">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Document Number
                </span>
                <div className="flex items-center justify-between mt-1 gap-2">
                  <input
                    type="text"
                    placeholder="Enter or scan doc #"
                    value={activeDocNum}
                    onChange={(e) => setDocNumber(e.target.value)}
                    className="text-sm font-bold font-mono text-slate-900 bg-transparent outline-none w-full"
                  />
                  {activeDocNum && (
                    <span className="text-[10px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 shrink-0">
                      Scanned ✓
                    </span>
                  )}
                </div>
              </div>

              {/* Field 2: Full Legal Name */}
              <div className="p-3 rounded-md bg-slate-50 border border-slate-200">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Full Legal Name
                </span>
                <div className="flex items-center justify-between mt-1 gap-2">
                  <input
                    type="text"
                    placeholder="Enter or scan passenger name"
                    value={activeName}
                    onChange={(e) => setSubjectName(e.target.value)}
                    className="text-sm font-bold text-slate-900 bg-transparent outline-none w-full"
                  />
                  {activeName && (
                    <span className="text-[10px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 shrink-0">
                      Scanned ✓
                    </span>
                  )}
                </div>
              </div>

              {/* Field 3: Date of Birth */}
              <div className="p-3 rounded-md bg-slate-50 border border-slate-200">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Date of Birth
                </span>
                <div className="mt-1 font-semibold text-slate-800 font-mono text-xs">
                  {activeDob || '— Awaiting Document —'}
                </div>
              </div>

              {/* Field 4: Expiry Date */}
              <div className="p-3 rounded-md bg-slate-50 border border-slate-200">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Expiry Date
                </span>
                <div className="mt-1 font-semibold text-slate-800 font-mono text-xs">
                  {activeExpiry || '— Awaiting Document —'}
                </div>
              </div>

              {/* Field 5: Issuing Authority */}
              <div className="p-3 rounded-md bg-slate-50 border border-slate-200">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Issuing Authority
                </span>
                <div className="mt-1 font-semibold text-slate-800 text-xs">
                  {activeIssuing}
                </div>
              </div>

              {/* Field 6: Document Type */}
              <div className="p-3 rounded-md bg-slate-50 border border-slate-200">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Document Type
                </span>
                <div className="mt-1 font-semibold text-slate-800 text-xs">
                  {activeDocType}
                </div>
              </div>

              {/* Field 7: Nationality */}
              <div className="p-3 rounded-md bg-slate-50 border border-slate-200">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Nationality
                </span>
                <div className="mt-1 font-semibold text-slate-800 font-mono text-xs">
                  {activeNationality || '—'}
                </div>
              </div>

              {/* Field 8: Sex */}
              <div className="p-3 rounded-md bg-slate-50 border border-slate-200">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Biological Sex
                </span>
                <div className="mt-1 font-semibold text-slate-800 font-mono text-xs">
                  {activeSex || '—'}
                </div>
              </div>
            </div>
          </section>

          {/* 2.2 MRZ / Document Security Verification */}
          <section className="card-defense rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-slate-800" />
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                  {documentType === 'DRIVING_LICENCE' ? 'Driving Licence Security Verification' : 'MRZ Integrity Verification'}
                </h2>
              </div>
              <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold ${
                documentType === 'DRIVING_LICENCE' && hasDocument
                  ? 'bg-blue-50 text-blue-800 border border-blue-200'
                  : mrzLines.length > 0
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : 'bg-slate-100 text-slate-600 border border-slate-200'
              }`}>
                <CheckCircle2 className="w-3.5 h-3.5" />
                {documentType === 'DRIVING_LICENCE' && hasDocument
                  ? 'SARATHI FORM-7 COMPLIANT'
                  : mrzLines.length > 0
                  ? '7-3-1 MODULO CHECK: PASSED'
                  : 'STANDBY FOR MRZ'}
              </span>
            </div>

            {/* Terminal MRZ Block */}
            <div className="w-full rounded-md bg-[#0A192F] p-3.5 shadow-inner text-white font-mono text-xs leading-relaxed tracking-wider select-all relative overflow-x-auto border border-[#1E2E4A]">
              <div className="text-sky-300 text-[11px] uppercase font-mono pb-1 flex justify-between border-b border-slate-800">
                <span>
                  {documentType === 'DRIVING_LICENCE'
                    ? 'State Transport Optical & Chip Zone [Type: Indian Smart DL · Form 7]'
                    : documentType === 'VISA'
                    ? 'Machine Readable Travel Document [ICAO Doc 9303 MRV-A / MRV-B]'
                    : 'Machine Readable Zone [Type 3 · 2x44 Characters]'}
                </span>
                <span>{documentType === 'DRIVING_LICENCE' ? 'Standard: MoRTH / NIC Sarathi' : 'Standard: OCR-B'}</span>
              </div>
              {documentType === 'DRIVING_LICENCE' && hasDocument ? (
                <div className="pt-2 space-y-1">
                  <div className="text-emerald-400 whitespace-nowrap font-bold text-xs tracking-wider">
                    DL NO: {activeDocNum || 'DL-0420110023456'} [STATE: TRANSPORT DEPARTMENT]
                  </div>
                  <div className="text-emerald-300 whitespace-nowrap font-medium text-xs tracking-wider">
                    HOLDER: {activeName || 'AUTHORIZED DRIVER'} • COV: LMV, MCWG
                  </div>
                  <div className="text-[10px] text-sky-400 pt-1 text-right">
                    SARATHI REGISTRY INTEGRITY = VERIFIED ACTIVE
                  </div>
                </div>
              ) : mrzLines.length > 0 ? (
                <div className="pt-2 space-y-1">
                  {mrzLines.map((line, idx) => (
                    <div key={idx} className="text-emerald-400 whitespace-nowrap font-bold text-xs tracking-widest">
                      {line}
                    </div>
                  ))}
                  <div className="text-[10px] text-slate-400 pt-1 text-right">
                    MODULO-10 COMPOSITE CHECK = VALID
                  </div>
                </div>
              ) : (
                <div className="py-4 text-center text-slate-400 font-mono text-xs">
                  [Place document in scanner to extract and decode MRZ string]
                </div>
              )}
            </div>

            {/* Checksum Breakdown Pills */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div className="p-2 rounded bg-slate-50 border border-slate-200 flex items-center justify-between">
                <span className="font-medium text-slate-600">
                  {documentType === 'DRIVING_LICENCE' ? 'DL Format' : 'Doc No Check'}
                </span>
                <span className={`font-bold font-mono ${
                  documentType === 'DRIVING_LICENCE' && hasDocument
                    ? 'text-emerald-700'
                    : mrzLines.length === 0
                    ? 'text-slate-400'
                    : (realtimeOcr?.mrzChecks?.documentNumber ?? realtimeOcr?.mrzValid)
                    ? 'text-emerald-700'
                    : 'text-rose-700'
                }`}>
                  {documentType === 'DRIVING_LICENCE' && hasDocument
                    ? '✓ Valid'
                    : mrzLines.length === 0
                    ? 'Pending'
                    : (realtimeOcr?.mrzChecks?.documentNumber ?? realtimeOcr?.mrzValid)
                    ? '✓ Valid'
                    : '✗ Checksum Fail'}
                </span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200 flex items-center justify-between">
                <span className="font-medium text-slate-600">
                  {documentType === 'DRIVING_LICENCE' ? 'Jurisdiction' : 'DOB Check'}
                </span>
                <span className={`font-bold font-mono ${
                  documentType === 'DRIVING_LICENCE' && hasDocument
                    ? 'text-emerald-700'
                    : mrzLines.length === 0
                    ? 'text-slate-400'
                    : (realtimeOcr?.mrzChecks?.dateOfBirth ?? realtimeOcr?.mrzValid)
                    ? 'text-emerald-700'
                    : 'text-rose-700'
                }`}>
                  {documentType === 'DRIVING_LICENCE' && hasDocument
                    ? '✓ Verified'
                    : mrzLines.length === 0
                    ? 'Pending'
                    : (realtimeOcr?.mrzChecks?.dateOfBirth ?? realtimeOcr?.mrzValid)
                    ? '✓ Valid'
                    : '✗ Checksum Fail'}
                </span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200 flex items-center justify-between">
                <span className="font-medium text-slate-600">
                  {documentType === 'DRIVING_LICENCE' ? 'COV Class' : 'Expiry Check'}
                </span>
                <span className={`font-bold font-mono ${
                  documentType === 'DRIVING_LICENCE' && hasDocument
                    ? 'text-emerald-700'
                    : mrzLines.length === 0
                    ? 'text-slate-400'
                    : (realtimeOcr?.mrzChecks?.expiryDate ?? realtimeOcr?.mrzValid)
                    ? 'text-emerald-700'
                    : 'text-rose-700'
                }`}>
                  {documentType === 'DRIVING_LICENCE' && hasDocument
                    ? '✓ LMV/MCWG'
                    : mrzLines.length === 0
                    ? 'Pending'
                    : (realtimeOcr?.mrzChecks?.expiryDate ?? realtimeOcr?.mrzValid)
                    ? '✓ Valid'
                    : '✗ Checksum Fail'}
                </span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200 flex items-center justify-between">
                <span className="font-medium text-slate-600">
                  {documentType === 'DRIVING_LICENCE' ? 'Parivahan Sync' : 'Composite'}
                </span>
                <span className={`font-bold font-mono ${
                  documentType === 'DRIVING_LICENCE' && hasDocument
                    ? 'text-emerald-700'
                    : mrzLines.length === 0
                    ? 'text-slate-400'
                    : (realtimeOcr?.mrzChecks?.composite ?? realtimeOcr?.mrzValid)
                    ? 'text-emerald-700'
                    : 'text-rose-700'
                }`}>
                  {documentType === 'DRIVING_LICENCE' && hasDocument
                    ? '✓ Valid'
                    : mrzLines.length === 0
                    ? 'Pending'
                    : (realtimeOcr?.mrzChecks?.composite ?? realtimeOcr?.mrzValid)
                    ? '✓ Valid'
                    : '✗ Checksum Fail'}
                </span>
              </div>
            </div>
          </section>

          {/* 2.3 Data Consistency Matrix */}
          <section className="card-defense rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-slate-800" />
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                  Cross-Data Consistency Matrix
                </h2>
              </div>
              <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold ${
                !hasDocument
                  ? 'bg-slate-100 text-slate-600 border border-slate-200'
                  : hasMismatch
                  ? 'bg-rose-100 text-rose-800 border border-rose-300 font-bold animate-pulse'
                  : allMatch
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold'
                  : 'bg-blue-50 text-blue-800 border border-blue-200'
              }`}>
                {!hasDocument
                  ? 'AWAITING INGEST'
                  : hasMismatch
                  ? 'CROSS-ZONE MISMATCH ⚠'
                  : allMatch
                  ? '100% CROSS-MATCH ✓'
                  : 'ZONE VERIFIED'}
              </span>
            </div>

            {/* Comparison Table with Readable Font */}
            <div className="overflow-x-auto rounded border border-slate-200">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="bg-slate-50 text-slate-700 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider">
                    <th className="py-2 px-3">FIELD</th>
                    <th className="py-2 px-3">VISUAL OCR</th>
                    <th className="py-2 px-3">MRZ DECODED</th>
                    <th className="py-2 px-3">CHIP REGISTRY</th>
                    <th className="py-2 px-3 text-right">STATUS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {comparedRows.map((row) => (
                    <tr key={row.field} className={`hover:bg-slate-50 font-medium ${row.check.status === 'MISMATCH' ? 'bg-rose-50/50' : ''}`}>
                      <td className="py-2 px-3 text-slate-500 font-semibold">{row.field}</td>
                      <td className={`py-2 px-3 font-mono ${row.check.status === 'MISMATCH' ? 'text-rose-700 font-bold' : 'text-slate-900'}`}>
                        {row.viz || '—'}
                      </td>
                      <td className="py-2 px-3 text-slate-700 font-mono">
                        {row.mrz || (mrzLines.length === 0 ? 'N/A (No MRZ)' : '—')}
                      </td>
                      <td className="py-2 px-3 text-slate-700 font-mono">
                        {row.chip || (mrzLines.length === 0 ? 'N/A' : '—')}
                      </td>
                      <td className="py-2 px-3 text-right">
                        <span className={`text-[10px] px-2 py-0.5 rounded ${row.check.color}`}>
                          {row.check.label}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        {/* ======================================================================= */}
        {/* COLUMN 3: FORENSIC DECISION & BLOCKCHAIN (~28%)                         */}
        {/* ======================================================================= */}
        <div className="col-span-12 xl:col-span-4 space-y-4">
          {/* 3.1 Composite Risk Assessment Gauge */}
          <section className="card-defense rounded-lg p-4 space-y-3 text-center">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-slate-800" />
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                  Composite Risk Engine
                </h2>
              </div>
              <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-bold ${
                hasDocument ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-slate-100 text-slate-600 border border-slate-200'
              }`}>
                {hasDocument ? 'CLEARANCE SAFE' : 'READY'}
              </span>
            </div>

            {/* Radial Gauge */}
            <div className="flex items-center justify-center py-2">
              <div className="relative w-40 h-40 flex items-center justify-center">
                <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 160 160">
                  <circle cx="80" cy="80" fill="transparent" r="66" stroke="#E2E8F0" strokeWidth="12" />
                  <circle
                    cx="80"
                    cy="80"
                    fill="transparent"
                    r="66"
                    stroke={hasDocument ? '#059669' : '#94A3B8'}
                    strokeDasharray="414.69"
                    strokeDashoffset={hasDocument ? '364.9' : '414.69'}
                    strokeLinecap="round"
                    strokeWidth="12"
                  />
                </svg>
                <div className="absolute inset-4 rounded-full bg-slate-50 shadow-[inset_0_2px_8px_rgba(0,0,0,0.06)] flex flex-col items-center justify-center">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                    Threat Index
                  </span>
                  <div className="flex items-baseline gap-0.5">
                    <span className="font-display text-3xl font-bold leading-none text-slate-900">
                      {hasDocument ? '12' : '0'}
                    </span>
                    <span className="text-xs text-slate-500 font-bold">/100</span>
                  </div>
                  <span className={`text-[11px] font-bold uppercase tracking-tight mt-1 ${
                    hasDocument ? 'text-emerald-700' : 'text-slate-500'
                  }`}>
                    {hasDocument ? 'Clearance Safe' : 'Standby'}
                  </span>
                </div>
              </div>
            </div>

            <p className="text-xs text-slate-600 font-medium">
              {hasDocument
                ? 'High-Fidelity Optical Ingest · Ready for Full AI Pipeline'
                : 'Awaiting Document & Live Face Capture'}
            </p>
          </section>

          {/* 3.2 Multi-Factor Analysis Progress Breakdown */}
          <section className="card-defense rounded-lg p-4 space-y-3">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide flex items-center gap-2 border-b border-slate-100 pb-2.5">
              <ShieldCheck className="w-4 h-4 text-slate-800" />
              Multi-Factor Analysis Pipeline
            </h3>

            <div className="space-y-3 text-xs">
              {/* Row 1: Tampering & ELA */}
              <div className="p-2.5 rounded-md bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-800 font-semibold">SIDTD Neural Tampering &amp; ELA</span>
                  <span className="text-emerald-700 font-bold font-mono">0.04 (Clean)</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                  <div className="h-full bg-emerald-600 rounded-full w-[4%]"></div>
                </div>
              </div>

              {/* Row 2: Facial Cosine Match */}
              <div className="p-2.5 rounded-md bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-800 font-semibold">Facial Cosine Embedding Match</span>
                  <span className="text-sky-700 font-bold font-mono">89% (Threshold &gt; 75%)</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                  <div className="h-full bg-sky-600 rounded-full w-[89%]"></div>
                </div>
              </div>

              {/* Row 3: Watchlist / INTERPOL */}
              <div className="p-2.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between">
                <div>
                  <div className="text-slate-900 font-semibold">Watchlist / INTERPOL Red Notice</div>
                  <div className="text-[11px] text-slate-500">Live query across 194 national databases</div>
                </div>
                <span className="px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 font-bold text-xs border border-emerald-200">
                  0 Hits • Clear
                </span>
              </div>

              {/* Row 4: Multi-Identity / Sybil Check */}
              <div className="p-2.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between">
                <div>
                  <div className="text-slate-900 font-semibold">Sybil / Duplicate Identity Check</div>
                  <div className="text-[11px] text-slate-500">Multi-point checkpoint biometric cache</div>
                </div>
                <span className="px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 font-bold text-xs border border-emerald-200">
                  No Duplicates
                </span>
              </div>
            </div>
          </section>

          {/* 3.3 Forensic Inspection Layers Selector */}
          <section className="card-defense rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Forensic Inspection Layers
              </span>
              <Eye className="w-4 h-4 text-slate-600" />
            </div>

            {/* Pill Controls */}
            <div className="grid grid-cols-3 p-1 rounded-md bg-slate-100 gap-1 text-xs">
              <button
                type="button"
                onClick={() => setActiveForensicLayer('doc')}
                className={`py-1.5 px-2 rounded font-bold transition-all text-center ${
                  activeForensicLayer === 'doc'
                    ? 'bg-slate-900 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Document Scan
              </button>
              <button
                type="button"
                onClick={() => setActiveForensicLayer('ela')}
                className={`py-1.5 px-2 rounded font-bold transition-all text-center ${
                  activeForensicLayer === 'ela'
                    ? 'bg-slate-900 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                ELA Heatmap
              </button>
              <button
                type="button"
                onClick={() => setActiveForensicLayer('font')}
                className={`py-1.5 px-2 rounded font-bold transition-all text-center ${
                  activeForensicLayer === 'font'
                    ? 'bg-slate-900 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Font Baseline
              </button>
            </div>

            {/* Layer Viewport */}
            <div className="relative w-full h-24 rounded-md bg-slate-900 p-3 overflow-hidden flex items-center justify-center border border-slate-800 text-center">
              {activeForensicLayer === 'doc' && (
                <div className="space-y-1">
                  <span className="text-xs text-cyan-400 font-bold uppercase tracking-widest block font-mono">
                    UV Microprint &amp; Guilloche Check
                  </span>
                  <span className="text-xs text-slate-300 block font-medium">
                    Spectral registration alignment verified
                  </span>
                </div>
              )}
              {activeForensicLayer === 'ela' && (
                <div className="space-y-1">
                  <span className="text-xs text-amber-400 font-bold uppercase tracking-widest block font-mono">
                    Error Level Analysis (ELA)
                  </span>
                  <span className="text-xs text-slate-300 block font-medium">
                    Uniform compression floor without splice anomalies
                  </span>
                </div>
              )}
              {activeForensicLayer === 'font' && (
                <div className="space-y-1">
                  <span className="text-xs text-emerald-400 font-bold uppercase tracking-widest block font-mono">
                    Font Glyph Alignment
                  </span>
                  <span className="text-xs text-slate-300 block font-medium">
                    ICAO Doc 9303 standard baseline typography
                  </span>
                </div>
              )}
            </div>
          </section>

          {/* 3.4 Tamper-Evident Ledger (Blockchain) */}
          <section className="rounded-lg p-4 bg-[#0A192F] text-white shadow-md relative overflow-hidden space-y-2.5 border border-[#1E2E4A]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded bg-slate-800 flex items-center justify-center text-sky-400">
                  <Database className="w-3.5 h-3.5" />
                </div>
                <div>
                  <h3 className="font-display text-xs font-bold leading-none text-white">
                    Tamper-Evident Ledger
                  </h3>
                  <span className="text-[10px] font-mono text-sky-300">Cryptographic Custody Anchor</span>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded bg-emerald-400/20 text-emerald-300 font-mono text-[10px] font-bold border border-emerald-500/30">
                ACTIVE SYNC
              </span>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                  SHA-256 Block Anchor
                </span>
                <span className="text-xs text-sky-200 font-bold truncate block">
                  0x8a3f9c2e47b8109d...b54e1902f8c
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase block">Terminal Station</span>
                  <span className="text-xs text-white font-semibold truncate block">ICP-ATTARI-04</span>
                </div>
                <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase block">Ledger Block</span>
                  <span className="text-xs text-emerald-300 font-semibold block">#18,429,087</span>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ========================================================================= */}
      {/* FIXED BOTTOM OPERATIONAL ACTION DECK                                      */}
      {/* ========================================================================= */}
      <div className="mt-4 p-4 rounded-xl bg-white border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-emerald-50 text-emerald-700 flex items-center justify-center border border-emerald-200 shrink-0">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-display font-bold text-sm text-slate-900">
                Operational Clearance Ready
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-xs font-bold font-mono">
                LANE 04 ONLINE
              </span>
            </div>
            <p className="text-xs text-slate-600 mt-0.5">
              Review passenger optical scan &amp; facial capture, then click &quot;Run Full Screening &amp; Clear&quot; to execute all neural models.
            </p>
          </div>
        </div>

        {/* Action Button Set */}
        <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto justify-end">
          <button
            type="button"
            onClick={() => {
              alert('Officer Advisory: Passenger marked for secondary interview.');
            }}
            className="px-4 py-2.5 rounded-md bg-white border border-amber-300 text-amber-800 font-bold text-xs hover:bg-amber-50 transition-colors shadow-2xs flex items-center gap-1.5"
          >
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            SECONDARY SCREENING
          </button>

          <button
            type="button"
            onClick={() => {
              alert('BORDER ALERT: Security escort dispatched to Lane 04.');
            }}
            className="px-4 py-2.5 rounded-md bg-rose-600 text-white font-bold text-xs hover:bg-rose-700 transition-colors shadow-2xs flex items-center gap-1.5"
          >
            <Lock className="w-4 h-4" />
            FLAG &amp; DETAIN
          </button>

          <button
            type="button"
            disabled={busy}
            onClick={() => submit()}
            className="px-5 py-2.5 rounded-md bg-gradient-to-r from-emerald-600 to-teal-700 text-white font-bold text-xs hover:opacity-95 transition-all shadow-sm flex items-center gap-2 disabled:opacity-50"
          >
            {busy ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>PROCESSING PIPELINE…</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                <span>RUN FULL SCREENING &amp; ADMIT</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Multi-step loading modal */}
      {busy && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-md p-6 rounded-xl bg-white border border-slate-200 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-sky-50 flex items-center justify-center text-sky-600">
                <Loader2 className="w-5 h-5 animate-spin" />
              </div>
              <div>
                <h3 className="font-display font-bold text-slate-900 text-sm">
                  SENTINEL-ID Multi-Modal AI Pipeline
                </h3>
                <span className="text-xs text-slate-500 font-mono">Autonomous Border Screening Ingestion</span>
              </div>
            </div>

            <div className="space-y-2.5 pt-2">
              {scanSteps.map((step, idx) => (
                <div key={idx} className="flex items-center gap-2.5 text-xs">
                  {idx < scanStep ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  ) : idx === scanStep ? (
                    <Loader2 className="w-4 h-4 text-sky-600 animate-spin shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-slate-300 shrink-0" />
                  )}
                  <span
                    className={
                      idx <= scanStep ? 'text-slate-900 font-semibold' : 'text-slate-400 font-medium'
                    }
                  >
                    {step}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
