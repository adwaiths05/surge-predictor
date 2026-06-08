import { NextRequest, NextResponse } from 'next/server'
import { serverPredict } from '@/lib/api'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const data = await serverPredict(body.zone_name)
    return NextResponse.json(data)
  } catch (err: any) {
    return NextResponse.json(
      { detail: err?.message ?? 'Prediction failed' },
      { status: 500 },
    )
  }
}
