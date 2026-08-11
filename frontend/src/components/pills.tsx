import type { AlertStatus, Rating, Severity } from '../services/types';

const SEVERITY_STYLES: Record<Severity, string> = {
  red: 'bg-red-100 text-red-800 border-red-200',
  yellow: 'bg-amber-100 text-amber-800 border-amber-200',
  green: 'bg-green-100 text-green-800 border-green-200',
  gray: 'bg-gray-100 text-gray-700 border-gray-200',
};

const SEVERITY_LABEL: Record<Severity, string> = {
  red: 'Red',
  yellow: 'Yellow',
  green: 'Green',
  gray: 'Gray',
};

export function SeverityPill({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${SEVERITY_STYLES[severity]}`}
    >
      <span
        className="h-2 w-2 rounded-full"
        style={{ backgroundColor: SEVERITY_HEX[severity] }}
      />
      {SEVERITY_LABEL[severity]}
    </span>
  );
}

export const SEVERITY_HEX: Record<Severity, string> = {
  red: '#dc2626',
  yellow: '#f59e0b',
  green: '#16a34a',
  gray: '#9ca3af',
};

export function RatingPill({ rating }: { rating: Rating | null }) {
  if (!rating) {
    return (
      <span className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2.5 py-0.5 text-xs font-medium text-gray-500">
        n/a
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold text-white"
      style={{ backgroundColor: SEVERITY_HEX[rating] }}
    >
      {SEVERITY_LABEL[rating]}
    </span>
  );
}

const STATUS_STYLES: Record<AlertStatus, string> = {
  open: 'bg-red-50 text-red-700 border-red-200',
  in_progress: 'bg-amber-50 text-amber-700 border-amber-200',
  resolved: 'bg-green-50 text-green-700 border-green-200',
  deferred: 'bg-gray-50 text-gray-600 border-gray-200',
};

export const STATUS_LABEL: Record<AlertStatus, string> = {
  open: 'Open',
  in_progress: 'In progress',
  resolved: 'Resolved',
  deferred: 'Deferred',
};

export function StatusPill({ status }: { status: AlertStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}
