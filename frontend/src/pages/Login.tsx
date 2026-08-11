import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { errorMessage } from '../services/api';
import { ErrorMessage } from '../components/ErrorMessage';

const DEMO_CREDENTIALS = [
  { email: 'admin@example.com', password: 'admin', role: 'admin' },
  { email: 'operator@example.com', password: 'operator', role: 'operator' },
  { email: 'viewer@example.com', password: 'viewer', role: 'viewer' },
];

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('admin');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(errorMessage(err, 'Invalid email or password'));
    } finally {
      setSubmitting(false);
    }
  };

  const useDemo = (demoEmail: string, demoPassword: string) => {
    setEmail(demoEmail);
    setPassword(demoPassword);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-900 to-brand-700 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center text-white">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-white/15 text-xl font-bold">
            E
          </div>
          <h1 className="text-2xl font-semibold">EWA Dashboard</h1>
          <p className="text-sm text-brand-100/80">SAP EarlyWatch Alert analysis</p>
        </div>

        <div className="card p-6">
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="label" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="username"
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="label" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <ErrorMessage message={error} />

            <button type="submit" className="btn-primary w-full" disabled={submitting}>
              {submitting ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <div className="mt-6 border-t border-gray-100 pt-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
              Demo credentials
            </p>
            <ul className="space-y-1.5">
              {DEMO_CREDENTIALS.map((c) => (
                <li key={c.email}>
                  <button
                    type="button"
                    onClick={() => useDemo(c.email, c.password)}
                    className="flex w-full items-center justify-between rounded-md border border-gray-200 px-3 py-1.5 text-left text-xs hover:bg-gray-50"
                  >
                    <span className="font-mono text-gray-700">
                      {c.email} / {c.password}
                    </span>
                    <span className="capitalize text-gray-400">{c.role}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
