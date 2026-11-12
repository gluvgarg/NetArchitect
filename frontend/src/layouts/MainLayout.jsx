import React from 'react'
import { Navbar } from '../components/common/Navbar'

/**
 * Main application layout with header, responsive container, and academic footer.
 */
export function MainLayout({ backendStatus, latencyMs, onRefreshStatus, children }) {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#f8fafc',
        color: '#1e293b',
        fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
      }}
    >
      <Navbar
        backendStatus={backendStatus}
        latencyMs={latencyMs}
        onRefreshStatus={onRefreshStatus}
      />

      <main style={{ flex: 1, maxWidth: '1200px', width: '100%', margin: '0 auto', padding: '32px 24px' }}>
        {children}
      </main>

      <footer
        style={{
          borderTop: '1px solid #e2e8f0',
          backgroundColor: '#ffffff',
          padding: '20px 32px',
          textAlign: 'center',
          fontSize: '0.85rem',
          color: '#64748b',
        }}
      >
        <p style={{ margin: 0 }}>
          <strong>NetArchitect</strong> — Computer Networks Academic Project. Designed for algorithmic network recommendation, VLSM partitioning, routing optimization, and device config generation.
        </p>
      </footer>
    </div>
  )
}
