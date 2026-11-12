import React from 'react'
import { NETWORK_PROFILES } from '../data/networkProfiles'
import { ENGINE_MODULES } from '../data/engineModules'

export function Dashboard({ backendHealth }) {
  const { status, details, lastChecked, latencyMs, error, recheck } = backendHealth

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Hero Welcome Section */}
      <section
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '12px',
          padding: '28px 32px',
          border: '1px solid #e2e8f0',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        }}
      >
        <div style={{ maxWidth: '800px' }}>
          <h2 style={{ fontSize: '1.6rem', fontWeight: '800', color: '#0f172a', margin: '0 0 10px 0' }}>
            NetArchitect: Recommendation &amp; Config Engine
          </h2>
          <p style={{ fontSize: '1rem', color: '#475569', lineHeight: '1.6', margin: 0 }}>
            An academic Computer Networks system architected to solve physical transmission media selection,
            hierarchical VLSM IP subnetting, routing protocol optimization, and multi-vendor CLI configuration generation.
          </p>
        </div>
      </section>

      {/* Real-time Backend Health Connection Status Card */}
      <section
        style={{
          borderRadius: '12px',
          padding: '24px 28px',
          border: `1px solid ${status === 'connected' ? '#a7f3d0' : status === 'disconnected' ? '#fecaca' : '#fde68a'}`,
          backgroundColor: status === 'connected' ? '#f0fdf4' : status === 'disconnected' ? '#fff5f5' : '#fffbeb',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span
                style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  backgroundColor: status === 'connected' ? '#10b981' : status === 'disconnected' ? '#ef4444' : '#f59e0b',
                  display: 'inline-block',
                }}
              />
              <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: '700', color: '#0f172a' }}>
                FastAPI Backend Connection:{' '}
                <span style={{ textTransform: 'capitalize', color: status === 'connected' ? '#059669' : '#dc2626' }}>
                  {status}
                </span>
              </h3>
            </div>
            <p style={{ margin: '8px 0 0 0', fontSize: '0.9rem', color: '#475569' }}>
              Target Endpoint: <code>/health</code> on <code>http://127.0.0.1:8000</code> (CORS enabled)
            </p>
            {lastChecked && (
              <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#64748b' }}>
                Last checked: <strong>{lastChecked}</strong> {latencyMs !== null && `• Round-trip: ${latencyMs}ms`}
              </p>
            )}
            {details && (
              <div style={{ marginTop: '10px', fontSize: '0.85rem', color: '#065f46' }}>
                Response: <code>{JSON.stringify(details)}</code>
              </div>
            )}
            {error && (
              <div style={{ marginTop: '10px', fontSize: '0.85rem', color: '#b91c1c' }}>
                Diagnostic: {error}. Ensure FastAPI is started with: <code>uvicorn main:app --reload --port 8000</code>
              </div>
            )}
          </div>

          <button
            onClick={recheck}
            style={{
              padding: '8px 16px',
              backgroundColor: '#2563eb',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontWeight: '600',
              cursor: 'pointer',
              fontSize: '0.85rem',
            }}
          >
            Re-test Backend Health
          </button>
        </div>
      </section>

      {/* Mandatory Network Profiles */}
      <section>
        <div style={{ marginBottom: '16px' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: '700', margin: '0 0 4px 0', color: '#0f172a' }}>
            Mandatory Network Profiles
          </h3>
          <p style={{ margin: 0, fontSize: '0.9rem', color: '#64748b' }}>
            Managed by <code>services/scenario_service.py</code> with domain-specific distance and throughput constraints.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          {NETWORK_PROFILES.map((profile) => (
            <div
              key={profile.id}
              style={{
                backgroundColor: '#ffffff',
                borderRadius: '10px',
                padding: '20px',
                border: '1px solid #e2e8f0',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '700', color: '#1e293b' }}>
                  {profile.name}
                </h4>
                <span
                  style={{
                    fontSize: '0.75rem',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    backgroundColor: '#eff6ff',
                    color: '#2563eb',
                    fontWeight: '600',
                  }}
                >
                  {profile.scope}
                </span>
              </div>

              <div style={{ fontSize: '0.85rem', color: '#475569', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <div><strong>Bandwidth Target:</strong> {profile.bandwidth}</div>
                <div><strong>Latency Profile:</strong> {profile.latency}</div>
                <div><strong>Physical Media:</strong> {profile.primaryMedia}</div>
                <div><strong>Routing Strategy:</strong> {profile.routing}</div>
                <div><strong>Addressing:</strong> {profile.addressing}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Modular Algorithmic Engines Scaffolding Status */}
      <section>
        <div style={{ marginBottom: '16px' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: '700', margin: '0 0 4px 0', color: '#0f172a' }}>
            Modular Algorithm Engines
          </h3>
          <p style={{ margin: 0, fontSize: '0.9rem', color: '#64748b' }}>
            Clean module scaffolding established in <code>backend/engines/</code> ready for algorithm implementation.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
          {ENGINE_MODULES.map((eng) => (
            <div
              key={eng.name}
              style={{
                backgroundColor: '#ffffff',
                borderRadius: '8px',
                padding: '16px',
                border: '1px solid #e2e8f0',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '8px',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: '700', color: '#6366f1', textTransform: 'uppercase' }}>
                    {eng.layer}
                  </span>
                  <span
                    style={{
                      fontSize: '0.7rem',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      backgroundColor: '#e0e7ff',
                      color: '#4338ca',
                      fontWeight: '600',
                    }}
                  >
                    {eng.status}
                  </span>
                </div>
                <h4 style={{ margin: '0 0 6px 0', fontSize: '0.95rem', fontWeight: '700', color: '#0f172a' }}>
                  {eng.name}
                </h4>
                <p style={{ margin: 0, fontSize: '0.8rem', color: '#64748b', lineHeight: '1.4' }}>
                  {eng.purpose}
                </p>
              </div>
              <code style={{ fontSize: '0.75rem', color: '#0284c7', backgroundColor: '#f0f9ff', padding: '4px 6px', borderRadius: '4px' }}>
                {eng.file}
              </code>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
