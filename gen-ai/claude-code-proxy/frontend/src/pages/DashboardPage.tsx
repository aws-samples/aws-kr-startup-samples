import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '@/components/PageHeader';
import { api, UsageResponse, UsageTopUser, UsageTopUserSeries, User } from '@/lib/api';
import {
  fillMissingBuckets,
  formatKstDate,
  formatKstDateTime,
  KST_TIME_ZONE,
  resolveCustomRange,
  resolvePeriodRange,
  selectBucketType,
  UsagePeriod,
} from '@/lib/usageRange';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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
const MODEL_COLORS = ['#2563eb', '#0ea5e9', '#22c55e', '#f59e0b', '#ec4899'];
const USER_COLORS = ['#2563eb', '#0ea5e9', '#22c55e', '#f59e0b', '#ec4899'];

export default function DashboardPage() {
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [planUsage, setPlanUsage] = useState<UsageResponse | null>(null);
  const [topUsers, setTopUsers] = useState<UsageTopUser[]>([]);
  const [planTopUsers, setPlanTopUsers] = useState<UsageTopUser[]>([]);
  const [topUserSeries, setTopUserSeries] = useState<UsageTopUserSeries[]>([]);
  const [planTopUserSeries, setPlanTopUserSeries] = useState<UsageTopUserSeries[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [rangePreset, setRangePreset] = useState<RangePreset>('week');
  const [customRange, setCustomRange] = useState({ start: '', end: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [tokenView, setTokenView] = useState<'period' | 'cumulative'>('period');
  const [planTokenView, setPlanTokenView] = useState<'period' | 'cumulative'>('period');
  const [costView, setCostView] = useState<'period' | 'cumulative'>('period');
  const [userTokenView, setUserTokenView] = useState<'period' | 'cumulative'>('period');
  const [hoveredUserId, setHoveredUserId] = useState<string | null>(null);
  const [expandedChart, setExpandedChart] = useState<
    'token' | 'planToken' | 'cost' | 'requests' | 'topUserUsage' | 'modelMix' | 'ranking' | null
  >(null);

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

    const bedrockUsageParams = {
      ...usageParams,
      provider: 'bedrock' as const,
    };

    const planUsageParams = {
      ...usageParams,
      provider: 'plan' as const,
    };

    const topUsersLimit = 5;
    const topUsersParams = {
      bucket_type: bucketType,
      start_time: range.startTime.toISOString(),
      end_time: range.endTime.toISOString(),
      limit: topUsersLimit,
    };

    const planTopUsersParams = {
      ...topUsersParams,
      provider: 'plan' as const,
    };

    Promise.all([
      api.getUsage(bedrockUsageParams),
      api.getUsage(planUsageParams),
      api.getTopUsers(topUsersParams),
      api.getTopUserSeries(topUsersParams),
      api.getTopUsers(planTopUsersParams),
      api.getTopUserSeries(planTopUsersParams),
    ])
      .then(([
        bedrockUsageResponse,
        planUsageResponse,
        topUsersResponse,
        topUserSeriesResponse,
        planTopUsersResponse,
        planTopUserSeriesResponse,
      ]) => {
        if (!active) return;
        setUsage(bedrockUsageResponse);
        setPlanUsage(planUsageResponse);
        setTopUsers(topUsersResponse);
        setTopUserSeries(topUserSeriesResponse);
        setPlanTopUsers(planTopUsersResponse);
        setPlanTopUserSeries(planTopUserSeriesResponse);
      })
      .catch(() => {
        if (!active) return;
        setUsage(null);
        setPlanUsage(null);
        setTopUsers([]);
        setTopUserSeries([]);
        setPlanTopUsers([]);
        setPlanTopUserSeries([]);
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

  const planFilledBuckets = useMemo(() => {
    if (!planUsage || !range) return [];
    return fillMissingBuckets(
      planUsage.buckets,
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
  }, [planUsage, range, bucketType]);

  const chartData = useMemo(
    () =>
      filledBuckets.map((bucket) => ({
        time: formatBucketLabel(new Date(bucket.bucket_start), bucketType),
        totalTokens: bucket.total_tokens,
        inputTokens: bucket.input_tokens,
        outputTokens: bucket.output_tokens,
        cacheTokens: bucket.cache_write_tokens + bucket.cache_read_tokens,
        requests: bucket.requests,
        totalCost: parseCost(bucket.estimated_cost_usd),
        inputCost: parseCost(bucket.input_cost_usd),
        outputCost: parseCost(bucket.output_cost_usd),
        cacheWriteCost: parseCost(bucket.cache_write_cost_usd),
        cacheReadCost: parseCost(bucket.cache_read_cost_usd),
      })),
    [filledBuckets, bucketType]
  );

  const planChartData = useMemo(
    () =>
      planFilledBuckets.map((bucket) => ({
        time: formatBucketLabel(new Date(bucket.bucket_start), bucketType),
        totalTokens: bucket.total_tokens,
        inputTokens: bucket.input_tokens,
        outputTokens: bucket.output_tokens,
        cacheTokens: bucket.cache_write_tokens + bucket.cache_read_tokens,
        requests: bucket.requests,
      })),
    [planFilledBuckets, bucketType]
  );

  const cumulativeTokenData = useMemo(() => {
    let totalTokensRunning = 0;
    let inputTokensRunning = 0;
    let outputTokensRunning = 0;
    let cacheTokensRunning = 0;
    return chartData.map((point) => {
      totalTokensRunning += point.totalTokens;
      inputTokensRunning += point.inputTokens;
      outputTokensRunning += point.outputTokens;
      cacheTokensRunning += point.cacheTokens;
      return {
        ...point,
        totalTokens: totalTokensRunning,
        inputTokens: inputTokensRunning,
        outputTokens: outputTokensRunning,
        cacheTokens: cacheTokensRunning,
      };
    });
  }, [chartData]);

  const cumulativePlanTokenData = useMemo(() => {
    let totalTokensRunning = 0;
    let inputTokensRunning = 0;
    let outputTokensRunning = 0;
    let cacheTokensRunning = 0;
    return planChartData.map((point) => {
      totalTokensRunning += point.totalTokens;
      inputTokensRunning += point.inputTokens;
      outputTokensRunning += point.outputTokens;
      cacheTokensRunning += point.cacheTokens;
      return {
        ...point,
        totalTokens: totalTokensRunning,
        inputTokens: inputTokensRunning,
        outputTokens: outputTokensRunning,
        cacheTokens: cacheTokensRunning,
      };
    });
  }, [planChartData]);

  const cumulativeCostData = useMemo(() => {
    let totalCostRunning = 0;
    let inputCostRunning = 0;
    let outputCostRunning = 0;
    let cacheWriteCostRunning = 0;
    let cacheReadCostRunning = 0;
    return chartData.map((point) => {
      totalCostRunning += point.totalCost;
      inputCostRunning += point.inputCost;
      outputCostRunning += point.outputCost;
      cacheWriteCostRunning += point.cacheWriteCost;
      cacheReadCostRunning += point.cacheReadCost;
      return {
        ...point,
        totalCost: totalCostRunning,
        inputCost: inputCostRunning,
        outputCost: outputCostRunning,
        cacheWriteCost: cacheWriteCostRunning,
        cacheReadCost: cacheReadCostRunning,
      };
    });
  }, [chartData]);
  const userColorMap = useMemo(() => {
    const map = new Map<string, string>();
    topUserSeries.forEach((user, index) => {
      map.set(user.user_id, USER_COLORS[index % USER_COLORS.length]);
    });
    return map;
  }, [topUserSeries]);
  const userSeriesData = useMemo(() => {
    if (filledBuckets.length === 0 || topUserSeries.length === 0) return [];
    const rows = filledBuckets.map((bucket) => {
      const entry: Record<string, string | number> = {
        bucketStart: bucket.bucket_start,
        time: formatBucketLabel(new Date(bucket.bucket_start), bucketType),
      };
      topUserSeries.forEach((user) => {
        entry[user.user_id] = 0;
      });
      return entry;
    });
    const rowMap = new Map(
      rows.map((row) => [row.bucketStart as string, row])
    );
    topUserSeries.forEach((user) => {
      user.buckets.forEach((bucket) => {
        const row = rowMap.get(bucket.bucket_start);
        if (row) row[user.user_id] = bucket.total_tokens;
      });
    });
    return rows;
  }, [bucketType, filledBuckets, topUserSeries]);
  const cumulativeUserSeriesData = useMemo(() => {
    if (userSeriesData.length === 0 || topUserSeries.length === 0) return [];
    const runningTotals = new Map<string, number>();
    return userSeriesData.map((row) => {
      const next = { ...row };
      topUserSeries.forEach((user) => {
        const currentValue = Number(row[user.user_id] ?? 0);
        const running = (runningTotals.get(user.user_id) ?? 0) + currentValue;
        runningTotals.set(user.user_id, running);
        next[user.user_id] = running;
      });
      return next;
    });
  }, [topUserSeries, userSeriesData]);

  const planUserColorMap = useMemo(() => {
    const map = new Map<string, string>();
    planTopUserSeries.forEach((user, index) => {
      map.set(user.user_id, USER_COLORS[index % USER_COLORS.length]);
    });
    return map;
  }, [planTopUserSeries]);

  const planUserSeriesData = useMemo(() => {
    if (planFilledBuckets.length === 0 || planTopUserSeries.length === 0) return [];
    const rows = planFilledBuckets.map((bucket) => {
      const entry: Record<string, string | number> = {
        bucketStart: bucket.bucket_start,
        time: formatBucketLabel(new Date(bucket.bucket_start), bucketType),
      };
      planTopUserSeries.forEach((user) => {
        entry[user.user_id] = 0;
      });
      return entry;
    });
    const rowMap = new Map(
      rows.map((row) => [row.bucketStart as string, row])
    );
    planTopUserSeries.forEach((user) => {
      user.buckets.forEach((bucket) => {
        const row = rowMap.get(bucket.bucket_start);
        if (row) row[user.user_id] = bucket.total_tokens;
      });
    });
    return rows;
  }, [bucketType, planFilledBuckets, planTopUserSeries]);

  const cumulativePlanUserSeriesData = useMemo(() => {
    if (planUserSeriesData.length === 0 || planTopUserSeries.length === 0) return [];
    const runningTotals = new Map<string, number>();
    return planUserSeriesData.map((row) => {
      const next = { ...row };
      planTopUserSeries.forEach((user) => {
        const currentValue = Number(row[user.user_id] ?? 0);
        const running = (runningTotals.get(user.user_id) ?? 0) + currentValue;
        runningTotals.set(user.user_id, running);
        next[user.user_id] = running;
      });
      return next;
    });
  }, [planTopUserSeries, planUserSeriesData]);

  const renderTokenChart = (heightClass: string) => (
    <div className={heightClass}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={tokenView === 'cumulative' ? cumulativeTokenData : chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.4)" />
          <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 12 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={formatCompact} />
          <Tooltip
            contentStyle={{ borderRadius: 12, borderColor: '#e2e8f0' }}
            formatter={(value, name) => formatTooltipValue(value, name)}
          />
          <Legend verticalAlign="bottom" height={24} wrapperStyle={{ fontSize: 10 }} />
          <Line
            type="monotone"
            dataKey="totalTokens"
            name="Total Tokens"
            stroke="#0f172a"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="inputTokens"
            name="Input Tokens"
            stroke="#2563eb"
            strokeWidth={1.5}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="outputTokens"
            name="Output Tokens"
            stroke="#0ea5e9"
            strokeWidth={1.5}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="cacheTokens"
            name="Cache Tokens"
            stroke="#22c55e"
            strokeWidth={1.5}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  const renderPlanTokenChart = (heightClass: string) => (
    <div className={heightClass}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={planTokenView === 'cumulative' ? cumulativePlanUserSeriesData : planUserSeriesData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.4)" />
          <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 12 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={formatCompact} />
          <Tooltip
            contentStyle={{ borderRadius: 12, borderColor: '#e2e8f0' }}
            formatter={(value, name) => formatTooltipValue(value, name)}
          />
          <Legend verticalAlign="bottom" height={24} wrapperStyle={{ fontSize: 10 }} />
          {planTopUserSeries.map((user) => {
            const strokeColor = planUserColorMap.get(user.user_id) || '#2563eb';
            const isDimmed = hoveredUserId && hoveredUserId !== user.user_id;
            return (
              <Line
                key={user.user_id}
                type="monotone"
                dataKey={user.user_id}
                name={user.name}
                stroke={strokeColor}
                strokeWidth={hoveredUserId === user.user_id ? 2.5 : 2}
                strokeOpacity={isDimmed ? 0.25 : 1}
                dot={false}
                activeDot={{ r: hoveredUserId === user.user_id ? 4 : 3 }}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  const renderCostChart = (heightClass: string) => (
    <div className={heightClass}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={costView === 'cumulative' ? cumulativeCostData : chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.4)" />
          <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 12 }} />
          <YAxis
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            tickFormatter={formatCurrencyAxis}
          />
          <Tooltip
            contentStyle={{ borderRadius: 12, borderColor: '#e2e8f0' }}
            formatter={(value, name) => formatTooltipValue(value, name)}
          />
          <Legend verticalAlign="bottom" height={24} wrapperStyle={{ fontSize: 10 }} />
          <Line
            type="monotone"
            dataKey="totalCost"
            name="Total Cost"
            stroke={COST_COLORS.total}
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="inputCost"
            name="Input Cost"
            stroke={COST_COLORS.input}
            strokeWidth={1.5}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="outputCost"
            name="Output Cost"
            stroke={COST_COLORS.output}
            strokeWidth={1.5}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="cacheWriteCost"
            name="Cache Write"
            stroke={COST_COLORS.cacheWrite}
            strokeWidth={1.5}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="cacheReadCost"
            name="Cache Read"
            stroke={COST_COLORS.cacheRead}
            strokeWidth={1.5}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  const renderRequestChart = (heightClass: string) => (
    <div className={heightClass}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.4)" />
          <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 12 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={formatCompact} />
          <Tooltip
            contentStyle={{ borderRadius: 12, borderColor: '#e2e8f0' }}
            formatter={(value, name) => formatTooltipValue(value, name)}
          />
          <Bar dataKey="requests" name="Requests" fill="#1f2937" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );

  const renderTopUserUsageChart = (heightClass: string) => (
    <div className={heightClass}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={userTokenView === 'cumulative' ? cumulativeUserSeriesData : userSeriesData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.4)" />
          <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 12 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={formatCompact} />
          <Tooltip
            contentStyle={{ borderRadius: 12, borderColor: '#e2e8f0' }}
            formatter={(value, name) => formatTooltipValue(value, name)}
          />
          <Legend verticalAlign="bottom" height={24} wrapperStyle={{ fontSize: 10 }} />
          {topUserSeries.map((user) => {
            const strokeColor = userColorMap.get(user.user_id) || '#2563eb';
            const isDimmed = hoveredUserId && hoveredUserId !== user.user_id;
            return (
              <Line
                key={user.user_id}
                type="monotone"
                dataKey={user.user_id}
                name={user.name}
                stroke={strokeColor}
                strokeWidth={hoveredUserId === user.user_id ? 2.5 : 2}
                strokeOpacity={isDimmed ? 0.25 : 1}
                dot={false}
                activeDot={{ r: hoveredUserId === user.user_id ? 4 : 3 }}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  const renderModelMixChart = (heightClass: string) => (
    <div className={heightClass}>
      {costBreakdownData.length === 0 ? (
        <div className="flex h-full items-center justify-center rounded-xl border border-line bg-surface-2 px-4 py-6 text-sm text-muted">
          No model usage yet.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={costBreakdownData} layout="vertical" margin={{ left: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.4)" />
            <XAxis
              type="number"
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              tickFormatter={formatCurrencyAxis}
            />
            <YAxis
              dataKey="model"
              type="category"
              width={120}
              tick={{ fill: '#94a3b8', fontSize: 12 }}
            />
            <Tooltip
              contentStyle={{ borderRadius: 12, borderColor: '#e2e8f0' }}
              formatter={(value, name) => formatTooltipValue(value, name)}
              labelFormatter={(label) => `Model: ${label}`}
            />
            <Bar dataKey="totalCost" name="Total Cost">
              {costBreakdownData.map((entry) => (
                <Cell key={entry.modelId} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );

  const totalTokens = usage?.total_tokens ?? 0;
  const tokensPerRequest =
    usage && usage.total_requests > 0 ? usage.total_tokens / usage.total_requests : 0;
  const totalCost = usage ? parseCost(usage.estimated_cost_usd) : 0;
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
  const activeUsers = selectedUserId ? (usage ? 1 : 0) : users.length;
  const activeUsersNote = selectedUserId ? 'Filtered user' : 'All users';
  const costBreakdownData = useMemo(() => {
    if (!usage) return [];
    const sorted = [...usage.cost_breakdown]
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
    return sorted.map((item, index) => ({
      ...item,
      color: MODEL_COLORS[index % MODEL_COLORS.length],
    }));
  }, [usage]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Token Overview"
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
        <StatCard
          label="Input/Output Tokens"
          value={`${formatNumber(usage?.total_input_tokens ?? 0)} / ${formatNumber(
            usage?.total_output_tokens ?? 0
          )}`}
        />
        <StatCard label="Total Requests" value={formatNumber(usage?.total_requests ?? 0)} />
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
        <StatCard label="Active Users" value={formatNumber(activeUsers)} note={activeUsersNote} />
        <StatCard label="Top User Share" value={formatPercent(topUserShare)} note={topUserLabel} />
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
        <section className="space-y-3">
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="text-base font-semibold text-ink">Bedrock Token Usage</h3>
                  <p className="text-[11px] text-muted">Token mix by bucket.</p>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted">
                  <div className="inline-flex rounded-full border border-line bg-surface px-1 py-0.5 font-semibold shadow-soft">
                    <button
                      type="button"
                      onClick={() => setTokenView('period')}
                      className={[
                        'rounded-full px-2 py-1 transition',
                        tokenView === 'period'
                          ? 'bg-accent text-white'
                          : 'text-muted hover:text-ink',
                      ].join(' ')}
                    >
                      Period
                    </button>
                    <button
                      type="button"
                      onClick={() => setTokenView('cumulative')}
                      className={[
                        'rounded-full px-2 py-1 transition',
                        tokenView === 'cumulative'
                          ? 'bg-accent text-white'
                          : 'text-muted hover:text-ink',
                      ].join(' ')}
                    >
                      Cumulative
                    </button>
                  </div>
                  <div>{chartData.length} pts</div>
                  <button
                    type="button"
                    onClick={() => setExpandedChart('token')}
                    className="rounded-full border border-line px-3 py-1 font-semibold transition hover:text-ink hover:bg-surface-2"
                  >
                    Expand
                  </button>
                </div>
              </div>
              <div className="mt-6">{renderTokenChart('h-64')}</div>
            </div>

            <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="text-base font-semibold text-ink">Bedrock Cost Burn</h3>
                  <p className="text-[11px] text-muted">Estimated cost per bucket.</p>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted">
                  <div className="inline-flex rounded-full border border-line bg-surface px-1 py-0.5 font-semibold shadow-soft">
                    <button
                      type="button"
                      onClick={() => setCostView('period')}
                      className={[
                        'rounded-full px-2 py-1 transition',
                        costView === 'period'
                          ? 'bg-accent text-white'
                          : 'text-muted hover:text-ink',
                      ].join(' ')}
                    >
                      Period
                    </button>
                    <button
                      type="button"
                      onClick={() => setCostView('cumulative')}
                      className={[
                        'rounded-full px-2 py-1 transition',
                        costView === 'cumulative'
                          ? 'bg-accent text-white'
                          : 'text-muted hover:text-ink',
                      ].join(' ')}
                    >
                      Cumulative
                    </button>
                  </div>
                  <div>{formatCurrency(totalCost)}</div>
                  <button
                    type="button"
                    onClick={() => setExpandedChart('cost')}
                    className="rounded-full border border-line px-3 py-1 font-semibold transition hover:text-ink hover:bg-surface-2"
                  >
                    Expand
                  </button>
                </div>
              </div>
              <div className="mt-6">{renderCostChart('h-64')}</div>
            </div>
          </div>
        </section>
      )}

      {!isLoading && usage && (
        <section className="space-y-3">
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-ink">Top User Ranking</h3>
                  <p className="text-xs text-muted">
                    {selectedUserId ? 'All users (filter active).' : 'Token share by user.'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setExpandedChart('ranking')}
                  className="rounded-full border border-line px-3 py-1 text-xs font-semibold text-muted transition hover:text-ink hover:bg-surface-2"
                >
                  Expand
                </button>
              </div>
              <div className="mt-6 space-y-4">
                {topUsers.length === 0 && (
                  <div className="rounded-xl border border-line bg-surface-2 px-4 py-3 text-sm text-muted">
                    No usage data in this range.
                  </div>
                )}
                {topUsers.slice(0, 5).map((user) => (
                  <Link
                    key={user.user_id}
                    to={`/users/${user.user_id}`}
                    className={[
                      'block rounded-xl border border-transparent px-2 py-2 transition hover:border-line hover:bg-surface-2',
                      hoveredUserId === user.user_id ? 'bg-surface-2 border-line' : '',
                    ].join(' ')}
                    onMouseEnter={() => setHoveredUserId(user.user_id)}
                    onMouseLeave={() => setHoveredUserId(null)}
                  >
                    <div className="flex items-center justify-between text-sm font-semibold text-ink">
                      <span className="flex items-center gap-2">
                        <span
                          className="h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: userColorMap.get(user.user_id) || '#2563eb' }}
                        />
                        {user.name}
                      </span>
                      <span>{formatCompact(user.total_tokens)}</span>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-surface-2">
                      <div
                        className="h-2 rounded-full"
                        style={{
                          width: `${(user.total_tokens / topUserMaxTokens) * 100}%`,
                          backgroundColor: userColorMap.get(user.user_id) || '#2563eb',
                        }}
                      />
                    </div>
                    <div className="mt-2 text-xs text-muted">
                      {formatNumber(user.total_requests)} requests
                    </div>
                  </Link>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="text-base font-semibold text-ink">Top User Usage</h3>
                  <p className="text-[11px] text-muted">Total tokens per user.</p>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted">
                  <div className="inline-flex rounded-full border border-line bg-surface px-1 py-0.5 font-semibold shadow-soft">
                    <button
                      type="button"
                      onClick={() => setUserTokenView('period')}
                      className={[
                        'rounded-full px-2 py-1 transition',
                        userTokenView === 'period'
                          ? 'bg-accent text-white'
                          : 'text-muted hover:text-ink',
                      ].join(' ')}
                    >
                      Period
                    </button>
                    <button
                      type="button"
                      onClick={() => setUserTokenView('cumulative')}
                      className={[
                        'rounded-full px-2 py-1 transition',
                        userTokenView === 'cumulative'
                          ? 'bg-accent text-white'
                          : 'text-muted hover:text-ink',
                      ].join(' ')}
                    >
                      Cumulative
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={() => setExpandedChart('topUserUsage')}
                    className="rounded-full border border-line px-3 py-1 font-semibold transition hover:text-ink hover:bg-surface-2"
                  >
                    Expand
                  </button>
                </div>
              </div>
              <div className="mt-6">{renderTopUserUsageChart('h-96')}</div>
            </div>
          </div>
        </section>
      )}

      {!isLoading && usage && (
        <section className="space-y-3">
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="text-base font-semibold text-ink">Request Count</h3>
                  <p className="text-[11px] text-muted">Requests per bucket.</p>
                </div>
                <button
                  type="button"
                  onClick={() => setExpandedChart('requests')}
                  className="rounded-full border border-line px-3 py-1 text-[11px] font-semibold text-muted transition hover:text-ink hover:bg-surface-2"
                >
                  Expand
                </button>
              </div>
              <div className="mt-6">{renderRequestChart('h-64')}</div>
            </div>
            <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="text-base font-semibold text-ink">Model Mix</h3>
                  <p className="text-[11px] text-muted">Cost by model.</p>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted">
                  <div>{costBreakdownData.length} models</div>
                  <button
                    type="button"
                    onClick={() => setExpandedChart('modelMix')}
                    className="rounded-full border border-line px-3 py-1 font-semibold transition hover:text-ink hover:bg-surface-2"
                  >
                    Expand
                  </button>
                </div>
              </div>
              <div className="mt-6">{renderModelMixChart('h-64')}</div>
            </div>
          </div>
        </section>
      )}

      {!isLoading && (
        <section className="space-y-3">
          <div className="rounded-2xl border border-line bg-surface p-6 shadow-soft">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-base font-semibold text-ink">Plan Token Usage by User</h3>
                <p className="text-[11px] text-muted">Total tokens per user (Anthropic Plan API).</p>
              </div>
              {planTopUserSeries.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted">
                  <div className="inline-flex rounded-full border border-line bg-surface px-1 py-0.5 font-semibold shadow-soft">
                    <button
                      type="button"
                      onClick={() => setPlanTokenView('period')}
                      className={[
                        'rounded-full px-2 py-1 transition',
                        planTokenView === 'period'
                          ? 'bg-accent text-white'
                          : 'text-muted hover:text-ink',
                      ].join(' ')}
                    >
                      Period
                    </button>
                    <button
                      type="button"
                      onClick={() => setPlanTokenView('cumulative')}
                      className={[
                        'rounded-full px-2 py-1 transition',
                        planTokenView === 'cumulative'
                          ? 'bg-accent text-white'
                          : 'text-muted hover:text-ink',
                      ].join(' ')}
                    >
                      Cumulative
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={() => setExpandedChart('planToken')}
                    className="rounded-full border border-line px-3 py-1 font-semibold transition hover:text-ink hover:bg-surface-2"
                  >
                    Expand
                  </button>
                </div>
              )}
            </div>
            <div className="mt-6">
              {planTopUserSeries.length === 0 ? (
                <div className="flex h-64 items-center justify-center rounded-xl border border-line bg-surface-2 px-4 py-6 text-sm text-muted">
                  <div className="text-center">
                    <div className="text-base font-semibold">No Plan API usage yet</div>
                    <div className="mt-2 text-xs">
                      Plan API usage will appear here once users start making requests through the Anthropic Plan API.
                    </div>
                  </div>
                </div>
              ) : (
                renderPlanTokenChart('h-64')
              )}
            </div>
          </div>
        </section>
      )}
      {expandedChart && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-6"
          onClick={() => setExpandedChart(null)}
        >
          <div
            className="w-full max-w-6xl rounded-3xl border border-line bg-surface p-6 shadow-xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <div className="text-lg font-semibold text-ink">
                {expandedChart === 'token' && 'Bedrock Token Usage'}
                {expandedChart === 'planToken' && 'Plan Token Usage by User'}
                {expandedChart === 'cost' && 'Bedrock Cost Burn'}
                {expandedChart === 'requests' && 'Request Count'}
                {expandedChart === 'topUserUsage' && 'Top User Usage'}
                {expandedChart === 'modelMix' && 'Model Mix'}
                {expandedChart === 'ranking' && 'Top User Ranking'}
              </div>
              <button
                type="button"
                onClick={() => setExpandedChart(null)}
                className="rounded-full border border-line px-4 py-1.5 text-xs font-semibold text-muted transition hover:text-ink hover:bg-surface-2"
              >
                Close
              </button>
            </div>
            {expandedChart === 'token' && (
              <div className="mt-4">
                <div className="flex items-center justify-end gap-3 text-xs text-muted">
                  <button
                    type="button"
                    onClick={() => setTokenView('period')}
                    className={[
                      'rounded-full border border-line px-3 py-1 font-semibold transition',
                      tokenView === 'period'
                        ? 'bg-accent text-white'
                        : 'text-muted hover:text-ink hover:bg-surface-2',
                    ].join(' ')}
                  >
                    Period
                  </button>
                  <button
                    type="button"
                    onClick={() => setTokenView('cumulative')}
                    className={[
                      'rounded-full border border-line px-3 py-1 font-semibold transition',
                      tokenView === 'cumulative'
                        ? 'bg-accent text-white'
                        : 'text-muted hover:text-ink hover:bg-surface-2',
                    ].join(' ')}
                  >
                    Cumulative
                  </button>
                </div>
                <div className="mt-4">{renderTokenChart('h-[70vh]')}</div>
              </div>
            )}
            {expandedChart === 'planToken' && (
              <div className="mt-4">
                <div className="flex items-center justify-end gap-3 text-xs text-muted">
                  <button
                    type="button"
                    onClick={() => setPlanTokenView('period')}
                    className={[
                      'rounded-full border border-line px-3 py-1 font-semibold transition',
                      planTokenView === 'period'
                        ? 'bg-accent text-white'
                        : 'text-muted hover:text-ink hover:bg-surface-2',
                    ].join(' ')}
                  >
                    Period
                  </button>
                  <button
                    type="button"
                    onClick={() => setPlanTokenView('cumulative')}
                    className={[
                      'rounded-full border border-line px-3 py-1 font-semibold transition',
                      planTokenView === 'cumulative'
                        ? 'bg-accent text-white'
                        : 'text-muted hover:text-ink hover:bg-surface-2',
                    ].join(' ')}
                  >
                    Cumulative
                  </button>
                </div>
                <div className="mt-4">{renderPlanTokenChart('h-[70vh]')}</div>
              </div>
            )}
            {expandedChart === 'cost' && (
              <div className="mt-4">
                <div className="flex items-center justify-end gap-3 text-xs text-muted">
                  <button
                    type="button"
                    onClick={() => setCostView('period')}
                    className={[
                      'rounded-full border border-line px-3 py-1 font-semibold transition',
                      costView === 'period'
                        ? 'bg-accent text-white'
                        : 'text-muted hover:text-ink hover:bg-surface-2',
                    ].join(' ')}
                  >
                    Period
                  </button>
                  <button
                    type="button"
                    onClick={() => setCostView('cumulative')}
                    className={[
                      'rounded-full border border-line px-3 py-1 font-semibold transition',
                      costView === 'cumulative'
                        ? 'bg-accent text-white'
                        : 'text-muted hover:text-ink hover:bg-surface-2',
                    ].join(' ')}
                  >
                    Cumulative
                  </button>
                </div>
                <div className="mt-4">{renderCostChart('h-[70vh]')}</div>
              </div>
            )}
            {expandedChart === 'requests' && (
              <div className="mt-4">{renderRequestChart('h-[70vh]')}</div>
            )}
            {expandedChart === 'topUserUsage' && (
              <div className="mt-4">
                <div className="flex items-center justify-end gap-3 text-xs text-muted">
                  <button
                    type="button"
                    onClick={() => setUserTokenView('period')}
                    className={[
                      'rounded-full border border-line px-3 py-1 font-semibold transition',
                      userTokenView === 'period'
                        ? 'bg-accent text-white'
                        : 'text-muted hover:text-ink hover:bg-surface-2',
                    ].join(' ')}
                  >
                    Period
                  </button>
                  <button
                    type="button"
                    onClick={() => setUserTokenView('cumulative')}
                    className={[
                      'rounded-full border border-line px-3 py-1 font-semibold transition',
                      userTokenView === 'cumulative'
                        ? 'bg-accent text-white'
                        : 'text-muted hover:text-ink hover:bg-surface-2',
                    ].join(' ')}
                  >
                    Cumulative
                  </button>
                </div>
                <div className="mt-4">{renderTopUserUsageChart('h-[70vh]')}</div>
              </div>
            )}
            {expandedChart === 'modelMix' && (
              <div className="mt-4">{renderModelMixChart('h-[70vh]')}</div>
            )}
            {expandedChart === 'ranking' && (
              <div className="mt-4 max-h-[70vh] overflow-y-auto space-y-3">
                {topUsers.length === 0 && (
                  <div className="rounded-xl border border-line bg-surface-2 px-4 py-3 text-sm text-muted">
                    No usage data in this range.
                  </div>
                )}
                {topUsers.map((user) => (
                  <Link
                    key={user.user_id}
                    to={`/users/${user.user_id}`}
                    className="block rounded-xl border border-transparent px-3 py-3 transition hover:border-line hover:bg-surface-2"
                    onClick={() => setExpandedChart(null)}
                  >
                    <div className="flex items-center justify-between text-sm font-semibold text-ink">
                      <span className="flex items-center gap-2">
                        <span
                          className="h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: userColorMap.get(user.user_id) || '#2563eb' }}
                        />
                        {user.name}
                      </span>
                      <span>{formatCompact(user.total_tokens)}</span>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-surface-2">
                      <div
                        className="h-2 rounded-full"
                        style={{
                          width: `${(user.total_tokens / topUserMaxTokens) * 100}%`,
                          backgroundColor: userColorMap.get(user.user_id) || '#2563eb',
                        }}
                      />
                    </div>
                    <div className="mt-2 text-xs text-muted">
                      {formatNumber(user.total_requests)} requests
                    </div>
                  </Link>
                ))}
              </div>
            )}
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

function formatBucketLabel(date: Date, bucketType: 'minute' | 'hour' | 'day' | 'week' | 'month') {
  if (bucketType === 'minute' || bucketType === 'hour') {
    return formatKstTime(date);
  }
  return formatKstDateShort(date);
}

function formatKstDateShort(date: Date) {
  return date.toLocaleDateString('en-US', {
    timeZone: KST_TIME_ZONE,
    month: 'short',
    day: 'numeric',
  });
}

function formatKstTime(date: Date) {
  return date.toLocaleTimeString('en-US', {
    timeZone: KST_TIME_ZONE,
    hour: '2-digit',
    minute: '2-digit',
  });
}
