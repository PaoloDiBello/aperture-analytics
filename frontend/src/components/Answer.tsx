import { type ReactElement, type ReactNode } from 'react'

/** Very small markdown-ish renderer for agent answers.
 * Supports **bold**, `inline code`, and - bullets. Keeps things safe
 * (no raw HTML injection) and lightweight.
 */
function renderLine(line: string): ReactNode[] {
  const nodes: ReactNode[] = []
  const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g
  let lastIndex = 0
  let key = 0
  let match: RegExpExecArray | null
  while ((match = regex.exec(line)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(line.slice(lastIndex, match.index))
    }
    const token = match[0]
    if (token.startsWith('**')) {
      nodes.push(
        <strong key={key++}>{token.slice(2, -2)}</strong>,
      )
    } else {
      nodes.push(
        <code key={key++}>{token.slice(1, -1)}</code>,
      )
    }
    lastIndex = match.index + token.length
  }
  if (lastIndex < line.length) nodes.push(line.slice(lastIndex))
  return nodes
}

export function Answer({ text }: { text: string }) {
  const lines = text.split('\n')
  const blocks: (ReactElement | null)[] = []
  let key = 0

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue
    if (trimmed.startsWith('- ')) {
      blocks.push(
        <li key={key++}>{renderLine(trimmed.slice(2))}</li>,
      )
    } else if (trimmed.startsWith('• ')) {
      blocks.push(
        <li key={key++}>{renderLine(trimmed.slice(2))}</li>,
      )
    } else {
      blocks.push(<p key={key++}>{renderLine(trimmed)}</p>)
    }
  }

  return <div className="answer">{blocks}</div>
}
