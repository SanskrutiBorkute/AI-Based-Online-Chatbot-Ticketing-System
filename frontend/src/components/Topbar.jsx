import React, { useState, useEffect } from 'react';
import SvgIcon from './SvgIcon';

export default function Topbar({ pageTitle, t }) {
  const [time, setTime] = useState("");

  useEffect(() => {
    const updateTime = () => {
      setTime(new Date().toLocaleTimeString('en-IN', { hour12: false }) + " " + t.clockIST);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, [t]);

  return (
    <header id="topbar">
      <div style={{ flex: 1 }}>
        <h1 id="page-title" style={{ fontSize: '15px', fontWeight: 700, letterSpacing: '-.01em' }}>
          {pageTitle}
        </h1>
      </div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--surface-high)', borderRadius: '8px', padding: '6px 10px', border: '1px solid var(--border)' }}>
        <SvgIcon name="search" size={14} color="var(--text-muted)" />
        <input
          placeholder={t.searchPlaceholder}
          className="mono"
          style={{ background: 'none', border: 'none', outline: 'none', color: 'var(--text-muted)', fontSize: '12px', width: '160px' }}
        />
      </div>

      <span id="live-clock" className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '.05em' }}>
        {time}
      </span>

      <div style={{ position: 'relative' }}>
        <button className="btn-icon">
          <SvgIcon name="bell" size={16} />
          <span style={{ position: 'absolute', top: '2px', right: '2px', width: '8px', height: '8px', background: 'var(--red)', borderRadius: '50%', border: '2px solid var(--surface)' }}></span>
        </button>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingLeft: '8px', borderLeft: '1px solid var(--border)' }}>
        <div style={{ width: '30px', height: '30px', borderRadius: '8px', background: 'linear-gradient(135deg,#3B82F6,#8B5CF6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: 700 }}>
          RA
        </div>
        <div>
          <div style={{ fontSize: '12px', fontWeight: 600 }}>Rail Admin</div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Ops Manager</div>
        </div>
      </div>
    </header>
  );
}
