export interface DatasetPreview {
  name: string
  rows: number
  columns: number
  column_names: string[]
  dtypes: Record<string, string>
  preview: Record<string, unknown>[]
}

export interface UploadResponse {
  dataset_id: string
  preview: DatasetPreview
}

export interface QueryResponse {
  answer: string
}
