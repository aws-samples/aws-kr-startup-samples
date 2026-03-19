import { useEffect, useMemo, useState } from 'react';
import PageHeader from '@/components/PageHeader';
import { api, ModelPricingCatalog, ModelSlot } from '@/lib/api';

const inputClass =
  'w-full rounded-xl border border-line bg-surface px-4 py-2 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20';

const slotLabels: Record<ModelSlot['slot'], string> = {
  opus: 'Opus',
  sonnet: 'Sonnet',
  haiku: 'Haiku',
};

export default function ModelsPage() {
  const [slots, setSlots] = useState<ModelSlot[]>([]);
  const [pricing, setPricing] = useState<ModelPricingCatalog[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [editingSlot, setEditingSlot] = useState<ModelSlot | null>(null);
  const [bedrockModelId, setBedrockModelId] = useState('');

  useEffect(() => {
    void loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [slotResponse, pricingResponse] = await Promise.all([
        api.getModelSlots(),
        api.getPricingCatalog({ provider: 'bedrock' }),
      ]);
      setSlots(slotResponse);
      setPricing(pricingResponse);
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail;
      setError(detail || 'Failed to load model slots.');
    } finally {
      setIsLoading(false);
    }
  };

  const pricingModels = useMemo(
    () => new Set(pricing.filter((item) => item.is_active).map((item) => item.model_id)),
    [pricing]
  );

  const handleEdit = (slot: ModelSlot) => {
    setEditingSlot(slot);
    setBedrockModelId(slot.bedrock_model_id);
    setError('');
  };

  const handleCancel = () => {
    setEditingSlot(null);
    setBedrockModelId('');
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingSlot) return;
    if (!bedrockModelId.trim()) {
      setError('Bedrock model ID is required.');
      return;
    }

    try {
      const updated = await api.updateModelSlot(editingSlot.slot, {
        bedrock_model_id: bedrockModelId.trim(),
      });
      setSlots((prev) => prev.map((slot) => (slot.id === updated.id ? updated : slot)));
      handleCancel();
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail;
      setError(detail || 'Failed to update model slot.');
    }
  };

  const hasPricingMatch = bedrockModelId ? pricingModels.has(bedrockModelId.trim()) : true;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Admin"
        title="Models"
        subtitle="Manage the three standard Bedrock model slots used by the proxy."
      />

      {editingSlot && (
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-line bg-surface-2 p-6 shadow-soft"
        >
          <div className="mb-4 text-sm text-muted">
            Editing:{' '}
            <span className="font-semibold text-ink">{slotLabels[editingSlot.slot]}</span>
          </div>
          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
                Bedrock Model ID
              </label>
              <input
                type="text"
                value={bedrockModelId}
                onChange={(e) => setBedrockModelId(e.target.value)}
                className={`${inputClass} mt-2`}
                placeholder="global.anthropic.claude-sonnet-4-6"
              />
              {!hasPricingMatch && (
                <div className="mt-2 text-sm text-amber-700">
                  No active bedrock pricing row matches this model ID. Save is allowed, but pricing
                  must be added on the Pricing page.
                </div>
              )}
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-black"
              >
                Update
              </button>
              <button
                type="button"
                onClick={handleCancel}
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
          {isLoading ? 'Loading model slots...' : '3 standard slots'}
        </div>
        {!isLoading && slots.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-muted">
            Model slots are missing. Run the latest migration and refresh this page.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-[0.2em] text-muted">
                <th className="px-6 py-3">Slot</th>
                <th className="px-6 py-3">Bedrock Model ID</th>
                <th className="px-6 py-3">Updated</th>
                <th className="px-6 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {slots.map((slot) => (
                <tr key={slot.id} className="border-t border-line/60 hover:bg-surface-2">
                  <td className="px-6 py-4">
                    <div className="font-semibold text-ink">{slotLabels[slot.slot]}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="font-mono text-xs text-ink">{slot.bedrock_model_id}</div>
                    {!pricingModels.has(slot.bedrock_model_id) && (
                      <div className="mt-2 inline-flex rounded-full bg-amber-100 px-2 py-1 text-[11px] font-semibold text-amber-800">
                        Missing pricing
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 text-muted">{formatDate(slot.updated_at)}</td>
                  <td className="px-6 py-4 text-right">
                    <button
                      type="button"
                      onClick={() => handleEdit(slot)}
                      className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-ink transition hover:bg-surface"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
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
