import { useEffect, useState } from 'react';
import PageHeader from '@/components/PageHeader';
import { api, ModelMapping } from '@/lib/api';

const inputClass =
  'w-full rounded-xl border border-line bg-surface px-4 py-2 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20';

export default function ModelsPage() {
  const [mappings, setMappings] = useState<ModelMapping[]>([]);
  const [claudeModel, setClaudeModel] = useState('');
  const [bedrockModel, setBedrockModel] = useState('');
  const [description, setDescription] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [deletingMappings, setDeletingMappings] = useState<Record<string, boolean>>({});
  const [editingMapping, setEditingMapping] = useState<ModelMapping | null>(null);

  useEffect(() => {
    loadMappings();
  }, []);

  const loadMappings = async () => {
    setIsLoading(true);
    try {
      const response = await api.getModelMappings(false);
      setMappings(response);
    } catch {
      // silently fail
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!claudeModel.trim() || !bedrockModel.trim()) {
      setError('Claude model and Bedrock model are required.');
      return;
    }
    setError('');
    try {
      const mapping = await api.createModelMapping({
        claude_model: claudeModel,
        bedrock_model: bedrockModel,
        description: description || undefined,
        is_active: true,
      });
      setMappings((prev) => [mapping, ...prev]);
      setClaudeModel('');
      setBedrockModel('');
      setDescription('');
      setShowForm(false);
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail;
      setError(detail || 'Failed to create mapping.');
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingMapping) return;
    if (!bedrockModel.trim()) {
      setError('Bedrock model is required.');
      return;
    }
    setError('');
    try {
      const updated = await api.updateModelMapping(editingMapping.id, {
        bedrock_model: bedrockModel,
        description: description || undefined,
      });
      setMappings((prev) =>
        prev.map((m) => (m.id === updated.id ? updated : m))
      );
      setEditingMapping(null);
      setBedrockModel('');
      setDescription('');
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail;
      setError(detail || 'Failed to update mapping.');
    }
  };

  const handleDelete = async (mapping: ModelMapping) => {
    if (deletingMappings[mapping.id]) return;
    const confirmed = window.confirm(
      `Delete mapping for ${mapping.claude_model}?`
    );
    if (!confirmed) return;
    setDeleteError('');
    setDeletingMappings((prev) => ({ ...prev, [mapping.id]: true }));
    try {
      await api.deleteModelMapping(mapping.id);
      setMappings((prev) => prev.filter((item) => item.id !== mapping.id));
    } catch {
      setDeleteError('Failed to delete mapping.');
    } finally {
      setDeletingMappings((prev) => {
        if (!(mapping.id in prev)) return prev;
        const next = { ...prev };
        delete next[mapping.id];
        return next;
      });
    }
  };

  const handleEdit = (mapping: ModelMapping) => {
    setEditingMapping(mapping);
    setBedrockModel(mapping.bedrock_model);
    setDescription(mapping.description || '');
    setShowForm(false);
    setError('');
  };

  const handleCancelEdit = () => {
    setEditingMapping(null);
    setBedrockModel('');
    setDescription('');
    setError('');
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Admin"
        title="Model Mappings"
        subtitle="Map Claude Code model names to Bedrock model IDs for dynamic fallback."
        actions={
          <button
            type="button"
            onClick={() => {
              setShowForm((prev) => {
                if (prev) {
                  setClaudeModel('');
                  setBedrockModel('');
                  setDescription('');
                }
                return !prev;
              });
              setEditingMapping(null);
              setError('');
            }}
            className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white shadow-soft transition hover:bg-accent-strong"
          >
            {showForm ? 'Close' : 'New Mapping'}
          </button>
        }
      />

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="rounded-2xl border border-line bg-surface p-6 shadow-soft"
        >
          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.5fr)_auto] md:items-end">
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
                Claude Model
              </label>
              <input
                type="text"
                placeholder="claude-opus-5-0-..."
                value={claudeModel}
                onChange={(e) => setClaudeModel(e.target.value)}
                className={`${inputClass} mt-2`}
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
                Bedrock Model ID
              </label>
              <input
                type="text"
                placeholder="global.anthropic.claude-..."
                value={bedrockModel}
                onChange={(e) => setBedrockModel(e.target.value)}
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
                  setClaudeModel('');
                  setBedrockModel('');
                  setDescription('');
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

      {editingMapping && (
        <form
          onSubmit={handleUpdate}
          className="rounded-2xl border border-line bg-surface-2 p-6 shadow-soft"
        >
          <div className="mb-4 text-sm text-muted">
            Editing: <span className="font-semibold text-ink">{editingMapping.claude_model}</span>
          </div>
          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)_auto] md:items-end">
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
                Bedrock Model ID
              </label>
              <input
                type="text"
                placeholder="global.anthropic.claude-..."
                value={bedrockModel}
                onChange={(e) => setBedrockModel(e.target.value)}
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
            <div className="flex gap-3">
              <button
                type="submit"
                className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-black"
              >
                Update
              </button>
              <button
                type="button"
                onClick={handleCancelEdit}
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
          {isLoading ? 'Loading mappings...' : `${mappings.length} mappings`}
        </div>
        {deleteError && (
          <div className="px-6 pb-4 text-sm text-danger">{deleteError}</div>
        )}
        {mappings.length === 0 && !isLoading ? (
          <div className="px-6 py-12 text-center text-sm text-muted">
            No model mappings yet. Create your first mapping to get started.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-[0.2em] text-muted">
                <th className="px-6 py-3">Claude Model</th>
                <th className="px-6 py-3">Bedrock Model ID</th>
                <th className="px-6 py-3">Description</th>
                <th className="px-6 py-3">Updated</th>
                <th className="px-6 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {mappings.map((mapping) => {
                const isDeleting = Boolean(deletingMappings[mapping.id]);
                return (
                  <tr key={mapping.id} className="border-t border-line/60 hover:bg-surface-2">
                    <td className="px-6 py-4">
                      <div className="font-semibold text-ink">{mapping.claude_model}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-mono text-xs text-ink">{mapping.bedrock_model}</div>
                    </td>
                    <td className="px-6 py-4 text-muted">
                      {mapping.description || '-'}
                    </td>
                    <td className="px-6 py-4 text-muted">
                      {formatDate(mapping.updated_at)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => handleEdit(mapping)}
                          className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-ink transition hover:bg-surface"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(mapping)}
                          disabled={isDeleting}
                          className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-danger transition hover:bg-surface disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {isDeleting ? 'Deleting...' : 'Delete'}
                        </button>
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
