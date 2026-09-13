import React from 'react';
import { AlertTriangle, CheckCircle, ShieldAlert } from 'lucide-react';

interface RiskBadgeProps {
  level: 'LOW' | 'MEDIUM' | 'HIGH' | string;
  score?: number;
  showScore?: boolean;
}

export default function RiskBadge({ level, score, showScore = true }: RiskBadgeProps) {
  const normLevel = (level || 'LOW').toUpperCase();

  if (normLevel === 'HIGH') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-red-500/10 text-red-600 border border-red-500/20 shadow-sm animate-pulse">
        <ShieldAlert className="w-3.5 h-3.5" />
        HIGH RISK {showScore && score !== undefined && `(${score} pts)`}
      </span>
    );
  }

  if (normLevel === 'MEDIUM') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-600 border border-amber-500/20 shadow-sm">
        <AlertTriangle className="w-3.5 h-3.5" />
        MEDIUM RISK {showScore && score !== undefined && `(${score} pts)`}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 shadow-sm">
      <CheckCircle className="w-3.5 h-3.5" />
      LOW RISK {showScore && score !== undefined && `(${score} pts)`}
    </span>
  );
}
