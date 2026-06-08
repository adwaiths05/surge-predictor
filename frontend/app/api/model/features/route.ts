import { NextResponse } from 'next/server'
import { serverFetchModelFeatures } from '@/lib/api'

export async function GET() {
  try {
    const data = await serverFetchModelFeatures()
    return NextResponse.json(data)
  } catch (err: any) {
    return NextResponse.json(
      { detail: err?.message ?? 'Failed to fetch model features' },
      { status: 502 },
    )
  }
}
