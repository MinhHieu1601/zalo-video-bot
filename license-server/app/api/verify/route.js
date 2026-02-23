import { query } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function POST(request) {
  try {
    const { key, machine_id } = await request.json()
    
    if (!key || !machine_id) {
      return NextResponse.json({ valid: false, error: 'Missing key or machine_id' }, { status: 400 })
    }
    
    // Tim key trong database
    const result = await query(
      'SELECT * FROM api_keys WHERE key = $1 AND is_active = true',
      [key]
    )
    
    if (result.rows.length === 0) {
      return NextResponse.json({ valid: false, error: 'Key khong ton tai hoac da bi vo hieu' })
    }
    
    const keyData = result.rows[0]
    
    // Neu key chua gan may nao -> gan may nay
    if (!keyData.machine_id) {
      await query(
        'UPDATE api_keys SET machine_id = $1, last_used = NOW() WHERE key = $2',
        [machine_id, key]
      )
      return NextResponse.json({ valid: true, message: 'Key da duoc kich hoat cho may nay' })
    }
    
    // Neu key da gan may khac
    if (keyData.machine_id !== machine_id) {
      return NextResponse.json({ valid: false, error: 'Key da duoc su dung tren may khac' })
    }
    
    // Cap nhat last_used
    await query('UPDATE api_keys SET last_used = NOW() WHERE key = $1', [key])
    
    return NextResponse.json({ valid: true })
    
  } catch (error) {
    console.error('Verify error:', error)
    return NextResponse.json({ valid: false, error: 'Server error' }, { status: 500 })
  }
}
