import { useEffect, useState, FormEvent } from 'react'
import { DocumentRecord, getDocuments, uploadDocumentText, uploadDocumentFile, getChunkCount } from '../api/apiClient'

const documentFormats = ['md', 'txt', 'json', 'yaml']

type DocumentWithChunks = DocumentRecord & { chunk_count?: number; loading_chunks?: boolean }

function Documents() {
  const [documents, setDocuments] = useState<DocumentWithChunks[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingDocuments, setLoadingDocuments] = useState(false)
  const [message, setMessage] = useState('')
  const [name, setName] = useState('')
  const [format, setFormat] = useState('md')
  const [sourceType, setSourceType] = useState('')
  const [content, setContent] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [useFileUpload, setUseFileUpload] = useState(false)

  useEffect(() => {
    void fetchDocuments()
  }, [])

  const fetchDocuments = async () => {
    setLoadingDocuments(true)
    try {
      const docs = await getDocuments()
      setDocuments(docs as DocumentWithChunks[])

      docs.forEach(async (doc) => {
        try {
          const chunkCount = await getChunkCount(doc.id)
          setDocuments((prev) =>
            prev.map((d) => (d.id === doc.id ? { ...d, chunk_count: chunkCount } : d))
          )
        } catch {
          console.error(`Failed to get chunk count for doc ${doc.id}`)
        }
      })
    } catch {
      setMessage('Could not load documents.')
    } finally {
      setLoadingDocuments(false)
    }
  }

  const resetForm = () => {
    setName('')
    setFormat('md')
    setSourceType('')
    setContent('')
    setFile(null)
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      let created
      if (useFileUpload && file) {
        created = await uploadDocumentFile(name || file.name, format, sourceType, file)
      } else {
        created = await uploadDocumentText({
          name: name || 'Untitled document',
          content,
          format,
          source_type: sourceType || undefined,
        })
      }
      setMessage(`Document "${created.name}" uploaded successfully.`)
      resetForm()
      await fetchDocuments()
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed.'
      setMessage(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="section-title">Documents</h1>
      <div className="card">
        <div className="form-row">
          <label>
            Upload method
            <select value={useFileUpload ? 'file' : 'text'} onChange={(e) => setUseFileUpload(e.target.value === 'file')}>
              <option value="text">Paste text</option>
              <option value="file">Upload file</option>
            </select>
          </label>
        </div>

        <form onSubmit={handleSubmit} className="document-form">
          <div className="form-row">
            <label>
              Document name
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Document title" />
            </label>
          </div>

          <div className="form-row">
            <label>
              Format
              <select value={format} onChange={(e) => setFormat(e.target.value)}>
                {documentFormats.map((option) => (
                  <option value={option} key={option}>
                    {option.toUpperCase()}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Source type
              <input value={sourceType} onChange={(e) => setSourceType(e.target.value)} placeholder="e.g. user_story" />
            </label>
          </div>

          {useFileUpload ? (
            <div className="form-row">
              <label>
                File
                <input
                  type="file"
                  accept=".txt,.md,.json,.yaml,.yml"
                  onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
                />
              </label>
            </div>
          ) : (
            <div className="form-row">
              <label>
                Content
                <textarea
                  rows={10}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Paste document text here"
                />
              </label>
            </div>
          )}

          <div className="form-row">
            <button type="submit" disabled={loading}>
              {loading ? 'Uploading...' : 'Upload Document'}
            </button>
          </div>
        </form>

        {message && <p>{message}</p>}
      </div>

      <div className="card">
        <h2 className="section-title">Indexed Documents</h2>
        {loadingDocuments && documents.length === 0 ? (
          <div className="empty-state">Loading documents…</div>
        ) : documents.length === 0 ? (
          <div className="empty-state">No documents indexed yet. Add one to begin generating tests.</div>
        ) : (
          <table className="doc-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Format</th>
                <th>Source type</th>
                <th>Chunks</th>
                <th>Created at</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.name}</td>
                  <td>{doc.format}</td>
                  <td>{doc.source_type || '-'}</td>
                  <td>{doc.chunk_count !== undefined ? doc.chunk_count : '...'}</td>
                  <td>{new Date(doc.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default Documents
