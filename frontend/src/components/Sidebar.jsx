import React from 'react';
import SvgIcon from './SvgIcon';
import { apiFetch } from '../api';


export default function Sidebar({
  currentPage,
  navigate,
  sidebarCollapsed,
  toggleSidebar,
  currentLanguage,
  setLanguage,
  t
}) {
  return (
    <aside id="sidebar" className={sidebarCollapsed ? 'collapsed' : ''} style={{ width: sidebarCollapsed ? '60px' : '220px' }}>
      {/* Animated track decoration */}
      <svg width="24" height="100%" viewBox="0 0 24 200" fill="none" style={{ position: 'absolute', left: 0, top: 0, height: '100%', opacity: 0.3, pointerEvents: 'none' }}>
        <line x1="8" y1="0" x2="8" y2="2000" stroke="#F59E0B" strokeWidth="1" className="track-line" strokeDasharray="10 8" />
        <line x1="16" y1="0" x2="16" y2="2000" stroke="#F59E0B" strokeWidth="1" className="track-line" strokeDasharray="10 8" style={{ animationDelay: '1s' }} />
      </svg>

      {/* Logo */}
      <div style={{ padding: '18px 14px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '10px', zIndex: 1 }}>
        <div style={{ width: '32px', height: '32px', borderRadius: '8px', flexShrink: 0, background: 'linear-gradient(135deg,#F59E0B,#D97706)', display: 'flex', alignItems: 'center', justifyContent: 'center', animation: 'glow 3s ease-in-out infinite' }}>
          <SvgIcon name="train" size={16} color="#080D1A" />
        </div>
        {!sidebarCollapsed && (
          <div className="slide-in" id="logo-text">
            <div style={{ fontWeight: 800, fontSize: '15px', letterSpacing: '-.02em', color: 'var(--text)' }}>{t.logoTitle}</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '.08em', textTransform: 'uppercase' }}>{t.logoSubtitle}</div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: '2px', zIndex: 1 }}>
        <div className={`nav-item ${currentPage === 'dashboard' ? 'active' : ''}`} onClick={() => navigate('dashboard')}>
          <SvgIcon name="chart" size={18} color="currentColor" />
          {!sidebarCollapsed && <span className="nav-label">{t.dashboard}</span>}
        </div>
        <div className={`nav-item ${currentPage === 'ai' ? 'active' : ''}`} onClick={() => navigate('ai')}>
          <SvgIcon name="bot" size={18} color="currentColor" />
          {!sidebarCollapsed && <span className="nav-label">{t.assistant}</span>}
        </div>
        <div className={`nav-item ${currentPage === 'tickets' ? 'active' : ''}`} onClick={() => navigate('tickets')}>
          <SvgIcon name="ticket" size={18} color="currentColor" />
          {!sidebarCollapsed && <span className="nav-label">{t.tickets}</span>}
        </div>
        <div className={`nav-item ${currentPage === 'analytics' ? 'active' : ''}`} onClick={() => navigate('analytics')}>
          <SvgIcon name="chart" size={18} color="currentColor" />
          {!sidebarCollapsed && <span className="nav-label">{t.analytics}</span>}
        </div>
      </nav>

      {/* Bottom */}
      <div style={{ padding: '12px 8px', borderTop: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '4px', zIndex: 1 }}>
        {/* Language Selection menu in Sidebar */}
        {!sidebarCollapsed ? (
          <div style={{ display: 'flex', gap: '4px', padding: '6px 8px', background: 'var(--surface-high)', borderRadius: '6px', marginBottom: '8px' }}>
            {['en', 'hi', 'mr'].map(lang => (
              <button
                key={lang}
                onClick={() => setLanguage(lang)}
                style={{
                  flex: 1,
                  background: currentLanguage === lang ? 'linear-gradient(135deg, #F59E0B, #D97706)' : 'transparent',
                  color: currentLanguage === lang ? '#080D1A' : 'var(--text-muted)',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '4px 0',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  textTransform: 'uppercase',
                  transition: 'all 0.15s'
                }}
              >
                {lang}
              </button>
            ))}
          </div>
        ) : (
          <button
            onClick={() => setLanguage(currentLanguage === 'en' ? 'hi' : currentLanguage === 'hi' ? 'mr' : 'en')}
            className="btn-icon"
            style={{ marginBottom: '8px', fontSize: '11px', fontWeight: 'bold', textTransform: 'uppercase', color: 'var(--amber)' }}
            title="Switch Language"
          >
            {currentLanguage}
          </button>
        )}

        <div className="nav-item">
          <SvgIcon name="gear" size={18} color="currentColor" />
          {!sidebarCollapsed && <span className="nav-label">{t.settings}</span>}
        </div>

        <div className="nav-item" style={{ marginTop: '2px' }} onClick={toggleSidebar} title={sidebarCollapsed ? t.expand : t.collapse}>
          <SvgIcon name="refresh" size={18} color="currentColor" />
          {!sidebarCollapsed && <span className="nav-label">{t.collapse}</span>}
        </div>
      </div>
    </aside>
  );
}
