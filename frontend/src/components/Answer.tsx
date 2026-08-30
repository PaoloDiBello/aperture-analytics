import { Fragment, type ReactNode } from 'react'

function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = []
  const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g
  let lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index))
    const token = match[0]
    if (token.startsWith('**')) nodes.push(<strong key={nodes.length}>{token.slice(2, -2)}</strong>)
    else nodes.push(<code key={nodes.length}>{token.slice(1, -1)}</code>)
    lastIndex = match.index + token.length
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex))
  return nodes
}

function renderLines(lines: string[]): ReactNode[] {
  const nodes: ReactNode[] = []
  let list: ReactNode[] = []
  let inList = false

  const flush = () => {
    if (inList) {
      nodes.push(
        <ul key={nodes.length} className="my-2 list-disc space-y-1 pl-5">
          {list}
        </ul>,
      )
      list = []
      inList = false
    }
  }

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) {
      flush()
      continue
    }
    if (line.startsWith('- ')) {
      if (!inList) {
        inList = true
        list = []
      }
      list.push(<li key={list.length}>{renderInline(line.slice(2))}</li>)
    } else if (/^\d+\. /.test(line)) {
      flush()
      nodes.push(<p key={nodes.length}>{renderInline(line)}</p>)
    } else {
      flush()
      nodes.push(<p key={nodes.length} className={nodes.length ? 'mt-2' : ''}>{renderInline(line)}</p>)
    }
  }
  flush()
  return nodes
}

export function Answer({ text }: { text: string }) {
  return (
    <div className="text-[13px] leading-relaxed text-foreground">
      <style>{'code { background: rgba(255,255,255,0.08); padding: 0 0.25em; border-radius: 4px; }'}</style>
      {renderLines(text.split('\n')).map((n, i) => (
        <Fragment key={i}>{n}</Fragment>
      ))}
    </div>
  )
}
