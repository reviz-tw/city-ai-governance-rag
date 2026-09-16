import {ReactNode, useEffect, useRef} from 'react';
import {X} from 'lucide-react';

/** Native modal semantics keep keyboard focus in the active (including nested) panel. */
export function WorkspacePanel({title, onClose, children, className = ''}: {
  title: string; onClose: () => void; children: ReactNode; className?: string;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current!;
    element.showModal();
    return () => element.close();
  }, []);
  return <dialog ref={dialog} className={`workspace-panel ${className}`} aria-label={title}
    onCancel={event => {event.preventDefault(); onClose();}}
    onKeyDown={event => {
      if (event.key !== 'Tab') return;
      const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button, a[href], input, select, textarea, summary, [tabindex]'))
        .filter(element => element.tabIndex >= 0 && !element.matches(':disabled') && element.getClientRects().length > 0);
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {event.preventDefault(); last?.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first?.focus();}
    }}
    onClick={event => {
      if (event.target !== event.currentTarget) return;
      const rect = event.currentTarget.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) onClose();
    }}>
    <div className="panel-header"><h2>{title}</h2><button className="btn btn-secondary btn-icon" onClick={onClose} aria-label="關閉 / Close" autoFocus><X size={16}/></button></div>
    <div className="panel-body">{children}</div>
  </dialog>;
}
