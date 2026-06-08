import { NextResponse } from 'next/server'
import { serverFetchHeatmap } from '@/lib/api'

export async function GET() {
  try {
    const data = await serverFetchHeatmap()
    return NextResponse.json(data, {
      headers: {
        // Heatmap data is fresh for up to 5 minutes on CDN
        'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
      },
    })
  } catch (err: any) {
    return NextResponse.json(
      { detail: err?.message ?? 'Failed to fetch heatmap' },
      { status: 502 },
    )
  }
}
