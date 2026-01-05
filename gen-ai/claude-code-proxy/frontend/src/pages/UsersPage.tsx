import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '@/components/PageHeader';
import { api, User, UserBudgetStatus } from '@/lib/api';

const inputClass =
  'w-full rounded-xl border border-line bg-surface px-4 py-2 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20';

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const percentFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 1,
});

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [monthlyBudget, setMonthlyBudget] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [budgetLoading, setBudgetLoading] = useState(false);
  const [error, setError] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [deletingUsers, setDeletingUsers] = useState<Record<string, boolean>>({});
  const [budgetsByUser, setBudgetsByUser] = useState<Record<string, UserBudgetStatus>>(
    {}
  );

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    api
      .getUsers()
      .then((response) => {
        if (!active) return;
        setUsers(response);
        if (response.length === 0) {
          setBudgetsByUser({});
          return;
        }
        setBudgetLoading(true);
        Promise.all(
          response.map(async (user) => {
            try {
              const status = await api.getUserBudget(user.id);
              return [user.id, status] as const;
            } catch {
              return null;
            }
          })
        )
          .then((entries) => {
            if (!active) return;
            const next: Record<string, UserBudgetStatus> = {};
            entries.forEach((entry) => {
              if (!entry) return;
              next[entry[0]] = entry[1];
            });
            setBudgetsByUser(next);
          })
          .finally(() => {
            if (active) setBudgetLoading(false);
          });
      })
      .catch(() => {})
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Name is required.');
      return;
    }
    const budgetValue = monthlyBudget.trim();
    let budgetPayload: string | number | undefined;
    if (budgetValue) {
      const parsed = Number(budgetValue);
      if (!Number.isFinite(parsed)) {
        setError('Budget must be a valid number.');
        return;
      }
      if (parsed < 0.01 || parsed > 999999.99) {
        setError('Budget must be between $0.01 and $999,999.99.');
        return;
      }
      budgetPayload = parsed.toFixed(2);
    }
    setError('');
    const user = await api.createUser({
      name,
      description: description || undefined,
      monthly_budget_usd: budgetPayload,
    });
    setUsers((prev) => [user, ...prev]);
    if (budgetPayload !== undefined) {
      api
        .getUserBudget(user.id)
        .then((status) => {
          setBudgetsByUser((prev) => ({ ...prev, [user.id]: status }));
        })
        .catch(() => {});
    }
    setName('');
    setDescription('');
    setMonthlyBudget('');
    setShowForm(false);
  };

  const handleDelete = async (user: User) => {
    if (deletingUsers[user.id]) return;
    const confirmed = window.confirm(
      `Delete ${user.name}? This will revoke all access keys.`
    );
    if (!confirmed) return;
    setDeleteError('');
    setDeletingUsers((prev) => ({ ...prev, [user.id]: true }));
    try {
      await api.deleteUser(user.id);
      setUsers((prev) => prev.filter((item) => item.id !== user.id));
      setBudgetsByUser((prev) => {
        if (!(user.id in prev)) return prev;
        const next = { ...prev };
        delete next[user.id];
        return next;
      });
    } catch {
      setDeleteError('Failed to delete user.');
    } finally {
      setDeletingUsers((prev) => {
        if (!(user.id in prev)) return prev;
        const next = { ...prev };
        delete next[user.id];
        return next;
      });
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Admin"
        title="Users"
        subtitle="Manage user access, status, and activity from a single list."
        actions={
          <button
            type="button"
            onClick={() => {
              setShowForm((prev) => {
                if (prev) {
                  setName('');
                  setDescription('');
                  setMonthlyBudget('');
                }
                return !prev;
              });
              setError('');
            }}
            className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white shadow-soft transition hover:bg-accent-strong"
          >
            {showForm ? 'Close' : 'New User'}
          </button>
        }
      />

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="rounded-2xl border border-line bg-surface p-6 shadow-soft"
        >
          <div className="grid gap-4 md:grid-cols-[minmax(0,1.1fr)_minmax(0,1.6fr)_minmax(0,1fr)_auto] md:items-end">
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
                Name
              </label>
              <input
                type="text"
                placeholder="User name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={`${inputClass} mt-2`}
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
                Description
              </label>
              <input
                type="text"
                placeholder="Optional description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className={`${inputClass} mt-2`}
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
                Monthly Budget (USD)
              </label>
              <input
                type="number"
                min="0.01"
                max="999999.99"
                step="0.01"
                placeholder="Unlimited"
                value={monthlyBudget}
                onChange={(e) => setMonthlyBudget(e.target.value)}
                className={`${inputClass} mt-2`}
              />
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-black"
              >
                Create
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setError('');
                  setName('');
                  setDescription('');
                  setMonthlyBudget('');
                }}
                className="rounded-full border border-line px-4 py-2 text-sm font-semibold text-ink transition hover:bg-surface-2"
              >
                Cancel
              </button>
            </div>
          </div>
          {error && <div className="mt-3 text-sm text-danger">{error}</div>}
        </form>
      )}

      <div className="rounded-2xl border border-line bg-surface shadow-soft">
        <div className="border-b border-line px-6 py-4 text-sm font-semibold text-ink">
          {isLoading ? 'Loading users...' : `${users.length} users`}
        </div>
        {deleteError && (
          <div className="px-6 pb-4 text-sm text-danger">{deleteError}</div>
        )}
        {users.length === 0 && !isLoading ? (
          <div className="px-6 py-12 text-center text-sm text-muted">
            No users yet. Create your first user to get started.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-[0.2em] text-muted">
                <th className="px-6 py-3">User</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Budget (Bedrock)</th>
                <th className="px-6 py-3">Updated</th>
                <th className="px-6 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => {
                const budgetStatus = budgetsByUser[user.id];
                const isDeleting = Boolean(deletingUsers[user.id]);
                return (
                  <tr key={user.id} className="border-t border-line/60 hover:bg-surface-2">
                    <td className="px-6 py-4">
                      <div className="font-semibold text-ink">{user.name}</div>
                      <div className="text-xs text-muted">
                        {user.description || 'No description'}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={[
                          'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold',
                          user.status === 'active'
                            ? 'bg-success/10 text-success'
                            : 'bg-danger/10 text-danger',
                        ].join(' ')}
                      >
                        {user.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-muted">
                      {budgetStatus ? (
                        <div className="space-y-1">
                          <div className="font-semibold text-ink">
                            {budgetStatus.monthly_budget_usd
                              ? formatBudget(budgetStatus.monthly_budget_usd)
                              : 'Unlimited'}
                          </div>
                          <div className="text-xs text-muted">
                            Usage {formatBudget(budgetStatus.current_usage_usd)}
                            {budgetStatus.monthly_budget_usd &&
                              budgetStatus.usage_percentage !== null && (
                                <> · {formatPercent(budgetStatus.usage_percentage)}</>
                              )}
                          </div>
                        </div>
                      ) : budgetLoading ? (
                        <span className="text-xs text-muted">Loading...</span>
                      ) : (
                        <span className="text-xs text-muted">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-muted">
                      {formatDate(user.updated_at)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => handleDelete(user)}
                          disabled={isDeleting}
                          className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-danger transition hover:bg-surface disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {isDeleting ? 'Deleting...' : 'Delete'}
                        </button>
                        <Link
                          to={`/users/${user.id}`}
                          className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-ink transition hover:bg-surface-2"
                        >
                          View
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatBudget(value: string | number) {
  const parsed = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(parsed)) return '-';
  return currencyFormatter.format(parsed);
}

function formatPercent(value: number) {
  if (!Number.isFinite(value)) return '-';
  return `${percentFormatter.format(value)}%`;
}
