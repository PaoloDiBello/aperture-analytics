import type { DatasetPreview } from '../types'

export function PreviewTable({ preview }: { preview: DatasetPreview }) {
  return (
    <div className="preview">
      <div className="preview-meta">
        <strong>{preview.name}</strong>
        <span>
          {preview.rows} rows × {preview.columns} columns
        </span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {preview.column_names.map((c) => (
                <th key={c}>
                  {c}
                  <span className="dtype">{preview.dtypes[c]}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {preview.preview.map((row, i) => (
              <tr key={i}>
                {preview.column_names.map((c) => (
                  <td key={c}>{String(row[c] ?? '')}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
