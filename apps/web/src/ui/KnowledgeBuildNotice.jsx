import React from 'react';
import { request } from './api.js';
import { UiLocaleContext } from './UiLocale';
import './KnowledgeBuildNotice.css';

/** Read-only projection of the existing background job; never starts a build. */
export function KnowledgeBuildNotice({ courseId, refreshToken = 0 }) {
    const { t } = React.useContext(UiLocaleContext);
    const [build, setBuild] = React.useState(null);
    const [error, setError] = React.useState(false);
    React.useEffect(() => {
        let disposed = false;
        let timer;
        setBuild(null);
        const poll = async () => {
            try {
                const next = await request(`/courses/${encodeURIComponent(courseId)}/knowledge-build-status`);
                if (disposed) return;
                setBuild(next);
                setError(false);
            } catch {
                if (disposed) return;
                setError(true);
            }
            timer = setTimeout(poll, document.hidden ? 30000 : 5000);
        };
        void poll();
        return () => { disposed = true; clearTimeout(timer); };
    }, [courseId, refreshToken]);
    if (error) return <p className="helper-note" role="alert">{t('autoTree.unavailable')}</p>;
    if (!build) return null;
    const ready = ['READY', 'READY_WITH_EXCEPTIONS', 'EXISTING_ACTIVE'].includes(build.status);
    let stage = build.status;
    if (ready && Object.values(build.upload_coverage || {}).some(count => count > 0)) stage = 'READY_WITH_EXCEPTIONS';
    if (!ready) {
        if (build.worker_enabled === false || build.billable_enabled === false) stage = 'DISABLED';
        else if (build.worker_running === false) stage = 'WORKER_UNAVAILABLE';
        else if (build.open_upload_batches) stage = 'PARSING';
    }
    const labels = {
        NOT_RECONCILED: 'waiting', WAITING_SOURCE: 'source', QUEUED: 'queued',
        BUILDING: 'building', READY: 'ready', EXISTING_ACTIVE: 'ready',
        READY_WITH_EXCEPTIONS: 'partial', BLOCKED: 'failed', FAILED: 'failed',
        UNKNOWN: 'unknown', DISABLED: 'disabled', NOT_ENABLED: 'disabled',
        WORKER_UNAVAILABLE: 'unavailable', PARSING: 'parsing',
    };
    const progress = build.progress;
    const totalStages = progress?.total_stages || 5;
    const done = progress?.completed_stages ?? (ready ? totalStages : 0);
    const phaseLabels = { ANALYSIS: 'analysis', OUTLINE: 'outline',
        TEACHING_SPEC: 'specs', SAVING: 'saving' };
    const phaseLabel = phaseLabels[progress?.last_observed_phase || progress?.phase];
    return <div className="helper-note knowledge-build-notice" role="status" aria-live="polite">
        <span>{t(`autoTree.${labels[stage] || 'waiting'}`)}</span>
        <progress max={totalStages} value={done} aria-label={t('autoTree.progress')}
            aria-valuetext={t('autoTree.progressStages', {done,total:totalStages})} />
        <small>
            {phaseLabel ? `${t(`autoTree.${phaseLabel}`)} · ` : ''}
            {t('autoTree.progressStages', {done,total:totalStages})}
            {progress?.files_total > 0 && <> · {t('autoTree.progressFiles', {
                done:progress.files_completed,total:progress.files_total})}</>}
            {progress?.saved_results > 0 && <> · {t('autoTree.progressSaved', {
                count:progress.saved_results})}</>}
        </small>
        {build.tree_version_id && <> · <a href={`#/course/${encodeURIComponent(courseId)}/learn`}>{t('autoTree.learn')}</a></>}
    </div>;
}
