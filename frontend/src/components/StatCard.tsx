import type { ReactNode } from 'react';

interface StatCardProps {
  label: string;
  value: ReactNode;
  hint?: string;
  accent?: 'default' | 'red' | 'amber' | 'green';
}

const ACCENTS: Record<NonNullable<StatCardProps['accent']>, string> = {
  default: 'text-gray-900',
  red: 'text-red-600',
  amber: 'text-amber-600',
  green: 'text-green-600',
};

export function StatCard({ label, value, hint, accent = 'default' }: StatCardProps) {
  return (
    <div className="card p-5">
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <p className={`mt-2 text-3xl font-semibold ${ACCENTS[accent]}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-gray-400">{hint}</p>}
    </div>
  );
}
