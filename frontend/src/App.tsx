import { useState } from 'react'
import Dashboard from './pages/Dashboard'
import Documents from './pages/Documents'
import GenerateTests from './pages/GenerateTests'
import Results from './pages/Results'
import History from './pages/History'
import './App.css'

const pages = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'documents', label: 'Documents' },
  { key: 'generate', label: 'Generate Tests' },
  { key: 'results', label: 'Results' },
  { key: 'history', label: 'History' },
]

type PageKey = 'dashboard' | 'documents' | 'generate' | 'results' | 'history'

function App() {
  const [currentPage, setCurrentPage] = useState<PageKey>('dashboard')

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">TestPilot Lite RAG</div>
        <nav>
          {pages.map((page) => (
            <button
              key={page.key}
              className={currentPage === page.key ? 'active' : ''}
              onClick={() => setCurrentPage(page.key as PageKey)}
            >
              {page.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="content">
        {currentPage === 'dashboard' && <Dashboard />}
        {currentPage === 'documents' && <Documents />}
        {currentPage === 'generate' && <GenerateTests />}
        {currentPage === 'results' && <Results />}
        {currentPage === 'history' && <History />}
      </main>
    </div>
  )
}

export default App
