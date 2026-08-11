import { useCallback, useEffect, useState } from 'react';
import type { Alert, AlertStatus } from '../services/types';
import {
  errorMessage,
  fetchAlert,
  fetchSimilarAlerts,
  updateAlertStatus,
} from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { Drawer } from './Drawer';
import { Spinner } from './Spinner';
import { ErrorMessage } from './ErrorMessage';
import { SeverityPill, StatusPill, STATUS_LABEL } from './pills';

interface Props {
  alertId: string | null;
  onClose: () => void;
  onUpdated?: (alert: Alert) => void;
  onSelectAlert?: (id: string) => void;
}

const STATUS_OPTIONS: AlertStatus[] = ['open', 'in_progress', 'resolved', 'deferred'];

function noteUrl(ref: string): string {
  const num = ref.replace(/\D/g, '');
  return `https://me.sap.com/notes/${num || ref}`;
}

export function AlertDetailDrawer({ alertId, onClose, onUpdated, onSelectAlert }: Props) {
  const { hasRole } = useAuth();
  const canEdit = hasRole('operator');

  const [alert, setAlert] = useState<Alert | null>(null);
  const [similar, setSimilar] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [status, setStatus] = useState<AlertStatus>('open');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    setSaved(false);
    setSaveError(null);
    try {
      const [a, sim] = await Promise.all([
        fetchAlert(id),
        fetchSimilarAlerts(id).catch(() => [] as Alert[]),
      ]);
      setAlert(a);
      setStatus(a.status);
      setNotes(a.resolution_notes ?? '');
      setSimilar(sim);
    } catch (err) {
      setError(errorMessage(err, 'Failed to load alert'));
      setAlert(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (alertId != null) {
      void load(alertId);
    } else {
      setAlert(null);
      setSimilar([]);
    }
  }, [alertId, load]);

  const onSave = async () => {
    if (!alert) return;
    setSaving(true);
    setSaveError(null);
    setSaved(false);
    try {
      const updated = await updateAlertStatus(alert.id, {
        status,
        resolution_notes: notes || undefined,
      });
      setAlert(updated);
      setSaved(true);
      onUpdated?.(updated);
    } catch (err) {
      setSaveError(errorMessage(err, 'Failed to update status'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Drawer
      open={alertId != null}
      onClose={onClose}
      title={
        alert ? (
          <div className="space-y-2">
            <SeverityPill severity={alert.severity} />
            <h2 className="text-base font-semibold text-gray-900">{alert.title}</h2>
            <p className="text-xs text-gray-500">
              <span className="font-mono font-semibold">{alert.system_sid}</span> · {alert.chapter}
              {alert.report_date ? ` · ${alert.report_date}` : ''}
            </p>
          </div>
        ) : (
          <h2 className="text-base font-semibold text-gray-900">Alert</h2>
        )
      }
    >
      {loading && <Spinner label="Loading alert…" />}
      <ErrorMessage message={error} />

      {alert && !loading && (
        <div className="space-y-6">
          {alert.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {alert.tags.map((t) => (
                <span
                  key={t}
                  className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                >
                  {t}
                </span>
              ))}
            </div>
          )}

          {alert.description && (
            <section>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-400">
                Description
              </h3>
              <p className="whitespace-pre-wrap text-sm text-gray-700">{alert.description}</p>
            </section>
          )}

          {alert.recommendation && (
            <section>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-400">
                Recommendation
              </h3>
              <p className="whitespace-pre-wrap text-sm text-gray-700">{alert.recommendation}</p>
            </section>
          )}

          {alert.sap_note_refs.length > 0 && (
            <section>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-400">
                SAP Notes
              </h3>
              <div className="flex flex-wrap gap-2">
                {alert.sap_note_refs.map((ref) => (
                  <a
                    key={ref}
                    href={noteUrl(ref)}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex items-center gap-1 rounded-md border border-brand-200 bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700 hover:bg-brand-100"
                  >
                    Note {ref}
                    <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M14 5h5v5M19 5l-9 9M12 5H7a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-5" />
                    </svg>
                  </a>
                ))}
              </div>
            </section>
          )}

          <section className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
              Status
            </h3>
            {!canEdit && (
              <div className="mb-2">
                <StatusPill status={alert.status} />
                <p className="mt-2 text-xs text-gray-400">
                  You need operator access to change status.
                </p>
              </div>
            )}
            {canEdit && (
              <div className="space-y-3">
                <div>
                  <label className="label" htmlFor="status-select">
                    Status
                  </label>
                  <select
                    id="status-select"
                    className="input"
                    value={status}
                    onChange={(e) => setStatus(e.target.value as AlertStatus)}
                  >
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>
                        {STATUS_LABEL[s]}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label" htmlFor="notes">
                    Resolution notes
                  </label>
                  <textarea
                    id="notes"
                    className="input min-h-[80px]"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Optional notes about the resolution…"
                  />
                </div>
                <ErrorMessage message={saveError} />
                <div className="flex items-center gap-3">
                  <button type="button" className="btn-primary" onClick={onSave} disabled={saving}>
                    {saving ? 'Saving…' : 'Save status'}
                  </button>
                  {saved && <span className="text-xs text-green-600">Saved.</span>}
                </div>
              </div>
            )}
          </section>

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
              Similar alerts
            </h3>
            {similar.length === 0 ? (
              <p className="text-sm text-gray-400">No similar alerts found.</p>
            ) : (
              <ul className="divide-y divide-gray-100 rounded-lg border border-gray-200">
                {similar.map((s) => (
                  <li key={s.id}>
                    <button
                      type="button"
                      className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-gray-50"
                      onClick={() => onSelectAlert?.(s.id)}
                    >
                      <SeverityPill severity={s.severity} />
                      <span className="min-w-0 flex-1 truncate text-sm text-gray-700">
                        {s.title}
                      </span>
                      <span className="font-mono text-xs text-gray-400">{s.system_sid}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </Drawer>
  );
}
