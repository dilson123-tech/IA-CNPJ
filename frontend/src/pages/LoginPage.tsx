import type { FormEvent } from 'react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../services/api'
import { setToken } from '../services/auth'

export default function LoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      const result = await login({ username, password })
      setToken(result.access_token)
      navigate('/dashboard')
    } catch {
      setError('Login inválido. Confira usuário e senha.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div>
          <p className="login-card__eyebrow">IA-CNPJ</p>
          <h1 className="login-card__title">Acesso ao painel</h1>
          <p className="login-card__text">
            Entre para visualizar indicadores, relatórios e insights consultivos.
          </p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label className="login-form__field">
            <span>Usuário</span>
            <input
              type="text"
              placeholder="seu_usuario"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </label>

          <label className="login-form__field">
            <span>Senha</span>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>

          {error ? <p className="login-form__error">{error}</p> : null}

          <button className="login-form__button" type="submit" disabled={loading}>
            {loading ? 'Entrando...' : 'Entrar no painel'}
          </button>
        </form>
      </section>
    </main>
  )
}
