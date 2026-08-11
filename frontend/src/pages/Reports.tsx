import { useCallback, useEffect, useRef, useState, type DragEvent } from 'react';
import type { Report, ReportPreview } from '../services/types';
import {
  deleteReport,
  errorMessage,
  fetchReports,
  isConflict,
  previewReport,
  uploadReport,
} from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { useSystems } from '../hooks/useSystems';
import { Card } from '../components/Card';
import { Table, Th, Td, EmptyRow } from '../components/Table';
import { RatingPill, SeverityPill } from '../components/pills';
import { Spinner } from '../components/Spinner';
import { ErrorMessage } from '../components/ErrorMessage';

export function Reports() {
  const { hasRole } = useAuth();
  const { systems, refresh: refreshSystems } = useSystems();
  const canUpload = hasRole('operator');
  const canDelete = hasRole('admin');
  const sidById = (id: string) => systems.find((s) => s.id === id)?.sid ?? `#${id}`;

  const [reports, setReports] = useState<Report[]>([]);
  const [loadingReports, setLoadingReports] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ReportPreview | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const loadReports = useCallback(async () => {
    setLoadingReports(true);
    try {
      const data = await fetchReports();
      setReports(data);
      setListError(null);
    } catch (err) {
      setListError(errorMessage(err, 'Failed to load reports'));
    } finally {
      setLoadingReports(false);
    }
  }, []);

  useEffect(() => {
    void loadReports();
  }, [loadReports]);

  const resetUpload = () => {
    setFile(null);
    setPreview(null);
    setPreviewError(null);
    setSaveError(null);
    setConflict(false);
    setSaveSuccess(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const handleFile = async (selected: File) => {
    setFile(selected);
    setPreview(null);
    setPreviewError(null);
    setSaveError(null);
    setConflict(false);
    setSaveSuccess(null);
    setPreviewing(true);
    try {
      const p = await previewReport(selected);
      setPreview(p);
    } catch (err) {
      setPreviewError(errorMessage(err, 'Failed to parse report'));
    } finally {
      setPreviewing(false);
    }
  };

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) void handleFile(f);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) void handleFile(f);
  };

  const save = async (replaceExisting: boolean) => {
    if (!file || !preview) return;
    setSaving(true);
    setSaveError(null);
    setConflict(false);
    try {
      await uploadReport(file, {
        sid: preview.sid,
        reportDate: preview.report_date,
        replaceExisting,
      });
      setSaveSuccess(`Report for ${preview.sid} (${preview.report_date}) saved.`);
      resetUpload();
      await Promise.all([loadReports(), refreshSystems()]);
    } catch (err) {
      if (isConflict(err)) {
        setConflict(true);
        setSaveError(
          'A report for this system and date already exists. Replace the existing one?',
        );
      } else {
        setSaveError(errorMessage(err, 'Failed to save report'));
      }
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async (id: string) => {
    if (!window.confirm('Delete this report and its alerts? This cannot be undone.')) return;
    try {
      await deleteReport(id);
      await Promise.all([loadReports(), refreshSystems()]);
    } catch (err) {
      setListError(errorMessage(err, 'Failed to delete report'));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Reports</h1>
        <p className="text-sm text-gray-500">Upload and manage EarlyWatch Alert reports.</p>
      </div>

      {canUpload && (
        <Card title="Upload report">
          <div
            className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
              dragging ? 'border-brand-500 bg-brand-50' : 'border-gray-300 bg-gray-50'
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <svg viewBox="0 0 24 24" className="mb-3 h-10 w-10 text-gray-400" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V4m0 0L8 8m4-4l4 4M20 16.5A3.5 3.5 0 0016.5 13H16a5 5 0 10-9.9 1" />
            </svg>
            <p className="text-sm text-gray-600">
              Drag &amp; drop an EWA report here, or{' '}
              <button
                type="button"
                className="font-medium text-brand-600 hover:underline"
                onClick={() => inputRef.current?.click()}
              >
                browse
              </button>
            </p>
            <p className="mt-1 text-xs text-gray-400">
              SAP EWA reports — .DOC (Word XML), PDF, HTML or TXT
            </p>
            {file && <p className="mt-3 text-sm font-medium text-gray-700">{file.name}</p>}
            <input
              ref={inputRef}
              type="file"
              className="hidden"
              onChange={onInputChange}
              accept=".doc,.docx,.pdf,.html,.htm,.txt,.xml"
            />
          </div>

          {previewing && <Spinner label="Parsing report…" />}
          <ErrorMessage message={previewError} />

          {preview && (
            <div className="mt-5 space-y-4">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div>
                  <p className="text-xs text-gray-400">Detected SID</p>
                  <p className="font-mono font-semibold text-gray-800">{preview.sid}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Report date</p>
                  <p className="font-medium text-gray-800">{preview.report_date}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">System type</p>
                  <p className="font-medium text-gray-800">{preview.system_type ?? '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Overall rating</p>
                  <RatingPill rating={preview.overall_rating} />
                </div>
              </div>

              {preview.ratings.length > 0 && (
                <div>
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
                    Chapter ratings
                  </h3>
                  <div className="overflow-hidden rounded-lg border border-gray-200">
                    <Table>
                      <thead className="bg-gray-50">
                        <tr>
                          <Th>Chapter</Th>
                          <Th>Rating</Th>
                          <Th>Score</Th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {preview.ratings.map((r, i) => (
                          <tr key={`${r.chapter}-${i}`}>
                            <Td>{r.chapter}</Td>
                            <Td>
                              <RatingPill rating={r.rating} />
                            </Td>
                            <Td>{r.score ?? '—'}</Td>
                          </tr>
                        ))}
                      </tbody>
                    </Table>
                  </div>
                </div>
              )}

              <div>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
                  Alerts ({preview.alert_count})
                </h3>
                {preview.alerts.length === 0 ? (
                  <p className="text-sm text-gray-400">No alerts detected.</p>
                ) : (
                  <ul className="divide-y divide-gray-100 rounded-lg border border-gray-200">
                    {preview.alerts.map((a, i) => (
                      <li key={i} className="flex items-center gap-3 px-3 py-2">
                        <SeverityPill severity={a.severity} />
                        <span className="min-w-0 flex-1 truncate text-sm text-gray-700">
                          {a.title}
                        </span>
                        <span className="text-xs text-gray-400">{a.chapter}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <ErrorMessage message={saveError} />
              {saveSuccess && <p className="text-sm text-green-600">{saveSuccess}</p>}

              <div className="flex flex-wrap gap-3">
                {!conflict && (
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => save(false)}
                    disabled={saving}
                  >
                    {saving ? 'Saving…' : 'Save report'}
                  </button>
                )}
                {conflict && (
                  <button
                    type="button"
                    className="btn-danger"
                    onClick={() => save(true)}
                    disabled={saving}
                  >
                    {saving ? 'Replacing…' : 'Replace existing'}
                  </button>
                )}
                <button type="button" className="btn-secondary" onClick={resetUpload}>
                  Cancel
                </button>
              </div>
            </div>
          )}
        </Card>
      )}

      {saveSuccess && !preview && <p className="text-sm text-green-600">{saveSuccess}</p>}

      <Card title="Existing reports" bodyClassName="p-0">
        {loadingReports ? (
          <Spinner label="Loading reports…" />
        ) : (
          <>
            {listError && (
              <div className="p-5">
                <ErrorMessage message={listError} />
              </div>
            )}
            <Table>
              <thead className="bg-gray-50">
                <tr>
                  <Th>System</Th>
                  <Th>Date</Th>
                  <Th>File</Th>
                  <Th>Method</Th>
                  <Th>Overall</Th>
                  {canDelete && <Th />}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {reports.length === 0 && (
                  <EmptyRow colSpan={canDelete ? 6 : 5} message="No reports uploaded yet." />
                )}
                {reports.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <Td className="font-mono text-xs font-semibold">{sidById(r.system_id)}</Td>
                    <Td>{r.report_date}</Td>
                    <Td className="max-w-[16rem]">
                      <span className="block truncate">{r.file_name}</span>
                    </Td>
                    <Td className="capitalize">{r.upload_method}</Td>
                    <Td>
                      <RatingPill rating={r.overall_rating} />
                    </Td>
                    {canDelete && (
                      <Td>
                        <button
                          type="button"
                          className="text-xs font-medium text-red-600 hover:underline"
                          onClick={() => onDelete(r.id)}
                        >
                          Delete
                        </button>
                      </Td>
                    )}
                  </tr>
                ))}
              </tbody>
            </Table>
          </>
        )}
      </Card>
    </div>
  );
}
