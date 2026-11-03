import {ReactNode, useEffect, useMemo, useState} from 'react';
import {answerRevealOffsets} from '../lib/answer-reveal';
import {useLocale} from '../lib/locale';

/** Animate presentation only; copying, exports and persistence use the full answer. */
export function AnswerContent({content, start, animate, language, render}: {
  content: string; start?: number; animate: boolean; language?: string;
  render: (content: string) => ReactNode;
}) {
  const {t} = useLocale();
  const [skipped, setSkipped] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const offsets = useMemo(() => start === undefined ? [content.length] : answerRevealOffsets(content, start), [content, start]);
  const [visibleEnd, setVisibleEnd] = useState(offsets[0]);
  const enabled = animate && start !== undefined && !skipped && !reducedMotion;
  const revealing = enabled && visibleEnd < content.length;

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const changed = () => setReducedMotion(media.matches);
    media.addEventListener('change', changed);
    return () => media.removeEventListener('change', changed);
  }, []);

  useEffect(() => {
    if (!enabled) return;
    const started = performance.now();
    const duration = Math.min(5000, Math.max(500, offsets.length * 2));
    let frame: number;
    let previous = -Infinity;
    const tick = (now: number) => {
      const progress = Math.min(1, (now - started) / duration);
      if (now - previous >= 32 || progress === 1) {
        setVisibleEnd(offsets[Math.floor(progress * (offsets.length - 1))]);
        previous = now;
      }
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [enabled, offsets]);

  return <>
    <div className="answer-content" dir="auto" lang={language} aria-busy={revealing}>
      {render(enabled ? content.slice(0, visibleEnd) : content)}
      {revealing && <span className="streaming-mark" aria-hidden="true"/>}
    </div>
    {revealing && <button className="btn btn-ghost reveal-answer" onClick={() => setSkipped(true)}>{t('showFullAnswer')}</button>}
  </>;
}
