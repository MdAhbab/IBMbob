export function OrchestratorLogo({
  size = 32,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  const id = `og-${Math.random().toString(36).slice(2, 8)}`;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      aria-hidden
    >
      <defs>
        <linearGradient id={`${id}-bg`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#6366f1" />
          <stop offset="55%" stopColor="#8b5cf6" />
          <stop offset="100%" stopColor="#ec4899" />
        </linearGradient>
        <linearGradient id={`${id}-stroke`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#fde68a" stopOpacity="0.9" />
        </linearGradient>
        <filter id={`${id}-glow`} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="1.2" />
        </filter>
      </defs>
      <rect
        x="1.25"
        y="1.25"
        width="29.5"
        height="29.5"
        rx="8"
        fill={`url(#${id}-bg)`}
      />
      <rect
        x="1.25"
        y="1.25"
        width="29.5"
        height="29.5"
        rx="8"
        fill="url(#${id}-bg)"
        opacity="0.0"
      />
      <g filter={`url(#${id}-glow)`} opacity="0.55">
        <path
          d="M9.5 10.5 L15 16 L9.5 21.5"
          stroke="#ffffff"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        <line
          x1="16.5"
          y1="22"
          x2="22.5"
          y2="22"
          stroke="#ffffff"
          strokeWidth="2.2"
          strokeLinecap="round"
        />
      </g>
      <path
        d="M9.5 10.5 L15 16 L9.5 21.5"
        stroke={`url(#${id}-stroke)`}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <line
        x1="16.5"
        y1="22"
        x2="22.5"
        y2="22"
        stroke={`url(#${id}-stroke)`}
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}
