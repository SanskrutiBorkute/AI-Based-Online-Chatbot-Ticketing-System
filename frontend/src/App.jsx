import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import DashboardView from './components/DashboardView';
import ChatView from './components/ChatView';
import TicketsView from './components/TicketsView';
import AnalyticsView from './components/AnalyticsView';
import { translations } from './localization';

export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [language, setLanguage] = useState('en');
  const [toasts, setToasts] = useState([]);

  const addToast = (type, message) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const getPageTitle = () => {
    const t = translations[language];
    if (currentPage === 'dashboard') return t.dashboard;
    if (currentPage === 'ai') return t.assistant;
    if (currentPage === 'tickets') return t.tickets;
    if (currentPage === 'analytics') return t.analytics;
    return t.dashboard;
  };

  const t = translations[language];

  return (
    <div id="app" style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)' }}>
      {/* Sidebar Navigation */}
      <Sidebar
        currentPage={currentPage}
        navigate={setCurrentPage}
        sidebarCollapsed={sidebarCollapsed}
        toggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
        currentLanguage={language}
        setLanguage={setLanguage}
        t={t}
      />

      {/* Main View Area */}
      <div id="main" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Topbar pageTitle={getPageTitle()} t={t} />
        
        <main id="content" style={{ flex: 1, overflowY: 'auto', position: 'relative' }}>
          {currentPage === 'dashboard' && (
            <DashboardView t={t} navigate={setCurrentPage} addToast={addToast} />
          )}
          {currentPage === 'ai' && (
            <ChatView t={t} currentLanguage={language} addToast={addToast} />
          )}
          {currentPage === 'tickets' && (
            <TicketsView t={t} addToast={addToast} />
          )}
          {currentPage === 'analytics' && (
            <AnalyticsView t={t} />
          )}
        </main>
      </div>

      {/* Toast Notifications */}
      <div id="toast-container">
        {toasts.map((toast) => {
          const colors = { success: '#10B981', error: '#EF4444', info: '#F59E0B' };
          const bg = toast.type === 'success' ? '#10B98120' : toast.type === 'error' ? '#EF444420' : '#F59E0B20';
          const border = toast.type === 'success' ? '#10B98140' : toast.type === 'error' ? '#EF444440' : '#F59E0B44';

          return (
            <div
              key={toast.id}
              className="toast"
              style={{
                background: bg,
                border: `1px solid ${border}`,
                pointerEvents: 'all'
              }}
            >
              <span
                style={{
                  display: 'inline-block',
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  background: colors[toast.type] || '#F59E0B',
                  animation: 'pulse 2s infinite'
                }}
              ></span>
              <span style={{ fontSize: '13px', flex: 1 }}>{toast.message}</span>
              <button
                onClick={() => removeToast(toast.id)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  fontSize: '16px',
                  lineHeight: 1
                }}
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
