import { useState } from 'react'
import './App.css'
import { askQuestion, uploadDataset } from './api'
import type { DatasetPreview } from './types'
import { FileUpload } from './components/FileUpload'
import { PreviewTable } from './components/PreviewTable'
import { Answer } from './components/Answer'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

function App() {
  const [dataset, setDataset] = useState<DatasetPreview | null>(null)
  const [datasetId, setDatasetId] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [busy, setBusy] = useState(false)

  async function handleFile(file: File) {
    setError(null)
    setUploading(true)
    try {
      const res = await uploadDataset(file)
      setDataset(res.preview)
      setDatasetId(res.dataset_id)
      setMessages([])
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setUploading(false)
    }
  }

  async function handleAsk() {
    const q = question.trim()
    if (!q || !datasetId || busy) return
    setQuestion('')
    setError(null)
    setMessages((m) => [...m, { role: 'user', content: q }])
    setBusy(true)
    try {
      const res = await askQuestion(datasetId, q)
      setMessages((m) => [...m, { role: 'assistant', content: res.answer }])
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: `⚠️ ${(e as Error).message}` }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">Aperture Analytics</div>
        <div className="tagline">Ask anything. It sees into your data.</div>
      </header>

      <main className="main">
        {!dataset ? (
          <section className="landing">
            <h1>Understand your data by asking questions</h1>
            <p className="lede">
              Upload a CSV and ask natural-language questions. A tool-using AI
              agent inspects the data, runs real calculations, and answers with
              evidence from your numbers.
            </p>
            <FileUpload onFile={handleFile} loading={uploading} />
            {error && <div className="error">{error}</div>}
            <div className="examples">
              <span>Try asking:</span>
              <ul>
                <li>“Which product generated the most revenue?”</li>
                <li>“Show me the top 5 products by profit.”</li>
                <li>“Why did revenue drop in March?”</li>
              </ul>
            </div>
          </section>
        ) : (
          <div className="workspace">
            <section className="panel wood">
              <div className="panel-head">
                <h2>Dataset</h2>
                <button
                  className="reset"
                  onClick={() => {
                    setDataset(null)
                    setDatasetId(null)
                    setMessages([])
                  }}
                >
                  Upload another
                </button>
              </div>
              <PreviewTable preview={dataset} />
            </section>

            <section className="panel chat">
              <div className="panel-head">
                <h2>Ask the agent</h2>
              </div>
              <div className="messages">
                {messages.length === 0 && (
                  <p className="hint">
                    Ask a question about <strong>{dataset.name}</strong>.
                  </p>
                )}
                {messages.map((m, i) =>
                  m.role === 'user' ? (
                    <div key={i} className="msg user">
                      {m.content}
                    </div>
                  ) : (
                    <div key={i} className="msg assistant">
                      <Answer text={m.content} />
                    </div>
                  ),
                )}
                {busy && <div className="msg assistant busy">Analyzing…</div>}
              </div>
              <div className="composer">
                <input
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
                  placeholder="Ask about your data…"
                  disabled={busy}
                />
                <button onClick={handleAsk} disabled={busy || !question.trim()}>
                  Ask
                </button>
              </div>
              {error && <div className="error">{error}</div>}
            </section>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
