import React, { useState, useEffect } from 'react';
import SvgIcon from './SvgIcon';
import { apiFetch } from '../api';

export default function TicketsView({ t, addToast }) {
  const [tickets, setTickets] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchVal, setSearchVal] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  
  // New ticket form state
  const [formType, setFormType] = useState('refund');
  const [formRoute, setFormRoute] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formPriority, setFormPriority] = useState('medium');
  const [formDesc, setFormDesc] = useState('');
  const [formPassenger, setFormPassenger] = useState('');
  const [formPnr, setFormPnr] = useState('');
  const [formTrain, setFormTrain] = useState('');

  const fetchTickets = async () => {
    try {
      const data = await apiFetch(`/api/tickets?status=${statusFilter}&search=${encodeURIComponent(searchVal)}`);
      setTickets(data || []);
      if (data.length > 0 && !selectedTicket) {
        // select first by default
        setSelectedTicket(data[0]);
      } else if (selectedTicket) {
        // keep selected updated
        const updated = data.find(tk => tk.id === selectedTicket.id);
        if (updated) setSelectedTicket(updated);
      }
    } catch (err) {
      console.error("Error fetching tickets:", err);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, [statusFilter, searchVal]);

  const selectTicket = (id) => {
    const match = tickets.find(tk => tk.id === id);
    if (match) setSelectedTicket(match);
  };

  const handleResolve = async (ticketId) => {
    try {
      const body = { status: 'closed' };
      // if there is a satisfaction score, backend will accept it; avoid generating random values
      const data = await apiFetch(`/api/tickets/${ticketId}`, { method: 'PUT', body: JSON.stringify(body) });
      if (data && data.success) {
        addToast('success', `Ticket resolved successfully`);
        fetchTickets();
      }
    } catch (err) {
      console.error("Error updating ticket status:", err);
    }
  };

  // Removed frontend-generated satisfaction scores to avoid fake analytics

  const createTicket = async () => {
    if (!formDesc || !formPassenger) {
      addToast('error', 'Please fill in passenger name and description');
      return;
    }

    try {
      const body = {
        type: formType,
        desc: formDesc,
        route: formRoute || null,
        email: formEmail || null,
        passenger: formPassenger,
        pnr: formPnr || null,
        train: formTrain || null,
        priority: formPriority
      };
      const data = await apiFetch('/api/tickets', { method: 'POST', body: JSON.stringify(body) });
      if (data && data.success) {
        addToast('success', `Ticket created with ID ${data.ticket_id}`);
        setModalOpen(false);
        // Reset form
        setFormRoute('');
        setFormEmail('');
        setFormDesc('');
        setFormPassenger('');
        setFormPnr('');
        setFormTrain('');
        // Refetch
        fetchTickets();
      }
    } catch (err) {
      console.error("Error creating ticket:", err);
    }
  };

  const priorityColor = (p) => {
    return p === 'critical' ? '#EF4444' : p === 'high' ? '#F97316' : p === 'medium' ? '#F59E0B' : '#6B82A0';
  };

  const getPriorityClass = (priority) => {
    if (priority === 'critical') return 'badge-critical';
    if (priority === 'high') return 'badge-high';
    if (priority === 'medium') return 'badge-pending';
    return 'badge-closed';
  };

  const getStatusClass = (status) => {
    if (status === 'open') return 'badge-open';
    if (status === 'pending') return 'badge-pending';
    return 'badge-closed';
  };

  return (
    <div id="page-tickets" className="page active" style={{ flexDirection: 'row', height: '100%', overflow: 'hidden', display: 'flex' }}>
      
      {/* Tickets List Panel */}
      <div style={{ width: '420px', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', overflow: 'hidden', flexShrink: 0 }}>
        
        <div style={{ padding: '16px', borderBottom: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <SvgIcon name="search" size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
              <input
                className="input-field"
                placeholder={t.searchTickets}
                value={searchVal}
                onChange={(e) => setSearchVal(e.target.value)}
                style={{ paddingLeft: '32px', fontSize: '12px' }}
              />
            </div>
            <button className="btn-primary" onClick={() => setModalOpen(true)} style={{ flexShrink: 0 }}>
              <SvgIcon name="plus" size={14} />
              {t.newTicket}
            </button>
          </div>
          
          <div style={{ display: 'flex', gap: '6px' }}>
            {['all', 'open', 'pending', 'closed'].map(s => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  fontSize: '11px',
                  cursor: 'pointer',
                  background: statusFilter === s ? '#F59E0B22' : 'transparent',
                  color: statusFilter === s ? 'var(--amber)' : 'var(--text-muted)',
                  border: `1px solid ${statusFilter === s ? '#F59E0B44' : 'var(--border)'}`,
                  fontFamily: 'inherit',
                  fontWeight: 500,
                  textTransform: 'uppercase'
                }}
              >
                {s === 'all' ? t.all : s === 'open' ? t.open : s === 'pending' ? t.pending : t.closed}
              </button>
            ))}
          </div>
        </div>

        {/* Tickets Scroll list */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {tickets.map(tk => (
            <div
              key={tk.id}
              onClick={() => selectTicket(tk.id)}
              style={{
                padding: '14px 16px',
                cursor: 'pointer',
                borderBottom: '1px solid #1A2B4740',
                background: selectedTicket?.id === tk.id ? 'var(--surface-high)' : 'transparent',
                borderLeft: `3px solid ${selectedTicket?.id === tk.id ? 'var(--amber)' : 'transparent'}`,
                transition: 'all .15s'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: 'var(--amber)' }}>{tk.id}</span>
                  <span className={`badge ${getStatusClass(tk.status)}`}>{tk.status.toUpperCase()}</span>
                </div>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                  {tk.created_at ? tk.created_at.split(' ')[1] : ''}
                </span>
              </div>
              <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '3px' }}>
                {tk.type.replace('_', ' ').toUpperCase()}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                {tk.passenger} · {tk.route}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: '4px' }}>
                  {tk.tags?.slice(0, 2).map((tag, i) => (
                    <span key={i} style={{ fontSize: '10px', background: 'var(--surface-high)', color: 'var(--text-muted)', padding: '2px 7px', borderRadius: '10px', border: '1px solid var(--border)' }}>
                      #{tag}
                    </span>
                  ))}
                </div>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: priorityColor(tk.priority) }}></div>
              </div>
            </div>
          ))}
        </div>

      </div>

      {/* Ticket Detailed Inspection Panel */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
        {selectedTicket ? (
          <div className="fade-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '14px', color: 'var(--amber)' }}>{selectedTicket.id}</span>
                  <span className={`badge ${getStatusClass(selectedTicket.status)}`}>{selectedTicket.status.toUpperCase()}</span>
                  <span className={`badge ${getPriorityClass(selectedTicket.priority)}`}>{selectedTicket.priority.toUpperCase()}</span>
                </div>
                <h2 style={{ fontSize: '18px', fontWeight: 700 }}>
                  {selectedTicket.type.replace('_', ' ').toUpperCase()}
                </h2>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>{selectedTicket.route} · {selectedTicket.train}</p>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn-ghost" style={{ fontSize: '12px' }} onClick={() => { navigator.clipboard.writeText(selectedTicket.id); addToast('success', 'Ticket ID copied'); }}>
                  <SvgIcon name="copy" size={13} />
                  {t.copyId}
                </button>
                {selectedTicket.status !== 'closed' && (
                  <button className="btn-primary" style={{ fontSize: '12px' }} onClick={() => handleResolve(selectedTicket.id)}>
                    <SvgIcon name="check" size={13} />
                    {t.resolve}
                  </button>
                )}
              </div>
            </div>

            {/* Ticket Info Card list */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
              {[
                { label: t.passenger, value: selectedTicket.passenger },
                { label: t.email, value: selectedTicket.email },
                { label: t.pnr, value: selectedTicket.pnr || "N/A", mono: true },
                { label: t.assignee, value: selectedTicket.assignee },
                { label: t.created, value: selectedTicket.created_at },
                { label: t.replies, value: selectedTicket.satisfaction_score ? `Score: ${selectedTicket.satisfaction_score}%` : "No feedback yet" },
              ].map((f, i) => (
                <div key={i} className="card" style={{ padding: '12px' }}>
                  <div style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--text-muted)', marginBottom: '4px' }}>{f.label}</div>
                  <div style={{ fontSize: '13px', fontWeight: 500, fontFamily: f.mono ? 'JetBrains Mono,monospace' : 'inherit' }}>{f.value}</div>
                </div>
              ))}
            </div>

            {/* Description */}
            <div className="card" style={{ padding: '16px', marginBottom: '16px' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--text-muted)', marginBottom: '10px' }}>{t.issueDescription}</div>
              <p style={{ fontSize: '13px', lineHeight: 1.7 }}>{selectedTicket.description}</p>
            </div>

            {/* AI Predictions */}
            
            {selectedTicket.ai_suggestion && (
              <div style={{ background: 'linear-gradient(135deg,#F59E0B08,#8B5CF608)', border: '1px solid #F59E0B33', borderRadius: '12px', padding: '16px', marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                  <div style={{ width: '24px', height: '24px', borderRadius: '8px', background: 'linear-gradient(135deg,#F59E0B,#8B5CF6)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <SvgIcon name="zap" size={13} color="#fff" />
                  </div>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--amber)' }}>{t.aiRecommendation}</span>
                  <span className="badge badge-info" style={{ fontSize: '10px' }}>{t.autoGenerated}</span>
                </div>
                <div
  style={{
    fontSize: '13px',
    lineHeight: 1.7,
    whiteSpace: 'pre-wrap',
    overflow: 'visible'
  }}
>
  {selectedTicket.ai_suggestion}
</div>
              </div>
            )}

            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {selectedTicket.tags?.map((tag, i) => (
                <span key={i} style={{ background: 'var(--surface-high)', border: '1px solid var(--border)', borderRadius: '20px', padding: '4px 12px', fontSize: '12px', color: 'var(--text-muted)' }}>
                  #{tag}
                </span>
              ))}
            </div>

          </div>
        ) : (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '12px', color: 'var(--text-muted)' }}>
            <SvgIcon name="ticket" size={40} />
            <p style={{ fontSize: '14px' }}>{t.selectTicketMsg}</p>
          </div>
        )}
      </div>

      {/* NEW TICKET MODAL */}
      {modalOpen && (
        <div className="modal-overlay" onClick={() => setModalOpen(false)}>
          <div className="card modal-box fade-in" onClick={(e) => e.stopPropagation()} style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <span style={{ fontWeight: 600, fontSize: '15px' }}>{t.createTicketModalTitle}</span>
              <button className="btn-icon" onClick={() => setModalOpen(false)}>
                <SvgIcon name="close" size={16} />
              </button>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>{t.passenger}</label>
                <input className="input-field" placeholder="Enter passenger name" value={formPassenger} onChange={(e) => setFormPassenger(e.target.value)} />
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>{t.ticketTypeLabel}</label>
                <select className="input-field" value={formType} onChange={(e) => setFormType(e.target.value)}>
                  <option value="refund">Refund Request</option>
                  <option value="payment_failure">Payment Failure</option>
                  <option value="booking_issue">Booking Issue</option>
                  <option value="login_issue">Login / Account Issue</option>
                  <option value="train_delay">Train Delay</option>
                  <option value="cancellation">Cancellation</option>
                  <option value="luggage_issue">Luggage Issue</option>
                  <option value="catering_complaint">Catering Complaint</option>
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>{t.routeLabel}</label>
                  <input className="input-field" placeholder="e.g. Pune → Mumbai" value={formRoute} onChange={(e) => setFormRoute(e.target.value)} />
                </div>
                <div>
                  <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>{t.train}</label>
                  <input className="input-field" placeholder="e.g. 12124 Deccan" value={formTrain} onChange={(e) => setFormTrain(e.target.value)} />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>{t.pnr}</label>
                  <input className="input-field" placeholder="10-digit number" value={formPnr} onChange={(e) => setFormPnr(e.target.value)} />
                </div>
                <div>
                  <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>{t.passengerEmailLabel}</label>
                  <input className="input-field" placeholder="passenger@email.com" value={formEmail} onChange={(e) => setFormEmail(e.target.value)} />
                </div>
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>{t.priorityLabel}</label>
                <select className="input-field" value={formPriority} onChange={(e) => setFormPriority(e.target.value)}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>{t.descriptionLabel}</label>
                <textarea className="input-field" rows="3" placeholder="Describe the issue in detail..." value={formDesc} onChange={(e) => setFormDesc(e.target.value)} style={{ resize: 'none' }}></textarea>
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '4px' }}>
                <button className="btn-ghost" onClick={() => setModalOpen(false)}>{t.cancel}</button>
                <button className="btn-primary" onClick={createTicket}>{t.createTicket}</button>
              </div>

            </div>
          </div>
        </div>
      )}

    </div>
  );
}
