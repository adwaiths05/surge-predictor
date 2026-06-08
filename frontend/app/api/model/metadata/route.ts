import { NextResponse } from 'next/server'
import { serverFetchModelMetadata } from '@/lib/api'

export async function GET() {
  try {
    const data = await serverFetchModelMetadata()
    return NextResponse.json(data)
  } catch (err: any) {
    return NextResponse.json(
      { detail: err?.message ?? 'Failed to fetch model metadata' },
      { status: 502 },
    )
  }
}
