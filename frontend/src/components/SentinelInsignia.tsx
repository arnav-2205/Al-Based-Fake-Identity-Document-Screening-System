import React from 'react';

export interface SentinelInsigniaProps {
  className?: string;
  size?: number;
}

export const SentinelInsignia: React.FC<SentinelInsigniaProps> = ({ className = '', size = 32 }) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 100 100"
      width={size}
      height={size}
      fill="none"
      className={className}
    >
      <defs>
        <linearGradient id="shieldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#1E3A8A" />
          <stop offset="50%" stopColor="#0E2439" />
          <stop offset="100%" stopColor="#0A192F" />
        </linearGradient>
        <linearGradient id="goldTrim" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#FDE047" />
          <stop offset="50%" stopColor="#EAB308" />
          <stop offset="100%" stopColor="#CA8A04" />
        </linearGradient>
        <linearGradient id="cyanCore" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#38BDF8" />
          <stop offset="100%" stopColor="#2563EB" />
        </linearGradient>
      </defs>
      {/* Outer Institutional Shield */}
      <path
        d="M50 8 L84 20 C84 55 50 88 50 88 C50 88 16 55 16 20 Z"
        fill="url(#shieldGrad)"
        stroke="url(#goldTrim)"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      {/* Inner Border Line */}
      <path
        d="M50 14 L78 24 C78 52 50 80 50 80 C50 80 22 52 22 24 Z"
        fill="none"
        stroke="#94A3B8"
        strokeWidth="1"
        strokeOpacity="0.4"
      />
      {/* Security Star / Geometric Emblem */}
      <path
        d="M50 26 L55 37 L67 37 L57 45 L61 56 L50 49 L39 56 L43 45 L33 37 L45 37 Z"
        fill="url(#goldTrim)"
        opacity="0.95"
      />
      {/* Digital Biometric Iris / Reticle center */}
      <circle cx="50" cy="62" r="9" stroke="url(#cyanCore)" strokeWidth="2" fill="#0A192F" />
      <circle cx="50" cy="62" r="4" fill="#38BDF8" />
      <line x1="50" y1="50" x2="50" y2="52" stroke="#38BDF8" strokeWidth="2" />
      <line x1="50" y1="72" x2="50" y2="74" stroke="#38BDF8" strokeWidth="2" />
      <line x1="38" y1="62" x2="40" y2="62" stroke="#38BDF8" strokeWidth="2" />
      <line x1="60" y1="62" x2="62" y2="62" stroke="#38BDF8" strokeWidth="2" />
    </svg>
  );
};

export default SentinelInsignia;
