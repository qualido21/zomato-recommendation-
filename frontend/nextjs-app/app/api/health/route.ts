import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    status: 'ok',
    dataset_loaded: true,
    llm_provider: 'groq',
  });
}
