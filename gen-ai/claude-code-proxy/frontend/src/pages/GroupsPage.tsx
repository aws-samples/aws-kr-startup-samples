import { useEffect, useState } from 'react';
import PageHeader from '@/components/PageHeader';
import { api, Group, GroupBudgetStatus, GroupMember, GroupUsage } from '@/lib/api';

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

function formatBudget(value: string | number) {
  const parsed = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(parsed)) return '-';
  return currencyFormatter.format(parsed);
}

function formatPercent(value: number) {
  if (!Number.isFinite(value)) return '-';
  return `${percentFormatter.format(value)}%`;
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function GroupsPage() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [budgets, setBudgets] = useState<Record<string, GroupBudgetStatus>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [budgetLoading, setBudgetLoading] = useState(false);

  // Create form
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [monthlyBudget, setMonthlyBudget] = useState('');
  const [error, setError] = useState('');

  // Detail panel
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [usage, setUsage] = useState<GroupUsage | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Budget edit
  const [editBudgetGroupId, setEditBudgetGroupId] = useState<string | null>(null);
  const [editBudgetValue, setEditBudgetValue] = useState('');

  useEffect(() => {
    loadGroups();
  }, []);

  async function loadGroups() {
    setIsLoading(true);
    try {
      const data = await api.getGroups();
      setGroups(data);
      setBudgetLoading(true);
      const entries = await Promise.all(
        data.map(async (g) => {
          try {
            const b = await api.getGroupBudget(g.id);
            return [g.id, b] as const;
          } catch {
            return null;
          }
        })
      );
      const next: Record<string, GroupBudgetStatus> = {};
      entries.forEach((e) => { if (e) next[e[0]] = e[1]; });
      setBudgets(next);
    } catch { /* ignore */ } finally {
      setIsLoading(false);
      setBudgetLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setError('Name is required.'); return; }
    let budgetPayload: string | undefined;
    if (monthlyBudget.trim()) {
      const parsed = Number(monthlyBudget);
      if (!Number.isFinite(parsed) || parsed < 0.01 || parsed > 999999.99) {
        setError('Budget must be between $0.01 and $999,999.99.');
        return;
      }
      budgetPayload = parsed.toFixed(2);
    }
    setError('');
    try {
      const group = await api.createGroup({ name, description: description || undefined, monthly_budget_usd: budgetPayload });
      setGroups((prev) => [group, ...prev]);
      setName(''); setDescription(''); setMonthlyBudget(''); setShowForm(false);
    } catch (err: any) {
      setError(err?.detail || 'Failed to create group.');
    }
  }

  async function handleDelete(group: Group) {
    if (!window.confirm(`Delete group "${group.name}"?`)) return;
    try {
      await api.deleteGroup(group.id);
      setGroups((prev) => prev.filter((g) => g.id !== group.id));
      if (selectedGroup === group.id) setSelectedGroup(null);
    } catch { /* ignore */ }
  }

  async function openDetail(groupId: string) {
    setSelectedGroup(groupId);
    setDetailLoading(true);
    try {
      const [m, u] = await Promise.all([
        api.getGroupMembers(groupId),
        api.getGroupUsage(groupId),
      ]);
      setMembers(m);
      setUsage(u);
    } catch { /* ignore */ } finally {
      setDetailLoading(false);
    }
  }

  async function handleBudgetSave(groupId: string) {
    const value = editBudgetValue.trim();
    const payload = value ? Number(value).toFixed(2) : null;
    try {
      const updated = await api.updateGroupBudget(groupId, payload);
      setBudgets((prev) => ({ ...prev, [groupId]: updated }));
      setEditBudgetGroupId(null);
    } catch { /* ignore */ }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Admin"
        title="Groups"
        subtitle="Manage groups, budgets, and members. Groups are auto-created from SSO Permission Sets."
        actions={
          <button
            type="button"
            onClick={() => { setShowForm((p) => !p); setError(''); }}
            className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white shadow-soft transition hover:bg-accent-strong"
          >
            {showForm ? 'Close' : 'New Group'}
          </button>
        }
      />

      {showForm && (
        <form onSubmit={handleCreate} className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
          <div className="grid gap-4 md:grid-cols-[1fr_1.5fr_1fr_auto] md:items-end">
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Name</label>
              <input type="text" placeholder="Group name" value={name} onChange={(e) => setName(e.target.value)} className={`${inputClass} mt-2`} />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Description</label>
              <input type="text" placeholder="Optional" value={description} onChange={(e) => setDescription(e.target.value)} className={`${inputClass} mt-2`} />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Monthly Budget (USD)</label>
              <input type="number" min="0.01" max="999999.99" step="0.01" placeholder="Unlimited" value={monthlyBudget} onChange={(e) => setMonthlyBudget(e.target.value)} className={`${inputClass} mt-2`} />
            </div>
            <div className="flex gap-3">
              <button type="submit" className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-black">Create</button>
              <button type="button" onClick={() => { setShowForm(false); setError(''); }} className="rounded-full border border-line px-4 py-2 text-sm font-semibold text-ink transition hover:bg-surface-2">Cancel</button>
            </div>
          </div>
          {error && <div className="mt-3 text-sm text-danger">{error}</div>}
        </form>
      )}

      <div className="rounded-2xl border border-line bg-surface shadow-soft">
        <div className="border-b border-line px-6 py-4 text-sm font-semibold text-ink">
          {isLoading ? 'Loading groups...' : `${groups.length} groups`}
        </div>
        {groups.length === 0 && !isLoading ? (
          <div className="px-6 py-12 text-center text-sm text-muted">
            No groups yet. Groups are auto-created when SSO users authenticate.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-[0.2em] text-muted">
                <th className="px-6 py-3">Group</th>
                <th className="px-6 py-3">Members</th>
                <th className="px-6 py-3">Budget</th>
                <th className="px-6 py-3">Created</th>
                <th className="px-6 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => {
                const budgetStatus = budgets[group.id];
                return (
                  <tr key={group.id} className="border-t border-line/60 hover:bg-surface-2">
                    <td className="px-6 py-4">
                      <div className="font-semibold text-ink">{group.name}</div>
                      <div className="text-xs text-muted">{group.description || 'No description'}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center rounded-full bg-surface-2 px-2.5 py-1 text-xs font-semibold text-ink">
                        {group.member_count}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-muted">
                      {editBudgetGroupId === group.id ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="number" min="0.01" max="999999.99" step="0.01" placeholder="Unlimited"
                            value={editBudgetValue} onChange={(e) => setEditBudgetValue(e.target.value)}
                            className="w-28 rounded-lg border border-line bg-surface px-2 py-1 text-xs"
                          />
                          <button onClick={() => handleBudgetSave(group.id)} className="text-xs font-semibold text-accent">Save</button>
                          <button onClick={() => setEditBudgetGroupId(null)} className="text-xs text-muted">Cancel</button>
                        </div>
                      ) : budgetStatus ? (
                        <div className="space-y-1 cursor-pointer" onClick={() => { setEditBudgetGroupId(group.id); setEditBudgetValue(budgetStatus.monthly_budget_usd ?? ''); }}>
                          <div className="font-semibold text-ink">
                            {budgetStatus.monthly_budget_usd ? formatBudget(budgetStatus.monthly_budget_usd) : 'Unlimited'}
                          </div>
                          <div className="text-xs text-muted">
                            Usage {formatBudget(budgetStatus.current_usage_usd)}
                            {budgetStatus.monthly_budget_usd && budgetStatus.usage_percentage !== null && (
                              <> &middot; {formatPercent(budgetStatus.usage_percentage)}</>
                            )}
                          </div>
                        </div>
                      ) : budgetLoading ? (
                        <span className="text-xs text-muted">Loading...</span>
                      ) : (
                        <span className="text-xs text-muted">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-muted">{formatDate(group.created_at)}</td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button onClick={() => handleDelete(group)} className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-danger transition hover:bg-surface">Delete</button>
                        <button onClick={() => openDetail(group.id)} className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-ink transition hover:bg-surface-2">Detail</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {selectedGroup && (
        <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-ink">
              Group Detail: {groups.find((g) => g.id === selectedGroup)?.name}
            </h3>
            <button onClick={() => setSelectedGroup(null)} className="text-sm text-muted hover:text-ink">Close</button>
          </div>

          {detailLoading ? (
            <div className="text-sm text-muted">Loading...</div>
          ) : (
            <>
              {usage && (
                <div className="rounded-xl border border-line bg-surface-2 p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted mb-2">Current Month Usage</div>
                  <div className="text-2xl font-semibold text-ink">{formatBudget(usage.total_estimated_cost_usd)}</div>
                </div>
              )}

              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted mb-3">Members ({members.length})</div>
                {members.length === 0 ? (
                  <div className="text-sm text-muted">No members</div>
                ) : (
                  <div className="space-y-2">
                    {members.map((m) => (
                      <div key={m.user_id} className="flex items-center justify-between rounded-xl border border-line/60 px-4 py-3">
                        <span className="text-sm font-semibold text-ink">{m.name}</span>
                        <span className={[
                          'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold',
                          m.status === 'active' ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger',
                        ].join(' ')}>
                          {m.status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
