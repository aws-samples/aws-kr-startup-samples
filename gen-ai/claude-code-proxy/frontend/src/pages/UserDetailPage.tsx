import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import PageHeader from '@/components/PageHeader';
import { api, AccessKey, UsageResponse, User, UserBudgetStatus } from '@/lib/api';
import {
  formatKstDate,
  resolveCustomRange,
  resolvePeriodRange,
  selectBucketType,
  UsagePeriod,
} from '@/lib/usageRange';

const inputClass =
  'w-full rounded-xl border border-line bg-surface px-4 py-2 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20';

type RangePreset = UsagePeriod | 'custom';

const RANGE_PRESETS: { key: RangePreset; label: string }[] = [
  { key: 'day', label: 'Day' },
  { key: 'week', label: 'Week' },
  { key: 'month', label: 'Month' },
  { key: 'custom', label: 'Custom' },
];

const numberFormatter = new Intl.NumberFormat('en-US');
const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 6,
});
const currencyShortFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const percentFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 1,
});

export default function UserDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [keys, setKeys] = useState<AccessKey[]>([]);
  const [pendingKey, setPendingKey] = useState<{ value: string; label: string } | null>(
    null
  );
  const [copied, setCopied] = useState(false);
  const [bedrockKey, setBedrockKey] = useState('');
  const [selectedKeyId, setSelectedKeyId] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [usageLoading, setUsageLoading] = useState(false);
  const [rangePreset, setRangePreset] = useState<RangePreset>('month');
  const [customRange, setCustomRange] = useState({ start: '', end: '' });
  const [budgetStatus, setBudgetStatus] = useState<UserBudgetStatus | null>(null);
  const [budgetInput, setBudgetInput] = useState('');
  const [budgetLoading, setBudgetLoading] = useState(false);
  const [budgetSaving, setBudgetSaving] = useState(false);
  const [budgetError, setBudgetError] = useState('');
  const [budgetNotice, setBudgetNotice] = useState('');
  const [routingStrategy, setRoutingStrategy] = useState<'plan_first' | 'bedrock_only'>('plan_first');
  const [routingSaving, setRoutingSaving] = useState(false);
  const [routingNotice, setRoutingNotice] = useState('');

  const showNotice = (message: string) => {
    setNotice(message);
    setTimeout(() => setNotice(''), 2500);
  };

  const showBudgetNotice = (message: string) => {
    setBudgetNotice(message);
    setTimeout(() => setBudgetNotice(''), 2500);
  };

  const showRoutingNotice = (message: string) => {
    setRoutingNotice(message);
    setTimeout(() => setRoutingNotice(''), 2500);
  };

  useEffect(() => {
    if (!id) return;
    let active = true;
    api.getUser(id).then((response) => {
      if (!active) return;
      setUser(response);
      setRoutingStrategy(response.routing_strategy || 'plan_first');
    });
    api.getAccessKeys(id).then((response) => {
      if (!active) return;
      setKeys(response);
    });
    setBudgetLoading(true);
    api
      .getUserBudget(id)
      .then((response) => {
        if (!active) return;
        setBudgetStatus(response);
        setBudgetInput(response.monthly_budget_usd ?? '');
      })
      .catch(() => {
        if (!active) return;
        setBudgetStatus(null);
      })
      .finally(() => {
        if (active) setBudgetLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

  const usageRange = useMemo(() => {
    if (rangePreset === 'custom') {
      if (!customRange.start || !customRange.end) return null;
      return resolveCustomRange(customRange.start, customRange.end);
    }
    return resolvePeriodRange(rangePreset);
  }, [customRange.end, customRange.start, rangePreset]);

  const bucketType = useMemo(
    () => (usageRange ? selectBucketType(usageRange.rangeDays) : 'day'),
    [usageRange]
  );

  useEffect(() => {
    if (!id || !usageRange) return;
    let active = true;
    setUsageLoading(true);

    const usageParams = {
      user_id: id,
      bucket_type: bucketType,
      ...(rangePreset === 'custom'
        ? { start_date: usageRange.startDate, end_date: usageRange.endDate }
        : { period: rangePreset }),
    };

    api
      .getUsage(usageParams)
      .then((response) => {
        if (!active) return;
        setUsage(response);
      })
      .catch(() => {
        if (!active) return;
        setUsage(null);
      })
      .finally(() => {
        if (active) setUsageLoading(false);
      });

    return () => {
      active = false;
    };
  }, [bucketType, id, rangePreset, usageRange]);

  const activeKeys = useMemo(
    () => keys.filter((key) => key.status === 'active').length,
    [keys]
  );
  const revokedKeys = keys.length - activeKeys;
  const selectedKey = useMemo(
    () => keys.find((key) => key.id === selectedKeyId) || null,
    [keys, selectedKeyId]
  );
  const totalCost = usage ? parseCost(usage.estimated_cost_usd) : 0;
  const inputCost = usage ? parseCost(usage.total_input_cost_usd) : 0;
  const outputCost = usage ? parseCost(usage.total_output_cost_usd) : 0;
  const cacheWriteCost = usage ? parseCost(usage.total_cache_write_cost_usd) : 0;
  const cacheReadCost = usage ? parseCost(usage.total_cache_read_cost_usd) : 0;
  const cacheCost = cacheWriteCost + cacheReadCost;
  const cacheTokens = usage
    ? usage.total_cache_write_tokens + usage.total_cache_read_tokens
    : 0;
  const costRows = useMemo(() => {
    if (!usage) return [];
    return [...usage.cost_breakdown]
      .map((item) => ({
        model: formatModelLabel(item.model_id),
        inputCost: parseCost(item.input_cost_usd),
        outputCost: parseCost(item.output_cost_usd),
        cacheWriteCost: parseCost(item.cache_write_cost_usd),
        cacheReadCost: parseCost(item.cache_read_cost_usd),
        totalCost: parseCost(item.total_cost_usd),
      }))
      .sort((a, b) => b.totalCost - a.totalCost);
  }, [usage]);
  const budgetUsagePercent = budgetStatus?.usage_percentage ?? null;
  const budgetProgress =
    budgetUsagePercent !== null ? Math.min(100, Math.max(0, budgetUsagePercent)) : 0;
  const budgetOverLimit = budgetUsagePercent !== null && budgetUsagePercent >= 100;

  const handleIssueKey = async () => {
    if (!id) return;
    const key = await api.createAccessKey(id, { bedrock_region: 'ap-northeast-2' });
    if (key.raw_key) {
      setPendingKey({ value: key.raw_key, label: 'New key issued' });
      setCopied(false);
    }
    const { raw_key, ...safeKey } = key;
    setKeys((prev) => [{ ...safeKey, has_bedrock_key: false }, ...prev]);
  };

  const handleRevoke = async (keyId: string) => {
    await api.revokeAccessKey(keyId);
    setKeys((prev) =>
      prev.map((k) =>
        k.id === keyId ? { ...k, status: 'revoked', has_bedrock_key: false } : k
      )
    );
  };

  const handleRegisterBedrock = async () => {
    if (selectedKey?.has_bedrock_key) {
      showNotice('Bedrock key is already linked.');
      return;
    }
    if (selectedKeyId && bedrockKey) {
      await api.registerBedrockKey(selectedKeyId, bedrockKey);
      setBedrockKey('');
      setKeys((prev) =>
        prev.map((k) =>
          k.id === selectedKeyId ? { ...k, has_bedrock_key: true } : k
        )
      );
      setSelectedKeyId(null);
      showNotice('Bedrock key registered.');
    }
  };

  const handleDeactivate = async () => {
    if (!id) return;
    await api.deactivateUser(id);
    navigate('/users');
  };

  const handleBudgetSave = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!id) return;
    setBudgetError('');

    const trimmed = budgetInput.trim();
    let payload: string | number | null = null;
    if (trimmed) {
      const parsed = Number(trimmed);
      if (!Number.isFinite(parsed)) {
        setBudgetError('Enter a valid number.');
        return;
      }
      if (parsed < 0.01 || parsed > 999999.99) {
        setBudgetError('Budget must be between $0.01 and $999,999.99.');
        return;
      }
      payload = parsed.toFixed(2);
    }

    setBudgetSaving(true);
    try {
      const updated = await api.updateUserBudget(id, payload);
      setBudgetStatus(updated);
      setBudgetInput(updated.monthly_budget_usd ?? '');
      setUser((prev) =>
        prev ? { ...prev, monthly_budget_usd: updated.monthly_budget_usd } : prev
      );
      showBudgetNotice('Budget updated.');
    } catch {
      setBudgetError('Failed to update budget.');
    } finally {
      setBudgetSaving(false);
    }
  };

  const handleRoutingStrategyChange = async (newStrategy: 'plan_first' | 'bedrock_only') => {
    if (!id || routingSaving) return;
    setRoutingSaving(true);
    try {
      const updated = await api.updateUserRoutingStrategy(id, newStrategy);
      setRoutingStrategy(updated.routing_strategy);
      setUser((prev) => (prev ? { ...prev, routing_strategy: updated.routing_strategy } : prev));
      showRoutingNotice('Routing strategy updated.');
    } catch (err: unknown) {
      const detail = (err as { detail?: { code?: string; message?: string } | string })?.detail;
      if (typeof detail === 'object' && detail?.message) {
        showRoutingNotice(detail.message);
      } else if (typeof detail === 'string') {
        showRoutingNotice(detail);
      } else {
        showRoutingNotice('Failed to update routing strategy.');
      }
    } finally {
      setRoutingSaving(false);
    }
  };

  const handleCopyPendingKey = async () => {
    if (!pendingKey?.value) return;
    const copySucceeded = await copyToClipboard(pendingKey.value);
    if (copySucceeded) {
      setCopied(true);
      showNotice('Key copied to clipboard.');
      setTimeout(() => setCopied(false), 2000);
      return;
    }
    showNotice('Copy failed. Try again.');
  };

  if (!user) {
    return (
      <div className="rounded-2xl border border-line bg-surface p-8 text-sm text-muted">
        Loading user...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Users"
        title={user.name}
        subtitle={user.description || 'No description'}
        actions={
          <>
            <Link
              to="/users"
              className="rounded-full border border-line px-4 py-2 text-sm font-semibold text-ink transition hover:bg-surface-2"
            >
              Back to Users
            </Link>
            <span
              className={[
                'inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold',
                user.status === 'active' ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger',
              ].join(' ')}
            >
              {user.status}
            </span>
            {user.status === 'active' && (
              <button
                onClick={handleDeactivate}
                className="rounded-full bg-danger px-4 py-2 text-sm font-semibold text-white shadow-soft transition hover:bg-red-600"
              >
                Deactivate
              </button>
            )}
          </>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
          <h2 className="text-lg font-semibold text-ink">Profile</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 text-sm">
            <Detail label="User ID" value={user.id} mono />
            <Detail label="Created" value={formatDate(user.created_at)} />
            <Detail label="Updated" value={formatDate(user.updated_at)} />
            <Detail label="Status" value={user.status} />
          </div>
        </div>
        <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
          <h2 className="text-lg font-semibold text-ink">Access Summary</h2>
          <div className="mt-4 space-y-3 text-sm text-muted">
            <SummaryRow label="Total keys" value={keys.length} />
            <SummaryRow label="Active keys" value={activeKeys} />
            <SummaryRow label="Revoked keys" value={revokedKeys} />
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-ink">Routing Strategy</h2>
            <p className="text-xs text-muted">
              Control how requests are routed for this user.
            </p>
          </div>
          <span className="inline-flex items-center rounded-full bg-accent/10 px-3 py-1 text-xs font-semibold text-accent">
            {routingStrategy === 'plan_first' ? 'Plan First' : 'Bedrock Only'}
          </span>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => handleRoutingStrategyChange('plan_first')}
            disabled={routingSaving}
            className={[
              'rounded-2xl border p-4 text-left transition',
              routingStrategy === 'plan_first'
                ? 'border-accent bg-accent/5 ring-2 ring-accent/20'
                : 'border-line hover:border-accent/50 hover:bg-surface-2',
            ].join(' ')}
          >
            <div className="flex items-center gap-2">
              <div
                className={[
                  'h-4 w-4 rounded-full border-2',
                  routingStrategy === 'plan_first' ? 'border-accent bg-accent' : 'border-muted',
                ].join(' ')}
              />
              <span className="font-semibold text-ink">Plan First</span>
            </div>
            <p className="mt-2 text-xs text-muted">
              Try Anthropic Plan API first. Falls back to Bedrock if Plan fails or rate limited.
            </p>
          </button>
          <button
            type="button"
            onClick={() => handleRoutingStrategyChange('bedrock_only')}
            disabled={routingSaving}
            className={[
              'rounded-2xl border p-4 text-left transition',
              routingStrategy === 'bedrock_only'
                ? 'border-accent bg-accent/5 ring-2 ring-accent/20'
                : 'border-line hover:border-accent/50 hover:bg-surface-2',
            ].join(' ')}
          >
            <div className="flex items-center gap-2">
              <div
                className={[
                  'h-4 w-4 rounded-full border-2',
                  routingStrategy === 'bedrock_only' ? 'border-accent bg-accent' : 'border-muted',
                ].join(' ')}
              />
              <span className="font-semibold text-ink">Bedrock Only</span>
            </div>
            <p className="mt-2 text-xs text-muted">
              Skip Plan API entirely. All requests go directly to AWS Bedrock.
            </p>
          </button>
        </div>

        {routingNotice && (
          <div className="mt-4 text-sm text-success">{routingNotice}</div>
        )}
        {routingSaving && (
          <div className="mt-4 text-sm text-muted">Saving...</div>
        )}
      </div>

      <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-ink">Monthly Budget (Bedrock)</h2>
            <p className="text-xs text-muted">
              Current month usage only, KST period boundaries.
            </p>
          </div>
          {budgetStatus && (
            <span
              className={[
                'inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold',
                budgetOverLimit ? 'bg-danger/10 text-danger' : 'bg-accent/10 text-accent',
              ].join(' ')}
            >
              {budgetStatus.monthly_budget_usd
                ? `${formatPercent(budgetStatus.usage_percentage)} used`
                : 'Unlimited'}
            </span>
          )}
        </div>

        {budgetLoading && (
          <div className="mt-4 rounded-2xl border border-line bg-surface p-4 text-sm text-muted">
            Loading budget status...
          </div>
        )}

        {!budgetLoading && !budgetStatus && (
          <div className="mt-4 rounded-2xl border border-line bg-surface p-4 text-sm text-muted">
            Budget status unavailable right now.
          </div>
        )}

        {!budgetLoading && budgetStatus && (
          <>
            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <BudgetMetric
                label="Budget"
                value={
                  budgetStatus.monthly_budget_usd
                    ? formatBudget(budgetStatus.monthly_budget_usd)
                    : 'Unlimited'
                }
              />
              <BudgetMetric
                label="Usage"
                value={formatBudget(budgetStatus.current_usage_usd)}
                note="Bedrock only"
              />
              <BudgetMetric
                label="Remaining"
                value={
                  budgetStatus.remaining_usd
                    ? formatBudget(budgetStatus.remaining_usd)
                    : 'Unlimited'
                }
              />
              <BudgetMetric
                label="Period"
                value={`${formatBudgetDate(budgetStatus.period_start)} - ${formatBudgetDate(
                  budgetStatus.period_end
                )}`}
              />
            </div>

            {budgetStatus.monthly_budget_usd && (
              <div className="mt-4">
                <div className="flex items-center justify-between text-xs text-muted">
                  <span>Usage</span>
                  <span>{formatPercent(budgetStatus.usage_percentage)} of budget</span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-surface-2">
                  <div
                    className={`h-2 rounded-full ${budgetOverLimit ? 'bg-danger' : 'bg-accent'}`}
                    style={{ width: `${budgetProgress}%` }}
                  />
                </div>
              </div>
            )}
          </>
        )}

        <form
          onSubmit={handleBudgetSave}
          className="mt-6 grid gap-4 rounded-2xl border border-line bg-surface-2 p-4 sm:grid-cols-[minmax(0,1fr)_auto]"
        >
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
              Set Monthly Budget (USD)
            </label>
            <input
              type="number"
              min="0.01"
              max="999999.99"
              step="0.01"
              placeholder="Unlimited"
              value={budgetInput}
              onChange={(event) => setBudgetInput(event.target.value)}
              className={`${inputClass} mt-2`}
            />
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <button
              type="submit"
              disabled={budgetSaving}
              className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-black disabled:opacity-60"
            >
              {budgetSaving ? 'Saving...' : 'Save'}
            </button>
            <button
              type="button"
              onClick={() => setBudgetInput('')}
              className="rounded-full border border-line px-4 py-2 text-sm font-semibold text-ink transition hover:bg-surface"
            >
              Unlimited
            </button>
          </div>
          <div className="text-sm sm:col-span-2">
            {budgetError && <div className="text-danger">{budgetError}</div>}
            {budgetNotice && <div className="text-success">{budgetNotice}</div>}
          </div>
        </form>
      </div>

      <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-ink">Cost & Usage</h2>
            <p className="text-xs text-muted">KST-based ranges, stored pricing snapshots.</p>
          </div>
          <div className="inline-flex flex-wrap rounded-full border border-line bg-surface p-1 shadow-soft">
            {RANGE_PRESETS.map((preset) => (
              <button
                key={preset.key}
                type="button"
                onClick={() => setRangePreset(preset.key)}
                className={[
                  'rounded-full px-4 py-1.5 text-sm font-semibold transition',
                  rangePreset === preset.key
                    ? 'bg-accent text-white shadow-soft'
                    : 'text-muted hover:text-ink hover:bg-surface-2',
                ].join(' ')}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        {rangePreset === 'custom' && (
          <div className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl border border-line bg-surface-2 p-4 text-xs text-muted">
            <div className="text-xs uppercase tracking-[0.28em] text-muted">Custom Range</div>
            <input
              type="date"
              value={customRange.start}
              onChange={(event) =>
                setCustomRange((prev) => ({ ...prev, start: event.target.value }))
              }
              className="rounded-full border border-line bg-surface px-3 py-1.5 text-xs text-ink"
            />
            <span className="text-muted">to</span>
            <input
              type="date"
              value={customRange.end}
              onChange={(event) =>
                setCustomRange((prev) => ({ ...prev, end: event.target.value }))
              }
              className="rounded-full border border-line bg-surface px-3 py-1.5 text-xs text-ink"
            />
            <span className="text-muted">Inclusive range · UTC+9</span>
          </div>
        )}

        {usageRange && (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
            <div>
              Range:{' '}
              {rangePreset === 'custom'
                ? `${usageRange.startDate} - ${usageRange.endDate}`
                : `${formatKstDate(usageRange.startTime)} - ${formatKstDate(
                    usageRange.endTime
                  )}`}{' '}
              (KST)
            </div>
            <div>Bucket: {bucketType}</div>
          </div>
        )}

        {usageLoading && (
          <div className="mt-6 rounded-2xl border border-line bg-surface p-6 text-sm text-muted">
            Loading usage data...
          </div>
        )}

        {!usageLoading && !usage && (
          <div className="mt-6 rounded-2xl border border-line bg-surface p-6 text-sm text-muted">
            No usage data available for this range yet.
          </div>
        )}

        {!usageLoading && usage && (
          <>
            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                label="Estimated Cost"
                value={formatCurrency(totalCost)}
                note={`Requests ${formatNumber(usage.total_requests)}`}
              />
              <MetricCard label="Input Cost" value={formatCurrency(inputCost)} />
              <MetricCard label="Output Cost" value={formatCurrency(outputCost)} />
              <MetricCard
                label="Cache Cost"
                value={formatCurrency(cacheCost)}
                note={`${formatNumber(cacheTokens)} cache tokens`}
              />
            </div>

            <div className="mt-6 overflow-hidden rounded-2xl border border-line">
              {costRows.length === 0 ? (
                <div className="px-6 py-10 text-center text-sm text-muted">
                  No cost breakdown recorded for this user.
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-[0.2em] text-muted">
                      <th className="px-6 py-3">Model</th>
                      <th className="px-6 py-3">Input</th>
                      <th className="px-6 py-3">Output</th>
                      <th className="px-6 py-3">Cache Write</th>
                      <th className="px-6 py-3">Cache Read</th>
                      <th className="px-6 py-3 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {costRows.map((row) => (
                      <tr key={row.model} className="border-t border-line/60">
                        <td className="px-6 py-4 font-medium text-ink">{row.model}</td>
                        <td className="px-6 py-4 text-muted">
                          {formatCurrency(row.inputCost)}
                        </td>
                        <td className="px-6 py-4 text-muted">
                          {formatCurrency(row.outputCost)}
                        </td>
                        <td className="px-6 py-4 text-muted">
                          {formatCurrency(row.cacheWriteCost)}
                        </td>
                        <td className="px-6 py-4 text-muted">
                          {formatCurrency(row.cacheReadCost)}
                        </td>
                        <td className="px-6 py-4 text-right font-semibold text-ink">
                          {formatCurrency(row.totalCost)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </div>

      <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-ink">Access Keys</h2>
            <p className="text-xs text-muted">Issue, revoke, and register Bedrock keys.</p>
          </div>
          {user.status === 'active' && (
            <button
              onClick={handleIssueKey}
              className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white shadow-soft transition hover:bg-accent-strong"
            >
              Issue New Key
            </button>
          )}
        </div>

        {pendingKey && (
          <div className="mt-5 rounded-2xl border border-line bg-surface-2 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-xs uppercase tracking-[0.24em] text-muted">
                  {pendingKey.label}
                </div>
                <p className="mt-1 text-sm text-muted">
                  Copy now. The full key is never shown in the UI.
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleCopyPendingKey}
                  className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-ink transition hover:bg-surface"
                >
                  {copied ? 'Copied' : 'Copy'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setPendingKey(null);
                    setCopied(false);
                  }}
                  className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-ink transition hover:bg-surface"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        )}

        {selectedKeyId && (
          <div className="mt-5 rounded-2xl border border-line bg-surface-2 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-xs uppercase tracking-[0.24em] text-muted">
                  Register Bedrock API Key
                </div>
                <p className="mt-1 text-sm text-muted">
                  Attach Bedrock credentials to this access key.
                </p>
                {selectedKey && (
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted">
                    <span className="rounded-full border border-line bg-surface px-3 py-1">
                      Key {selectedKey.key_prefix}...
                    </span>
                    <span className="rounded-full border border-line bg-surface px-3 py-1">
                      Region {selectedKey.bedrock_region}
                    </span>
                    <span className="rounded-full border border-line bg-surface px-3 py-1">
                      Created {formatDate(selectedKey.created_at)}
                    </span>
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => setSelectedKeyId(null)}
                className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-ink transition hover:bg-surface"
              >
                Cancel
              </button>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <input
                type="password"
                placeholder="Bedrock API Key"
                value={bedrockKey}
                onChange={(e) => setBedrockKey(e.target.value)}
                className={`${inputClass} max-w-xs`}
              />
              <button
                type="button"
                onClick={handleRegisterBedrock}
                className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-black"
              >
                Register
              </button>
            </div>
          </div>
        )}

        {notice && <div className="mt-4 text-sm text-success">{notice}</div>}

        <div className="mt-6 overflow-hidden rounded-2xl border border-line">
          {keys.length === 0 ? (
            <div className="px-6 py-10 text-center text-sm text-muted">
              No access keys yet.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-[0.2em] text-muted">
                  <th className="px-6 py-3">Prefix</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Bedrock</th>
                  <th className="px-6 py-3">Region</th>
                  <th className="px-6 py-3">Created</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {keys.map((key) => (
                  <tr
                    key={key.id}
                    className={[
                      'border-t border-line/60 hover:bg-surface-2',
                      selectedKeyId === key.id ? 'bg-surface-2' : '',
                    ].join(' ')}
                  >
                    <td className="px-6 py-4 font-mono text-xs text-ink">
                      {key.key_prefix}...
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={[
                          'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold',
                          key.status === 'active'
                            ? 'bg-success/10 text-success'
                            : key.status === 'rotating'
                            ? 'bg-accent/10 text-accent'
                            : 'bg-danger/10 text-danger',
                        ].join(' ')}
                      >
                        {key.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {key.has_bedrock_key ? (
                        <span className="inline-flex items-center rounded-full bg-accent/10 px-2.5 py-1 text-xs font-semibold text-accent">
                          Linked
                        </span>
                      ) : (
                        <span className="text-xs text-muted">Not set</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-muted">{key.bedrock_region}</td>
                    <td className="px-6 py-4 text-muted">
                      {formatDate(key.created_at)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {key.status === 'active' && (
                        <div className="flex items-center justify-end gap-2">
                          {!key.has_bedrock_key && (
                            <button
                              onClick={() => setSelectedKeyId(key.id)}
                              className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-ink transition hover:bg-surface"
                            >
                              Bedrock
                            </button>
                          )}
                          <button
                            onClick={() => handleRevoke(key.id)}
                            className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-danger transition hover:bg-surface"
                          >
                            Revoke
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function Detail({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-[0.2em] text-muted">{label}</div>
      <div className={`mt-2 text-sm text-ink ${mono ? 'font-mono text-xs' : ''}`}>
        {value}
      </div>
    </div>
  );
}

function MetricCard({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-5 shadow-soft">
      <div className="text-xs uppercase tracking-[0.24em] text-muted">{label}</div>
      <div className="mt-3 text-2xl font-semibold text-ink">{value}</div>
      {note && <div className="mt-2 text-xs text-muted">{note}</div>}
    </div>
  );
}

function BudgetMetric({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <div className="text-xs uppercase tracking-[0.24em] text-muted">{label}</div>
      <div className="mt-2 text-xl font-semibold text-ink">{value}</div>
      {note && <div className="mt-1 text-xs text-muted">{note}</div>}
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between">
      <span>{label}</span>
      <span className="text-ink">{value}</span>
    </div>
  );
}

function formatNumber(value: number) {
  return numberFormatter.format(value);
}

function formatCurrency(value: number) {
  if (value >= 1) return currencyShortFormatter.format(value);
  return currencyFormatter.format(value);
}

function parseCost(value: string | number | undefined) {
  if (value === undefined) return 0;
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatBudget(value: string | number) {
  const parsed = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(parsed)) return '-';
  return currencyShortFormatter.format(parsed);
}

function formatBudgetDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) return '-';
  return `${percentFormatter.format(value)}%`;
}

function formatModelLabel(modelId: string) {
  if (modelId.includes('opus')) return 'Claude Opus 4.5';
  if (modelId.includes('sonnet')) return 'Claude Sonnet 4.5';
  if (modelId.includes('haiku')) return 'Claude Haiku 4.5';
  return modelId;
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

async function copyToClipboard(value: string) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value);
      return true;
    } catch {
      return false;
    }
  }

  const textarea = document.createElement('textarea');
  textarea.value = value;
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand('copy');
  document.body.removeChild(textarea);
  return copied;
}
