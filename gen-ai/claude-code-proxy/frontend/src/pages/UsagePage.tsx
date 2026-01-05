import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, UsageResponse, UsageTopUser, User } from '@/lib/api';
import {
  formatKstDateTime,
  resolveCustomRange,
  resolvePeriodRange,
  selectBucketType,
  UsagePeriod,
} from '@/lib/usageRange';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

type RangePreset = UsagePeriod | 'custom';

const RANGE_PRESETS: { key: RangePreset; label: string }[] = [
  { key: 'day', label: 'Day' },
  { key: 'week', label: 'Week' },
  { key: 'month', label: 'Month' },
  { key: 'custom', label: 'Custom' },
];

export default function UsagePage() {
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [userUsage, setUserUsage] = useState<UsageResponse | null>(null);
  const [topUsers, setTopUsers] = useState<UsageTopUser[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [rangePreset, setRangePreset] = useState<RangePreset>('week');
  const [customRange, setCustomRange] = useState({ start: '', end: '' });

  const range = useMemo(() => {
    if (rangePreset === 'custom') {
      if (!customRange.start || !customRange.end) return null;
      return resolveCustomRange(customRange.start, customRange.end);
    }
    return resolvePeriodRange(rangePreset);
  }, [customRange.end, customRange.start, rangePreset]);

  const bucketType = useMemo(() => {
    if (!range) return 'day';
    return selectBucketType(range.rangeDays);
  }, [range]);

  useEffect(() => {
    api.getUsers().then(setUsers).catch(() => {});
  }, []);

  useEffect(() => {
    if (!range) return;

    const usageParams = {
      bucket_type: bucketType,
      ...(rangePreset === 'custom'
        ? { start_date: range.startDate, end_date: range.endDate }
        : { period: rangePreset }),
    };

    const topUsersParams = {
      bucket_type: bucketType,
      start_time: range.startTime.toISOString(),
      end_time: range.endTime.toISOString(),
      limit: 8,
    };

    api.getUsage(usageParams).then(setUsage).catch(() => {});
    api.getTopUsers(topUsersParams).then(setTopUsers).catch(() => {});

    if (selectedUserId) {
      api.getUsage({ ...usageParams, user_id: selectedUserId })
        .then(setUserUsage)
        .catch(() => {});
    } else {
      setUserUsage(null);
    }
  }, [bucketType, range, rangePreset, selectedUserId]);

  const chartData =
    usage?.buckets.map((b) => ({
      time: formatKstDateTime(new Date(b.bucket_start)),
      tokens: b.total_tokens,
      requests: b.requests,
      inputTokens: b.input_tokens,
      outputTokens: b.output_tokens,
    })) || [];

  const userChartData =
    userUsage?.buckets.map((b) => ({
      time: formatKstDateTime(new Date(b.bucket_start)),
      tokens: b.total_tokens,
      requests: b.requests,
    })) || [];

  const topUserMaxTokens = Math.max(...topUsers.map((u) => u.total_tokens), 1);
  const selectedUser = users.find((user) => user.id === selectedUserId);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Usage Dashboard</h1>
          <p className="text-gray-500 text-sm">전체 사용량 트렌드와 사용자별 분포를 한 번에 확인하세요.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="inline-flex flex-wrap rounded-full border border-gray-200 bg-white p-1 shadow-sm">
            {RANGE_PRESETS.map((preset) => (
              <button
                key={preset.key}
                type="button"
                onClick={() => setRangePreset(preset.key)}
                className={`px-4 py-1.5 text-sm font-semibold rounded-full transition ${
                  rangePreset === preset.key
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>
          <Link to="/users" className="text-blue-600 text-sm font-semibold">
            ← Back to Users
          </Link>
        </div>
      </div>

      {rangePreset === 'custom' && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
          <div className="text-sm text-gray-600 font-semibold">Custom Range</div>
          <input
            type="date"
            value={customRange.start}
            onChange={(e) => setCustomRange((prev) => ({ ...prev, start: e.target.value }))}
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
          />
          <span className="text-gray-400 text-sm">to</span>
          <input
            type="date"
            value={customRange.end}
            onChange={(e) => setCustomRange((prev) => ({ ...prev, end: e.target.value }))}
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
          />
          <div className="text-xs text-gray-500">KST (UTC+9) inclusive range</div>
        </div>
      )}

      {usage && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard label="Total Tokens" value={usage.total_tokens} />
            <MetricCard label="Total Requests" value={usage.total_requests} />
            <MetricCard label="Input Tokens" value={usage.total_input_tokens} />
            <MetricCard label="Output Tokens" value={usage.total_output_tokens} />
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 lg:col-span-2">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold">전체 토큰 추세</h2>
                <div className="text-xs text-gray-500 font-semibold">Bucket: {bucketType}</div>
              </div>
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="tokensGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563eb" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Area type="monotone" dataKey="tokens" stroke="#2563eb" fill="url(#tokensGradient)" />
                  <Line type="monotone" dataKey="requests" stroke="#0f172a" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
              <h2 className="text-lg font-bold mb-4">Top Users</h2>
              <div className="space-y-4">
                {topUsers.length === 0 && (
                  <div className="text-sm text-gray-500">No usage data in this range.</div>
                )}
                {topUsers.map((user) => (
                  <button
                    key={user.user_id}
                    onClick={() => setSelectedUserId(user.user_id)}
                    className="w-full text-left"
                    type="button"
                  >
                    <div className="flex items-center justify-between text-sm font-semibold text-gray-700">
                      <span>{user.name}</span>
                      <span>{user.total_tokens.toLocaleString()}</span>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-gray-100">
                      <div
                        className="h-2 rounded-full bg-blue-500"
                        style={{ width: `${(user.total_tokens / topUserMaxTokens) * 100}%` }}
                      />
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      {user.total_requests} requests
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 lg:col-span-2">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold">
                  {selectedUser ? `${selectedUser.name} 사용자 추세` : '사용자별 토큰 추세'}
                </h2>
                <select
                  value={selectedUserId}
                  onChange={(e) => setSelectedUserId(e.target.value)}
                  className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
                >
                  <option value="">All users</option>
                  {users.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.name}
                    </option>
                  ))}
                </select>
              </div>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={userChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="tokens" stroke="#2563eb" strokeWidth={2} />
                  <Line type="monotone" dataKey="requests" stroke="#0f172a" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
              <h2 className="text-lg font-bold mb-4">Totals</h2>
              <div className="space-y-3 text-sm text-gray-700">
                <div className="flex justify-between">
                  <span>Requests</span>
                  <span>{usage.total_requests.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Total Tokens</span>
                  <span>{usage.total_tokens.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Input Tokens</span>
                  <span>{usage.total_input_tokens.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Output Tokens</span>
                  <span>{usage.total_output_tokens.toLocaleString()}</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100">
      <div className="text-sm text-gray-500 font-semibold">{label}</div>
      <div className="text-2xl font-bold mt-2">{value.toLocaleString()}</div>
    </div>
  );
}
