import { NextResponse } from 'next/server'
import { serverFetchZones } from '@/lib/api'

export async function GET() {
  try {
    const data = await serverFetchZones()
    return NextResponse.json(data)
  } catch (err: any) {
    return NextResponse.json(
      { detail: err?.message ?? 'Failed to fetch zones' },
      { status: 502 },
    )
  }
}
