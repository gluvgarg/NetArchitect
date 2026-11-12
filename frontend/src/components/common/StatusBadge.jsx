import React from 'react'

/**
 * StatusBadge: Visual indicator for backend connectivity.
 */
export function StatusBadge({ status, latencyMs }) {
  const getBadgeConfig = () => {
    switch (status) {
      case 'connected':
        return {
          text: `Backend Online${latencyMs ? ` (${latencyMs}ms)` : ''}`,
          color: '#10b981',
          bgColor: '#d1fae5',
          borderColor: '#6ee7b7',
        }
      case 'disconnected':
        return {
          text: 'Backend Offline',
          color: '#ef4444',
          bgColor: '#fee2e2',
          borderColor: '#fca5a5',
        }
      case 'checking':
      default:
        return {
          text: 'Connecting...',
          color: '#f59e0b',
          bgColor: '#fef3c7',
          borderColor: '#fcd34d',
        }
    }
  }

  const { text, color, bgColor, borderColor } = getBadgeConfig()

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        padding: '6px 14px',
        borderRadius: '9999px',
        fontSize: '0.85rem',
        fontWeight: '600',
        backgroundColor: bgColor,
        color: color,
        border: `1px solid ${borderColor}`,
        fontFamily: 'inherit',
      }}
    >
      <span
        style={{
          width: '9px',
          height: '9px',
          borderRadius: '50%',
          backgroundColor: color,
          display: 'inline-block',
        }}
      />
      {text}
    </div>
  )
}
