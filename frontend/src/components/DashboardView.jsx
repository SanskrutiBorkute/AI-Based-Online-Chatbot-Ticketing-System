import React, { useState, useEffect } from 'react';
import SvgIcon from './SvgIcon';
import { apiFetch } from '../api';

export default function DashboardView({ t, navigate, addToast }) {
  const [stats, setStats] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [trains, setTrains] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      // Fetch statistics
      const statsData = await apiFetch('/api/dashboard/stats');
      setStats(statsData || {});

      // Fetch recent tickets
      const ticketsData = await apiFetch('/api/tickets');
      setTickets((ticketsData || []).slice(0, 5)); // show recent 5

      // Fetch live trains
      const trainsData = await apiFetch('/api/dashboard/trains');
      setTrains(trainsData || []);
      
      setLoading(false);
    } catch (err) {
      console.error("Error fetching dashboard data:", err);
      setStats({});
      setTickets([]);
      setTrains([]);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000); // refresh every 15s
    return () => clearInterval(interval);
  }, []);

  const sparklineSVG = (data, color) => {
    if (!data || !data.length) return '';
    const width = 80;
    const height = 32;
    const max = Math.max(...data);
    const min = Math.min(...data);
    const pts = data.map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / (max - min || 1)) * height;
      return `${x},${y}`;
    }).join(' ');
    return (
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
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

  if (loading || !stats) {
    return (
      <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '32px', height: '32px', border: '3px solid var(--border)', borderTopColor: 'var(--amber)', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
          <span style={{ fontSize: '13px' }}>Loading Dashboard...</span>
        </div>
      </div>
    );
  }

  const kpiDefs = [
    { label: t.totalTickets, value: stats.totalTickets ?? 0, delta: stats.totalDelta ?? 0, color: 'blue', icon: 'chart', spark: stats.weeklyVolume || [] },
    { label: t.openTickets, value: stats.openTickets ?? 0, delta: stats.openDelta ?? 0, color: 'amber', icon: 'ticket', spark: stats.weeklyVolume || [] },
    { label: t.resolvedTickets, value: stats.resolvedTickets ?? 0, delta: stats.resolvedDelta ?? 0, color: 'green', icon: 'check', spark: stats.resolutionRate || [] },
    { label: t.criticalTickets, value: stats.criticalTickets ?? 0, delta: stats.criticalDelta ?? 0, color: 'red', icon: 'bell' }
  ];

  if (stats.aiResolvedCount !== undefined) {
    kpiDefs.push({
      label: t.aiResolvedIssues,
      value: stats.aiResolvedCount ?? 0,
      delta: 0,
      color: 'purple',
      icon: 'bot'
    });
  }

  if (!loading && stats.totalTickets === 0) {
    return (
      <div id="page-dashboard" className="page active" style={{ overflowY: 'auto', padding: '24px', gap: '20px', flexDirection: 'column', display: 'flex' }}>
        <div>
          <h2 style={{ fontSize: '16px', fontWeight: 700 }}>{t.logoTitle} {t.logoSubtitle}</h2>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '3px' }}>Operations Control & Support Center</p>
        </div>
        
        {/* KPI Row (empty states / 0 metrics) */}
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          {kpiDefs.map((k, i) => {
            const cardColor = k.color === 'amber' ? '#F59E0B' : k.color === 'green' ? '#10B981' : k.color === 'blue' ? '#3B82F6' : k.color === 'red' ? '#EF4444' : '#8B5CF6';
            return (
              <div key={i} className={`stat-card stat-${k.color}`}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.06em', fontWeight: 500 }}>
                    {k.label}
                  </span>
                  <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: `${cardColor}22`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: cardColor }}>
                    <SvgIcon name={k.icon} size={16} color={cardColor} />
                  </div>
                </div>
                <div style={{ fontSize: '26px', fontWeight: 800, letterSpacing: '-.03em', marginBottom: '8px' }}>0</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  {k.label === t.aiResolvedIssues ? "Resolved by Chatbot" : "No activity recorded"}
                </div>
              </div>
            );
          })}
        </div>

        <div className="card text-center" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '320px', border: '1px dashed var(--border)', borderRadius: '12px', padding: '40px', color: 'var(--text-muted)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', textAlign: 'center' }}>
            <SvgIcon name="ticket" size={48} color="var(--text-muted)" />
            <div>
              <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text)', marginBottom: '6px' }}>No Support Tickets in Operations Database</h3>
              <p style={{ fontSize: '12px', maxWidth: '420px', margin: '0 auto', color: 'var(--text-muted)' }}>
                Your railway operations database is currently empty. You can submit support tickets manually or use the AI Assistant chatbot to troubleshoot operational issues.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button className="btn-primary" style={{ padding: '8px 18px' }} onClick={() => navigate('assistant')}>
                <SvgIcon name="bot" size={14} color="#080D1A" />
                Go to AI Assistant
              </button>
              <button className="btn-ghost" style={{ padding: '8px 18px' }} onClick={() => navigate('tickets')}>
                <SvgIcon name="ticket" size={14} />
                Create Support Ticket
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div id="page-dashboard" className="page active" style={{ overflowY: 'auto', padding: '24px', gap: '20px', flexDirection: 'column', display: 'flex' }}>
      
      {/* KPI Row */}
      <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
        {kpiDefs.map((k, i) => {
          const deltaSign = k.delta >= 0 ? '+' : '';
          const deltaColor = k.delta >= 0 ? '#10B981' : '#EF4444';
          const arrowIcon = k.delta >= 0 ? 'arrowUp' : 'arrowDown';
          const cardColor = k.color === 'amber' ? '#F59E0B' : k.color === 'green' ? '#10B981' : k.color === 'blue' ? '#3B82F6' : k.color === 'red' ? '#EF4444' : '#8B5CF6';

          return (
            <div key={i} className={`stat-card stat-${k.color}`}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.06em', fontWeight: 500 }}>
                  {k.label}
                </span>
                <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: `${cardColor}22`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: cardColor }}>
                  <SvgIcon name={k.icon} size={16} color={cardColor} />
                </div>
              </div>
              <div style={{ fontSize: '26px', fontWeight: 800, letterSpacing: '-.03em', marginBottom: '8px' }}>{k.value}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                {k.label !== t.aiResolvedIssues ? (
                  <span style={{ fontSize: '11px', color: deltaColor, display: 'flex', alignItems: 'center', gap: '3px' }}>
                    <SvgIcon name={arrowIcon} size={12} color={deltaColor} />
                    {Math.abs(k.delta)}% {t.vsYesterday}
                  </span>
                ) : (
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Resolved by Chatbot
                  </span>
                )}
                {k.spark && sparklineSVG(k.spark, cardColor)}
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Grid: Recent Tickets & Train Statuses */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '16px' }}>
        
        {/* Recent Tickets Activity */}
        <div className="card" style={{ padding: '20px', overflowX: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <span style={{ fontWeight: 600, fontSize: '14px' }}>{t.recentActivity}</span>
            <button className="btn-primary" style={{ fontSize: '12px', padding: '6px 12px' }} onClick={() => navigate('tickets')}>
              <SvgIcon name="plus" size={13} />
              {t.newTicket}
            </button>
          </div>
          
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '500px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['ID', t.type, t.route, t.train, t.priority, t.status].map((h, i) => (
                  <th key={i} style={{ padding: '6px 10px', textAlign: 'left', fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '.05em' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tickets.map((ticket) => (
                <tr key={ticket.id} className="table-row">
                  <td style={{ padding: '10px', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: 'var(--amber)' }}>
                    {ticket.id}
                  </td>
                  <td style={{ padding: '10px', fontSize: '13px' }}>
                    {ticket.type.replace('_', ' ').toUpperCase()}
                  </td>
                  <td style={{ padding: '10px', fontSize: '12px', color: 'var(--text-muted)' }}>
                    {ticket.route}
                  </td>
                  <td style={{ padding: '10px', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: 'var(--text-muted)' }}>
                    {ticket.train}
                  </td>
                  <td style={{ padding: '10px' }}>
                    <span className={`badge ${getPriorityClass(ticket.priority)}`}>
                      {ticket.priority.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ padding: '10px' }}>
                    <span className={`badge ${getStatusClass(ticket.status)}`}>
                      {ticket.status.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Live Train Status */}
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <span style={{ fontWeight: 600, fontSize: '14px' }}>{t.liveTrainStatus}</span>
            <span style={{ display: 'inline-block', width: '7px', height: '7px', borderRadius: '50%', background: 'var(--green)', animation: 'pulse 2s infinite', boxShadow: '0 0 6px var(--green)' }}></span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {trains.map((tr) => {
              const occColor = tr.occupancy > 95 ? '#EF4444' : tr.occupancy > 80 ? '#F59E0B' : '#10B981';
              return (
                <div key={tr.train_id} style={{ background: 'var(--surface-high)', borderRadius: '10px', padding: '12px', border: tr.status === 'delayed' ? '1px solid #F59E0B44' : '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: 600 }}>{tr.name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{tr.route}</div>
                    </div>
                    <div>
                      {tr.status === 'delayed' ? (
                        <span style={{ fontSize: '11px', color: 'var(--amber)', fontWeight: 600 }}>+{tr.delay}m</span>
                      ) : (
                        <span style={{ fontSize: '11px', color: 'var(--green)', fontWeight: 600 }}>{t.onTime}</span>
                      )}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div className="progress-bar" style={{ flex: 1 }}>
                      <div className="progress-fill" style={{ width: `${tr.occupancy}%`, background: occColor }}></div>
                    </div>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)', width: '28px' }}>{tr.occupancy}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Ticket Volume Chart - 13 Days Bar Chart */}
      <div className="card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: '14px' }}>{t.weeklyVolumeTitle}</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>{t.weeklyVolumeSubtitle}</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '4px', alignItems: 'flex-end', height: '80px' }}>
          {(stats.weeklyVolume || []).map((vol, i) => {
            const max = Math.max(...(stats.weeklyVolume || [1]));
            const heightPercent = `${(vol / max) * 100}%`;
            const isLast = i === ((stats.weeklyVolume || []).length - 1);
            return (
              <div
                key={i}
                className="mini-chart-bar"
                style={{
                  height: heightPercent,
                  background: isLast ? 'var(--amber)' : '#F59E0B66',
                  borderRadius: '3px 3px 0 0',
                  flex: 1
                }}
                title={`Day ${13-i} ago: ${vol} tickets`}
              />
            );
          })}
        </div>
      </div>
      
    </div>
  );
}
