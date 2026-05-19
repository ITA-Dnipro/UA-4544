import { useRef, useState } from 'react'
import ReCAPTCHA from 'react-google-recaptcha'

// TODO(#72, #73): Minimal stub for testing reCAPTCHA + backend integration.
// Replace with full design. Preserve:
//   1. react-google-recaptcha (already in package.json)
//   2. import ReCAPTCHA from 'react-google-recaptcha'
//   3. const recaptchaRef = useRef<ReCAPTCHA>(null)
//   4. <ReCAPTCHA ref={recaptchaRef} sitekey={import.meta.env.VITE_RECAPTCHA_SITE_KEY} />
//   5. const token = recaptchaRef.current?.getValue() on submit
//   6. Include recaptcha_token: token in POST /api/auth/register/ body
//   7. recaptchaRef.current?.reset() after submit
//   Available roles: 'startup' | 'investor' | 'org_admin'

const SITE_KEY = import.meta.env.VITE_RECAPTCHA_SITE_KEY as string | undefined
const API_URL = import.meta.env.VITE_API_URL as string | undefined

export default function Register() {
  const recaptchaRef = useRef<ReCAPTCHA>(null)
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)
  const [loading, setLoading] = useState(false)

  if (!SITE_KEY || !API_URL) {
  return (
    <p style={{ color: 'red', padding: 24 }}>
      {import.meta.env.DEV
        ? 'Dev config error: VITE_RECAPTCHA_SITE_KEY or VITE_API_URL missing in frontend/.env'
        : 'Registration is temporarily unavailable. Please try again later.'}
    </p>
    )
  }
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const token = recaptchaRef.current?.getValue()
    if (!token) {
      setIsError(true)
      setMessage('Please complete the captcha')
      return
    }
    const form = e.currentTarget
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/auth/register/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: (form.elements.namedItem('email') as HTMLInputElement).value,
          password: (form.elements.namedItem('password') as HTMLInputElement).value,
          role: (form.elements.namedItem('role') as HTMLSelectElement).value,
          recaptcha_token: token,
        }),
      })
      const json = await res.json()
      setIsError(!res.ok)
      const errorMsg = json.detail || Object.values(json).flat().join('. ')
      setMessage(res.ok ? json.detail : errorMsg)
    } catch {
      setIsError(true)
      setMessage('Network error')
    } finally {
      setLoading(false)
      recaptchaRef.current?.reset()
    }
  }

  return (
    <div style={{ maxWidth: 400, margin: '60px auto', padding: 24, border: '1px solid #ddd', borderRadius: 8 }}>
      <h2 style={{ marginBottom: 20 }}>Register</h2>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <input name="email" type="email" placeholder="Email" required style={{ padding: 8, borderRadius: 4, border: '1px solid #ccc' }} />
        <input name="password" type="password" placeholder="Password" required style={{ padding: 8, borderRadius: 4, border: '1px solid #ccc' }} />
        <select name="role" style={{ padding: 8, borderRadius: 4, border: '1px solid #ccc' }}>
          <option value="startup">Startup</option>
          <option value="investor">Investor</option>
          <option value="org_admin">Org Admin</option>
        </select>
        <ReCAPTCHA ref={recaptchaRef} sitekey={SITE_KEY} />
        <button type="submit" disabled={loading} style={{ padding: '10px 0', borderRadius: 4, background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer' }}>
          {loading ? 'Loading...' : 'Register'}
        </button>
        {message && <p style={{ color: isError ? 'red' : 'green' }}>{message}</p>}
      </form>
    </div>
  )
}
