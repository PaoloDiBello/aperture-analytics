import { useRef, useState } from 'react'
import { UploadCloud, FileText, Sparkles, BarChart3, Table2, Database, X, Trophy, TrendingUp, ArrowUp, Bot } from 'lucide-react'
import { askQuestion, uploadDataset } from './api'
import type { DatasetPreview } from './types'
import { Answer } from './components/Answer'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card'
import { Separator } from './ui/separator'

type Msg = { role: 'user' | 'assistant'; content: string }

export function HomePage() {
  const [dataset, setDataset] = useState<DatasetPreview | null>(null)
  const [datasetId, setDatasetId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<Msg[]>([])
  const [busy, setBusy] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  async function handleFile(file: File) {
    setError(null)
    setFileName(file.name)
    try {
      const res = await uploadDataset(file)
      setDataset(res.preview)
      setDatasetId(res.dataset_id)
    } catch (e) {
      setError((e as Error).message)
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
      setMessages((m) => [...m, { role: 'assistant', content: `Error: ${(e as Error).message}` }])
    } finally {
      setBusy(false)
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) handleFile(file)
  }

  function reset() {
    setDataset(null)
    setDatasetId(null)
    setMessages([])
    setError(null)
    setFileName(null)
    setQuestion('')
  }

  /* ---------------- Landing (no dataset) ---------------- */
  if (!dataset) {
    return (
      <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-6 text-foreground">
        {/* ambient gradient glows */}
        <div className="pointer-events-none absolute -top-32 left-1/2 h-[480px] w-[720px] -translate-x-1/2 rounded-full bg-primary/20 blur-[120px]" />
        <div className="pointer-events-none absolute bottom-0 right-0 h-[360px] w-[360px] rounded-full bg-violet-500/20 blur-[120px]" />

        <div className="relative w-full max-w-xl text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-xs text-muted-foreground shadow-sm">
            <Sparkles className="size-3.5 text-primary" />
            AI-powered CSV analysis
          </div>

          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Aperture <span className="text-primary">Analytics</span>
          </h1>
          <p className="mx-auto mt-4 max-w-md text-base text-muted-foreground">
            Upload a CSV and ask anything. The agent inspects your data and answers in plain English.
          </p>

          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) handleFile(f)
            }}
          />

          {/* Dropzone */}
          <div
            onClick={() => fileRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            className={`mt-8 cursor-pointer rounded-2xl border border-dashed p-12 transition-all ${
              dragging
                ? 'border-primary bg-primary/10'
                : 'border-border bg-card/50 hover:border-primary/60 hover:bg-card'
            }`}
          >
            <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-primary/15">
              <UploadCloud className="size-7 text-primary" />
            </div>
            <p className="mt-4 text-sm font-medium text-foreground">
              {dragging ? 'Drop it here' : 'Drag & drop a CSV'}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">or click to browse</p>
            <Button className="mt-5" variant="secondary">
              Choose CSV
            </Button>
          </div>

          {fileName && !error && fileName !== null && (
            <p className="mt-3 text-xs text-emerald-400">Uploading {fileName}…</p>
          )}
          {error && (
            <p className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-red-300">
              {error}
            </p>
          )}

          <div className="mt-8 flex items-center justify-center gap-3 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5"><BarChart3 className="size-3.5" /> Charts</span>
            <Separator orientation="vertical" className="h-4" />
            <span className="inline-flex items-center gap-1.5"><Table2 className="size-3.5" /> Preview</span>
            <Separator orientation="vertical" className="h-4" />
            <span className="inline-flex items-center gap-1.5"><Sparkles className="size-3.5" /> Agent answers</span>
          </div>
        </div>
      </div>
    )
  }

  /* ---------------- Workspace (dataset loaded) ---------------- */
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      {/* Top bar */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-6">
          <div className="flex items-center gap-2.5">
            <img src="/favicon.svg" alt="Aperture Analytics" className="h-7 w-7" />
            <span className="text-sm font-semibold tracking-tight">Aperture Analytics</span>
          </div>

          <div className="flex items-center gap-2">
            {fileName && (
              <Badge variant="outline" className="max-w-[180px] gap-1.5">
                <FileText className="size-3.5" />
                <span className="truncate">{fileName}</span>
              </Badge>
            )}
            <Button variant="outline" size="sm" onClick={reset}>
              <X className="size-4" />
              New dataset
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-6xl flex-1 gap-6 px-6 py-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        {/* Left: data panel */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Database className="size-4 text-primary" />
                  Dataset
                </CardTitle>
                <Badge variant="secondary">{dataset.rows} rows</Badge>
              </div>
              <CardDescription>
                {dataset.columns} columns &middot; {fileName}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {dataset.column_names.map((c) => (
                  <Badge key={c} variant="accent" className="font-mono text-[11px]">
                    {c}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Table2 className="size-4 text-primary" />
                Preview
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-left text-xs">
                  <thead className="bg-secondary/50">
                    <tr>
                      {dataset.column_names.slice(0, 5).map((c) => (
                        <th key={c} className="whitespace-nowrap px-3 py-2 font-semibold text-muted-foreground">
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {dataset.preview.slice(0, 6).map((row, i) => (
                      <tr key={i} className="hover:bg-accent/40">
                        {dataset.column_names.slice(0, 5).map((c) => (
                          <td key={c} className="max-w-[120px] truncate px-3 py-2 text-muted-foreground">
                            {String(row[c] ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Showing first {Math.min(6, dataset.preview.length)} of {dataset.rows} rows
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Right: chat panel */}
        <Card className="relative flex min-h-[600px] flex-col overflow-hidden">
          {/* subtle top glow */}
          <div className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-primary/10 to-transparent" />

          <CardContent className="relative flex flex-1 flex-col pt-5">
            {/* Messages */}
            <div className="flex flex-1 flex-col gap-4 overflow-y-auto pr-1">
              {messages.length === 0 && !busy && (
                <div className="flex flex-1 flex-col items-center justify-center text-center">
                  {/* orb */}
                  <div className="relative mb-5 flex size-16 items-center justify-center">
                    <div className="absolute inset-0 rounded-full bg-primary/30 blur-xl" />
                    <div className="relative flex size-14 items-center justify-center rounded-full border border-border bg-card shadow-inner">
                      <Bot className="size-7 text-primary" />
                    </div>
                  </div>

                  <p className="text-sm font-medium text-foreground">What should we figure out?</p>
                  <p className="mt-1 max-w-[260px] text-xs text-muted-foreground">
                    Ask in plain English and the agent will dig through your data and explain the answer.
                  </p>

                  <div className="mt-5 grid w-full gap-2">
                    {[
                      { t: 'Total revenue', d: 'Sum up the revenue column' },
                      { t: 'Top product', d: 'Which product sold the most?' },
                      { t: 'Trends', d: 'Spot patterns over time' },
                    ].map((s, idx) => (
                      <button
                        key={s.t}
                        onClick={() => setQuestion(s.d)}
                        className="group flex items-center gap-3 rounded-xl border border-border bg-card/60 px-4 py-3 text-left transition-all hover:border-primary/50 hover:bg-card hover:shadow-lg"
                        style={{ animationDelay: `${idx * 60}ms` }}
                      >
                        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 transition-colors group-hover:bg-primary/20">
                          {idx === 0 ? <BarChart3 className="size-4 text-primary" /> : idx === 1 ? <Trophy className="size-4 text-primary" /> : <TrendingUp className="size-4 text-primary" />}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-foreground">{s.t}</p>
                          <p className="text-xs text-muted-foreground">{s.d}</p>
                        </div>
                        <ArrowUp className="ml-auto size-4 shrink-0 -rotate-45 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((m, i) => (
                <div key={i} className={m.role === 'user' ? 'ml-auto' : ''}>
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                      m.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'border border-border bg-card text-foreground'
                    }`}
                  >
                    {m.role === 'user' ? m.content : <Answer text={m.content} />}
                  </div>
                </div>
              ))}

              {busy && (
                <div className="rounded-2xl border border-border bg-card px-4 py-3 self-start">
                  <span className="flex items-center gap-1.5">
                    <span className="size-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.2s]" />
                    <span className="size-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.1s]" />
                    <span className="size-1.5 animate-bounce rounded-full bg-primary" />
                  </span>
                </div>
              )}
            </div>

            {/* Input */}
            <div className="mt-4 border-t border-border pt-4">
              {error && (
                <p className="mb-3 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-red-300">
                  {error}
                </p>
              )}
              <div className="flex items-center gap-2 rounded-2xl border border-border bg-card p-1.5 shadow-sm transition-colors focus-within:border-primary/60 focus-within:shadow-lg">
                <input
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
                  placeholder="Ask anything about your data…"
                  disabled={busy}
                  className="flex-1 bg-transparent px-2.5 py-1.5 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
                />
                <Button
                  size="icon"
                  onClick={handleAsk}
                  disabled={busy || !question.trim()}
                  className="size-8 rounded-xl bg-gradient-to-br from-primary to-violet-500"
                >
                  <ArrowUp className="size-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}

function App() {
  return <HomePage />
}

export default App
