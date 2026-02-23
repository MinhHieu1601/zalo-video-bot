import { query } from '@/lib/db'
import { NextResponse } from 'next/server'

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin123'

export async function POST(request) {
  const auth = request.headers.get('authorization')
  if (!auth || auth !== `Bearer ${ADMIN_PASSWORD}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
  
  try {
    const { searchParams } = new URL(request.url)
    const keyId = searchParams.get('id')
    
    if (!keyId) {
      return NextResponse.json({ error: 'Missing key id' }, { status: 400 })
    }
    
    await query('UPDATE api_keys SET machine_id = NULL WHERE id = $1', [keyId])
    return NextResponse.json({ message: 'Machine ID reset' })
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}
