import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { Alert, DashboardSummary } from '../services/types';
import { errorMessage, fetchAlerts, fetchSummary } from '../services/api';
import { useSystems } from '../hooks/useSystems';
import { Card } from '../components/Card';
import { StatCard } from '../components/StatCard';
import { Spinner } from '../components/Spinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { RatingPill, SeverityPill, SEVERITY_HEX } from '../components/pills';
import { Table, Th, Td, EmptyRow } from '../components/Table';
import { AlertDetailDrawer } from '../components/AlertDetailDrawer';

const STATUS_COLORS: Record<string, string> = {
  open: '#dc2626',
  in_progress: '#f59e0b',
  resolved: '#16a34a',
  deferred: '#9ca3af',
};

export function Dashboard() {
  const { systems } = useSystems();
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [criticalAlerts, setCriticalAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [sum, crit] = await Promise.all([
          fetchSummary(),
          fetchAlerts({ severity: 'red', status: 'open', limit: 8 }),
        ]);
        if (!active) return;
        setSummary(sum);
        setCriticalAlerts(crit);
      } catch (err) {
        if (active) setError(errorMessage(err, 'Failed to load dashboard'));
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const severityData = useMemo(() => {
    if (!summary) return [];
    const b = summary.severity_breakdown;
    return [
      { name: 'Red', key: 'red', value: b.red },
      { name: 'Yellow', key: 'yellow', value: b.yellow },
      { name: 'Green', key: 'green', value: b.green },
      { name: 'Gray', key: 'gray', value: b.gray },
    ].filter((d) => d.value > 0);
  }, [summary]);

  const statusData = useMemo(() => {
    if (!summary) return [];
    const b = summary.status_breakdown;
    return [
      { name: 'Open', key: 'open', value: b.open },
      { name: 'In progress', key: 'in_progress', value: b.in_progress },
      { name: 'Resolved', key: 'resolved', value: b.resolved },
      { name: 'Deferred', key: 'deferred', value: b.deferred },
    ];
  }, [summary]);

  if (loading) return <Spinner label="Loading dashboard…" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500">Overview across all monitored SAP systems.</p>
      </div>

      <ErrorMessage message={error} />

      {summary && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total Systems" value={summary.total_systems} />
            <StatCard label="Total Reports" value={summary.total_reports} />
            <StatCard label="Open Alerts" value={summary.open_alerts} accent="amber" />
            <StatCard label="Critical Alerts" value={summary.critical_alerts} accent="red" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card title="Severity breakdown">
              {severityData.length === 0 ? (
                <p className="py-10 text-center text-sm text-gray-400">No alert data.</p>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={severityData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={90}
                        paddingAngle={2}
                      >
                        {severityData.map((d) => (
                          <Cell key={d.key} fill={SEVERITY_HEX[d.key as keyof typeof SEVERITY_HEX]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="mt-2 flex flex-wrap justify-center gap-4">
                    {severityData.map((d) => (
                      <span key={d.key} className="flex items-center gap-1.5 text-xs text-gray-600">
                        <span
                          className="h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: SEVERITY_HEX[d.key as keyof typeof SEVERITY_HEX] }}
                        />
                        {d.name} ({d.value})
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </Card>

            <Card title="Status breakdown">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={statusData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <XAxis dataKey="name" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis allowDecimals={false} fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip cursor={{ fill: 'rgba(0,0,0,0.04)' }} />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {statusData.map((d) => (
                        <Cell key={d.key} fill={STATUS_COLORS[d.key]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      )}

      <Card title="Systems overview" bodyClassName="p-0">
        <Table>
          <thead className="bg-gray-50">
            <tr>
              <Th>SID</Th>
              <Th>Type</Th>
              <Th>Landscape</Th>
              <Th>Latest rating</Th>
              <Th>Open alerts</Th>
              <Th>Critical</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {systems.length === 0 && <EmptyRow colSpan={6} message="No systems registered yet." />}
            {systems.map((s) => (
              <tr
                key={s.id}
                className="cursor-pointer hover:bg-gray-50"
                onClick={() => navigate(`/trends/${s.id}`)}
              >
                <Td className="font-mono font-semibold text-gray-900">{s.sid}</Td>
                <Td>{s.system_type ?? '—'}</Td>
                <Td>{s.landscape ?? '—'}</Td>
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
      </Card>

      <Card title="Recent critical alerts" bodyClassName="p-0">
        {criticalAlerts.length === 0 ? (
          <p className="p-6 text-center text-sm text-gray-400">No open critical alerts. 🎉</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {criticalAlerts.map((a) => (
              <li key={a.id}>
                <button
                  type="button"
                  className="flex w-full items-center gap-3 px-5 py-3 text-left hover:bg-gray-50"
                  onClick={() => setSelectedAlert(a.id)}
                >
                  <SeverityPill severity={a.severity} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-gray-800">
                      {a.title}
                    </span>
                    <span className="block truncate text-xs text-gray-400">
                      {a.chapter}
                    </span>
                  </span>
                  <span className="font-mono text-xs text-gray-500">{a.system_sid}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <AlertDetailDrawer
        alertId={selectedAlert}
        onClose={() => setSelectedAlert(null)}
        onSelectAlert={(id) => setSelectedAlert(id)}
      />
    </div>
  );
}
