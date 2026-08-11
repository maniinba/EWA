import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { Alert } from '../services/types';
import { errorMessage, search } from '../services/api';
import { Card } from '../components/Card';
import { Table, Th, Td, EmptyRow } from '../components/Table';
import { SeverityPill, StatusPill } from '../components/pills';
import { Spinner } from '../components/Spinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { AlertDetailDrawer } from '../components/AlertDetailDrawer';

export function SearchResults() {
  const [searchParams] = useSearchParams();
  const q = searchParams.get('q') ?? '';

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<number | null>(null);

  useEffect(() => {
    if (!q) {
      setAlerts([]);
      setTotal(0);
      return;
    }
    let active = true;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const res = await search(q);
        if (!active) return;
        setAlerts(res.alerts);
        setTotal(res.total);
      } catch (err) {
        if (active) setError(errorMessage(err, 'Search failed'));
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [q]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Search</h1>
        <p className="text-sm text-gray-500">
          {q ? (
            <>
              Results for <span className="font-medium text-gray-700">“{q}”</span>
              {!loading && ` — ${total} match${total === 1 ? '' : 'es'}`}
            </>
          ) : (
            'Type a query in the top search bar.'
          )}
        </p>
      </div>

      {loading && <Spinner label="Searching…" />}
      <ErrorMessage message={error} />

      {q && !loading && !error && (
        <Card bodyClassName="p-0">
          <Table>
            <thead className="bg-gray-50">
              <tr>
                <Th>Severity</Th>
                <Th>Title</Th>
                <Th>System</Th>
                <Th>Chapter</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {alerts.length === 0 && <EmptyRow colSpan={5} message="No alerts matched." />}
              {alerts.map((a) => (
                <tr
                  key={a.id}
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => setSelectedAlert(a.id)}
                >
                  <Td>
                    <SeverityPill severity={a.severity} />
                  </Td>
                  <Td className="max-w-md">
                    <span className="block truncate font-medium text-gray-800">{a.title}</span>
                    {a.description && (
                      <span className="block truncate text-xs text-gray-400">{a.description}</span>
                    )}
                  </Td>
                  <Td className="font-mono text-xs">{a.system_sid}</Td>
                  <Td>{a.chapter}</Td>
                  <Td>
                    <StatusPill status={a.status} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      )}

      <AlertDetailDrawer
        alertId={selectedAlert}
        onClose={() => setSelectedAlert(null)}
        onSelectAlert={(id) => setSelectedAlert(id)}
      />
    </div>
  );
}
