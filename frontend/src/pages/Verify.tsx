import React, { FormEvent, useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, extractRealtimeOcr, RealtimeOcrResult } from '../api/client';
import {
  ScanLine,
  FileText,
  Camera,
  Sparkles,
  AlertCircle,
  CheckCircle,
  Loader2,
  User,
  FileCode,
  Video,
  RefreshCw,
  StopCircle,
  Check,
  Zap,
  Clock,
  ShieldCheck,
  Eye,
  EyeOff,
  Copy,
  CheckCheck,
  Hash,
  Calendar,
  Globe,
  Layers,
  Award,
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
  const [showRawOcr, setShowRawOcr] = useState(false);
  const [showMrzDetails, setShowMrzDetails] = useState(true);
  const [copiedField, setCopiedField] = useState<string | null>(null);

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
      setCameraError('Camera access denied or unavailable. Please check browser permissions or upload a file.');
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

  function copyText(text: string, field: string) {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
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

      // Auto-populate form inputs if extracted
      if (data?.fields?.name) {
        setSubjectName(data.fields.name);
      }
      const num = data?.fields?.documentNumber || data?.fields?.passportNumber;
      if (num) {
        setDocNumber(num);
      }
      if (data?.detectedDocumentType === 'PASSPORT') {
        setDocumentType('PASSPORT');
      } else if (
        data?.detectedDocumentType &&
        ['DRIVING_LICENCE', 'AADHAAR', 'PAN', 'VOTER_ID', 'NATIONAL_ID'].includes(data.detectedDocumentType)
      ) {
        setDocumentType('NATIONAL_ID');
      }
    } catch (err: any) {
      console.warn('Real-time OCR extraction non-fatal error:', err);
      setOcrError('Real-time OCR preview encountered an issue. Standard full screening remains available.');
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

  function loadSample(type: 'valid' | 'forged' | 'blacklist') {
    let nameVal = 'AARAV SHARMA';
    let numVal = 'Z9876543';
    let color = '#1e3a8a';

    if (type === 'forged') {
      nameVal = 'JOHN FICTITIOUS';
      numVal = 'P1234567';
      color = '#7f1d1d';
    } else if (type === 'blacklist') {
      nameVal = 'ANON SUSPECT';
      numVal = 'X9988776';
      color = '#78350f';
    }

    setSubjectName(nameVal);
    setDocNumber(numVal);

    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
      <rect width="600" height="400" fill="#0f172a" rx="16"/>
      <rect x="20" y="20" width="560" height="360" fill="${color}" opacity="0.3" rx="12" stroke="#334155" stroke-width="2"/>
      <text x="50" y="70" fill="#ffffff" font-family="sans-serif" font-weight="bold" font-size="22">REPUBLIC OF INDIA - PASSPORT</text>
      <text x="50" y="110" fill="#94a3b8" font-family="monospace" font-size="14">TYPE: P | CODE: IND | PASSPORT NO: ${numVal}</text>
      <circle cx="100" cy="210" r="50" fill="#334155"/>
      <text x="100" y="215" fill="#94a3b8" text-anchor="middle" font-size="12">PHOTO</text>
      <text x="180" y="170" fill="#ffffff" font-family="sans-serif" font-weight="bold" font-size="16">NAME: ${nameVal}</text>
      <text x="180" y="200" fill="#cbd5e1" font-family="sans-serif" font-size="14">DOB: 12 APR 1985 | SEX: M</text>
      <text x="180" y="230" fill="#cbd5e1" font-family="sans-serif" font-size="14">EXPIRY: 09 MAY 2028</text>
      <rect x="40" y="300" width="520" height="60" fill="#020617" rx="6" stroke="#1e293b"/>
      <text x="55" y="325" fill="#38bdf8" font-family="monospace" font-size="13">P&lt;IND${nameVal.replace(' ', '&lt;')}&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;</text>
      <text x="55" y="348" fill="#38bdf8" font-family="monospace" font-size="13">${numVal}&lt;4IND8504128M2805098&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;04</text>
    </svg>`;

    const blob = new Blob([svg], { type: 'image/svg+xml' });
    const file = new File([blob], `passport_${numVal}.svg`, { type: 'image/svg+xml' });
    handleDocChange(file);
  }

  const [result, setResult] = useState<any>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    let targetFile = docFile;

    if (!targetFile && docNumber) {
      const nameVal = subjectName || 'Subject ' + docNumber;
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400">
        <rect width="600" height="400" fill="#0f172a"/>
        <text x="50" y="80" fill="#ffffff" font-size="20">PASSPORT ${docNumber}</text>
        <text x="50" y="120" fill="#cbd5e1" font-size="16">NAME: ${nameVal}</text>
      </svg>`;
      const blob = new Blob([svg], { type: 'image/svg+xml' });
      targetFile = new File([blob], `doc_${docNumber}.svg`, { type: 'image/svg+xml' });
    }

    if (!targetFile) return;

    setBusy(true);
    setError('');
    setResult(null);
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
      setResult(verificationResult);

      // Short delay to show completion animation, then navigate
      if (verificationResult?.verificationId) {
        setTimeout(() => {
          setBusy(false);
          nav(`/verification/${verificationResult.verificationId}`);
        }, 1200);
      } else {
        setBusy(false);
      }
    } catch (err: any) {
      clearInterval(interval);
      const data = err?.response?.data;
      let msg =
        (typeof data === 'string' && data.trim()) ||
        data?.message ||
        data?.error ||
        (err?.response?.status ? `Server error ${err.response.status}${data ? `: ${typeof data === 'object' ? JSON.stringify(data) : data}` : ''}` : '') ||
        err?.message ||
        'Verification execution failed — check backend logs.';
      if (err?.response?.status === 403 || err?.response?.status === 401) {
        msg = 'Session expired. Please click Logout (top right icon) and sign in again with officer1 / officer123.';
      }
      setError(msg);
      setBusy(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Title */}
      <div className="bg-slate-900/60 border border-slate-800/80 p-8 rounded-3xl shadow-xl backdrop-blur-md flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-3 tracking-tight">
            <ScanLine className="w-7 h-7 text-blue-400" />
            <span>New Document Forensic Screening</span>
          </h1>
          <p className="text-xs text-slate-400 font-normal">
            Upload document scans or generate custom passports for multi-factor AI evaluation.
          </p>
        </div>

        <div className="flex flex-col gap-1.5 text-right">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Quick Presets</span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => loadSample('valid')}
              className="text-xs bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 px-3 py-1.5 rounded-xl border border-emerald-500/20 font-bold transition-all"
            >
              Valid Passport
            </button>
            <button
              type="button"
              onClick={() => loadSample('forged')}
              className="text-xs bg-red-500/10 text-red-400 hover:bg-red-500/20 px-3 py-1.5 rounded-xl border border-red-500/20 font-bold transition-all"
            >
              Forged ELA
            </button>
            <button
              type="button"
              onClick={() => loadSample('blacklist')}
              className="text-xs bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 px-3 py-1.5 rounded-xl border border-amber-500/20 font-bold transition-all"
            >
              Watchlist Hit
            </button>
          </div>
        </div>
      </div>

      {/* Main Upload Form */}
      <form onSubmit={submit} className="bg-slate-900/60 border border-slate-800/80 p-8 sm:p-10 rounded-3xl shadow-2xl space-y-8 backdrop-blur-md">
        {/* Document Classification */}
        <div>
          <label className="block text-xs font-bold uppercase text-slate-300 tracking-wider mb-3">
            Document Classification
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {[
              { id: 'NATIONAL_ID', label: 'National ID' },
              { id: 'PASSPORT', label: 'Passport' },
              { id: 'VISA', label: 'Visa' },
              { id: 'DRIVING_LICENCE', label: 'Driving Licence' },
              { id: 'OTHER_GOVT_DOC', label: 'Other Govt Doc' },
            ].map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setDocumentType(t.id)}
                className={`py-3.5 px-4 rounded-2xl border text-xs font-extrabold transition-all text-center ${
                  documentType === t.id
                    ? 'bg-blue-600/20 border-blue-500 text-blue-400 shadow-xl shadow-blue-950/40'
                    : 'bg-slate-950/60 border-slate-800/80 text-slate-400 hover:border-slate-700'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Optional Text Inputs */}
        <div className="grid sm:grid-cols-2 gap-6">
          <div>
            <label className="block text-xs font-bold text-slate-300 mb-2">
              Document / Serial # (Optional)
            </label>
            <div className="relative">
              <FileCode className="w-4.5 h-4.5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
              <input
                className="w-full bg-slate-950 border border-slate-800/80 rounded-2xl pl-11 pr-4 py-3 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-blue-500 transition-all"
                placeholder="e.g. Z9876543"
                value={docNumber}
                onChange={(e) => setDocNumber(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-300 mb-2">
              Subject Name (Optional)
            </label>
            <div className="relative">
              <User className="w-4.5 h-4.5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
              <input
                className="w-full bg-slate-950 border border-slate-800/80 rounded-2xl pl-11 pr-4 py-3 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-blue-500 transition-all"
                placeholder="e.g. Aarav Sharma"
                value={subjectName}
                onChange={(e) => setSubjectName(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Upload Dropzones */}
        <div className="grid md:grid-cols-2 gap-8">
          {/* Document Dropzone with Dual Mode (Upload or Webcam) */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="text-xs font-bold uppercase text-slate-300 tracking-wider">
                Primary Document Scan <span className="text-red-400">*</span>
              </label>
              <div className="flex bg-slate-900/80 p-0.5 rounded-xl border border-slate-800 text-[11px] font-semibold">
                <button
                  type="button"
                  onClick={() => {
                    stopDocCamera();
                    setDocMode('upload');
                  }}
                  className={`px-2.5 py-1 rounded-lg transition-all ${
                    docMode === 'upload'
                      ? 'bg-blue-600 text-white shadow-sm font-bold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Upload File
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setDocMode('camera');
                    startDocCamera();
                  }}
                  className={`px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 ${
                    docMode === 'camera'
                      ? 'bg-blue-600 text-white shadow-sm font-bold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Video className="w-3 h-3" />
                  <span>Scan via Cam</span>
                </button>
              </div>
            </div>

            <div className="relative border-2 border-dashed border-slate-700/80 hover:border-blue-500/60 bg-slate-950/60 rounded-3xl p-5 text-center transition-all min-h-[220px] flex flex-col items-center justify-center overflow-hidden">
              {docPreview ? (
                <div className="relative w-full h-44 flex flex-col items-center justify-center">
                  <img src={docPreview} alt="Doc preview" className="w-full h-full object-contain rounded-xl" />
                  <div className="absolute top-2 left-2 bg-blue-500/20 text-blue-300 text-[10px] font-bold px-2.5 py-1 rounded-lg border border-blue-500/30 flex items-center gap-1 backdrop-blur-md">
                    <Check className="w-3 h-3" />
                    <span>Doc Loaded</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      handleDocChange(null);
                      stopDocCamera();
                    }}
                    className="absolute top-2 right-2 bg-slate-900/90 text-xs text-red-400 hover:text-red-300 px-3 py-1 rounded-xl border border-red-500/30 font-bold transition-all shadow-md"
                  >
                    Clear
                  </button>
                </div>
              ) : docMode === 'camera' ? (
                <div className="w-full flex flex-col items-center space-y-3">
                  {docCameraError ? (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400 text-xs flex items-center gap-2 text-left">
                      <AlertCircle className="w-4 h-4 flex-shrink-0" />
                      <span>{docCameraError}</span>
                    </div>
                  ) : isDocCameraActive ? (
                    <div className="relative w-full max-w-[320px] h-40 bg-black rounded-2xl overflow-hidden shadow-inner border border-blue-500/40">
                      <video ref={docVideoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
                      {/* Document alignment target box */}
                      <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                        <div className="w-48 h-32 border-2 border-dashed border-cyan-400/80 rounded-xl" />
                      </div>
                      <div className="absolute bottom-1 left-2 text-[9px] text-cyan-300/80 font-mono">
                        HOLD DOCUMENT IN RECTANGLE
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={startDocCamera}
                      className="flex flex-col items-center space-y-2 p-4 text-blue-400 hover:text-blue-300"
                    >
                      <Video className="w-8 h-8 animate-bounce" />
                      <span className="text-xs font-bold text-slate-200">Open Camera to Scan Document</span>
                    </button>
                  )}

                  <div className="flex items-center gap-2 pt-1">
                    {isDocCameraActive && (
                      <button
                        type="button"
                        onClick={captureDocPhoto}
                        className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-extrabold px-4 py-2 rounded-xl shadow-lg shadow-blue-900/40 flex items-center gap-1.5 transition-all"
                      >
                        <Camera className="w-4 h-4" />
                        <span>Snap Document & Extract</span>
                      </button>
                    )}
                    {isDocCameraActive && (
                      <button
                        type="button"
                        onClick={stopDocCamera}
                        className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-3 py-2 rounded-xl border border-slate-700 font-semibold"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <label className="cursor-pointer flex flex-col items-center space-y-3">
                  <div className="p-4 bg-blue-500/10 text-blue-400 rounded-2xl">
                    <FileText className="w-7 h-7" />
                  </div>
                  <span className="text-xs font-bold text-slate-200">Click or drag image file here</span>
                  <span className="text-[10px] text-slate-500 font-medium">Supports Passports, Driving Licences, Aadhaar, PAN, Voter IDs</span>
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => handleDocChange(e.target.files?.[0] ?? null)}
                  />
                </label>
              )}
            </div>
          </div>

          {/* Live Subject Photo Dropzone & Camera */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="text-xs font-bold uppercase text-slate-300 tracking-wider">
                Subject Live Photo (Optional)
              </label>
              <div className="flex bg-slate-900/80 p-0.5 rounded-xl border border-slate-800 text-[11px] font-semibold">
                <button
                  type="button"
                  onClick={() => {
                    stopCamera();
                    setLiveMode('upload');
                  }}
                  className={`px-2.5 py-1 rounded-lg transition-all ${
                    liveMode === 'upload'
                      ? 'bg-blue-600 text-white shadow-sm font-bold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Upload File
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setLiveMode('camera');
                    startCamera();
                  }}
                  className={`px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 ${
                    liveMode === 'camera'
                      ? 'bg-indigo-600 text-white shadow-sm font-bold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Video className="w-3 h-3" />
                  <span>Live Webcam</span>
                </button>
              </div>
            </div>

            <div className="relative border-2 border-dashed border-slate-700/80 hover:border-indigo-500/60 bg-slate-950/60 rounded-3xl p-5 text-center transition-all min-h-[220px] flex flex-col items-center justify-center overflow-hidden">
              {livePreview ? (
                <div className="relative w-full h-44 flex flex-col items-center justify-center">
                  <img src={livePreview} alt="Live subject preview" className="w-full h-full object-contain rounded-xl" />
                  <div className="absolute top-2 left-2 bg-emerald-500/20 text-emerald-300 text-[10px] font-bold px-2.5 py-1 rounded-lg border border-emerald-500/30 flex items-center gap-1 backdrop-blur-md">
                    <Check className="w-3 h-3" />
                    <span>Photo Attached</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      handleLiveChange(null);
                      stopCamera();
                    }}
                    className="absolute top-2 right-2 bg-slate-900/90 text-xs text-red-400 hover:text-red-300 px-3 py-1 rounded-xl border border-red-500/30 font-bold transition-all shadow-md"
                  >
                    Clear / Retake
                  </button>
                </div>
              ) : liveMode === 'camera' ? (
                <div className="w-full flex flex-col items-center space-y-3">
                  {cameraError ? (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400 text-xs flex items-center gap-2 text-left">
                      <AlertCircle className="w-4 h-4 flex-shrink-0" />
                      <span>{cameraError}</span>
                    </div>
                  ) : isCameraActive ? (
                    <div className="relative w-full max-w-[280px] h-40 bg-black rounded-2xl overflow-hidden shadow-inner border border-indigo-500/40">
                      <video
                        ref={videoRef}
                        autoPlay
                        playsInline
                        muted
                        className="w-full h-full object-cover"
                      />
                      {/* Biometric Face Target Reticle */}
                      <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                        <div className="w-24 h-32 border-2 border-dashed border-indigo-400/70 rounded-full animate-pulse" />
                      </div>
                      <div className="absolute bottom-1 left-2 text-[9px] text-indigo-300/80 font-mono">
                        LIVE FEED READY
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={startCamera}
                      className="flex flex-col items-center space-y-2 p-4 text-indigo-400 hover:text-indigo-300"
                    >
                      <Video className="w-8 h-8 animate-bounce" />
                      <span className="text-xs font-bold text-slate-200">Click to Open Camera</span>
                    </button>
                  )}

                  <div className="flex items-center gap-2 pt-1">
                    {isCameraActive && (
                      <button
                        type="button"
                        onClick={capturePhoto}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-extrabold px-4 py-2 rounded-xl shadow-lg shadow-indigo-900/40 flex items-center gap-1.5 transition-all"
                      >
                        <Camera className="w-4 h-4" />
                        <span>Capture Photo</span>
                      </button>
                    )}
                    {isCameraActive && (
                      <button
                        type="button"
                        onClick={stopCamera}
                        className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-3 py-2 rounded-xl border border-slate-700 font-semibold"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <label className="cursor-pointer flex flex-col items-center space-y-3">
                  <div className="p-4 bg-indigo-500/10 text-indigo-400 rounded-2xl">
                    <Camera className="w-7 h-7" />
                  </div>
                  <span className="text-xs font-bold text-slate-200">Click or drag live subject photo</span>
                  <span className="text-[10px] text-slate-500 font-medium">Or switch to "Live Webcam" tab above</span>
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => handleLiveChange(e.target.files?.[0] ?? null)}
                  />
                </label>
              )}
            </div>
          </div>
        </div>

        {/* Real-Time OCR Intelligence & Field Extraction Dashboard */}
        {(ocrLoading || realtimeOcr || ocrError) && (
          <div className="relative overflow-hidden bg-gradient-to-br from-slate-900/95 via-slate-950/90 to-blue-950/30 border border-blue-500/30 rounded-3xl p-6 sm:p-8 shadow-2xl space-y-6 backdrop-blur-xl transition-all">
            {/* Top Glowing Laser Accent */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 via-cyan-400 to-indigo-500" />

            {/* OCR Processing State */}
            {ocrLoading && (
              <div className="space-y-4 py-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-cyan-500/10 text-cyan-400 rounded-xl animate-pulse">
                      <Zap className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-extrabold text-white flex items-center gap-2">
                        <span>Real-Time Neural OCR Stream</span>
                        <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
                      </h3>
                      <p className="text-[11px] text-slate-400">
                        Analyzing layout, resolving orientation, and validating ICAO / VIZ fields in real time…
                      </p>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono font-bold text-cyan-300 bg-cyan-950/60 border border-cyan-500/30 px-2.5 py-1 rounded-full uppercase tracking-wider animate-pulse">
                    Live Processing
                  </span>
                </div>

                {/* Progress bar shimmer */}
                <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                  <div className="h-full bg-gradient-to-r from-blue-500 via-cyan-400 to-indigo-500 rounded-full animate-pulse w-3/4" />
                </div>
              </div>
            )}

            {/* OCR Notice (non-fatal) */}
            {ocrError && !ocrLoading && (
              <div className="flex items-center gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-2xl text-amber-300 text-xs">
                <AlertCircle className="w-4.5 h-4.5 flex-shrink-0" />
                <span>{ocrError}</span>
              </div>
            )}

            {/* Completed OCR Real-Time Extraction Dashboard */}
            {realtimeOcr && !ocrLoading && (
              <div className="space-y-6">
                {/* Header with Badges & Metrics */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2.5">
                      <span className="relative flex h-2.5 w-2.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                      </span>
                      <h3 className="text-sm font-black uppercase tracking-wider text-emerald-400 flex items-center gap-2">
                        <span>⚡ Real-Time OCR Intelligence Stream</span>
                      </h3>
                      {realtimeOcr.extractionTimeMs && (
                        <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950/60 border border-cyan-500/30 px-2 py-0.5 rounded-full flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {realtimeOcr.extractionTimeMs}ms
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400">
                      All identity parameters parsed and automatically synchronized to the form.
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {/* Document Type Badge */}
                    <span className="text-[11px] font-bold px-3 py-1 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5" />
                      {realtimeOcr.detectedDocumentType?.replace('_', ' ') || 'DOCUMENT'}
                    </span>

                    {/* Confidence Badge */}
                    <span className="text-[11px] font-bold px-3 py-1 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
                      <Award className="w-3.5 h-3.5" />
                      {Math.round((realtimeOcr.confidence || 0.9) * 100)}% Accuracy
                    </span>

                    {/* MRZ Status Badge */}
                    {realtimeOcr.mrzValid ? (
                      <span className="text-[11px] font-bold px-3 py-1 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5 shadow-sm">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                        MRZ 100% Validated
                      </span>
                    ) : realtimeOcr.mrz ? (
                      <span className="text-[11px] font-bold px-3 py-1 rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1.5">
                        <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
                        MRZ Cross-Referenced
                      </span>
                    ) : (
                      <span className="text-[11px] font-bold px-3 py-1 rounded-xl bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5" />
                        Visual Inspection Zone
                      </span>
                    )}

                    {docFile && (
                      <button
                        type="button"
                        onClick={() => triggerRealtimeOcr(docFile)}
                        className="text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-xl border border-slate-700 flex items-center gap-1 font-semibold transition-all"
                        title="Re-run real-time OCR extraction"
                      >
                        <RefreshCw className="w-3 h-3" />
                        <span>Re-Scan</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Key-Value Fields Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
                  {/* Document Number */}
                  <div className="bg-slate-950/80 border border-slate-800/80 rounded-2xl p-3.5 hover:border-blue-500/40 transition-all group relative">
                    <div className="flex items-center justify-between text-[10px] uppercase font-bold text-slate-400 mb-1">
                      <span className="flex items-center gap-1">
                        <Hash className="w-3 h-3 text-blue-400" />
                        Document / Serial #
                      </span>
                      <button
                        type="button"
                        onClick={() => copyText(realtimeOcr.fields.documentNumber || realtimeOcr.fields.passportNumber || '', 'docNumber')}
                        className="text-slate-500 hover:text-cyan-300 transition-colors"
                        title="Copy to clipboard"
                      >
                        {copiedField === 'docNumber' ? <CheckCheck className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      </button>
                    </div>
                    <div className="text-sm font-black text-white font-mono tracking-wide">
                      {realtimeOcr.fields.documentNumber || realtimeOcr.fields.passportNumber || '—'}
                    </div>
                    <span className="text-[9px] text-emerald-400/80 font-medium flex items-center gap-1 mt-1">
                      <Check className="w-2.5 h-2.5" /> Auto-populated in form
                    </span>
                  </div>

                  {/* Subject Name */}
                  <div className="bg-slate-950/80 border border-slate-800/80 rounded-2xl p-3.5 hover:border-blue-500/40 transition-all group relative">
                    <div className="flex items-center justify-between text-[10px] uppercase font-bold text-slate-400 mb-1">
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3 text-blue-400" />
                        Holder Name
                      </span>
                      <button
                        type="button"
                        onClick={() => copyText(realtimeOcr.fields.name || '', 'name')}
                        className="text-slate-500 hover:text-cyan-300 transition-colors"
                        title="Copy to clipboard"
                      >
                        {copiedField === 'name' ? <CheckCheck className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      </button>
                    </div>
                    <div className="text-sm font-black text-white tracking-wide truncate">
                      {realtimeOcr.fields.name || '—'}
                    </div>
                    <span className="text-[9px] text-emerald-400/80 font-medium flex items-center gap-1 mt-1">
                      <Check className="w-2.5 h-2.5" /> Auto-populated in form
                    </span>
                  </div>

                  {/* Nationality */}
                  <div className="bg-slate-950/80 border border-slate-800/80 rounded-2xl p-3.5 hover:border-blue-500/40 transition-all">
                    <span className="text-xs font-black uppercase text-blue-400 font-mono tracking-wider flex items-center gap-1.5">
                      <Zap className="w-3.5 h-3.5 text-blue-400 animate-pulse" />
                      REAL-TIME OCR INTELLIGENCE STREAM
                    </span>
                    <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-lg bg-blue-500/10 text-blue-300 border border-blue-500/20 font-mono">
                      Detected: {realtimeOcr.detectedDocumentType || realtimeOcr.visualZone?.detectedDocumentType || 'NATIONAL ID'}
                    </span>
                    <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono flex items-center gap-1">
                      <Globe className="w-3 h-3 text-emerald-400" />
                      Country: {realtimeOcr.issuingCountry || realtimeOcr.visualZone?.issuingCountry || 'INDIA'}
                    </span>
                    <div className="text-sm font-black text-white font-mono">
                      {realtimeOcr.fields.nationality || '—'}
                    </div>
                    <span className="text-[9px] text-slate-500 font-medium mt-1 block">
                      ISO Country Standard
                    </span>
                  </div>

                  {/* Date of Birth */}
                  <div className="bg-slate-950/80 border border-slate-800/80 rounded-2xl p-3.5 hover:border-blue-500/40 transition-all">
                    <div className="text-[10px] uppercase font-bold text-slate-400 mb-1 flex items-center gap-1">
                      <Calendar className="w-3 h-3 text-blue-400" />
                      Date of Birth
                    </div>
                    <div className="text-sm font-black text-white font-mono">
                      {realtimeOcr.fields.dateOfBirth || '—'}
                    </div>
                    <span className="text-[9px] text-slate-500 font-medium mt-1 block">
                      YYYY-MM-DD
                    </span>
                  </div>

                  {/* Gender */}
                  <div className="bg-slate-950/80 border border-slate-800/80 rounded-2xl p-3.5 hover:border-blue-500/40 transition-all">
                    <div className="text-[10px] uppercase font-bold text-slate-400 mb-1">
                      Gender / Sex
                    </div>
                    <div className="text-sm font-black text-white">
                      {realtimeOcr.fields.gender === 'M' ? 'Male (M)' : realtimeOcr.fields.gender === 'F' ? 'Female (F)' : realtimeOcr.fields.gender || '—'}
                    </div>
                    <span className="text-[9px] text-slate-500 font-medium mt-1 block">
                      Identity Record
                    </span>
                  </div>

                  {/* Expiry Date / Validity */}
                  <div className="bg-slate-950/80 border border-slate-800/80 rounded-2xl p-3.5 hover:border-blue-500/40 transition-all">
                    <div className="text-[10px] uppercase font-bold text-slate-400 mb-1 flex items-center justify-between">
                      <span>Validity / Expiry</span>
                      {realtimeOcr.fields.expiryDate && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">
                          Recorded
                        </span>
                      )}
                    </div>
                    <div className="text-sm font-black text-white font-mono">
                      {realtimeOcr.fields.expiryDate || '—'}
                    </div>
                    <span className="text-[9px] text-slate-500 font-medium mt-1 block">
                      {realtimeOcr.fields.issueDate ? `Issue Date: ${realtimeOcr.fields.issueDate}` : 'Expiration Audit'}
                    </span>
                  </div>

                  {/* Father / Spouse Name (if present) */}
                  {realtimeOcr.visualZone?.fatherName && (
                    <div className="bg-slate-950/80 border border-slate-800/80 rounded-2xl p-3.5 hover:border-blue-500/40 transition-all">
                      <div className="text-[10px] uppercase font-bold text-slate-400 mb-1">
                        Father / Guardian / Spouse
                      </div>
                      <div className="text-sm font-black text-white truncate">
                        {String(realtimeOcr.visualZone.fatherName)}
                      </div>
                      <span className="text-[9px] text-slate-500 font-medium mt-1 block">
                        Relation Record
                      </span>
                    </div>
                  )}

                  {/* Address (if present) */}
                  {realtimeOcr.visualZone?.address && (
                    <div className="sm:col-span-2 bg-slate-950/80 border border-slate-800/80 rounded-2xl p-3.5 hover:border-blue-500/40 transition-all">
                      <div className="text-[10px] uppercase font-bold text-slate-400 mb-1">
                        Registered Address
                      </div>
                      <div className="text-xs font-semibold text-slate-200 line-clamp-2">
                        {String(realtimeOcr.visualZone.address)}
                      </div>
                    </div>
                  )}
                </div>

                {/* MRZ Lines Viewer (for Passports) OR National ID QR Audit (for National IDs) */}
                {realtimeOcr.detectedDocumentType === 'PASSPORT' && realtimeOcr.mrz ? (
                  <div className="bg-slate-950/90 border border-slate-800/90 rounded-2xl p-4 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <button
                        type="button"
                        onClick={() => setShowMrzDetails(!showMrzDetails)}
                        className="text-xs font-extrabold text-cyan-300 hover:text-cyan-200 flex items-center gap-1.5 transition-colors"
                      >
                        <FileCode className="w-3.5 h-3.5" />
                        <span>Machine Readable Zone (MRZ) Checksum Audit</span>
                        {showMrzDetails ? <EyeOff className="w-3 h-3 text-slate-500 ml-1" /> : <Eye className="w-3 h-3 text-slate-500 ml-1" />}
                      </button>

                      {realtimeOcr.mrzChecks && (
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {Object.entries(realtimeOcr.mrzChecks).map(([key, ok]) => (
                            <span
                              key={key}
                              className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded-md border ${
                                ok
                                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                                  : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                              }`}
                            >
                              {key}: {ok ? 'PASS ✓' : 'MISMATCH'}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {showMrzDetails && (
                      <div className="bg-black/80 rounded-xl p-3 border border-slate-800 overflow-x-auto">
                        <pre className="text-xs font-mono text-cyan-400 tracking-widest leading-relaxed whitespace-pre font-bold">
                          {realtimeOcr.mrz}
                        </pre>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-slate-950/90 border border-slate-800/90 rounded-2xl p-4 space-y-3 font-sans">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <span className="text-xs font-extrabold text-cyan-300 flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
                        <span>National ID QR Code &amp; Visual Audit Stream</span>
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        QR Detected: {realtimeOcr.qrDetected || realtimeOcr.visualZone?.qrDetected ? 'YES' : 'NO'}
                      </span>
                    </div>

                    <div className="grid sm:grid-cols-3 gap-3 text-xs pt-1">
                      <div className="bg-slate-900/90 p-2.5 rounded-xl border border-slate-800 space-y-1">
                        <span className="text-[10px] text-slate-400 font-bold block">QR CODE STATUS</span>
                        <span className="font-bold text-white">
                          {realtimeOcr.qrDetected || realtimeOcr.visualZone?.qrDetected ? 'Detected & Extracted' : 'No QR Code'}
                        </span>
                      </div>
                      <div className="bg-slate-900/90 p-2.5 rounded-xl border border-slate-800 space-y-1">
                        <span className="text-[10px] text-slate-400 font-bold block">DIGITAL SIGNATURE</span>
                        <span className="font-mono text-[11px] font-bold text-amber-300">
                          {realtimeOcr.qrSignatureStatus || realtimeOcr.visualZone?.qrSignatureStatus || (realtimeOcr.qrSignatureVerified ? 'DIGITALLY VERIFIED' : 'UNVERIFIED (No PKI Root)')}
                        </span>
                      </div>
                      <div className="bg-slate-900/90 p-2.5 rounded-xl border border-slate-800 space-y-1">
                        <span className="text-[10px] text-slate-400 font-bold block">QR ↔ OCR CONSISTENCY</span>
                        <span className="font-mono text-[11px] font-bold text-emerald-400">
                          {realtimeOcr.qrOcrMatchStatus || realtimeOcr.visualZone?.qrOcrMatchStatus || 'NOT_APPLICABLE'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Raw OCR Text Stream Toggle */}
                {realtimeOcr.visualZone?.rawText && (
                  <div>
                    <button
                      type="button"
                      onClick={() => setShowRawOcr(!showRawOcr)}
                      className="text-xs font-semibold text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition-colors"
                    >
                      {showRawOcr ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                      <span>{showRawOcr ? 'Hide Raw OCR Text Stream' : 'Inspect Raw Extracted OCR Stream'}</span>
                    </button>

                    {showRawOcr && (
                      <div className="mt-2 bg-black/70 border border-slate-800/80 rounded-2xl p-4 max-h-48 overflow-y-auto font-mono text-[11px] text-slate-300 leading-relaxed whitespace-pre-wrap">
                        {String(realtimeOcr.visualZone.rawText)}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="flex items-center gap-3 p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium">
            <AlertCircle className="w-4.5 h-4.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Action Button */}
        <button
          disabled={(!docFile && !docNumber) || busy}
          type="submit"
          className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-extrabold py-4 rounded-2xl shadow-xl shadow-blue-900/40 disabled:opacity-50 transition-all text-sm flex items-center justify-center gap-2.5"
        >
          {busy ? (
            <>
              <Loader2 className="w-4.5 h-4.5 animate-spin text-white" />
              <span>Executing Forensic Pipeline…</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4.5 h-4.5 text-blue-300" />
              <span>Execute Real-Time Forensic Screening</span>
            </>
          )}
        </button>
      </form>

      {/* Inline Results Panel (shown when result is available but navigation didn't occur) */}
      {result && !busy && (
        <div className="bg-slate-900/60 border border-slate-800/80 p-8 rounded-3xl shadow-2xl space-y-6 backdrop-blur-md">
          <div className="flex items-center gap-3">
            {result.finalResult === 'CLEAR' ? (
              <CheckCircle className="w-8 h-8 text-emerald-400" />
            ) : result.finalResult === 'REJECT' ? (
              <AlertCircle className="w-8 h-8 text-red-400" />
            ) : (
              <AlertCircle className="w-8 h-8 text-amber-400" />
            )}
            <div>
              <h2 className="text-xl font-bold text-white">Screening Complete</h2>
              <p className="text-xs text-slate-400">Verification #{result.verificationId} • Risk: {result.riskLevel}</p>
            </div>
            <div className="ml-auto flex flex-col items-end gap-1">
              <span className={`px-4 py-2 rounded-xl text-xs font-extrabold ${
                result.finalResult === 'CLEAR' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                result.finalResult === 'REJECT' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                'bg-amber-500/20 text-amber-400 border border-amber-500/30'
              }`}>{result.finalResult}</span>
              {result.finalResult === 'REJECT' && result.riskLevel === 'LOW' && (
                <span className="text-[10px] font-bold text-red-400 bg-red-950/80 px-2.5 py-0.5 rounded-lg border border-red-500/30">
                  Hard Security Rule Triggered
                </span>
              )}
            </div>
          </div>

          <div className="grid sm:grid-cols-3 gap-4">
            <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800/80">
              <p className="text-[10px] uppercase font-bold text-slate-400 mb-1">Risk Score</p>
              <p className="text-2xl font-bold text-white">{result.riskScore?.toFixed(1)}<span className="text-xs text-slate-400">/100</span></p>
            </div>
            <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800/80">
              <p className="text-[10px] uppercase font-bold text-slate-400 mb-1">Tamper Score</p>
              <p className="text-2xl font-bold text-white">{(result.tamperingScore * 100)?.toFixed(1)}%</p>
            </div>
            <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800/80">
              <p className="text-[10px] uppercase font-bold text-slate-400 mb-1">Face Match</p>
              <p className="text-2xl font-bold text-white">
                {result.faceMatchStatus === 'NOT_PERFORMED' || result.faceMatchStatus === 'SKIPPED'
                  ? 'N/A'
                  : `${(result.faceMatchScore * 100)?.toFixed(1)}%`}
              </p>
            </div>
          </div>

          {result.extracted && (
            <div className="bg-slate-950 p-5 rounded-2xl border border-slate-800/80 space-y-2">
              <p className="text-[10px] uppercase font-bold text-slate-400 mb-2">Extracted Data (OCR)</p>
              <div className="grid sm:grid-cols-2 gap-x-6 gap-y-1 text-xs">
                {result.extracted.name && <p><span className="text-slate-400">Name:</span> <span className="text-white font-bold">{result.extracted.name}</span></p>}
                {result.extracted.passportNumber && <p><span className="text-slate-400">Passport #:</span> <span className="text-white font-bold">{result.extracted.passportNumber}</span></p>}
                {result.extracted.nationality && <p><span className="text-slate-400">Nationality:</span> <span className="text-white font-bold">{result.extracted.nationality}</span></p>}
                {result.extracted.dateOfBirth && <p><span className="text-slate-400">DOB:</span> <span className="text-white font-bold">{result.extracted.dateOfBirth}</span></p>}
                {result.extracted.gender && <p><span className="text-slate-400">Gender:</span> <span className="text-white font-bold">{result.extracted.gender}</span></p>}
                {result.extracted.expiryDate && <p><span className="text-slate-400">Expiry:</span> <span className="text-white font-bold">{result.extracted.expiryDate}</span></p>}
              </div>
            </div>
          )}

          {result.reasons?.length > 0 && (
            <div className="bg-slate-950 p-5 rounded-2xl border border-slate-800/80 space-y-2">
              <p className="text-[10px] uppercase font-bold text-slate-400 mb-2">Forensic Audit Trail</p>
              <ul className="space-y-1.5">
                {result.reasons.map((r: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                    <span className="text-slate-600 select-none">•</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.verificationId && (
            <button
              onClick={() => nav(`/verification/${result.verificationId}`)}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-extrabold py-3 rounded-2xl shadow-xl text-xs flex items-center justify-center gap-2"
            >
              <FileText className="w-4 h-4" />
              View Full Forensic Report →
            </button>
          )}
        </div>
      )}

      {/* Progress Step Modal Overlay */}
      {busy && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex items-center justify-center p-6">
          <div className="bg-slate-900 border border-slate-800 p-8 rounded-3xl max-w-md w-full shadow-2xl space-y-6 text-center">
            <div className="relative w-16 h-16 mx-auto flex items-center justify-center">
              <div className="absolute inset-0 rounded-full border-4 border-blue-500/20 border-t-blue-500 animate-spin" />
              <ScanLine className="w-8 h-8 text-blue-400 animate-pulse" />
            </div>

            <div className="space-y-1">
              <h3 className="text-xl font-bold text-white">Screening Pipeline Running</h3>
              <p className="text-xs text-slate-400">Executing multi-factor AI &amp; cryptographic verification</p>
            </div>

            <div className="space-y-3 text-left bg-slate-950 p-5 rounded-2xl border border-slate-800/80">
              {scanSteps.map((step, idx) => (
                <div key={idx} className="flex items-center gap-3 text-xs">
                  {idx < scanStep ? (
                    <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  ) : idx === scanStep ? (
                    <Loader2 className="w-4 h-4 text-blue-400 animate-spin flex-shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-slate-700 flex-shrink-0" />
                  )}
                  <span className={idx === scanStep ? 'text-blue-300 font-bold' : idx < scanStep ? 'text-slate-300' : 'text-slate-600'}>
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
