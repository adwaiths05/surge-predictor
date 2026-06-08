import { NextResponse } from 'next/server'
import { serverFetchKpis } from '@/lib/api'

export async function GET() {
  try {
    const data = await serverFetchKpis()
    return NextResponse.json(data)
  } catch (err: any) {
    return NextResponse.json(
      { detail: err?.message ?? 'Failed to fetch KPIs' },
      { status: 502 },
    )
  }
}
