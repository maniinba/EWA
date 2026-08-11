import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { createSystem, errorMessage, purgeData } from '../services/api';
import { useSystems } from '../hooks/useSystems';
import { useAuth } from '../hooks/useAuth';
import { Card } from '../components/Card';
import { Table, Th, Td, EmptyRow } from '../components/Table';
import { RatingPill } from '../components/pills';
import { ErrorMessage } from '../components/ErrorMessage';
import { Spinner } from '../components/Spinner';

export function Systems() {
  const { systems, loading, refresh } = useSystems();
  const { hasRole } = useAuth();
  const canCreate = hasRole('operator');
  const isAdmin = hasRole('admin');
  const navigate = useNavigate();

  const [purging, setPurging] = useState(false);
  const [purgeMsg, setPurgeMsg] = useState<string | null>(null);

  const onPurge = async () => {
    if (
      !window.confirm(
        'Delete ALL systems, reports, alerts and rating history? Users are kept. This cannot be undone.',
      )
    )
      return;
    setPurging(true);
    setPurgeMsg(null);
    try {
      const res = await purgeData();
      const d = res.deleted;
      setPurgeMsg(
        `Cleared ${d.systems} systems, ${d.reports} reports, ${d.alerts} alerts.`,
      );
      await refresh();
    } catch (err) {
      setPurgeMsg(errorMessage(err, 'Failed to clear data'));
    } finally {
      setPurging(false);
    }
  };

  const [sid, setSid] = useState('');
  const [description, setDescription] = useState('');
  const [systemType, setSystemType] = useState('');
  const [landscape, setLandscape] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      await createSystem({
        sid: sid.trim().toUpperCase(),
        description: description.trim() || undefined,
        system_type: systemType.trim() || undefined,
        landscape: landscape.trim() || undefined,
      });
      setSuccess(`System ${sid.trim().toUpperCase()} registered.`);
      setSid('');
      setDescription('');
      setSystemType('');
      setLandscape('');
      await refresh();
    } catch (err) {
      setError(errorMessage(err, 'Failed to register system'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Systems</h1>
        <p className="text-sm text-gray-500">Registered SAP systems and their alert stats.</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card title="All systems" bodyClassName="p-0">
            {loading ? (
              <Spinner label="Loading systems…" />
            ) : (
              <Table>
                <thead className="bg-gray-50">
                  <tr>
                    <Th>SID</Th>
                    <Th>Type</Th>
                    <Th>Landscape</Th>
                    <Th>Reports</Th>
                    <Th>Latest</Th>
                    <Th>Open</Th>
                    <Th>Critical</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {systems.length === 0 && (
                    <EmptyRow colSpan={7} message="No systems registered yet." />
                  )}
                  {systems.map((s) => (
                    <tr
                      key={s.id}
                      className="cursor-pointer hover:bg-gray-50"
                      onClick={() => navigate(`/trends/${s.id}`)}
                    >
                      <Td className="font-mono font-semibold text-gray-900">
                        {s.sid}
                        {s.description && (
                          <span className="block font-sans text-xs font-normal text-gray-400">
                            {s.description}
                          </span>
                        )}
                      </Td>
                      <Td>{s.system_type ?? '—'}</Td>
                      <Td>{s.landscape ?? '—'}</Td>
                      <Td>{s.report_count}</Td>
                      <Td>
                        <RatingPill rating={s.latest_rating} />
                      </Td>
                      <Td>{s.open_alerts}</Td>
                      <Td>
                        {s.critical_alerts > 0 ? (
                          <span className="font-semibold text-red-600">{s.critical_alerts}</span>
                        ) : (
                          '0'
                        )}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>
        </div>

        <div>
          <Card title="Register system">
            {!canCreate ? (
              <p className="text-sm text-gray-400">
                You need operator access to register systems.
              </p>
            ) : (
              <form onSubmit={onSubmit} className="space-y-3">
                <div>
                  <label className="label" htmlFor="sid">
                    SID <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="sid"
                    className="input font-mono uppercase"
                    value={sid}
                    onChange={(e) => setSid(e.target.value)}
                    placeholder="PRD"
                    maxLength={12}
                    required
                  />
                </div>
                <div>
                  <label className="label" htmlFor="description">
                    Description
                  </label>
                  <input
                    id="description"
                    className="input"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Production ERP"
                  />
                </div>
                <div>
                  <label className="label" htmlFor="system_type">
                    System type
                  </label>
                  <input
                    id="system_type"
                    className="input"
                    value={systemType}
                    onChange={(e) => setSystemType(e.target.value)}
                    placeholder="ABAP / HANA / Java…"
                  />
                </div>
                <div>
                  <label className="label" htmlFor="landscape">
                    Landscape
                  </label>
                  <input
                    id="landscape"
                    className="input"
                    value={landscape}
                    onChange={(e) => setLandscape(e.target.value)}
                    placeholder="Production / QA / Dev"
                  />
                </div>

                <ErrorMessage message={error} />
                {success && <p className="text-sm text-green-600">{success}</p>}

                <button type="submit" className="btn-primary w-full" disabled={submitting}>
                  {submitting ? 'Registering…' : 'Register system'}
                </button>
              </form>
            )}
          </Card>

          {isAdmin && (
            <Card title="Danger zone" className="mt-6 border-red-200">
              <p className="text-sm text-gray-600">
                Remove all demo / imported data (systems, reports, alerts, ratings).
                User accounts are preserved.
              </p>
              <button
                type="button"
                className="btn-danger mt-3 w-full"
                onClick={onPurge}
                disabled={purging}
              >
                {purging ? 'Clearing…' : 'Clear all data'}
              </button>
              {purgeMsg && <p className="mt-2 text-sm text-gray-700">{purgeMsg}</p>}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
