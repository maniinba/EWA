import { useCallback, useEffect, useState, type FormEvent } from 'react';
import type { ConnectorActionResult, ConnectorStatus } from '../services/types';
import {
  errorMessage,
  fetchConnectorNow,
  fetchConnectorStatus,
  saveConnectorConfig,
  testConnector,
} from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { Card } from '../components/Card';
import { Spinner } from '../components/Spinner';
import { ErrorMessage } from '../components/ErrorMessage';

function formatResult(result: ConnectorActionResult): string {
  try {
    return JSON.stringify(result, null, 2);
  } catch {
    return String(result);
  }
}

export function Connector() {
  const { hasRole } = useAuth();
  const canView = hasRole('operator');
  const canConfigure = hasRole('admin');

  const [status, setStatus] = useState<ConnectorStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [sUser, setSUser] = useState('');
  const [sPassword, setSPassword] = useState('');
  const [enabled, setEnabled] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [configSuccess, setConfigSuccess] = useState<string | null>(null);

  const [actionResult, setActionResult] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [fetching, setFetching] = useState(false);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const s = await fetchConnectorStatus();
      setStatus(s);
      setSUser(s.s_user ?? '');
      setEnabled(s.enabled);
    } catch (err) {
      setError(errorMessage(err, 'Failed to load connector status'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (canView) void loadStatus();
    else setLoading(false);
  }, [canView, loadStatus]);

  const onSaveConfig = async (e: FormEvent) => {
    e.preventDefault();
    setSavingConfig(true);
    setConfigError(null);
    setConfigSuccess(null);
    try {
      const updated = await saveConnectorConfig({
        client_id: clientId || undefined,
        client_secret: clientSecret || undefined,
        s_user: sUser || undefined,
        s_password: sPassword || undefined,
        enabled,
      });
      setStatus(updated);
      setConfigSuccess('Connector configuration saved.');
      setClientSecret('');
      setSPassword('');
    } catch (err) {
      setConfigError(errorMessage(err, 'Failed to save configuration'));
    } finally {
      setSavingConfig(false);
    }
  };

  const onTest = async () => {
    setTesting(true);
    setActionError(null);
    setActionResult(null);
    try {
      const res = await testConnector();
      setActionResult(formatResult(res));
      await loadStatus();
    } catch (err) {
      setActionError(errorMessage(err, 'Connection test failed'));
    } finally {
      setTesting(false);
    }
  };

  const onFetch = async () => {
    setFetching(true);
    setActionError(null);
    setActionResult(null);
    try {
      const res = await fetchConnectorNow();
      setActionResult(formatResult(res));
      await loadStatus();
    } catch (err) {
      setActionError(errorMessage(err, 'Fetch failed'));
    } finally {
      setFetching(false);
    }
  };

  if (!canView) {
    return (
      <Card>
        <p className="py-8 text-center text-sm text-gray-400">
          You need operator access to view the SAP connector.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">SAP Connector</h1>
        <p className="text-sm text-gray-500">
          Connect to SAP for Me to fetch EarlyWatch Alert reports automatically.
        </p>
      </div>

      {loading ? (
        <Spinner label="Loading connector…" />
      ) : (
        <>
          <ErrorMessage message={error} />

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card title="Status">
              {status ? (
                <dl className="grid grid-cols-2 gap-y-3 text-sm">
                  <dt className="text-gray-400">Configured</dt>
                  <dd className="font-medium">
                    {status.configured ? (
                      <span className="text-green-600">Yes</span>
                    ) : (
                      <span className="text-gray-500">No</span>
                    )}
                  </dd>
                  <dt className="text-gray-400">Enabled</dt>
                  <dd className="font-medium">
                    {status.enabled ? (
                      <span className="text-green-600">Yes</span>
                    ) : (
                      <span className="text-gray-500">No</span>
                    )}
                  </dd>
                  <dt className="text-gray-400">S-User</dt>
                  <dd className="font-mono">{status.s_user ?? '—'}</dd>
                  <dt className="text-gray-400">Last sync</dt>
                  <dd>{status.last_sync_at ?? '—'}</dd>
                  <dt className="text-gray-400">Last status</dt>
                  <dd>{status.last_sync_status ?? '—'}</dd>
                  <dt className="text-gray-400">Message</dt>
                  <dd className="break-words">{status.last_sync_message ?? '—'}</dd>
                </dl>
              ) : (
                <p className="text-sm text-gray-400">No status available.</p>
              )}

              <div className="mt-5 flex flex-wrap gap-3">
                <button type="button" className="btn-secondary" onClick={onTest} disabled={testing}>
                  {testing ? 'Testing…' : 'Test connection'}
                </button>
                <button type="button" className="btn-primary" onClick={onFetch} disabled={fetching}>
                  {fetching ? 'Fetching…' : 'Fetch now'}
                </button>
              </div>

              <ErrorMessage message={actionError} />
              {actionResult && (
                <pre className="mt-3 max-h-60 overflow-auto rounded-lg bg-gray-900 p-3 text-xs text-gray-100">
                  {actionResult}
                </pre>
              )}
            </Card>

            <Card title="Configuration">
              {!canConfigure ? (
                <p className="text-sm text-gray-400">
                  You need admin access to change connector configuration.
                </p>
              ) : (
                <form onSubmit={onSaveConfig} className="space-y-3">
                  <div>
                    <label className="label" htmlFor="client_id">
                      OAuth Client ID
                    </label>
                    <input
                      id="client_id"
                      className="input"
                      value={clientId}
                      onChange={(e) => setClientId(e.target.value)}
                      placeholder="Leave blank to keep existing"
                      autoComplete="off"
                    />
                  </div>
                  <div>
                    <label className="label" htmlFor="client_secret">
                      OAuth Client Secret
                    </label>
                    <input
                      id="client_secret"
                      type="password"
                      className="input"
                      value={clientSecret}
                      onChange={(e) => setClientSecret(e.target.value)}
                      placeholder="Leave blank to keep existing"
                      autoComplete="new-password"
                    />
                  </div>
                  <div>
                    <label className="label" htmlFor="s_user">
                      S-User
                    </label>
                    <input
                      id="s_user"
                      className="input"
                      value={sUser}
                      onChange={(e) => setSUser(e.target.value)}
                      placeholder="S0001234567"
                      autoComplete="off"
                    />
                  </div>
                  <div>
                    <label className="label" htmlFor="s_password">
                      S-User Password
                    </label>
                    <input
                      id="s_password"
                      type="password"
                      className="input"
                      value={sPassword}
                      onChange={(e) => setSPassword(e.target.value)}
                      placeholder="Leave blank to keep existing"
                      autoComplete="new-password"
                    />
                  </div>
                  <label className="flex items-center gap-2 text-sm text-gray-700">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                      checked={enabled}
                      onChange={(e) => setEnabled(e.target.checked)}
                    />
                    Enable connector
                  </label>

                  <ErrorMessage message={configError} />
                  {configSuccess && <p className="text-sm text-green-600">{configSuccess}</p>}

                  <button type="submit" className="btn-primary w-full" disabled={savingConfig}>
                    {savingConfig ? 'Saving…' : 'Save configuration'}
                  </button>
                </form>
              )}

              <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
                Secrets are stored encrypted server-side and never returned to the browser. A live
                fetch requires valid SAP for Me OAuth credentials.
              </p>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
