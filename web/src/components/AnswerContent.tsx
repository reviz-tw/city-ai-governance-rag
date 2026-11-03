import {ReactNode, useEffect, useMemo, useRef, useState} from 'react';
import {advanceAnswerReveal, answerRevealOffsets} from '../lib/answer-reveal';
import {useLocale} from '../lib/locale';

/** Animate presentation only; copying, exports and persistence use the full answer. */
export function AnswerContent({content, start, animate, streaming = false, language, render}: {
  content: string; start?: number; animate: boolean; streaming?: boolean; language?: string;
  render: (content: string) => ReactNode;
}) {
  const {t} = useLocale();
  const [skipped, setSkipped] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const offsets = useMemo(() => start === undefined ? [content.length] : answerRevealOffsets(content, start, streaming), [content, start, streaming]);
  const [visibleEnd, setVisibleEnd] = useState(offsets[0]);
  const position = useRef(offsets[0]);
  const lastFrame = useRef(0);
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
    let frame: number;
    if (!lastFrame.current) lastFrame.current = performance.now();
    const tick = (now: number) => {
      if (now - lastFrame.current >= 32) {
        position.current = advanceAnswerReveal(offsets, position.current, Math.min(64, now - lastFrame.current));
        setVisibleEnd(position.current);
        lastFrame.current = now;
      }
      if (position.current < offsets[offsets.length - 1]) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [enabled, offsets]);

  return <>
    <div className="answer-content" dir="auto" lang={language} aria-busy={streaming || revealing}>
      {render(enabled ? content.slice(0, visibleEnd) : content)}
      {(revealing || (streaming && start !== undefined)) && <span className="streaming-mark" aria-hidden="true"/>}
    </div>
    {revealing && <button className="btn btn-ghost reveal-answer" onClick={() => setSkipped(true)}>{t('showFullAnswer')}</button>}
  </>;
}
