export type SummaryItem = {
  label: string
  value: string
  helper: string
}

export type RecentTransaction = {
  id: string
  company: string
  category: string
  type: 'Entrada' | 'Saída'
  amount: string
  date: string
}

export type QuickAction = {
  title: string
  description: string
  href: string
}

export type Insight = {
  title: string
  description: string
  tone: 'positive' | 'warning' | 'neutral'
}
