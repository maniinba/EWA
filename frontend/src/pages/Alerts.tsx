import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { Alert, AlertFilters, Severity, AlertStatus } from '../services/types';
import { errorMessage, fetchAlerts } from '../services/api';
import { useSystems } from '../hooks/useSystems';
import { Card } from '../components/Card';
import { Table, Th, Td, EmptyRow } from '../components/Table';
import { SeverityPill, StatusPill } from '../components/pills';
import { Spinner } from '../components/Spinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { AlertDetailDrawer } from '../components/AlertDetailDrawer';

const SEVERITIES: Severity[] = ['red', 'yellow', 'green', 'gray'];
const STATUSES: AlertStatus[] = ['open', 'in_progress', 'resolved', 'deferred'];

export function Alerts() {
  const { systems } = useSystems();
  const [searchParams, setSearchParams] = useSearchParams();

  const [systemId, setSystemId] = useState<string>(searchParams.get('system_id') ?? '');
  const [severity, setSeverity] = useState<string>(searchParams.get('severity') ?? '');
  const [status, setStatus] = useState<string>(searchParams.get('status') ?? '');
  const [chapter, setChapter] = useState<string>(searchParams.get('chapter') ?? '');
  const [tag, setTag] = useState<string>(searchParams.get('tag') ?? '');

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const filters: AlertFilters = { limit: 200 };
    if (systemId) filters.system_id = Number(systemId);
    if (severity) filters.severity = severity as Severity;
    if (status) filters.status = status as AlertStatus;
    if (chapter) filters.chapter = chapter;
    if (tag) filters.tag = tag;
    try {
      const data = await fetchAlerts(filters);
      setAlerts(data);
    } catch (err) {
      setError(errorMessage(err, 'Failed to load alerts'));
    } finally {
      setLoading(false);
    }
  }, [systemId, severity, status, chapter, tag]);

  useEffect(() => {
    void load();
  }, [load]);

  // Keep URL in sync (so filters are shareable / survive reload).
  useEffect(() => {
    const params: Record<string, string> = {};
    if (systemId) params.system_id = systemId;
    if (severity) params.severity = severity;
    if (status) params.status = status;
    if (chapter) params.chapter = chapter;
    if (tag) params.tag = tag;
    setSearchParams(params, { replace: true });
  }, [systemId, severity, status, chapter, tag, setSearchParams]);

  const clearFilters = () => {
    setSystemId('');
    setSeverity('');
    setStatus('');
    setChapter('');
    setTag('');
  };

  const onAlertUpdated = (updated: Alert) => {
    setAlerts((prev) => prev.map((a) => (a.id === updated.id ? { ...a, ...updated } : a)));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Alerts</h1>
        <p className="text-sm text-gray-500">Filter and triage alerts across all systems.</p>
      </div>

      <Card title="Filters">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div>
            <label className="label" htmlFor="f-system">
              System
            </label>
            <select
              id="f-system"
              className="input"
              value={systemId}
              onChange={(e) => setSystemId(e.target.value)}
            >
              <option value="">All systems</option>
              {systems.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.sid}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="f-severity">
              Severity
            </label>
            <select
              id="f-severity"
              className="input"
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
            >
              <option value="">All</option>
              {SEVERITIES.map((s) => (
                <option key={s} value={s} className="capitalize">
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="f-status">
              Status
            </label>
            <select
              id="f-status"
              className="input"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="">All</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="f-chapter">
              Chapter
            </label>
            <input
              id="f-chapter"
              className="input"
              value={chapter}
              onChange={(e) => setChapter(e.target.value)}
              placeholder="e.g. Performance"
            />
          </div>
          <div>
            <label className="label" htmlFor="f-tag">
              Tag
            </label>
            <input
              id="f-tag"
              className="input"
              value={tag}
              onChange={(e) => setTag(e.target.value)}
              placeholder="e.g. hana"
            />
          </div>
        </div>
        <div className="mt-3 flex justify-end">
          <button type="button" className="btn-secondary" onClick={clearFilters}>
            Clear filters
          </button>
        </div>
      </Card>

      <Card
        title={`Results${!loading ? ` (${alerts.length})` : ''}`}
        bodyClassName="p-0"
      >
        {loading ? (
          <Spinner label="Loading alerts…" />
        ) : error ? (
          <div className="p-5">
            <ErrorMessage message={error} />
          </div>
        ) : (
          <Table>
            <thead className="bg-gray-50">
              <tr>
                <Th>Severity</Th>
                <Th>Title</Th>
                <Th>System</Th>
                <Th>Chapter</Th>
                <Th>Tags</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {alerts.length === 0 && (
                <EmptyRow colSpan={6} message="No alerts match these filters." />
              )}
              {alerts.map((a) => (
                <tr
                  key={a.id}
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => setSelectedAlert(a.id)}
                >
                  <Td>
                    <SeverityPill severity={a.severity} />
                  </Td>
                  <Td className="max-w-xs">
                    <span className="block truncate font-medium text-gray-800">{a.title}</span>
                  </Td>
                  <Td className="font-mono text-xs">{a.system_sid}</Td>
                  <Td>{a.chapter}</Td>
                  <Td>
                    <div className="flex max-w-[16rem] flex-wrap gap-1">
                      {a.tags.slice(0, 3).map((t) => (
                        <span
                          key={t}
                          className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600"
                        >
                          {t}
                        </span>
                      ))}
                      {a.tags.length > 3 && (
                        <span className="text-[11px] text-gray-400">+{a.tags.length - 3}</span>
                      )}
                    </div>
                  </Td>
                  <Td>
                    <StatusPill status={a.status} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <AlertDetailDrawer
        alertId={selectedAlert}
        onClose={() => setSelectedAlert(null)}
        onUpdated={onAlertUpdated}
        onSelectAlert={(id) => setSelectedAlert(id)}
      />
    </div>
  );
}
