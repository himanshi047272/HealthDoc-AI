import { lazy, Suspense } from 'react'
import { Skeleton } from './ui'

const Plot = lazy(async () => {
  const [factory, plotly] = await Promise.all([import('react-plotly.js/factory'), import('plotly.js-basic-dist-min')])
  return { default: (factory as any).default((plotly as any).default ?? plotly) }
})

export default function Chart({ data, title, yTitle }: { data: any[]; title: string; yTitle?: string }) {
  return (
    <Suspense fallback={<Skeleton h="h-40" />}>
      <Plot
        data={data}
        layout={{ title: { text: title, font: { size: 13 } }, autosize: true, height: 200, margin: { l: 40, r: 10, t: 30, b: 30 },
                  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', yaxis: { title: { text: yTitle } }, font: { family: 'DM Sans, sans-serif' } }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: '100%' }}
        useResizeHandler
      />
    </Suspense>
  )
}
