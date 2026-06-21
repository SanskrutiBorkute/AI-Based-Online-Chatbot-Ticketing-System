import React from 'react';

const PATHS = {
  arrowUp: "M12 19V5M5 12l7-7 7 7",
  arrowDown: "M12 5v14M5 12l7 7 7-7",
  ticket: "M2 9a2 2 0 012-2h16a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V9zm6 3h8M8 9v6",
  check: "M20 6L9 17l-5-5",
  clock: "M12 22a10 10 0 100-20 10 10 0 000 20zm0-14v4l3 3",
  bot: "M12 2a3 3 0 013 3v1h3a2 2 0 012 2v8a2 2 0 01-2 2H6a2 2 0 01-2-2V8a2 2 0 012-2h3V5a3 3 0 013-3zm-2 9a1 1 0 100 2 1 1 0 000-2zm4 0a1 1 0 100 2 1 1 0 000-2zm-2 3s-2 0-2 1.5h4c0-1.5-2-1.5-2-1.5z",
  thumbsUp: "M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3H14zm-7 0H4.72A2.23 2.23 0 002.5 11.18L1 20.5A2 2 0 003 23H7V9z",
  zap: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
  train: "M12 2c-4 0-8 1.5-8 5v9a3 3 0 006 0v-1h4v1a3 3 0 006 0V7c0-3.5-4-5-8-5zM8 15H6v-2h2v2zm10 0h-2v-2h2v2zM4 10V7h16v3H4z",
  map: "M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3V6z",
  plus: "M12 5v14M5 12h14",
  copy: "M8 4H6a2 2 0 00-2 2v14a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-2M8 4a2 2 0 012-2h4a2 2 0 012 2M8 4h8",
  refresh: "M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15",
  gear: "M12 15a3 3 0 100-6 3 3 0 000 6zm9.7-3a9.8 9.8 0 00-.2-1.9l2.1-1.6-2-3.5-2.5 1a9.4 9.4 0 00-1.6-1l-.4-2.6h-4l-.4 2.6a9.4 9.4 0 00-1.6 1l-2.5-1-2 3.5 2.1 1.6a9.8 9.8 0 000 3.8l-2.1 1.6 2 3.5 2.5-1a9.4 9.4 0 001.6 1l.4 2.6h4l.4-2.6a9.4 9.4 0 001.6-1l2.5 1 2-3.5-2.1-1.6a9.8 9.8 0 00.2-1.9z",
  search: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0",
  bell: "M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0",
  close: "M18 6L6 18M6 6l12 12",
  chart: "M3 3v18h18M7 16l4-4 4 4 4-6"
};

export default function SvgIcon({ name, size = 16, color = 'currentColor', className = '' }) {
  const d = PATHS[name] || "";
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d={d} />
    </svg>
  );
}
