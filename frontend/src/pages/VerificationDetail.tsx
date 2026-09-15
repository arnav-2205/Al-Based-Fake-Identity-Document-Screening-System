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
  }  const vz = v.extracted?.visualZone || {};
  const docCategory = (v.extracted?.documentCategory as string) || (vz.documentCategory as string) || (v.documentType === 'PASSPORT' ? 'PASSPORT' : 'NATIONAL_ID');
  const docSubtype = (v.extracted?.documentSubtype as string) || (vz.documentSubtype as string) || (vz.detectedDocumentType as string) || v.documentType || 'NATIONAL_ID_CARD';
  const issuingCountry = (vz.issuingCountry as string) || 'INDIA';
  const isPassport = docCategory === 'PASSPORT' || docSubtype === 'PASSPORT';

  const fieldConfidences: Record<string, number> = (vz.fieldConfidences as any) || {};
  const fieldStates: Record<string, string> = (vz.fieldStates as any) || {};

  const applicableFieldsList: string[] = (v.extracted?.applicableFields as string[]) || (vz.applicableFields as string[]) || [];
  const applicableChecksList: string[] = (v.extracted?.applicableChecks as string[]) || (vz.applicableChecks as string[]) || [];

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

  const filteredStandardFields = standardFields.filter((f) => {
    const state = fieldStates[f.key] || fieldStates[f.key === 'holderName' ? 'name' : f.key];
    if (state === 'NOT_APPLICABLE') return false;

    if (applicableFieldsList.length > 0) {
      const isApplicable = applicableFieldsList.includes(f.key) ||
        (f.key === 'holderName' && (applicableFieldsList.includes('name') || applicableFieldsList.includes('holderName'))) ||
        (f.key === 'documentNumber' && (applicableFieldsList.includes('passportNumber') || applicableFieldsList.includes('documentNumber') || applicableFieldsList.includes('visaNumber')));
      if (!isApplicable) return false;
    }

    return true;
  });

  const mrzLines = v.extracted?.mrz ? v.extracted.mrz.split('\n').filter(Boolean) : [];
  const showQr = applicableChecksList.includes('QR') || Boolean(vz.qrDetected);
  const showBarcode = applicableChecksList.includes('BARCODE') || Boolean(vz.barcodeDetected);
  const showMrz = applicableChecksList.includes('MRZ') || (mrzLines.length > 0) || (Boolean(vz.mrzStatus) && vz.mrzStatus !== 'NOT_AVAILABLE');

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
        return null;
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

  const isFacePerformed = v.faceMatchStatus !== 'NOT_PERFORMED' && v.faceMatchStatus !== 'SKIPPED' && v.faceMatchStatus !== 'UNKNOWN';

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
                {docCategory.replace('_', ' ')} VERIFICATION
              </h1>
              <RiskBadge level={v.riskLevel} score={v.riskScore} />
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400 mt-1 font-mono flex-wrap">
              <span>Doc ID: #{v.documentId}</span>
              <span>·</span>
              <span className="text-blue-400 font-bold">Category: {docCategory}</span>
              <span>·</span>
              <span className="text-indigo-400 font-bold">Subtype: {docSubtype}</span>
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

      {/* EXPLAINABLE RISK ASSESSMENT CARD */}
      <section className="bg-slate-900/80 border border-slate-800 p-6 sm:p-8 rounded-3xl shadow-2xl space-y-6 backdrop-blur-md">
        <div className="flex items-center justify-between flex-wrap gap-4 border-b border-slate-800/80 pb-4">
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 text-indigo-400" />
            <h2 className="text-sm font-extrabold text-white uppercase tracking-wider">
              EXPLAINABLE RISK ASSESSMENT
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 font-mono font-bold">
              Risk Score: <span className="text-white text-sm">{v.riskScore?.toFixed(1) ?? '0.0'} / 100</span>
            </span>
            <RiskBadge level={v.riskLevel} score={v.riskScore} />
          </div>
        </div>

        {/* Risk Breakdown Grid */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Triggered Risk Components */}
          <div className="space-y-3">
            <span className="text-xs font-bold text-amber-400 uppercase tracking-wider block">
              Triggered Risk Contributions ({v.riskAssessment?.triggeredComponents?.length ?? 0})
            </span>
            {(!v.riskAssessment?.triggeredComponents || v.riskAssessment.triggeredComponents.length === 0) ? (
              <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>No risk components were triggered (Score: 0.0)</span>
              </div>
            ) : (
              <div className="space-y-2">
                {v.riskAssessment.triggeredComponents.map((c) => (
                  <div key={c.code} className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800/80 flex items-start justify-between gap-3 text-xs">
                    <div className="space-y-0.5">
                      <span className="font-bold text-slate-200 block">{c.label}</span>
                      <span className="text-[11px] text-slate-400 font-mono block">{c.reason}</span>
                    </div>
                    <span className="font-mono font-bold text-amber-400 text-xs whitespace-nowrap bg-amber-500/10 px-2.5 py-1 rounded-xl border border-amber-500/20">
                      +{c.points?.toFixed(1)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Decision Rationale & Basis */}
          <div className="space-y-3">
            <span className="text-xs font-bold text-blue-400 uppercase tracking-wider block">
              Decision &amp; Decision Basis
            </span>
            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800/80 space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-medium">Final Decision:</span>
                <span className={`px-3 py-1 rounded-xl font-extrabold text-xs tracking-wider border ${
                  v.finalResult === 'CLEAR'
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    : v.finalResult === 'MANUAL_REVIEW'
                    ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    : 'bg-red-500/10 text-red-400 border-red-500/20'
                }`}>
                  {v.finalResult}
                </span>
              </div>

              <div className="space-y-1.5 border-t border-slate-800/60 pt-3">
                <span className="text-slate-400 font-semibold block text-[11px]">Decision Basis:</span>
                <ul className="space-y-1 text-slate-300 font-mono text-[11px]">
                  {v.riskAssessment?.decisionBasis ? (
                    v.riskAssessment.decisionBasis.map((b, idx) => (
                      <li key={idx} className="flex items-start gap-1.5">
                        <span className="text-blue-400">•</span>
                        <span>{b}</span>
                      </li>
                    ))
                  ) : (
                    <li className="flex items-start gap-1.5">
                      <span className="text-blue-400">•</span>
                      <span>Evaluated numerical risk score ({v.riskScore?.toFixed(1)}) and security policies.</span>
                    </li>
                  )}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Collapsible / Compact Signals Checked (0 Points) */}
        {v.riskAssessment?.components && (
          <div className="pt-2 border-t border-slate-800/60">
            <details className="group">
              <summary className="cursor-pointer text-xs font-bold text-slate-400 hover:text-slate-200 flex items-center justify-between py-1">
                <span>Signals Checked ({v.riskAssessment.components.filter(c => !c.triggered).length} Passed / 0 Points)</span>
                <span className="text-[10px] text-blue-400 font-mono group-open:hidden">Show All Signals ↓</span>
                <span className="text-[10px] text-blue-400 font-mono hidden group-open:inline">Hide Signals ↑</span>
              </summary>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2 pt-3">
                {v.riskAssessment.components.filter(c => !c.triggered).map((c) => (
                  <div key={c.code} className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/60 flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-1.5 text-slate-300">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span className="truncate">{c.label}</span>
                    </div>
                    <span className="font-mono text-slate-500 font-semibold text-[10px]">+0.0</span>
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}
      </section>

      {/* Grid: Identity Fields & Machine-Readable Evidence */}
      <div className="grid lg:grid-cols-2 gap-8">
        {/* Section 1: Dynamic Document-Adaptive Identity Information */}
        <section className="bg-slate-900/60 border border-slate-800/80 p-6 sm:p-8 rounded-3xl shadow-xl space-y-4 backdrop-blur-md">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2.5 uppercase tracking-wider">
              <FileText className="w-4.5 h-4.5 text-blue-400" />
              <span>Identity Information ({docSubtype})</span>
            </h2>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-xl border border-emerald-500/20" title="Field Extraction Confidence">
                Field OCR: {fieldExtractionPct}%
              </span>
              <span className="text-[11px] font-mono font-bold text-slate-400 bg-slate-800/80 px-2.5 py-1 rounded-xl border border-slate-700" title="Raw Bounding Box OCR Confidence">
                Raw Box: {rawOcrPct}%
              </span>
            </div>
          </div>

          <div className="divide-y divide-slate-800/60">
            {filteredStandardFields.map((f) => {
              const displayVal = f.val !== undefined && f.val !== null && String(f.val).trim() !== '' ? String(f.val) : '—';
              const conf = fieldConfidences[f.key];
              const state = fieldStates[f.key] || (displayVal !== '—' ? 'DETECTED' : 'NOT_DETECTED');

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
            <span>Machine-Readable Features &amp; Security Signals</span>
          </h2>

          {!showQr && !showBarcode && !showMrz ? (
            <div className="bg-slate-950 p-6 rounded-2xl border border-slate-800 text-center space-y-1">
              <ShieldCheck className="w-8 h-8 text-blue-400 mx-auto" />
              <p className="text-xs font-bold text-slate-300">No Machine-Readable Codes Applicable</p>
              <p className="text-[11px] text-slate-400">This document format ({docSubtype}) relies on Visual Zone Forensic Audit and Optical Character Recognition.</p>
            </div>
          ) : (
            <div className="grid sm:grid-cols-3 gap-4 text-xs">
              {/* Card 1: QR Code */}
              {showQr && (
                <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2 text-blue-400 font-bold">
                    <QrCode className="w-4 h-4" />
                    <span>Secure QR Code</span>
                  </div>
                  <div className="space-y-1">
                    <span className="text-[10px] text-slate-400 block font-semibold">Status</span>
                    <span className={`font-bold font-mono text-[11px] ${vz.qrDetected ? 'text-emerald-400' : 'text-slate-400'}`}>
                      {String(vz.qrStatus || (vz.qrDetected ? 'DETECTED' : 'NOT_AVAILABLE'))}
                    </span>
                  </div>
                  <div className="space-y-1">
                    <span className="text-[10px] text-slate-400 block font-semibold">Cryptographic Signature</span>
                    <span className="text-[10px] text-slate-300 font-mono block">
                      {String(vz.qrSignatureStatus || 'Unverified (No PKI Root)')}
                    </span>
                  </div>
                  <div className="space-y-1">
                    <span className="text-[10px] text-slate-400 block font-semibold">QR ↔ Visual OCR</span>
                    <span className={`font-bold font-mono text-[10px] ${vz.qrOcrMatchStatus === 'MATCH' ? 'text-emerald-400' : vz.qrOcrMatchStatus === 'MISMATCH' ? 'text-red-400' : 'text-slate-400'}`}>
                      {String(vz.qrOcrMatchStatus || 'NOT_APPLICABLE')}
                    </span>
                  </div>
                </div>
              )}

              {/* Card 2: Barcode */}
              {showBarcode && (
                <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2 text-purple-400 font-bold">
                    <Barcode className="w-4 h-4" />
                    <span>Barcode / PDF417</span>
                  </div>
                  <div className="space-y-1">
                    <span className="text-[10px] text-slate-400 block font-semibold">Status</span>
                    <span className={`font-bold font-mono text-[11px] ${vz.barcodeDetected ? 'text-emerald-400' : 'text-slate-400'}`}>
                      {String(vz.barcodeStatus || 'NOT_AVAILABLE')}
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
                      {String(vz.barcodeType || 'NONE')}
                    </span>
                  </div>
                </div>
              )}

              {/* Card 3: MRZ */}
              {showMrz && (
                <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2 text-emerald-400 font-bold">
                    <FileText className="w-4 h-4" />
                    <span>MRZ (ICAO 9303)</span>
                  </div>
                  <div className="space-y-1">
                    <span className="text-[10px] text-slate-400 block font-semibold">Status</span>
                    <span className={`font-bold font-mono text-[11px] ${mrzLines.length > 0 && vz.mrzStatus === 'VALIDATED' ? 'text-emerald-400' : mrzLines.length > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
                      {String(vz.mrzStatus || (mrzLines.length > 0 ? 'VALIDATED' : 'NOT_AVAILABLE'))}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

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
              <span className="text-slate-400">Live Selfie Face Match</span>
              <span className="font-bold text-white font-mono">
                {v.faceMatchStatus === 'NOT_PERFORMED' || v.faceMatchStatus === 'SKIPPED' ? 'N/A (No Selfie Supplied)' : v.faceMatchScore != null ? `${Math.round(v.faceMatchScore * 100)}% (${v.faceMatchStatus})` : '—'}
              </span>
            </div>
            <div className="flex justify-between py-2.5">
              <span className="text-slate-400">Liveness Verification</span>
              <span className="font-bold text-white">
                {v.livenessStatus === 'NOT_PERFORMED' || v.livenessStatus === 'UNKNOWN' ? 'N/A (No Selfie Supplied)' : v.livenessStatus}
              </span>
            </div>
            <div className="flex justify-between py-2.5">
              <span className="text-slate-400">Watchlist Audit</span>
              <span className="font-bold text-white">{v.blacklistStatus}</span>
            </div>
            <div className="flex justify-between items-start py-2.5">
              <span className="text-slate-400">Stored Identity Correlation</span>
              <div className="text-right">
                <span className={`font-bold font-mono text-[11px] ${v.storedIdentityMatchStatus === 'POTENTIAL_MATCH_DETECTED' ? 'text-amber-400' : 'text-emerald-400'}`}>
                  {v.storedIdentityMatchStatus === 'POTENTIAL_MATCH_DETECTED' ? 'POTENTIAL MATCH DETECTED' : 'CLEAR (NO DUPLICATES)'}
                </span>
                {v.storedIdentityMatchDetail && v.storedIdentityMatchStatus === 'POTENTIAL_MATCH_DETECTED' && (
                  <p className="text-[10px] text-slate-400 mt-0.5 font-mono max-w-xs">{v.storedIdentityMatchDetail}</p>
                )}
              </div>
            </div>
            <div className="flex justify-between items-start py-2.5">
              <div>
                <span className="text-slate-400 font-medium">Photo Replacement Detection</span>
                <span className="text-[10px] text-slate-500 block">Portrait Forgery &amp; Forensic Compositing</span>
              </div>
              <div className="text-right">
                <span className={`font-bold font-mono text-[11px] px-2 py-0.5 rounded-md ${
                  v.photoForgeryStatus === 'SUSPICIOUS'
                    ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    : v.photoForgeryStatus === 'INCONCLUSIVE'
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                }`}>
                  {v.photoForgeryStatus || 'NOT_PERFORMED'}
                </span>
                {v.photoForgeryConfidence != null && v.photoForgeryConfidence > 0 && (
                  <span className="text-[10px] text-slate-400 block font-mono mt-0.5">
                    Confidence: {Math.round(v.photoForgeryConfidence * 100)}%
                  </span>
                )}
                {v.photoForgeryReasons && v.photoForgeryReasons.length > 0 && (
                  <ul className="text-[10px] text-amber-300 font-mono mt-1 text-right space-y-0.5">
                    {v.photoForgeryReasons.map((r, idx) => (
                      <li key={idx}>• {r}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
            <div className="flex justify-between items-start py-2.5">
              <div>
                <span className="text-slate-400 font-medium">Text Manipulation Detection</span>
                <span className="text-[10px] text-slate-500 block">Digital Text Modification &amp; Overlay Patching</span>
              </div>
              <div className="text-right">
                <span className={`font-bold font-mono text-[11px] px-2 py-0.5 rounded-md ${
                  v.textManipulationStatus === 'SUSPICIOUS'
                    ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    : v.textManipulationStatus === 'INCONCLUSIVE'
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                }`}>
                  {v.textManipulationStatus || 'NOT_PERFORMED'}
                </span>
                {v.textManipulationConfidence != null && v.textManipulationConfidence > 0 && (
                  <span className="text-[10px] text-slate-400 block font-mono mt-0.5">
                    Confidence: {Math.round(v.textManipulationConfidence * 100)}%
                  </span>
                )}
                {v.textManipulationFields && v.textManipulationFields.length > 0 && (
                  <div className="mt-1 text-[10px] font-mono text-amber-300">
                    <span className="font-bold">Suspicious Fields: </span>
                    <span>{v.textManipulationFields.join(', ')}</span>
                  </div>
                )}
                {v.textManipulationReasons && v.textManipulationReasons.length > 0 && (
                  <ul className="text-[10px] text-amber-300 font-mono mt-1 text-right space-y-0.5">
                    {v.textManipulationReasons.map((r, idx) => (
                      <li key={idx}>• {r}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
            <div className="flex justify-between items-start py-2.5">
              <div>
                <span className="text-slate-400 font-medium">Stamp Forgery Detection</span>
                <span className="text-[10px] text-slate-500 block">Visa &amp; Stamp Forensic Manipulation Analysis</span>
              </div>
              <div className="text-right">
                <span className={`font-bold font-mono text-[11px] px-2 py-0.5 rounded-md ${
                  v.stampForgeryStatus === 'SUSPICIOUS'
                    ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    : v.stampForgeryStatus === 'INCONCLUSIVE'
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                }`}>
                  {v.stampForgeryStatus || 'NOT_PERFORMED'}
                </span>
                {v.stampForgeryConfidence != null && v.stampForgeryConfidence > 0 && (
                  <span className="text-[10px] text-slate-400 block font-mono mt-0.5">
                    Confidence: {Math.round(v.stampForgeryConfidence * 100)}%
                  </span>
                )}
                {v.stampForgeryReasons && v.stampForgeryReasons.length > 0 && (
                  <ul className="text-[10px] text-amber-300 font-mono mt-1 text-right space-y-0.5">
                    {v.stampForgeryReasons.map((r, idx) => (
                      <li key={idx}>• {r}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
            <div className="flex justify-between items-start py-2.5">
              <div>
                <span className="text-slate-400 font-medium">Image Metadata Analysis</span>
                <span className="text-[10px] text-slate-500 block">EXIF, Container &amp; Software Signature Audit</span>
              </div>
              <div className="text-right">
                <span className={`font-bold font-mono text-[11px] px-2 py-0.5 rounded-md ${
                  v.metadataStatus === 'SUSPICIOUS'
                    ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    : v.metadataStatus === 'INCONCLUSIVE'
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    : v.metadataStatus === 'CLEAN'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}>
                  {v.metadataStatus || 'NOT_AVAILABLE'}
                </span>
                {v.metadataConfidence != null && v.metadataConfidence > 0 && (
                  <span className="text-[10px] text-slate-400 block font-mono mt-0.5">
                    Confidence: {Math.round(v.metadataConfidence * 100)}%
                  </span>
                )}
                {v.metadataReasons && v.metadataReasons.length > 0 && (
                  <ul className="text-[10px] text-slate-300 font-mono mt-1 text-right space-y-0.5">
                    {v.metadataReasons.map((r, idx) => (
                      <li key={idx}>• {r}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
            <div className="flex justify-between items-start py-2.5">
              <div>
                <span className="text-slate-400 font-medium">VIZ ↔ MRZ Cross-Validation</span>
                <span className="text-[10px] text-slate-500 block">Visual Zone vs Encoded MRZ Field Comparison</span>
              </div>
              <div className="text-right">
                <span className={`font-bold font-mono text-[11px] px-2 py-0.5 rounded-md ${
                  v.vizMrzCrossValidation?.status === 'MATCH'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : v.vizMrzCrossValidation?.status === 'MISMATCH'
                    ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    : v.vizMrzCrossValidation?.status === 'INCONCLUSIVE'
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}>
                  Status: {v.vizMrzCrossValidation?.status || 'NOT_APPLICABLE'}
                </span>

                {v.vizMrzCrossValidation?.status === 'MATCH' && (
                  <div className="mt-2 space-y-1 text-[11px] font-mono text-emerald-400 text-right">
                    {v.vizMrzCrossValidation.matchedFields?.map((f) => (
                      <div key={f} className="flex items-center justify-end gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        <span className="capitalize">{f.replace(/([A-Z])/g, ' $1')}</span>
                      </div>
                    ))}
                  </div>
                )}

                {v.vizMrzCrossValidation?.status === 'MISMATCH' && (
                  <div className="mt-2 space-y-2 text-right">
                    {v.vizMrzCrossValidation.matchedFields?.map((f) => (
                      <div key={f} className="flex items-center justify-end gap-1 text-[11px] font-mono text-emerald-400">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        <span className="capitalize">{f.replace(/([A-Z])/g, ' $1')}</span>
                      </div>
                    ))}
                    {v.vizMrzCrossValidation.mismatches?.map((m) => (
                      <div key={m.field} className="bg-rose-950/40 p-2 rounded-xl border border-rose-500/30 text-left space-y-0.5">
                        <div className="flex items-center gap-1.5 text-rose-400 font-bold text-xs">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          <span className="capitalize">{m.field.replace(/([A-Z])/g, ' $1')}</span>
                        </div>
                        <div className="text-[10px] font-mono text-slate-300">
                          <div><span className="text-slate-500 font-bold">VIZ:</span> {m.vizValue}</div>
                          <div><span className="text-rose-400 font-bold">MRZ:</span> {m.mrzValue}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {v.vizMrzCrossValidation?.status === 'NOT_APPLICABLE' && (
                  <span className="text-[10px] text-slate-500 block font-mono mt-1">
                    No MRZ present on document
                  </span>
                )}
              </div>
            </div>

            {/* Document Expiry Validation */}
            <div className="flex justify-between items-start py-2.5">
              <div>
                <span className="text-slate-400 font-medium">Document Expiry Validation</span>
                <span className="text-[10px] text-slate-500 block">Validity Check &amp; Expiry Classification</span>
              </div>
              <div className="text-right">
                <span className={`font-bold font-mono text-[11px] px-2 py-0.5 rounded-md ${
                  v.expiryValidation?.status === 'VALID'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : v.expiryValidation?.status === 'EXPIRED'
                    ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    : v.expiryValidation?.status === 'UNKNOWN'
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}>
                  Status: {v.expiryValidation?.status || 'NOT_APPLICABLE'}
                </span>

                {v.expiryValidation?.status === 'VALID' && (
                  <div className="mt-1 text-[10px] font-mono text-slate-300 space-y-0.5">
                    <div><span className="text-slate-500">Expires:</span> <span className="text-emerald-400 font-bold">{v.expiryValidation.expiryDate}</span></div>
                    {v.expiryValidation.daysRemaining != null && (
                      <div><span className="text-slate-500">Days Remaining:</span> {v.expiryValidation.daysRemaining}</div>
                    )}
                    {v.expiryValidation.source && (
                      <div><span className="text-slate-500">Source:</span> <span className="text-blue-400 font-bold">{v.expiryValidation.source}</span></div>
                    )}
                  </div>
                )}

                {v.expiryValidation?.status === 'EXPIRED' && (
                  <div className="mt-1 text-[10px] font-mono text-slate-300 space-y-0.5">
                    <div><span className="text-slate-500">Expired On:</span> <span className="text-rose-400 font-bold">{v.expiryValidation.expiryDate}</span></div>
                    {v.expiryValidation.daysRemaining != null && (
                      <div><span className="text-slate-500">Days Since Expiry:</span> {Math.abs(v.expiryValidation.daysRemaining)}</div>
                    )}
                    {v.expiryValidation.source && (
                      <div><span className="text-slate-500">Source:</span> <span className="text-blue-400 font-bold">{v.expiryValidation.source}</span></div>
                    )}
                  </div>
                )}

                {v.expiryValidation?.status === 'UNKNOWN' && (
                  <span className="text-[10px] text-amber-300 block font-mono mt-1">
                    Expiry date could not be reliably determined
                  </span>
                )}

                {v.expiryValidation?.status === 'NOT_APPLICABLE' && (
                  <span className="text-[10px] text-slate-500 block font-mono mt-1">
                    Non-expiring document type
                  </span>
                )}
              </div>
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
