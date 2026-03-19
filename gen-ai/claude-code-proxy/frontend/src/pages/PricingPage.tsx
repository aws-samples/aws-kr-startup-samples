import { type ReactNode, useEffect, useMemo, useState } from 'react';
import PageHeader from '@/components/PageHeader';
import { api, ModelPricingCatalog, ModelSlot } from '@/lib/api';

const inputClass =
  'w-full rounded-xl border border-line bg-surface px-4 py-2 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20';

type PricingForm = {
  provider: 'bedrock' | 'plan';
  region: string;
  model_id: string;
  input_price_per_million: string;
  output_price_per_million: string;
  cache_write_price_per_million: string;
  cache_write_1h_price_per_million: string;
  cache_read_price_per_million: string;
  effective_date: string;
};

const emptyForm: PricingForm = {
  provider: 'bedrock',
  region: 'ap-northeast-2',
  model_id: '',
  input_price_per_million: '',
  output_price_per_million: '',
  cache_write_price_per_million: '',
  cache_write_1h_price_per_million: '',
  cache_read_price_per_million: '',
  effective_date: '2025-01-01',
};

export default function PricingPage() {
  const [entries, setEntries] = useState<ModelPricingCatalog[]>([]);
  const [slots, setSlots] = useState<ModelSlot[]>([]);
  const [providerFilter, setProviderFilter] = useState<'bedrock' | 'plan'>('bedrock');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [editingEntry, setEditingEntry] = useState<ModelPricingCatalog | null>(null);

  useEffect(() => {
    void loadData(providerFilter);
  }, [providerFilter]);

  const loadData = async (provider: 'bedrock' | 'plan') => {
    setIsLoading(true);
    try {
      const [pricingResponse, slotResponse] = await Promise.all([
        api.getPricingCatalog({ provider }),
        api.getModelSlots(),
      ]);
      setEntries(pricingResponse);
      setSlots(slotResponse);
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail;
      setError(detail || 'Failed to load pricing catalog.');
    } finally {
      setIsLoading(false);
    }
  };

  const activeSlotModels = useMemo(
    () => new Set(slots.map((slot) => slot.bedrock_model_id)),
    [slots]
  );

  const resetForm = () => {
    setForm({
      ...emptyForm,
      provider: providerFilter,
      region: providerFilter === 'plan' ? 'global' : 'ap-northeast-2',
    });
    setEditingEntry(null);
    setShowCreate(false);
    setError('');
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await api.createPricingCatalogEntry(form);
      setEntries((prev) => [...prev, created].sort(sortEntries));
      resetForm();
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail;
      setError(detail || 'Failed to create pricing entry.');
    }
  };

  const handleEdit = (entry: ModelPricingCatalog) => {
    setEditingEntry(entry);
    setShowCreate(false);
    setForm({
      provider: entry.provider,
      region: entry.region,
      model_id: entry.model_id,
      input_price_per_million: entry.input_price_per_million,
      output_price_per_million: entry.output_price_per_million,
      cache_write_price_per_million: entry.cache_write_price_per_million,
      cache_write_1h_price_per_million: entry.cache_write_1h_price_per_million,
      cache_read_price_per_million: entry.cache_read_price_per_million,
      effective_date: entry.effective_date,
    });
    setError('');
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingEntry) return;
    try {
      const updated = await api.updatePricingCatalogEntry(editingEntry.id, form);
      setEntries((prev) => prev.map((item) => (item.id === updated.id ? updated : item)).sort(sortEntries));
      resetForm();
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail;
      setError(detail || 'Failed to update pricing entry.');
    }
  };

  const handleDelete = async (entry: ModelPricingCatalog) => {
    if (!window.confirm(`Delete pricing entry for ${entry.model_id}?`)) return;
    try {
      await api.deletePricingCatalogEntry(entry.id);
      setEntries((prev) => prev.filter((item) => item.id !== entry.id));
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail;
      setError(detail || 'Failed to delete pricing entry.');
    }
  };

  const isBedrockEntryInUse = (entry: ModelPricingCatalog) =>
    entry.provider === 'bedrock' && activeSlotModels.has(entry.model_id);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Admin"
        title="Pricing"
        subtitle="Manage exact model ID pricing used for cost calculation."
        actions={
          <div className="flex items-center gap-3">
            <select
              value={providerFilter}
              onChange={(e) => {
                const next = e.target.value as 'bedrock' | 'plan';
                setProviderFilter(next);
                resetForm();
              }}
              className="rounded-full border border-line bg-surface px-4 py-2 text-sm font-semibold text-ink"
            >
              <option value="bedrock">Bedrock</option>
              <option value="plan">Plan</option>
            </select>
            <button
              type="button"
              onClick={() => {
                setShowCreate((prev) => !prev);
                setEditingEntry(null);
                setForm({
                  ...emptyForm,
                  provider: providerFilter,
                  region: providerFilter === 'plan' ? 'global' : 'ap-northeast-2',
                });
                setError('');
              }}
              className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white shadow-soft transition hover:bg-accent-strong"
            >
              {showCreate ? 'Close' : 'New Pricing'}
            </button>
          </div>
        }
      />

      {(showCreate || editingEntry) && (
        <form
          onSubmit={editingEntry ? handleUpdate : handleCreate}
          className="rounded-2xl border border-line bg-surface-2 p-6 shadow-soft"
        >
          <div className="mb-4 text-sm text-muted">
            {editingEntry ? 'Editing pricing entry' : 'Create pricing entry'}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <FormField label="Provider">
              <select
                value={form.provider}
                onChange={(e) => setForm((prev) => ({ ...prev, provider: e.target.value as 'bedrock' | 'plan' }))}
                className={inputClass}
              >
                <option value="bedrock">bedrock</option>
                <option value="plan">plan</option>
              </select>
            </FormField>
            <FormField label="Region">
              <input
                type="text"
                value={form.region}
                onChange={(e) => setForm((prev) => ({ ...prev, region: e.target.value }))}
                className={inputClass}
              />
            </FormField>
            <FormField label="Model ID">
              <input
                type="text"
                value={form.model_id}
                onChange={(e) => setForm((prev) => ({ ...prev, model_id: e.target.value }))}
                className={inputClass}
              />
            </FormField>
            <FormField label="Effective Date">
              <input
                type="date"
                value={form.effective_date}
                onChange={(e) => setForm((prev) => ({ ...prev, effective_date: e.target.value }))}
                className={inputClass}
              />
            </FormField>
            <FormField label="Input / 1M">
              <input
                type="text"
                value={form.input_price_per_million}
                onChange={(e) => setForm((prev) => ({ ...prev, input_price_per_million: e.target.value }))}
                className={inputClass}
              />
            </FormField>
            <FormField label="Output / 1M">
              <input
                type="text"
                value={form.output_price_per_million}
                onChange={(e) => setForm((prev) => ({ ...prev, output_price_per_million: e.target.value }))}
                className={inputClass}
              />
            </FormField>
            <FormField label="Cache Write / 1M">
              <input
                type="text"
                value={form.cache_write_price_per_million}
                onChange={(e) => setForm((prev) => ({ ...prev, cache_write_price_per_million: e.target.value }))}
                className={inputClass}
              />
            </FormField>
            <FormField label="Cache Write 1h / 1M">
              <input
                type="text"
                value={form.cache_write_1h_price_per_million}
                onChange={(e) => setForm((prev) => ({ ...prev, cache_write_1h_price_per_million: e.target.value }))}
                className={inputClass}
              />
            </FormField>
            <FormField label="Cache Read / 1M">
              <input
                type="text"
                value={form.cache_read_price_per_million}
                onChange={(e) => setForm((prev) => ({ ...prev, cache_read_price_per_million: e.target.value }))}
                className={inputClass}
              />
            </FormField>
          </div>
          <div className="mt-4 flex gap-3">
            <button
              type="submit"
              className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-black"
            >
              {editingEntry ? 'Update' : 'Create'}
            </button>
            <button
              type="button"
              onClick={resetForm}
              className="rounded-full border border-line px-4 py-2 text-sm font-semibold text-ink transition hover:bg-surface"
            >
              Cancel
            </button>
          </div>
          {error && <div className="mt-3 text-sm text-danger">{error}</div>}
        </form>
      )}

      <div className="rounded-2xl border border-line bg-surface shadow-soft">
        <div className="border-b border-line px-6 py-4 text-sm font-semibold text-ink">
          {isLoading ? 'Loading pricing...' : `${entries.length} pricing rows`}
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-[0.2em] text-muted">
              <th className="px-6 py-3">Model ID</th>
              <th className="px-6 py-3">Region</th>
              <th className="px-6 py-3">Input</th>
              <th className="px-6 py-3">Output</th>
              <th className="px-6 py-3">Cache 5m</th>
              <th className="px-6 py-3">Cache 1h</th>
              <th className="px-6 py-3">Updated</th>
              <th className="px-6 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.id} className="border-t border-line/60 hover:bg-surface-2">
                <td className="px-6 py-4">
                  <div className="font-mono text-xs text-ink">{entry.model_id}</div>
                  {isBedrockEntryInUse(entry) && (
                    <div className="mt-2 inline-flex rounded-full bg-accent/10 px-2 py-1 text-[11px] font-semibold text-accent">
                      In use by slot
                    </div>
                  )}
                </td>
                <td className="px-6 py-4 text-muted">{entry.region}</td>
                <td className="px-6 py-4 text-muted">{entry.input_price_per_million}</td>
                <td className="px-6 py-4 text-muted">{entry.output_price_per_million}</td>
                <td className="px-6 py-4 text-muted">{entry.cache_write_price_per_million}</td>
                <td className="px-6 py-4 text-muted">{entry.cache_write_1h_price_per_million}</td>
                <td className="px-6 py-4 text-muted">{formatDate(entry.updated_at)}</td>
                <td className="px-6 py-4 text-right">
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => handleEdit(entry)}
                      className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-ink transition hover:bg-surface"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(entry)}
                      className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-danger transition hover:bg-surface"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FormField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
        {label}
      </label>
      <div className="mt-2">{children}</div>
    </div>
  );
}

function sortEntries(a: ModelPricingCatalog, b: ModelPricingCatalog) {
  return `${a.provider}:${a.region}:${a.model_id}`.localeCompare(`${b.provider}:${b.region}:${b.model_id}`);
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
