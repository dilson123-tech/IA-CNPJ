import type { FormEvent } from 'react'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { login } from '../services/api'
import { isAuthenticated, setToken } from '../services/auth'

type LoginLocationState = {
  from?: {
    pathname?: string
  }
}

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const locationState = (location.state as LoginLocationState | null) ?? null
  const redirectTo = locationState?.from?.pathname || '/dashboard'

  useEffect(() => {
    if (isAuthenticated()) {
      navigate(redirectTo, { replace: true })
    }
  }, [navigate, redirectTo])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      const result = await login({ username, password })
      setToken(result.access_token)
      navigate(redirectTo, { replace: true })
    } catch {
      setError('Login inválido. Confira usuário e senha.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div>
          <p
            style={{
              margin: '0 0 8px',
              fontSize: '0.82rem',
              textTransform: 'uppercase',
              letterSpacing: '0.12em',
              color: 'var(--accent)',
            }}
          >
            IA-CNPJ
          </p>

          <h1>Acesso ao painel</h1>

          <p>
            Entre para acompanhar indicadores, relatórios financeiros e diagnósticos
            consultivos com leitura executiva do negócio.
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            <span>Usuário</span>
            <input
              type="text"
              placeholder="usuario@empresa.com"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
            />
          </label>

          <label>
            <span>Senha</span>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>

          {error ? (
            <p
              style={{
                margin: 0,
                color: '#ffd5db',
                background: '#3a1620',
                border: '1px solid rgba(248, 113, 113, 0.25)',
                borderRadius: '14px',
                padding: '12px 14px',
              }}
            >
              {error}
            </p>
          ) : null}

          <button type="submit" disabled={loading}>
            {loading ? 'Entrando...' : 'Entrar no painel'}
          </button>
        </form>
      </section>
    </main>
  )
}
