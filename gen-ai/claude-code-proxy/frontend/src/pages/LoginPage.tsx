import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';

const inputClass =
  'w-full rounded-xl border border-line bg-surface px-4 py-2 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await api.login(username, password);
      navigate('/dashboard');
    } catch {
      setError('Invalid credentials');
    }
  };

  return (
    <div className="min-h-screen">
      <div className="mx-auto grid min-h-screen max-w-6xl grid-cols-1 gap-8 px-6 py-12 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="hidden flex-col justify-center rounded-3xl border border-line bg-surface/70 p-10 shadow-soft lg:flex">
          <div className="text-xs uppercase tracking-[0.35em] text-muted">Claude Proxy</div>
          <h1 className="mt-4 text-3xl font-semibold text-ink">
            Admin Console for Token Operations
          </h1>
          <p className="mt-4 text-sm text-muted">
            Track throughput, cumulative burn, and concentration across all users.
          </p>
          <div className="mt-10 grid gap-4 text-sm text-muted">
            <div className="rounded-2xl border border-line bg-surface px-4 py-3">
              Monitor hourly token throughput.
            </div>
            <div className="rounded-2xl border border-line bg-surface px-4 py-3">
              Identify heavy users and risk concentration.
            </div>
            <div className="rounded-2xl border border-line bg-surface px-4 py-3">
              Keep usage aligned with operational goals.
            </div>
          </div>
        </div>

        <div className="flex items-center justify-center">
          <form
            onSubmit={handleSubmit}
            className="w-full max-w-md rounded-3xl border border-line bg-surface p-8 shadow-soft"
          >
            <div className="text-xs uppercase tracking-[0.3em] text-muted">Admin Access</div>
            <h2 className="mt-3 text-2xl font-semibold text-ink">Sign in</h2>
            <p className="mt-2 text-sm text-muted">
              Use your admin credentials to continue.
            </p>
            {error && <p className="mt-4 text-sm text-danger">{error}</p>}
            <div className="mt-6 space-y-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
                  Username
                </label>
                <input
                  type="text"
                  placeholder="Admin username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  className={`${inputClass} mt-2`}
                />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
                  Password
                </label>
                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  className={`${inputClass} mt-2`}
                />
              </div>
            </div>
            <button
              type="submit"
              className="mt-6 w-full rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-black"
            >
              Continue
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
