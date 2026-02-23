import { query, initDatabase } from '@/lib/db'
import { NextResponse } from 'next/server'
import crypto from 'crypto'

// Admin password tu env
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin123'

function checkAuth(request) {
  const auth = request.headers.get('authorization')
  if (!auth || auth !== `Bearer ${ADMIN_PASSWORD}`) {
    return false
  }
  return true
}

// GET - Lay danh sach keys
export async function GET(request) {
  if (!checkAuth(request)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
  
  try {
    await initDatabase()
    const result = await query('SELECT id, key, machine_id, is_active, created_at, last_used FROM api_keys ORDER BY created_at DESC')
    return NextResponse.json({ keys: result.rows })
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}

// POST - Tao key moi
export async function POST(request) {
  if (!checkAuth(request)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
  
  try {
    await initDatabase()
    const newKey = crypto.randomBytes(16).toString('hex')
    await query('INSERT INTO api_keys (key) VALUES ($1)', [newKey])
    return NextResponse.json({ key: newKey, message: 'Key created' })
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}

// DELETE - Xoa/vo hieu key
export async function DELETE(request) {
  if (!checkAuth(request)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
  
  try {
    const { searchParams } = new URL(request.url)
    const keyId = searchParams.get('id')
    
    if (!keyId) {
      return NextResponse.json({ error: 'Missing key id' }, { status: 400 })
    }
    
    await query('UPDATE api_keys SET is_active = false WHERE id = $1', [keyId])
    return NextResponse.json({ message: 'Key disabled' })
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}
