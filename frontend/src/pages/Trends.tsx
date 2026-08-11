import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { Trends as TrendsData, WhatChanged } from '../services/types';
import { errorMessage, fetchTrends, fetchWhatChanged } from '../services/api';
import { useSystems } from '../hooks/useSystems';
import { Card } from '../components/Card';
import { Spinner } from '../components/Spinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { SEVERITY_HEX } from '../components/pills';

const CHAPTER_LINE_COLORS = [
  '#2563eb',
  '#7c3aed',
  '#db2777',
  '#0891b2',
  '#ca8a04',
  '#059669',
  '#dc2626',
  '#4b5563',
];

function directionClass(direction: string): string {
  if (direction === 'better') return 'text-green-600';
  if (direction === 'worse') return 'text-red-600';
  return 'text-gray-500';
}

export function Trends() {
  const { systems } = useSystems();
  const { systemId } = useParams<{ systemId: string }>();
  const navigate = useNavigate();

  const [trends, setTrends] = useState<TrendsData | null>(null);
  const [changed, setChanged] = useState<WhatChanged | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const numericId = systemId ? Number(systemId) : null;

  useEffect(() => {
    if (numericId == null) {
      setTrends(null);
      setChanged(null);
      return;
    }
    let active = true;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const [t, c] = await Promise.all([
          fetchTrends(numericId),
          fetchWhatChanged(numericId).catch(() => null),
        ]);
        if (!active) return;
        setTrends(t);
        setChanged(c);
      } catch (err) {
        if (active) setError(errorMessage(err, 'Failed to load trends'));
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [numericId]);

  // Merge chapter trend scores into a single dataset keyed by report_date.
  const chapterChartData = useMemo(() => {
    if (!trends) return { rows: [], chapters: [] as string[] };
    const byDate = new Map<string, Record<string, number | string | null>>();
    const chapters: string[] = [];
    for (const ct of trends.chapter_trends) {
      chapters.push(ct.chapter);
      for (const p of ct.points) {
        const row = byDate.get(p.report_date) ?? { report_date: p.report_date };
        row[ct.chapter] = p.score ?? null;
        byDate.set(p.report_date, row);
      }
    }
    const rows = Array.from(byDate.values()).sort((a, b) =>
      String(a.report_date).localeCompare(String(b.report_date)),
    );
    return { rows, chapters };
  }, [trends]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Trends</h1>
          <p className="text-sm text-gray-500">Historical ratings and alert volumes per system.</p>
        </div>
        <div className="w-full sm:w-64">
          <label className="label" htmlFor="trend-system">
            System
          </label>
          <select
            id="trend-system"
            className="input"
            value={numericId ?? ''}
            onChange={(e) => {
              const v = e.target.value;
              navigate(v ? `/trends/${v}` : '/trends');
            }}
          >
            <option value="">Select a system…</option>
            {systems.map((s) => (
              <option key={s.id} value={s.id}>
                {s.sid}
              </option>
            ))}
          </select>
        </div>
      </div>

      {numericId == null && (
        <Card>
          <p className="py-8 text-center text-sm text-gray-400">
            Select a system to view its trends.
          </p>
        </Card>
      )}

      {loading && <Spinner label="Loading trends…" />}
      <ErrorMessage message={error} />

      {trends && !loading && (
        <>
          <Card title={`Alert volume over time — ${trends.system_sid}`}>
            {trends.alert_trend.length === 0 ? (
              <p className="py-8 text-center text-sm text-gray-400">No report history yet.</p>
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trends.alert_trend} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                    <XAxis dataKey="report_date" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis allowDecimals={false} fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="red"
                      stackId="1"
                      stroke={SEVERITY_HEX.red}
                      fill={SEVERITY_HEX.red}
                      fillOpacity={0.7}
                      name="Red"
                    />
                    <Area
                      type="monotone"
                      dataKey="yellow"
                      stackId="1"
                      stroke={SEVERITY_HEX.yellow}
                      fill={SEVERITY_HEX.yellow}
                      fillOpacity={0.7}
                      name="Yellow"
                    />
                    <Area
                      type="monotone"
                      dataKey="green"
                      stackId="1"
                      stroke={SEVERITY_HEX.green}
                      fill={SEVERITY_HEX.green}
                      fillOpacity={0.7}
                      name="Green"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </Card>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Card title="Chapter rating scores (3 = red, 1 = green)">
                {chapterChartData.rows.length === 0 ? (
                  <p className="py-8 text-center text-sm text-gray-400">
                    No chapter trend data.
                  </p>
                ) : (
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chapterChartData.rows} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                        <XAxis dataKey="report_date" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis
                          domain={[0, 3]}
                          ticks={[1, 2, 3]}
                          fontSize={12}
                          tickLine={false}
                          axisLine={false}
                        />
                        <Tooltip />
                        <Legend />
                        {chapterChartData.chapters.map((ch, i) => (
                          <Line
                            key={ch}
                            type="monotone"
                            dataKey={ch}
                            stroke={CHAPTER_LINE_COLORS[i % CHAPTER_LINE_COLORS.length]}
                            strokeWidth={2}
                            dot={{ r: 2 }}
                            connectNulls
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Card>
            </div>

            <div>
              <Card title="What changed">
                {!changed ? (
                  <p className="text-sm text-gray-400">No comparison available.</p>
                ) : (
                  <div className="space-y-4 text-sm">
                    <p className="text-xs text-gray-400">
                      {changed.from_date ?? '—'} → {changed.to_date ?? '—'}
                    </p>

                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-red-500">
                        New alerts ({changed.new_alerts.length})
                      </h3>
                      {changed.new_alerts.length === 0 ? (
                        <p className="text-xs text-gray-400">None</p>
                      ) : (
                        <ul className="list-disc space-y-0.5 pl-4 text-gray-700">
                          {changed.new_alerts.map((a, i) => (
                            <li key={i}>{a}</li>
                          ))}
                        </ul>
                      )}
                    </div>

                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-green-600">
                        Resolved alerts ({changed.resolved_alerts.length})
                      </h3>
                      {changed.resolved_alerts.length === 0 ? (
                        <p className="text-xs text-gray-400">None</p>
                      ) : (
                        <ul className="list-disc space-y-0.5 pl-4 text-gray-700">
                          {changed.resolved_alerts.map((a, i) => (
                            <li key={i}>{a}</li>
                          ))}
                        </ul>
                      )}
                    </div>

                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-400">
                        Rating changes ({changed.rating_changes.length})
                      </h3>
                      {changed.rating_changes.length === 0 ? (
                        <p className="text-xs text-gray-400">None</p>
                      ) : (
                        <ul className="space-y-1">
                          {changed.rating_changes.map((rc, i) => (
                            <li key={i} className="flex items-center justify-between gap-2">
                              <span className="truncate text-gray-700">{rc.chapter}</span>
                              <span className={`whitespace-nowrap font-medium ${directionClass(rc.direction)}`}>
                                {rc.from ?? '—'} → {rc.to ?? '—'}
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                )}
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
