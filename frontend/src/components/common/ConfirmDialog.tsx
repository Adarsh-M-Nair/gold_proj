import { useEffect } from "react";
import { Trash2, LoaderCircle } from "lucide-react";

export function ConfirmDialog({
  title,
  description,
  busy,
  onCancel,
  onConfirm,
}: {
  title: string;
  description: string;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !busy) onCancel();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [busy, onCancel]);
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && !busy && onCancel()}>
      <section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <span className="dialog-icon"><Trash2 size={20} /></span>
        <h2 id="confirm-title">{title}</h2><p>{description}</p>
        <div className="dialog-actions"><button type="button" className="button button-quiet" disabled={busy} onClick={onCancel}>Cancel</button><button type="button" className="button button-danger" disabled={busy} onClick={onConfirm}>{busy ? <><LoaderCircle className="spin" size={15} />Archiving…</> : <><Trash2 size={15} />Archive pledge</>}</button></div>
      </section>
    </div>
  );
}
