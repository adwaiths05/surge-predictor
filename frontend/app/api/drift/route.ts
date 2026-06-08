import { NextResponse } from 'next/server'
import { serverFetchDrift } from '@/lib/api'

export async function GET() {
  try {
    const data = await serverFetchDrift()
    return NextResponse.json(data)
  } catch (err: any) {
    return NextResponse.json(
      { detail: err?.message ?? 'Failed to fetch drift summary' },
      { status: 502 },
    )
  }
}
