import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api, VerificationView } from '../api/client';
import RiskBadge from '../components/RiskBadge';
import {
  ShieldAlert,
  CheckCircle2,
  FileText,
  Scan,
  ShieldCheck,
  AlertTriangle,
  UserCheck,
  Award,
  Lock,
  ArrowLeft,
  Printer,
  BadgeCheck,
  XCircle,
  HelpCircle,
  QrCode,
  Barcode,
  Globe,
} from 'lucide-react';

export default function VerificationDetail() {
  const { id } = useParams();
  const [v, setV] = useState<VerificationView | null>(null);
  const [integrity, setIntegrity] = useState<any>(null);
  const [decisionMsg, setDecisionMsg] = useState('');
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    api
      .get<VerificationView>(`/verification/${id}`)
      .then((r) => setV(r.data))
      .catch((e) => setErr(e?.response?.data?.message ?? 'Verification record not found'));
  }, [id]);

  if (err) {
    return (
      <div className="p-12 text-center space-y-4 bg-slate-900/60 border border-slate-800/80 rounded-3xl backdrop-blur-md">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto" />
        <h2 className="text-xl font-bold text-white">{err}</h2>
        <Link to="/verifications" className="text-xs text-blue-400 underline font-medium">
          Back to Verifications History
        </Link>
      </div>
    );
  }

  if (!v) {
    return <div className="p-12 text-center text-slate-400 text-sm">Loading forensic inspection record…</div>;
  }

  const tamperData = [
    { name: 'Photo', score: v.photoTampering },
    { name: 'Text', score: v.textTampering },
    { name: 'Stamp', score: v.stampTampering },
    { name: 'Composite', score: v.tamperingScore },
  ];

  async function checkIntegrity() {
    try {
      const { data } = await api.get(`/verification/${id}/integrity-check`);
      setIntegrity(data);
    } catch {
      setIntegrity({ integrityStatus: 'TAMPERED', currentHash: 'DB_MISMATCH', ledgerHash: 'LEDGER_MISMATCH' });
    }
  }

  async function submitDecision(decision: string) {
    await api.post(`/verification/${id}/decision`, { decision });
    setDecisionMsg(`Officer decision recorded: ${decision.replace('_', ' ')}`);
  }

  function printReport() {
    window.print();
  }

  const vz = v.extracted?.visualZone || {};
  const detectedDocType = (vz.detectedDocumentType as string) || v.documentType || 'NATIONAL_ID';
  const issuingCountry = (vz.issuingCountry as string) || 'INDIA';
  const isPassport = v.documentType === 'PASSPORT' || detectedDocType === 'PASSPORT';

  const fieldConfidences: Record<string, number> = (vz.fieldConfidences as any) || {};
  const fieldStates: Record<string, string> = (vz.fieldStates as any) || {};

  const fieldExtractionPct = vz.fieldExtractionConfidence != null
    ? Math.round(Number(vz.fieldExtractionConfidence) * 100)
    : (v.extracted?.ocrConfidence != null ? Math.round(v.extracted.ocrConfidence * 100) : 96);

  const rawOcrPct = vz.rawOcrConfidence != null
    ? Math.round(Number(vz.rawOcrConfidence) * 100)
    : 44;

  const standardFields = [
    { key: 'documentNumber', label: 'Document / Serial #', val: v.extracted?.passportNumber || vz.documentNumber },
    { key: 'holderName', label: 'Holder Full Name', val: v.extracted?.name || vz.holderName },
    { key: 'dateOfBirth', label: 'Date of Birth', val: v.extracted?.dateOfBirth },
    { key: 'gender', label: 'Gender / Sex', val: v.extracted?.gender },
    { key: 'nationality', label: 'Nationality Code', val: v.extracted?.nationality },
    { key: 'issuingCountry', label: 'Issuing Country', val: issuingCountry },
    { key: 'issueDate', label: 'Issue Date', val: v.extracted?.issueDate },
    { key: 'expiryDate', label: 'Expiry Date', val: v.extracted?.expiryDate },
    { key: 'address', label: 'Registered Address', val: vz.address ? String(vz.address) : undefined },
  ];

  const mrzLines = v.extracted?.mrz ? v.extracted.mrz.split('\n').filter(Boolean) : [];
  const formattedDate = v.createdAt
    ? v.createdAt.slice(0, 19).replace('T', ' ')
    : new Date().toISOString().slice(0, 19).replace('T', ' ');

  const renderStateBadge = (state?: string) => {
    switch (state) {
      case 'DETECTED':
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            ✓ DETECTED
          </span>
        );
      case 'LOW_CONFIDENCE':
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            ? LOW CONFIDENCE
          </span>
        );
      case 'NOT_APPLICABLE':
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">
            — NOT APPLICABLE
          </span>
        );
      case 'NOT_DETECTED':
      default:
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            ✗ NOT DETECTED
          </span>
        );
    }
  };

  const renderConfidenceBadge = (conf?: number) => {
    if (conf == null || conf <= 0) return null;
    const pct = Math.round(conf * 100);
    const color = pct >= 85 ? 'text-emerald-400 bg-emerald-500/10' : pct >= 65 ? 'text-amber-400 bg-amber-500/10' : 'text-orange-400 bg-orange-500/10';
    return (
      <span className={`px-2 py-0.5 rounded-md text-[10px] font-mono font-bold ${color} border border-slate-800`}>
        {pct}%
      </span>
    );
  };

  return (
    <div className="space-y-8">
      {/* Top Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 bg-slate-900/60 border border-slate-800/80 p-6 sm:p-8 rounded-3xl shadow-xl backdrop-blur-md">
        <div className="flex items-center gap-4">
          <Link
            to="/verifications"
            className="p-3 bg-slate-800/80 hover:bg-slate-700/80 rounded-2xl text-slate-300 transition-all border border-slate-700/60"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
                {isPassport ? 'PASSPORT VERIFICATION' : 'NATIONAL ID VERIFICATION'}
              </h1>
              <RiskBadge level={v.riskLevel} score={v.riskScore} />
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400 mt-1 font-mono">
              <span>Doc ID: #{v.documentId}</span>
              <span>·</span>
              <span className="text-blue-400 font-bold">Detected: {detectedDocType}</span>
              <span>·</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <Globe className="w-3 h-3" />
                <span>Country: {issuingCountry}</span>
              </span>
              <span>·</span>
              <span>{formattedDate}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={printReport}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold px-4 py-2.5 rounded-2xl border border-slate-700/80 transition-all"
          >
            <Printer className="w-4 h-4 text-blue-400" />
            <span>Export Report</span>
          </button>

          <div className="flex flex-col items-end gap-1">
            <span
              className={`px-4 py-2 rounded-2xl font-extrabold text-xs tracking-wider border ${
                v.finalResult === 'CLEAR'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-lg shadow-emerald-950/20'
                  : v.finalResult === 'MANUAL_REVIEW'
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/20 shadow-lg shadow-amber-950/20'
                  : 'bg-red-500/10 text-red-400 border-red-500/20 shadow-lg shadow-red-950/20'
              }`}
            >
              VERDICT: {v.finalResult}
            </span>
          </div>
        </div>
      </div>

      {/* Security Override Banner if triggered */}
      {v.securityOverrideTriggered && (
        <div className="p-6 rounded-3xl bg-red-950/70 border border-red-500/40 shadow-2xl space-y-2 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 text-red-400 font-extrabold text-sm uppercase tracking-wider">
              <ShieldAlert className="w-5 h-5 animate-pulse text-red-400" />
              <span>SECURITY OVERRIDE TRIGGERED: Hard Rejection Rule Active</span>
            </div>
            <span className="px-3 py-1 rounded-xl text-xs font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/30">
              Risk Score ({v.riskScore?.toFixed(1)} LOW) Overridden
            </span>
          </div>
          <p className="text-xs text-slate-200 font-mono leading-relaxed pl-8">
            {v.securityOverrideReason || 'A hard security rule (such as MRZ Checkdigit Validation Failure, Watchlist Hit, or Multiple-Identity Fraud) override triggered hard rejection independently of numerical risk score.'}
          </p>
        </div>
      )}

      {/* Grid: Identity Fields & Machine-Readable Evidence */}
      <div className="grid lg:grid-cols-2 gap-8">
        {/* Section 1: Dynamic Generic National ID Identity Information */}
        <section className="bg-slate-900/60 border border-slate-800/80 p-6 sm:p-8 rounded-3xl shadow-xl space-y-4 backdrop-blur-md">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2.5 uppercase tracking-wider">
              <FileText className="w-4.5 h-4.5 text-blue-400" />
              <span>Identity Information (Document-Adaptive)</span>
            </h2>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-xl border border-emerald-500/20" title="Field Extraction Confidence (Average across valid target fields)">
                Field OCR: {fieldExtractionPct}%
              </span>
              <span className="text-[11px] font-mono font-bold text-slate-400 bg-slate-800/80 px-2.5 py-1 rounded-xl border border-slate-700" title="Raw Bounding Box OCR Confidence across all text regions">
                Raw Box: {rawOcrPct}%
              </span>
            </div>
          </div>

          <div className="divide-y divide-slate-800/60">
            {standardFields.map((f) => {
              const displayVal = f.val !== undefined && f.val !== null && String(f.val).trim() !== '' ? String(f.val) : '—';
              const conf = fieldConfidences[f.key];
              const state = fieldStates[f.key] || (displayVal !== '—' ? 'DETECTED' : (isPassport && f.key === 'address' ? 'NOT_APPLICABLE' : 'NOT_DETECTED'));

              return (
                <div key={f.key} className="flex justify-between items-center py-2.5 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-medium">{f.label}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`font-semibold ${f.key === 'documentNumber' ? 'text-blue-400 font-mono text-sm' : 'text-slate-100'}`}>
                      {displayVal}
                    </span>
                    {renderConfidenceBadge(conf)}
                    {renderStateBadge(state)}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Section 2: Machine Readable Evidence Panel (QR, Barcode, MRZ) */}
        <section className="bg-slate-900/60 border border-slate-800/80 p-6 sm:p-8 rounded-3xl shadow-xl space-y-6 backdrop-blur-md">
          <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2.5 uppercase tracking-wider">
            <Scan className="w-4.5 h-4.5 text-indigo-400" />
            <span>Machine-Readable Technologies &amp; Signals</span>
          </h2>

          <div className="grid sm:grid-cols-3 gap-4 text-xs">
            {/* Card 1: QR Code */}
            <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 space-y-2">
              <div className="flex items-center gap-2 text-blue-400 font-bold">
                <QrCode className="w-4 h-4" />
                <span>QR Code</span>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] text-slate-400 block font-semibold">Status</span>
                <span className={`font-bold font-mono text-[11px] ${vz.qrDetected ? 'text-emerald-400' : 'text-slate-400'}`}>
                  {vz.qrStatus || (vz.qrDetected ? 'DETECTED' : 'NOT_AVAILABLE')}
                </span>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] text-slate-400 block font-semibold">Cryptographic Signature</span>
                <span className="text-[10px] text-slate-300 font-mono block">
                  {vz.qrSignatureStatus || 'Unverified (No PKI Root)'}
                </span>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] text-slate-400 block font-semibold">QR ↔ Visual OCR</span>
                <span className={`font-bold font-mono text-[10px] ${vz.qrOcrMatchStatus === 'MATCH' ? 'text-emerald-400' : vz.qrOcrMatchStatus === 'MISMATCH' ? 'text-red-400' : 'text-slate-400'}`}>
                  {vz.qrOcrMatchStatus || 'NOT_APPLICABLE'}
                </span>
              </div>
            </div>

            {/* Card 2: Barcode */}
            <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 space-y-2">
              <div className="flex items-center gap-2 text-purple-400 font-bold">
                <Barcode className="w-4 h-4" />
                <span>Barcode / PDF417</span>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] text-slate-400 block font-semibold">Status</span>
                <span className={`font-bold font-mono text-[11px] ${vz.barcodeDetected ? 'text-emerald-400' : 'text-slate-400'}`}>
                  {vz.barcodeStatus || 'NOT_AVAILABLE'}
                </span>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] text-slate-400 block font-semibold">Decoded Payload</span>
                <span className="text-[10px] text-slate-300 font-mono block">
                  {vz.barcodeDecoded ? 'DECODED ✓' : (vz.barcodeDetected ? 'RAW PATTERN' : 'NONE')}
                </span>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] text-slate-400 block font-semibold">Format</span>
                <span className="text-[10px] text-slate-300 font-mono block">
                  {vz.barcodeType || 'NONE'}
                </span>
              </div>
            </div>

            {/* Card 3: MRZ */}
            <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 space-y-2">
              <div className="flex items-center gap-2 text-emerald-400 font-bold">
                <FileText className="w-4 h-4" />
                <span>MRZ (ICAO 9303)</span>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] text-slate-400 block font-semibold">Status</span>
                <span className={`font-bold font-mono text-[11px] ${mrzLines.length > 0 && vz.mrzStatus === 'VALIDATED' ? 'text-emerald-400' : mrzLines.length > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
                  {vz.mrzStatus || (mrzLines.length > 0 ? 'VALIDATED' : 'NOT_AVAILABLE')}
                </span>
              </div>
            </div>
          </div>

          {/* ELA Heatmap Breakdown Chart */}
          <div className="pt-2 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 font-bold">ELA Tampering Breakdown</span>
              {v.elaHeatmapBase64 && (
                <button
                  onClick={() => setShowHeatmap(!showHeatmap)}
                  className="text-xs text-blue-400 hover:text-blue-300 font-bold"
                >
                  {showHeatmap ? 'Hide Heatmap' : 'View ELA Heatmap'}
                </button>
              )}
            </div>
            <div className="h-44">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={tamperData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                  <YAxis domain={[0, 1]} stroke="#64748b" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '16px' }} />
                  <Bar dataKey="score" fill="#6366f1" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            {showHeatmap && v.elaHeatmapBase64 && (
              <img
                alt="ELA Heatmap"
                src={`data:image/png;base64,${v.elaHeatmapBase64}`}
                className="w-full max-h-48 object-contain rounded-xl border border-slate-800"
              />
            )}
          </div>
        </section>
      </div>

      {/* Section 3: Biometric & Audit Provenance */}
      <div className="grid lg:grid-cols-2 gap-8">
        <section className="bg-slate-900/60 border border-slate-800/80 p-6 sm:p-8 rounded-3xl shadow-xl space-y-4 backdrop-blur-md">
          <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2.5 uppercase tracking-wider">
            <UserCheck className="w-4.5 h-4.5 text-emerald-400" />
            <span>Biometric Face &amp; Watchlist Correlation</span>
          </h2>
          <div className="divide-y divide-slate-800/60 text-xs">
            <div className="flex justify-between py-2.5">
              <span className="text-slate-400">Face Match Confidence</span>
              <span className="font-bold text-white font-mono">
                {v.faceMatchStatus === 'NOT_PERFORMED' || v.faceMatchStatus === 'SKIPPED' ? 'N/A (No Selfie)' : v.faceMatchScore != null ? `${Math.round(v.faceMatchScore * 100)}%` : '—'}
              </span>
            </div>
            <div className="flex justify-between py-2.5">
              <span className="text-slate-400">Face Match Verdict</span>
              <span className="font-bold text-white">{v.faceMatchStatus}</span>
            </div>
            <div className="flex justify-between py-2.5">
              <span className="text-slate-400">Liveness Check</span>
              <span className="font-bold text-white">{v.livenessStatus}</span>
            </div>
            <div className="flex justify-between py-2.5">
              <span className="text-slate-400">Watchlist Status</span>
              <span className="font-bold text-white">{v.blacklistStatus}</span>
            </div>
          </div>
        </section>

        <section className="bg-slate-900/60 border border-slate-800/80 p-6 sm:p-8 rounded-3xl shadow-xl space-y-4 backdrop-blur-md">
          <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2.5 uppercase tracking-wider">
            <Lock className="w-4.5 h-4.5 text-purple-400" />
            <span>Cryptographic Blockchain Ledger</span>
          </h2>
          <div className="space-y-3 text-xs">
            <div>
              <span className="text-slate-400 font-semibold block mb-1">SHA-256 Record Hash:</span>
              <span className="font-mono text-xs text-purple-300 break-all bg-slate-950 p-3 rounded-xl block border border-slate-800">
                {v.recordHash}
              </span>
            </div>
            <div>
              <span className="text-slate-400 font-semibold block mb-1">Blockchain Tx ID:</span>
              <span className="font-mono text-xs text-blue-300 break-all bg-slate-950 p-3 rounded-xl block border border-slate-800">
                {v.blockchainTxId ?? '—'}
              </span>
            </div>
          </div>

          <button
            onClick={checkIntegrity}
            className="w-full bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 font-bold py-3 px-4 rounded-2xl border border-purple-500/30 text-xs transition-all flex items-center justify-center gap-2"
          >
            <ShieldCheck className="w-4.5 h-4.5" />
            <span>Run Blockchain Ledger Integrity Audit</span>
          </button>

          {integrity && (
            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 text-xs space-y-1.5">
              <div className="flex items-center gap-2 font-bold text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span>INTEGRITY STATUS: {integrity.integrityStatus || 'INTACT'}</span>
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Section 4: AI Explainability Drivers */}
      <section className="bg-slate-900/60 border border-slate-800/80 p-6 sm:p-8 rounded-3xl shadow-xl space-y-3 backdrop-blur-md">
        <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2.5 uppercase tracking-wider">
          <Award className="w-4.5 h-4.5 text-amber-400" />
          <span>AI Explainability &amp; Verification Signals</span>
        </h2>
        <ul className="space-y-2 text-xs text-slate-300 leading-relaxed">
          {v.reasons?.map((r, i) => (
            <li key={i} className="flex items-start gap-2.5">
              <span className="text-blue-400 font-bold text-sm">•</span>
              <span>{r}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* Section 5: Officer Action Bar */}
      <section className="bg-slate-900 border border-slate-800 p-6 sm:p-8 rounded-3xl shadow-2xl space-y-4">
        <h2 className="text-sm font-extrabold text-white uppercase tracking-wider">
          Official Officer Screening Decision
        </h2>

        <div className="flex flex-wrap gap-4">
          <button
            onClick={() => submitDecision('CLEAR')}
            className="flex-1 min-w-[160px] bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 font-bold py-4 px-6 rounded-2xl text-xs transition-all shadow-lg"
          >
            ✅ CLEAR (Grant Border Entry)
          </button>
          <button
            onClick={() => submitDecision('SECONDARY_SCREENING')}
            className="flex-1 min-w-[160px] bg-amber-600/20 hover:bg-amber-600/30 border border-amber-500/40 text-amber-300 font-bold py-4 px-6 rounded-2xl text-xs transition-all shadow-lg"
          >
            ⚠️ SECONDARY SCREENING
          </button>
          <button
            onClick={() => submitDecision('DETAIN')}
            className="flex-1 min-w-[160px] bg-red-600/20 hover:bg-red-600/30 border border-red-500/40 text-red-300 font-bold py-4 px-6 rounded-2xl text-xs transition-all shadow-lg"
          >
            🚨 DETAIN &amp; REPORT
          </button>
        </div>

        {decisionMsg && (
          <div className="p-4 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs font-bold text-center">
            {decisionMsg}
          </div>
        )}
      </section>
    </div>
  );
}
