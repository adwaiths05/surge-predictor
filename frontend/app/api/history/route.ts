import { NextRequest, NextResponse } from 'next/server'
import { serverFetchHistory } from '@/lib/api'

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const zone = searchParams.get('zone')
  const days = parseInt(searchParams.get('days') ?? '7', 10)

  if (!zone) {
    return NextResponse.json({ detail: 'zone query param required' }, { status: 400 })
  }

  try {
    const data = await serverFetchHistory(zone, days)
    return NextResponse.json(data)
  } catch (err: any) {
    return NextResponse.json(
      { detail: err?.message ?? 'Failed to fetch history' },
      { status: 502 },
    )
  }
}
