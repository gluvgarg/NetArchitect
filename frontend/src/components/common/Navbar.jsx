import React from 'react'
import { StatusBadge } from './StatusBadge'

/**
 * Main application navigation bar.
 */
export function Navbar({ backendStatus, latencyMs, onRefreshStatus }) {
  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 32px',
        borderBottom: '1px solid #e2e8f0',
        backgroundColor: '#ffffff',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            backgroundColor: '#2563eb',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: '800',
            fontSize: '1.1rem',
          }}
        >
          NA
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '1.25rem', fontWeight: '700', margin: 0, color: '#0f172a' }}>
              NetArchitect
            </h1>
            <span
              style={{
                fontSize: '0.75rem',
                backgroundColor: '#f1f5f9',
                color: '#475569',
                padding: '2px 8px',
                borderRadius: '4px',
                fontWeight: '500',
              }}
            >
              Academic CN Engine
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '0.8rem', color: '#64748b' }}>
            Recommendation &amp; Configuration Engine for Computer Networks
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <StatusBadge status={backendStatus} latencyMs={latencyMs} />
        <button
          onClick={onRefreshStatus}
          title="Re-check FastAPI connection"
          style={{
            padding: '6px 12px',
            borderRadius: '6px',
            border: '1px solid #cbd5e1',
            backgroundColor: '#ffffff',
            color: '#334155',
            cursor: 'pointer',
            fontSize: '0.82rem',
            fontWeight: '500',
          }}
        >
          Ping API
        </button>
      </div>
    </header>
  )
}
