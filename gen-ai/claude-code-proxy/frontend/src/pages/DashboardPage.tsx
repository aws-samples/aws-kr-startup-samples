import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '@/components/PageHeader';
import { api, UsageBucket, UsageResponse, UsageTopUser, User } from '@/lib/api';
import {
  fillMissingBuckets,
  formatKstDate,
  formatKstDateTime,
  resolveCustomRange,
  resolvePeriodRange,
  selectBucketType,
  UsagePeriod,
} from '@/lib/usageRange';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

type RangePreset = UsagePeriod | 'custom';

const RANGE_PRESETS: { key: RangePreset; label: string }[] = [
  { key: 'day', label: 'Day' },
  { key: 'week', label: 'Week' },
  { key: 'month', label: 'Month' },
  { key: 'custom', label: 'Custom' },
];

const numberFormatter = new Intl.NumberFormat('en-US');
const compactFormatter = new Intl.NumberFormat('en-US', { notation: 'compact' });
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
const currencyCompactFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  notation: 'compact',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const COST_COLORS = {
  input: '#2563eb',
  output: '#0ea5e9',
  cacheWrite: '#22c55e',
  cacheRead: '#f59e0b',
  total: '#f97316',
};

export default function DashboardPage() {
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [topUsers, setTopUsers] = useState<UsageTopUser[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [rangePreset, setRangePreset] = useState<RangePreset>('week');
  const [customRange, setCustomRange] = useState({ start: '', end: '' });
  const [isLoading, setIsLoading] = useState(false);

  const range = useMemo(() => {
    if (rangePreset === 'custom') {
      if (!customRange.start || !customRange.end) return null;
      return resolveCustomRange(customRange.start, customRange.end);
    }
    return resolvePeriodRange(rangePreset);
  }, [customRange.end, customRange.start, rangePreset]);

  const bucketType = useMemo(
    () => (range ? selectBucketType(range.rangeDays) : 'day'),
    [range]
  );

  useEffect(() => {
    api.getUsers().then(setUsers).catch(() => setUsers([]));
  }, []);

  useEffect(() => {
    if (!range) return;
    let active = true;
    setIsLoading(true);

    const usageParams = {
      bucket_type: bucketType,
      user_id: selectedUserId || undefined,
      ...(rangePreset === 'custom'
        ? { start_date: range.startDate, end_date: range.endDate }
        : { period: rangePreset }),
    };

    const topUsersParams = {
      bucket_type: bucketType,
      start_time: range.startTime.toISOString(),
      end_time: range.endTime.toISOString(),
      limit: 6,
    };

    Promise.all([api.getUsage(usageParams), api.getTopUsers(topUsersParams)])
      .then(([usageResponse, topUsersResponse]) => {
        if (!active) return;
        setUsage(usageResponse);
        setTopUsers(topUsersResponse);
      })
      .catch(() => {
        if (!active) return;
        setUsage(null);
        setTopUsers([]);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [bucketType, range, rangePreset, selectedUserId]);

  const filledBuckets = useMemo(() => {
    if (!usage || !range) return [];
    return fillMissingBuckets(
      usage.buckets,
      range.startTime,
      range.endTime,
      bucketType,
      (bucketStart) => ({
        bucket_start: bucketStart.toISOString(),
        requests: 0,
        input_tokens: 0,
        output_tokens: 0,
        total_tokens: 0,
        cache_write_tokens: 0,
        cache_read_tokens: 0,
        input_cost_usd: '0',
        output_cost_usd: '0',
        cache_write_cost_usd: '0',
        cache_read_cost_usd: '0',
        estimated_cost_usd: '0',
      })
    );
  }, [usage, range, bucketType]);

  const chartData = useMemo(
    () =>
      filledBuckets.map((bucket) => ({
        time: formatKstDateTime(new Date(bucket.bucket_start)),
        totalTokens: bucket.total_tokens,
        inputTokens: bucket.input_tokens,
        outputTokens: bucket.output_tokens,
        requests: bucket.requests,
        estimatedCost: parseCost(bucket.estimated_cost_usd),
      })),
    [filledBuckets]
  );

  const cumulativeData = useMemo(() => {
    if (filledBuckets.length === 0) return [];
    let runningTotal = 0;
    return filledBuckets.map((bucket) => {
      runningTotal += bucket.total_tokens;
      return {
        time: formatKstDateTime(new Date(bucket.bucket_start)),
        cumulativeTokens: runningTotal,
      };
    });
  }, [filledBuckets]);

  const totalTokens = usage?.total_tokens ?? 0;
  const tokensPerRequest =
    usage && usage.total_requests > 0 ? usage.total_tokens / usage.total_requests : 0;
  const totalCost = usage ? parseCost(usage.estimated_cost_usd) : 0;
  const inputCost = usage ? parseCost(usage.total_input_cost_usd) : 0;
  const outputCost = usage ? parseCost(usage.total_output_cost_usd) : 0;
  const cacheWriteCost = usage ? parseCost(usage.total_cache_write_cost_usd) : 0;
  const cacheReadCost = usage ? parseCost(usage.total_cache_read_cost_usd) : 0;
  const cacheCost = usage
    ? cacheWriteCost + cacheReadCost
    : 0;
  const cacheTokens = usage
    ? usage.total_cache_write_tokens + usage.total_cache_read_tokens
    : 0;
  const costPerRequest = usage && usage.total_requests > 0 ? totalCost / usage.total_requests : 0;
  const outputInputRatio =
    usage && usage.total_input_tokens > 0
      ? usage.total_output_tokens / usage.total_input_tokens
      : 0;
  const selectedUser = users.find((user) => user.id === selectedUserId);
  const topUser = topUsers[0];
  const topUserShare = selectedUserId
    ? usage && totalTokens > 0
      ? 1
      : 0
    : usage && totalTokens > 0 && topUser
    ? topUser.total_tokens / totalTokens
    : 0;
  const topUserLabel = selectedUserId
    ? selectedUser?.name || 'Filtered user'
    : topUser
    ? topUser.name
    : 'No top user yet';
  const topUserMaxTokens = Math.max(...topUsers.map((user) => user.total_tokens), 1);
  const costBreakdownData = useMemo(() => {
    if (!usage) return [];
    return [...usage.cost_breakdown]
      .map((item) => ({
        model: formatModelLabel(item.model_id),
        modelId: item.model_id,
        inputCost: parseCost(item.input_cost_usd),
        outputCost: parseCost(item.output_cost_usd),
        cacheWriteCost: parseCost(item.cache_write_cost_usd),
        cacheReadCost: parseCost(item.cache_read_cost_usd),
        totalCost: parseCost(item.total_cost_usd),
      }))
      .sort((a, b) => b.totalCost - a.totalCost);
  }, [usage]);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Overview"
        title="Token Overview"
        subtitle="Monitor token throughput, cumulative burn, and user concentration in one view."
        actions={
          <>
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
            <select
              value={selectedUserId}
              onChange={(event) => setSelectedUserId(event.target.value)}
              className="rounded-full border border-line bg-surface px-4 py-2 text-sm font-semibold text-ink shadow-soft transition hover:bg-surface-2"
            >
              <option value="">All users</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.name}
                </option>
              ))}
            </select>
            <Link
              to="/users"
              className="rounded-full border border-line px-4 py-2 text-sm font-semibold text-ink transition hover:bg-surface-2"
            >
              Users
            </Link>
          </>
        }
      />

      {range && (
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
          <div>
            Range:{' '}
            {rangePreset === 'custom'
              ? `${range.startDate} - ${range.endDate}`
              : `${formatKstDate(range.startTime)} - ${formatKstDate(range.endTime)}`}{' '}
            (KST)
          </div>
          <div>Bucket: {bucketType}</div>
        </div>
      )}

      {rangePreset === 'custom' && (
        <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-line bg-surface p-4 text-xs text-muted shadow-soft">
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

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Estimated Cost"
          value={formatCurrency(totalCost)}
          note={`Cache ${formatCurrency(cacheCost)} · ${formatNumber(cacheTokens)} tokens`}
        />
        <StatCard label="Total Tokens" value={formatNumber(totalTokens)} />
        <StatCard label="Input Tokens" value={formatNumber(usage?.total_input_tokens ?? 0)} />
        <StatCard label="Output Tokens" value={formatNumber(usage?.total_output_tokens ?? 0)} />
        <StatCard label="Requests" value={formatNumber(usage?.total_requests ?? 0)} />
        <StatCard
          label="Tokens / Request"
          value={formatNumber(Math.round(tokensPerRequest))}
          note={`Output/Input ${outputInputRatio.toFixed(2)}x`}
        />
        <StatCard
          label="Cost / Request"
          value={formatCurrency(costPerRequest)}
          note="Average cost per request"
        />
        <StatCard
          label="Top User Share"
          value={formatPercent(topUserShare)}
          note={topUserLabel}
        />
      </div>

      {isLoading && (
        <div className="rounded-2xl border border-line bg-surface p-8 text-sm text-muted">
          Loading usage data...
        </div>
      )}

      {!isLoading && !usage && (
        <div className="rounded-2xl border border-line bg-surface p-8 text-sm text-muted">
          No usage data available yet. Metrics will populate as traffic flows through the proxy.
        </div>
      )}

      {!isLoading && usage && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,2.2fr)_minmax(0,1fr)]">
          <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-ink">Token Throughput</h2>
                <p className="text-xs text-muted">Input vs output tokens by bucket.</p>
              </div>
              <div className="text-xs text-muted">{chartData.length} points</div>
            </div>
            <div className="mt-6 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="inputGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563eb" stopOpacity={0.32} />
                      <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="outputGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.28} />
                      <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.4)" />
                  <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <YAxis
                    yAxisId="tokens"
                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                    tickFormatter={formatCompact}
                  />
                  <YAxis
                    yAxisId="cost"
                    orientation="right"
                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                    tickFormatter={formatCurrencyAxis}
                  />
                  <Tooltip
                    contentStyle={{ borderRadius: 12, borderColor: '#e2e8f0' }}
                    formatter={(value, name) => formatTooltipValue(value, name)}
                  />
                  <Area
                    type="monotone"
                    dataKey="inputTokens"
                    name="Input Tokens"
                    stroke="#2563eb"
                    fill="url(#inputGradient)"
                    strokeWidth={2}
                    yAxisId="tokens"
                  />
                  <Area
                    type="monotone"
                    dataKey="outputTokens"
                    name="Output Tokens"
                    stroke="#0ea5e9"
                    fill="url(#outputGradient)"
                    strokeWidth={2}
                    yAxisId="tokens"
                  />
                  <Line
                    type="monotone"
                    dataKey="requests"
                    name="Requests"
                    stroke="#0f172a"
                    strokeWidth={1.5}
                    yAxisId="tokens"
                  />
                  <Line
                    type="monotone"
                    dataKey="estimatedCost"
                    name="Estimated Cost"
                    stroke={COST_COLORS.total}
                    strokeWidth={2}
                    dot={false}
                    yAxisId="cost"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-ink">Top Users</h2>
                <p className="text-xs text-muted">
                  {selectedUserId ? 'All users (filter active).' : 'Token share by user.'}
                </p>
              </div>
            </div>
            <div className="mt-6 space-y-4">
              {topUsers.length === 0 && (
                <div className="rounded-xl border border-line bg-surface-2 px-4 py-3 text-sm text-muted">
                  No usage data in this range.
                </div>
              )}
              {topUsers.map((user) => (
                <Link
                  key={user.user_id}
                  to={`/users/${user.user_id}`}
                  className="block rounded-xl border border-transparent px-2 py-2 transition hover:border-line hover:bg-surface-2"
                >
                  <div className="flex items-center justify-between text-sm font-semibold text-ink">
                    <span>{user.name}</span>
                    <span>{formatCompact(user.total_tokens)}</span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-surface-2">
                    <div
                      className="h-2 rounded-full bg-accent"
                      style={{ width: `${(user.total_tokens / topUserMaxTokens) * 100}%` }}
                    />
                  </div>
                  <div className="mt-2 text-xs text-muted">
                    {formatNumber(user.total_requests)} requests
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {!isLoading && usage && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-ink">Cost Breakdown</h2>
                <p className="text-xs text-muted">Model-level costs by token type.</p>
              </div>
              <div className="text-xs text-muted">{costBreakdownData.length} models</div>
            </div>
            {costBreakdownData.length === 0 ? (
              <div className="mt-6 rounded-xl border border-line bg-surface-2 px-4 py-6 text-sm text-muted">
                No cost breakdown available for this range.
              </div>
            ) : (
              <div className="mt-6 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={costBreakdownData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.4)" />
                    <XAxis dataKey="model" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <YAxis
                      tick={{ fill: '#94a3b8', fontSize: 12 }}
                      tickFormatter={formatCurrencyAxis}
                    />
                    <Tooltip
                      contentStyle={{ borderRadius: 12, borderColor: '#e2e8f0' }}
                      formatter={(value, name) => formatTooltipValue(value, name)}
                      labelFormatter={(label) => `Model: ${label}`}
                    />
                    <Legend verticalAlign="top" height={36} />
                    <Bar
                      dataKey="inputCost"
                      name="Input Cost"
                      stackId="cost"
                      fill={COST_COLORS.input}
                    />
                    <Bar
                      dataKey="outputCost"
                      name="Output Cost"
                      stackId="cost"
                      fill={COST_COLORS.output}
                    />
                    <Bar
                      dataKey="cacheWriteCost"
                      name="Cache Write Cost"
                      stackId="cost"
                      fill={COST_COLORS.cacheWrite}
                    />
                    <Bar
                      dataKey="cacheReadCost"
                      name="Cache Read Cost"
                      stackId="cost"
                      fill={COST_COLORS.cacheRead}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-ink">Cost Mix</h2>
            <div className="mt-4 space-y-3 text-sm text-muted">
              <CostRow label="Input Cost" value={formatCurrency(inputCost)} />
              <CostRow label="Output Cost" value={formatCurrency(outputCost)} />
              <CostRow label="Cache Write" value={formatCurrency(cacheWriteCost)} />
              <CostRow label="Cache Read" value={formatCurrency(cacheReadCost)} />
              <div className="mt-4 border-t border-line pt-4">
                <CostRow label="Total Estimated" value={formatCurrency(totalCost)} strong />
              </div>
            </div>
            <div className="mt-4 text-xs text-muted">
              Cache tokens: {formatNumber(cacheTokens)}
            </div>
          </div>
        </div>
      )}

      {!isLoading && usage && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-ink">Cumulative Tokens</h2>
                <p className="text-xs text-muted">Total tokens consumed over the selected range.</p>
              </div>
            </div>
            <div className="mt-6 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={cumulativeData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.4)" />
                  <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <Tooltip contentStyle={{ borderRadius: 12, borderColor: '#e2e8f0' }} />
                  <Line type="monotone" dataKey="cumulativeTokens" stroke="#1d4ed8" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-ink">Focus</h2>
            <div className="mt-4 space-y-4 text-sm text-muted">
              <div>
                <div className="text-xs uppercase tracking-[0.28em] text-muted">Efficiency</div>
                <div className="mt-2 text-sm text-ink">
                  {formatNumber(Math.round(tokensPerRequest))} tokens/request
                </div>
                <div className="text-xs text-muted">
                  Output/Input ratio {outputInputRatio.toFixed(2)}x
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.28em] text-muted">Concentration</div>
                <div className="mt-2 text-sm text-ink">
                  {formatPercent(topUserShare)} owned by {topUser?.name || 'top user'}
                </div>
                <div className="text-xs text-muted">Track heavy consumers weekly.</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.28em] text-muted">Throughput</div>
                <div className="mt-2 text-sm text-ink">
                  {formatNumber(usage.total_requests)} requests in range
                </div>
                <div className="text-xs text-muted">Bucket size: {bucketType}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-5 shadow-soft">
      <div className="text-xs uppercase tracking-[0.24em] text-muted">{label}</div>
      <div className="mt-3 text-2xl font-semibold text-ink">{value}</div>
      {note && <div className="mt-2 text-xs text-muted">{note}</div>}
    </div>
  );
}

function CostRow({
  label,
  value,
  strong,
}: {
  label: string;
  value: string;
  strong?: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span>{label}</span>
      <span className={strong ? 'text-ink font-semibold' : 'text-ink'}>{value}</span>
    </div>
  );
}

function formatNumber(value: number) {
  return numberFormatter.format(value);
}

function formatCompact(value: number) {
  return compactFormatter.format(value);
}

function formatCurrency(value: number) {
  if (value >= 1) return currencyShortFormatter.format(value);
  return currencyFormatter.format(value);
}

function formatCurrencyAxis(value: number) {
  if (value >= 1000) return currencyCompactFormatter.format(value);
  if (value >= 1) return currencyShortFormatter.format(value);
  return currencyFormatter.format(value);
}

function formatTooltipValue(
  value: string | number | Array<string | number>,
  name: string | number
) {
  const label = String(name);
  const resolvedValue = Array.isArray(value) ? value[0] : value;
  const numericValue = typeof resolvedValue === 'number' ? resolvedValue : Number(resolvedValue);
  if (label.toLowerCase().includes('cost')) {
    return [formatCurrency(numericValue), label];
  }
  return [formatNumber(numericValue), label];
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function parseCost(value: string | number | undefined) {
  if (value === undefined) return 0;
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatModelLabel(modelId: string) {
  if (modelId.includes('opus')) return 'Claude Opus 4.5';
  if (modelId.includes('sonnet')) return 'Claude Sonnet 4.5';
  if (modelId.includes('haiku')) return 'Claude Haiku 4.5';
  return modelId;
}
