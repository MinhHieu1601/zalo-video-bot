'use client'

import { useState, useEffect } from 'react'

export default function AdminPage() {
  const [password, setPassword] = useState('')
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [keys, setKeys] = useState([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const fetchKeys = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/keys', {
        headers: { 'Authorization': `Bearer ${password}` }
      })
      const data = await res.json()
      if (res.ok) {
        setKeys(data.keys)
      } else {
        setMessage(data.error)
      }
    } catch (e) {
      setMessage('Error: ' + e.message)
    }
    setLoading(false)
  }

  const login = async () => {
    const res = await fetch('/api/keys', {
      headers: { 'Authorization': `Bearer ${password}` }
    })
    if (res.ok) {
      setIsLoggedIn(true)
      fetchKeys()
    } else {
      setMessage('Sai mat khau!')
    }
  }

  const createKey = async () => {
    const res = await fetch('/api/keys', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${password}` }
    })
    const data = await res.json()
    if (res.ok) {
      setMessage(`Key moi: ${data.key}`)
      fetchKeys()
    } else {
      setMessage(data.error)
    }
  }

  const disableKey = async (id) => {
    if (!confirm('Vo hieu key nay?')) return
    const res = await fetch(`/api/keys?id=${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${password}` }
    })
    if (res.ok) {
      fetchKeys()
    }
  }

  const resetMachine = async (id) => {
    if (!confirm('Reset machine ID cho key nay?')) return
    const res = await fetch(`/api/keys/reset?id=${id}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${password}` }
    })
    if (res.ok) {
      fetchKeys()
    }
  }

  if (!isLoggedIn) {
    return (
      <div style={{ padding: 40, maxWidth: 400, margin: 'auto' }}>
        <h1>License Admin</h1>
        <input 
          type="password" 
          placeholder="Admin password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          style={{ width: '100%', padding: 10, marginBottom: 10 }}
        />
        <button onClick={login} style={{ width: '100%', padding: 10 }}>
          Dang nhap
        </button>
        {message && <p style={{ color: 'red' }}>{message}</p>}
      </div>
    )
  }

  return (
    <div style={{ padding: 20, maxWidth: 900, margin: 'auto' }}>
      <h1>Quan ly License Keys</h1>
      
      <button onClick={createKey} style={{ padding: '10px 20px', marginBottom: 20 }}>
        + Tao Key Moi
      </button>
      <button onClick={fetchKeys} style={{ padding: '10px 20px', marginLeft: 10, marginBottom: 20 }}>
        Lam moi
      </button>
      
      {message && <p style={{ color: 'green', background: '#eee', padding: 10 }}>{message}</p>}
      
      {loading ? <p>Loading...</p> : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#333', color: '#fff' }}>
              <th style={{ padding: 10, textAlign: 'left' }}>Key</th>
              <th style={{ padding: 10 }}>Machine ID</th>
              <th style={{ padding: 10 }}>Trang thai</th>
              <th style={{ padding: 10 }}>Tao luc</th>
              <th style={{ padding: 10 }}>Hanh dong</th>
            </tr>
          </thead>
          <tbody>
            {keys.map(k => (
              <tr key={k.id} style={{ borderBottom: '1px solid #ddd' }}>
                <td style={{ padding: 10, fontFamily: 'monospace' }}>{k.key}</td>
                <td style={{ padding: 10, fontSize: 12 }}>{k.machine_id || '-'}</td>
                <td style={{ padding: 10, textAlign: 'center' }}>
                  {k.is_active ? '✅ Active' : '❌ Disabled'}
                </td>
                <td style={{ padding: 10, fontSize: 12 }}>
                  {new Date(k.created_at).toLocaleString()}
                </td>
                <td style={{ padding: 10 }}>
                  {k.is_active && (
                    <>
                      <button onClick={() => disableKey(k.id)} style={{ marginRight: 5 }}>
                        Vo hieu
                      </button>
                      {k.machine_id && (
                        <button onClick={() => resetMachine(k.id)}>
                          Reset may
                        </button>
                      )}
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
