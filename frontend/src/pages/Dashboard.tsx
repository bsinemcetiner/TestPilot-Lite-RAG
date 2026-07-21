import { useEffect, useState } from 'react'
import { getDocuments, getChunkCount } from '../api/apiClient'

function Dashboard() {
  const [docCount, setDocCount] = useState(0)
  const [chunkCount, setChunkCount] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const docs = await getDocuments()
        setDocCount(docs.length)

        let totalChunks = 0
        for (const doc of docs) {
          const count = await getChunkCount(doc.id)
          totalChunks += count
        }
        setChunkCount(totalChunks)
      } catch (error) {
        console.error('Failed to fetch stats', error)
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  return (
    <div>
      <h1 className="section-title">Dashboard</h1>

      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Documents Indexed</div>
          <div className="metric-value">{loading ? '...' : docCount}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Total Chunks</div>
          <div className="metric-value">{loading ? '...' : chunkCount}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">RAG Pipeline</div>
          <div className="metric-value">Ready</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Status</div>
          <div className="metric-value">Active</div>
        </div>
      </div>

      <div className="card">
        <h2 className="section-title">Welcome to TestPilot Lite RAG</h2>
        <p>
          TestPilot Lite RAG is an AI-powered test scenario generator that creates structured test cases from your project documentation.
        </p>

        <h3>Quick Start</h3>
        <ol>
          <li><strong>Upload Documents:</strong> Go to the Documents page and upload your user stories, acceptance criteria, or API specifications.</li>
          <li><strong>Index and Chunk:</strong> The system automatically chunks and indexes your documents using embeddings.</li>
          <li><strong>Generate Tests:</strong> Go to Generate Tests, describe a feature you want to test, and get structured test cases.</li>
          <li><strong>Export:</strong> Export your test cases in JSON, Markdown, CSV, or Gherkin format.</li>
        </ol>

        <h3>Supported Features</h3>
        <ul>
          <li>✅ Document upload (TXT, MD, JSON, YAML)</li>
          <li>✅ Automatic chunking and embedding</li>
          <li>✅ RAG-based test generation</li>
          <li>✅ Multiple test types (Positive, Negative, Edge Case, etc.)</li>
          <li>✅ Multiple export formats</li>
          <li>✅ Source document tracking</li>
        </ul>

        <h3>Technology Stack</h3>
        <ul>
          <li>Backend: FastAPI + SQLAlchemy</li>
          <li>Vector Store: ChromaDB</li>
          <li>Embeddings: sentence-transformers</li>
          <li>Frontend: React + TypeScript</li>
        </ul>
      </div>
    </div>
  )
}

export default Dashboard
