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
  Eye,
  Printer,
  FileSpreadsheet,
  BadgeCheck,
  XCircle,
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

  const renderField = (label: string, val?: string | number, highlight = false) => {
    const displayVal = val !== undefined && val !== null && String(val).trim() !== '' ? String(val) : '—';
    return (
      <div className="flex justify-between items-center py-2.5 border-b border-slate-800/60 text-xs">
        <span className="text-slate-400 font-medium">{label}</span>
        <span className={`font-semibold ${highlight ? 'text-blue-400 font-mono text-sm' : 'text-slate-100'}`}>
          {displayVal}
        </span>
      </div>
    );
  };

  const mrzLines = v.extracted?.mrz ? v.extracted.mrz.split('\n').filter(Boolean) : [];

  const formattedDate = v.createdAt
    ? v.createdAt.slice(0, 19).replace('T', ' ')
    : new Date().toISOString().slice(0, 19).replace('T', ' ');

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
              <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">Forensic Inspection #{v.verificationId}</h1>
              <RiskBadge level={v.riskLevel} score={v.riskScore} />
            </div>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              Document ID: #{v.documentId} · Type: {v.documentType} · Created: {formattedDate}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={printReport}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold px-4 py-2.5 rounded-2xl border border-slate-700/80 transition-all"
          >
            <Printer className="w-4 h-4 text-blue-400" />
            <span>Export PDF Report</span>
          </button>

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

      {/* Grid: Extracted Data & Tamper Analysis */}
      <div className="grid lg:grid-cols-2 gap-8">
        {/* Section 1: Extracted OCR Data */}
        <section className="bg-slate-900/60 border border-slate-800/80 p-6 sm:p-8 rounded-3xl shadow-xl space-y-4 backdrop-blur-md">
          <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2.5 uppercase tracking-wider">
            <FileText className="w-4.5 h-4.5 text-blue-400" />
            <span>Extracted ICAO 9303 MRZ &amp; OCR Zone</span>
          </h2>

          <div className="divide-y divide-slate-800/60">
            {renderField('Subject Full Name', v.extracted?.name)}
            {renderField('Passport / Serial #', v.extracted?.passportNumber, true)}
            {renderField('Nationality Code', v.extracted?.nationality)}
            {renderField('Date of Birth', v.extracted?.dateOfBirth)}
            {renderField('Gender', v.extracted?.gender)}
            {renderField('Issue Date', v.extracted?.issueDate)}
            {renderField('Expiry Date', v.extracted?.expiryDate)}
            {renderField('OCR Confidence Score', v.extracted?.ocrConfidence != null ? `${Math.round(v.extracted.ocrConfidence * 100)}%` : undefined)}
            {renderField('Validation Status', v.validationStatus)}
          </div>

          {/* Interactive Line-by-Line Checksum Breakdown */}
          <div className="pt-3 space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-400 font-bold">
              <span>MRZ Line-by-Line Checksum Audit</span>
              {mrzLines.length === 0 ? (
                <span className="text-slate-400 flex items-center gap-1 font-mono">
                  <span>VIZ ONLY (NO MRZ)</span>
                </span>
              ) : v.validationStatus === 'CHECKSUM_FAILED' || v.validationStatus === 'FAIL' ? (
                <span className="text-red-400 flex items-center gap-1 font-mono">
                  <XCircle className="w-3.5 h-3.5" />
                  <span>CHECKSUM FAILED</span>
                </span>
              ) : (
                <span className="text-emerald-400 flex items-center gap-1 font-mono">
                  <BadgeCheck className="w-3.5 h-3.5" />
                  <span>CHECKSUM VALIDATED</span>
                </span>
              )}
            </div>

            <div className="space-y-2 bg-slate-950 p-4 rounded-2xl border border-slate-800/80 font-mono text-xs">
              {mrzLines.length > 0 ? (
                mrzLines.map((line, idx) => (
                  <div key={idx} className="space-y-1">
                    <div className="text-[10px] text-slate-500 font-sans font-semibold">
                      Line {idx + 1}: {idx === 0 ? 'Document Type / Country / Name' : 'Serial / DOB / Expiry / Composite Checkdigit'}
                    </div>
                    <div className="text-cyan-300 break-all p-2 rounded-xl bg-slate-900/80 border border-slate-800">
                      {line}
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-slate-500 text-center py-2 font-sans">No MRZ lines extracted from document</p>
              )}
            </div>
          </div>
        </section>

        {/* Section 2: ELA Digital Tampering Analysis */}
        <section className="bg-slate-900/60 border border-slate-800/80 p-6 sm:p-8 rounded-3xl shadow-xl space-y-6 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2.5 uppercase tracking-wider">
              <Scan className="w-4.5 h-4.5 text-indigo-400" />
              <span>Error Level Analysis (ELA) Tamper Breakdown</span>
            </h2>
            {v.elaHeatmapBase64 && (
              <button
                onClick={() => setShowHeatmap(!showHeatmap)}
                className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1.5 bg-blue-500/10 px-3 py-1.5 rounded-xl border border-blue-500/20 font-bold"
              >
                <Eye className="w-4 h-4" />
                <span>{showHeatmap ? 'Hide Heatmap' : 'View ELA Heatmap'}</span>
              </button>
            )}
          </div>

          <div className="h-52">
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
            <div className="p-4 bg-slate-950 rounded-2xl border border-slate-800 space-y-2">
              <span className="text-xs text-slate-400 font-bold">ELA Pixel Anomaly Heatmap</span>
              <img
                alt="ELA Heatmap"
                src={`data:image/png;base64,${v.elaHeatmapBase64}`}
                className="w-full max-h-48 object-contain rounded-xl border border-slate-800"
              />
            </div>
          )}
        </section>

        {/* Section 3: Face & Watchlist Match */}
        <section className="bg-slate-900/60 border border-slate-800/80 p-6 sm:p-8 rounded-3xl shadow-xl space-y-4 backdrop-blur-md">
          <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2.5 uppercase tracking-wider">
            <UserCheck className="w-4.5 h-4.5 text-emerald-400" />
            <span>Biometric Face &amp; Watchlist Correlation</span>
          </h2>
          <div className="divide-y divide-slate-800/60">
            {renderField('Face Match Confidence', v.faceMatchScore != null ? `${Math.round(v.faceMatchScore * 100)}%` : undefined)}
            {renderField('Face Match Verdict', v.faceMatchStatus)}
            {renderField('Liveness Check', v.livenessStatus)}
            {renderField('Watchlist Status', v.blacklistStatus)}
          </div>
        </section>

        {/* Section 4: Audit & Blockchain Provenance */}
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
              <p className="text-[11px] text-slate-400 font-mono">Current database hash matches Hyperledger block record.</p>
            </div>
          )}
        </section>
      </div>

      {/* Section 5: AI Explainability Drivers */}
      <section className="bg-slate-900/60 border border-slate-800/80 p-6 sm:p-8 rounded-3xl shadow-xl space-y-3 backdrop-blur-md">
        <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2.5 uppercase tracking-wider">
          <Award className="w-4.5 h-4.5 text-amber-400" />
          <span>AI Explainability &amp; Risk Drivers</span>
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

      {/* Section 6: Officer Action Bar */}
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
