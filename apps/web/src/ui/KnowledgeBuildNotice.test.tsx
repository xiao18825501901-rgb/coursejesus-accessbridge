import { act, render, screen, cleanup } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { KnowledgeBuildNotice } from './KnowledgeBuildNotice.jsx';
import { request } from './api.js';

vi.mock('./api.js', () => ({ request: vi.fn(), setUiErrorTranslator: vi.fn() }));
afterEach(() => { cleanup(); vi.useRealTimers(); vi.clearAllMocks(); });

test('polls read-only status and offers learning when the automatic tree is ready', async () => {
  vi.useFakeTimers();
  vi.mocked(request).mockResolvedValueOnce({ status: 'QUEUED' })
    .mockResolvedValueOnce({ status: 'READY', tree_version_id: 'tree-1' });
  render(<KnowledgeBuildNotice courseId="new-course" />);
  await act(async () => {});
  expect(screen.getByRole('status')).toHaveTextContent('排队');
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(screen.getByRole('link')).toHaveAttribute('href', '#/course/new-course/learn');
  expect(request).toHaveBeenCalledTimes(2);
  expect(vi.mocked(request).mock.calls.every(args => args.length === 1)).toBe(true);
});

test('shows a disabled worker instead of implying generation is running', async () => {
  vi.mocked(request).mockResolvedValue({ status: 'QUEUED', worker_enabled: false });
  render(<KnowledgeBuildNotice courseId="new-course" />);
  expect(await screen.findByRole('status')).toHaveTextContent('尚未启用');
});

test('preserves UNKNOWN without offering a generation retry', async () => {
  vi.mocked(request).mockResolvedValue({ status: 'UNKNOWN' });
  render(<KnowledgeBuildNotice courseId="new-course" />);
  expect(await screen.findByRole('status')).toHaveTextContent('待核对');
  expect(screen.queryByRole('button')).toBeNull();
});

test('marks a usable tree as partial when selected files have not finished', async () => {
  vi.mocked(request).mockResolvedValue({
    status: 'READY', tree_version_id: 'partial-tree',
    upload_coverage: { missing_items: 1, pending_items: 0, failed_items: 0 },
  });
  render(<KnowledgeBuildNotice courseId="partial-course" />);
  expect(await screen.findByRole('status')).toHaveTextContent('部分');
  expect(screen.getByRole('link')).toHaveAttribute('href', '#/course/partial-course/learn');
});

test('renders observed stage and file counts instead of an invented time percentage', async () => {
  vi.mocked(request).mockResolvedValue({
    status: 'BUILDING', progress: { phase: 'OUTLINE', completed_stages: 2, total_stages: 5,
      files_completed: 3, files_total: 3, saved_results: 4 },
  });
  render(<KnowledgeBuildNotice courseId="new-or-appended-course" />);
  const bar = await screen.findByRole('progressbar');
  expect(bar).toHaveAttribute('value', '2');
  expect(bar).toHaveAttribute('max', '5');
  expect(screen.getByRole('status')).toHaveTextContent('3/3');
  expect(screen.getByRole('status')).toHaveTextContent('4');
  expect(screen.getByRole('status')).toHaveTextContent('知识点整理');
});

test('does not make an unknown result look completed', async () => {
  vi.mocked(request).mockResolvedValue({
    status: 'UNKNOWN', progress: { phase: 'UNKNOWN', last_observed_phase: 'OUTLINE',
      completed_stages: 2, total_stages: 5,
      files_completed: 3, files_total: 3, saved_results: 2 },
  });
  render(<KnowledgeBuildNotice courseId="unknown-course" />);
  const bar = await screen.findByRole('progressbar');
  expect(bar).toHaveAttribute('value', '2');
  expect(screen.getByRole('status')).toHaveTextContent('待核对');
  expect(screen.getByRole('status')).toHaveTextContent('知识点整理');
  expect(screen.queryByRole('button')).toBeNull();
});

test('shows new batch progress while keeping the previous tree accessible', async () => {
  vi.useFakeTimers();
  vi.mocked(request).mockResolvedValueOnce({ status: 'READY', tree_version_id: 'old-tree',
    progress: { phase: 'READY', completed_stages: 5, total_stages: 5 } })
    .mockResolvedValue({ status: 'BUILDING', tree_version_id: 'old-tree',
      progress: { phase: 'ANALYSIS', completed_stages: 1, total_stages: 5,
        files_completed: 2, files_total: 2 } });
  render(<KnowledgeBuildNotice courseId="append-course" />);
  await act(async () => {});
  expect(screen.getByRole('progressbar')).toHaveAttribute('value', '5');
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(screen.getByRole('progressbar')).toHaveAttribute('value', '1');
  expect(screen.getByRole('status')).toHaveTextContent('2/2');
  expect(screen.getByRole('link')).toHaveAttribute('href', '#/course/append-course/learn');
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(screen.getByRole('progressbar')).toHaveAttribute('value', '1');
});
