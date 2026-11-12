import React from 'react'
import { MainLayout } from './layouts/MainLayout'
import { Dashboard } from './pages/Dashboard'
import { useBackendHealth } from './hooks/useBackendHealth'

function App() {
  const backendHealth = useBackendHealth()

  return (
    <MainLayout
      backendStatus={backendHealth.status}
      latencyMs={backendHealth.latencyMs}
      onRefreshStatus={backendHealth.recheck}
    >
      <Dashboard backendHealth={backendHealth} />
    </MainLayout>
  )
}

export default App
