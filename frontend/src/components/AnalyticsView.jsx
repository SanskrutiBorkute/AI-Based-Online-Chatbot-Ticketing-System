import React, { useState, useEffect } from 'react';
import SvgIcon from './SvgIcon';
import { apiFetch } from '../api';

export default function AnalyticsView({ t }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('7d');

  const fetchAnalytics = async () => {
    try {
      const anaData = await apiFetch('/api/analytics/data');
      setData(anaData || {});
      setLoading(false);
    } catch (err) {
      console.error("Error fetching analytics:", err);
      setData({});
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [period]);

  const sparklineSVG = (sparkData, color) => {
    if (!sparkData || !sparkData.length) return '';
    const width = 220;
    const height = 40;
    const max = Math.max(...sparkData);
    const min = Math.min(...sparkData);
    const pts = sparkData.map((v, i) => {
      const x = (i / (sparkData.length - 1)) * width;
      const y = height - ((v - min) / (max - min || 1)) * height;
      return `${x},${y}`;
    }).join(' ');
    return (
      <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <polyline points={pts} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  };

  const donutSVG = (segments) => {
    const size = 110;
    const r = 36;
    const cx = size / 2;
    const cy = size / 2;
    const circumference = 2 * Math.PI * r;
    const total = segments.reduce((s, seg) => s + seg.value, 0);
    
    let offset = 0;
    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1A2B47" strokeWidth="10" />
        {segments.map((seg, i) => {
          const dash = (seg.value / (total || 1)) * circumference;
          const strokeOffset = offset;
          offset += dash;
          return (
            <circle
              key={i}
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={seg.color}
              strokeWidth="10"
              strokeDasharray={`${dash} ${circumference}`}
              strokeDashoffset={-strokeOffset}
              strokeLinecap="round"
            />
          );
        })}
      </svg>
    );
  };

  if (loading || !data) {
    return (
      <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '32px', height: '32px', border: '3px solid var(--border)', borderTopColor: 'var(--amber)', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
          <span style={{ fontSize: '13px' }}>Loading Analytics...</span>
        </div>
      </div>
    );
  }

  const volByType = data.volumeByType || [];
  const totalVolume = (volByType.length > 0) ? volByType.reduce((s, v) => s + v.value, 0) : 0;

  if (!loading && totalVolume === 0) {
    return (
      <div id="page-analytics" className="page active" style={{ overflowY: 'auto', padding: '24px', flexDirection: 'column', gap: '20px', display: 'flex' }}>
        <div>
          <h2 style={{ fontSize: '16px', fontWeight: 700 }}>{t.operationalAnalytics}</h2>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '3px' }}>{t.analyticsSubtitle}</p>
        </div>
        <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '360px', border: '1px dashed var(--border)', borderRadius: '12px', padding: '40px', color: 'var(--text-muted)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', textAlign: 'center' }}>
            <SvgIcon name="chart" size={48} color="var(--text-muted)" />
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text)' }}>No analytics data available.</h3>
            <p style={{ fontSize: '12px', maxWidth: '320px' }}>Charts and trends will be generated dynamically once tickets are registered in the database.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div id="page-analytics" className="page active" style={{ overflowY: 'auto', padding: '24px', flexDirection: 'column', gap: '20px', display: 'flex' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '16px', fontWeight: 700 }}>{t.operationalAnalytics}</h2>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '3px' }}>{t.analyticsSubtitle}</p>
        </div>
        
        <div style={{ display: 'flex', gap: '8px' }}>
          {['24h', '7d', '30d'].map(p => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              style={{
                padding: '6px 12px',
                borderRadius: '7px',
                fontSize: '12px',
                cursor: 'pointer',
                background: period === p ? '#F59E0B22' : 'transparent',
                color: period === p ? 'var(--amber)' : 'var(--text-muted)',
                border: `1px solid ${period === p ? '#F59E0B44' : 'var(--border)'}`,
                fontFamily: 'inherit',
                fontWeight: 500,
                transition: 'all .15s'
              }}
            >
              {p}
            </button>
          ))}
          <button className="btn-ghost" style={{ fontSize: '12px' }}>
            <SvgIcon name="refresh" size={13} />
            {t.export}
          </button>
        </div>
      </div>

      {/* KPIs Grids */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px' }}>
        {(data.kpis || []).map((k, i) => (
          <div key={i} className="stat-card" style={{ padding: '16px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '.06em' }}>
              {k.label === 'Total Tickets' ? t.totalTickets : 
               k.label === 'Open Tickets' ? t.openTickets : 
               k.label === 'Resolved Tickets' ? t.resolvedTickets : 
               k.label === 'Critical Tickets' ? t.criticalTickets : 
               k.label === 'AI Resolved Issues' ? t.aiResolvedIssues : k.label}
            </div>
            <div style={{ fontSize: '22px', fontWeight: 800 }}>{k.value}</div>
            {k.label !== 'AI Resolved Issues' && (
              <div style={{ fontSize: '11px', marginTop: '6px', color: k.good ? 'var(--green)' : 'var(--red)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <SvgIcon name={k.good ? 'arrowUp' : 'arrowDown'} size={11} color={k.good ? '#10B981' : '#EF4444'} />
                {Math.abs(k.delta)}% {t.thisPeriod}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Resolution Rate Weekly Trend Timeline */}
      <div className="card" style={{ padding: '20px' }}>
        <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{t.resolutionRateTrend}</div>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>{t.dailyVolumeSubtitle}</div>
        <div style={{ position: 'relative', height: '120px', marginBottom: '8px' }}>
          <div style={{ display: 'flex', gap: '6px', height: '100%', alignItems: 'flex-end', position: 'absolute', inset: 0 }}>
            {(data.volumeByDay || []).map((v, i) => {
              const maxV = Math.max(...(data.volumeByDay || [1]), 1);
              return (
                <div
                  key={i}
                  style={{
                    flex: 1,
                    borderRadius: '4px 4px 0 0',
                    height: `${(v / maxV) * 85}%`,
                    background: 'linear-gradient(180deg, var(--border-light), var(--surface-high))',
                    border: '1px solid var(--border)'
                  }}
                  title={`Tickets: ${v}`}
                />
              );
            })}
          </div>
          <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', display: 'flex', alignItems: 'center', paddingBottom: '10px' }}>
            {sparklineSVG(data.resolutionByDay, '#10B981')}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '6px', borderTop: '1px solid var(--border)' }}>
          {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, i) => (
            <div key={i} style={{ flex: 1, textAlign: 'center', fontSize: '10px', color: 'var(--text-muted)', paddingTop: '6px' }}>
              {day}
            </div>
          ))}
        </div>
      </div>

      {/* Distributions (Department & Category) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        
        {/* Department Distribution */}
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{t.departmentDistribution}</div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>Ticket volume by department</div>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <div style={{ position: 'relative', flexShrink: 0 }}>
              {donutSVG(data.volumeByDept || [])}
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                <div style={{ fontSize: '18px', fontWeight: 800 }}>{data.volumeByDept ? data.volumeByDept.reduce((s, v) => s + v.value, 0) : 0}</div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Total</div>
              </div>
            </div>
            <div style={{ flex: 1 }}>
              {(data.volumeByDept || []).map((seg, i) => {
                const total = data.volumeByDept.reduce((s, v) => s + v.value, 0);
                return (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: seg.color, flexShrink: 0 }}></div>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{seg.label}</span>
                    </div>
                    <span style={{ fontSize: '11px', fontWeight: 600 }}>{Math.round((seg.value / (total || 1)) * 100)}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Category Distribution */}
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{t.ticketCategoryDistribution}</div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>Ticket volume by category</div>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <div style={{ position: 'relative', flexShrink: 0 }}>
              {donutSVG(data.volumeByType || [])}
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                <div style={{ fontSize: '18px', fontWeight: 800 }}>{totalVolume}</div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Total</div>
              </div>
            </div>
            <div style={{ flex: 1 }}>
              {volByType.map((seg, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: seg.color, flexShrink: 0 }}></div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{seg.label}</span>
                  </div>
                  <span style={{ fontSize: '11px', fontWeight: 600 }}>{Math.round((seg.value / (totalVolume || 1)) * 100)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
