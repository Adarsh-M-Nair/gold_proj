import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { X, Gem, ExternalLink } from "lucide-react";
import type { PledgeMatch } from "../../types/matching";
import { formatDate } from "../../utils/formatting";
import { similarityPercent } from "./MatchResultCard";

export function MatchDetailsDialog({ match, onClose }: { match: PledgeMatch; onClose: () => void }) {
  const [imageIndex, setImageIndex] = useState(0);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const images = match.images ?? [];
  const activeImage = images[imageIndex]?.url ?? match.stored_image_url;
  const title = match.pledge_id || "Pledge record";

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="catalogue-dialog" role="dialog" aria-modal="true" aria-labelledby="match-details-title">
        <header className="catalogue-dialog-header">
          <div>
            <p className="eyebrow">Pledge match · #{match.rank ?? 1}</p>
            <h2 id="match-details-title">{title}</h2>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close match details"><X size={19} /></button>
        </header>
        <div className="catalogue-dialog-body">
          <div className="catalogue-gallery">
            {activeImage ? (
              <img className="catalogue-main-image" src={activeImage} alt={`${title} pledged jewellery view ${imageIndex + 1}`} />
            ) : (
              <div className="catalogue-image-empty"><Gem size={34} /><span>Pledge image unavailable</span></div>
            )}
            {images.length > 1 && (
              <div className="catalogue-thumbnails" aria-label="More pledge images">
                {images.map((image, index) => (
                  <button
                    key={image.id}
                    type="button"
                    className={index === imageIndex ? "selected" : ""}
                    onClick={() => setImageIndex(index)}
                    aria-label={`Show pledge image ${index + 1}${image.id === match.matched_image_id ? " (closest match)" : ""}`}
                    aria-pressed={index === imageIndex}
                  >
                    <img src={image.url} alt="" loading="lazy" />
                  </button>
                ))}
              </div>
            )}
          </div>
          <dl className="catalogue-match-facts">
            <div><dt>Similarity</dt><dd>{similarityPercent(match.similarity_score)}%</dd></div>
            <div><dt>Customer</dt><dd>{match.customer_name || "Not specified"}</dd></div>
            <div><dt>Phone</dt><dd>{match.phone_number || "Not specified"}</dd></div>
            <div><dt>Aadhaar</dt><dd>{match.masked_aadhaar || "Not specified"}</dd></div>
            <div><dt>Category</dt><dd>{match.jewellery_category || "Not specified"}</dd></div>
            <div><dt>Purity</dt><dd>{match.purity || "Not specified"}</dd></div>
            <div><dt>Registered</dt><dd>{match.registered_at ? formatDate(match.registered_at) : "Not specified"}</dd></div>
            <div><dt>Status</dt><dd>{match.pledge_status || "Not specified"}</dd></div>
            {match.jewellery_description && <div><dt>Description</dt><dd>{match.jewellery_description}</dd></div>}
          </dl>
        </div>
        {match.pledge_uuid && (
          <footer className="catalogue-dialog-footer">
            <Link className="button button-primary" to={`/pledges/${encodeURIComponent(match.pledge_uuid)}`}>
              <ExternalLink size={16} />Open pledge record
            </Link>
          </footer>
        )}
      </section>
    </div>
  );
}
