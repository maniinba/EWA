import { NavLink } from 'react-router-dom';
import type { SystemItem } from '../services/types';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/systems', label: 'Systems' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/reports', label: 'Reports' },
  { to: '/trends', label: 'Trends' },
  { to: '/connector', label: 'Connector' },
];

interface SidebarProps {
  systems: SystemItem[];
  onNavigate?: () => void;
}

export function Sidebar({ systems, onNavigate }: SidebarProps) {
  return (
    <div className="flex h-full w-64 flex-col bg-brand-900 text-brand-50">
      <div className="flex items-center gap-2 border-b border-white/10 px-5 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/15 text-lg font-bold">
          E
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight">EWA Dashboard</p>
          <p className="text-[11px] text-brand-100/70">EarlyWatch Alert analysis</p>
        </div>
      </div>

      <nav className="px-3 py-4">
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.end}
                onClick={onNavigate}
                className={({ isActive }) =>
                  `block rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-white/15 text-white'
                      : 'text-brand-100/80 hover:bg-white/10 hover:text-white'
                  }`
                }
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="mt-2 min-h-0 flex-1 overflow-y-auto border-t border-white/10 px-3 py-4">
        <p className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-wide text-brand-100/50">
          Systems
        </p>
        <ul className="space-y-1">
          {systems.length === 0 && (
            <li className="px-2 text-xs text-brand-100/50">No systems yet</li>
          )}
          {systems.map((sys) => (
            <li key={sys.id}>
              <NavLink
                to={`/trends/${sys.id}`}
                onClick={onNavigate}
                className={({ isActive }) =>
                  `flex items-center justify-between rounded-lg px-3 py-1.5 text-sm transition-colors ${
                    isActive ? 'bg-white/15 text-white' : 'text-brand-100/80 hover:bg-white/10'
                  }`
                }
              >
                <span className="truncate font-mono text-xs font-semibold">{sys.sid}</span>
                {sys.open_alerts > 0 && (
                  <span className="ml-2 inline-flex min-w-[1.25rem] items-center justify-center rounded-full bg-red-600 px-1.5 py-0.5 text-[11px] font-semibold text-white">
                    {sys.open_alerts}
                  </span>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
