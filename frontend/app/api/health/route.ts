import { NextResponse } from 'next/server'
import { serverFetchHealth } from '@/lib/api'

export async function GET() {
  try {
    const data = await serverFetchHealth()
    return NextResponse.json(data)
  } catch (err: any) {
    return NextResponse.json(
      { detail: err?.message ?? 'Backend unreachable' },
      { status: 502 },
    )
  }
}
