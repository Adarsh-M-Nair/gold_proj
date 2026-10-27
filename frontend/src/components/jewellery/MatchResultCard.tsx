import { Gem } from "lucide-react";
import type { PledgeMatch } from "../../types/matching";

export function similarityPercent(score: number | undefined): number {
  return Math.round((score ?? 0) * (score && score <= 1 ? 100 : 1));
}

export function MatchResultCard({
  match,
  index,
  onSelect,
}: {
  match: PledgeMatch;
  index: number;
  onSelect: () => void;
}) {
  const title = match.pledge_id || "Pledge record";
  const imageUrl = match.stored_image_url ?? match.images?.[0]?.url;
  return (
    <button className="match-card match-card-button" type="button" onClick={onSelect} aria-label={`View details for ${title}`}>
      {imageUrl ? (
        <img src={imageUrl} alt={`${title} pledged jewellery`} loading="lazy" />
      ) : (
        <span className="match-placeholder"><Gem size={25} /></span>
      )}
      <div className="match-card-content">
        <span className="match-rank">#{match.rank ?? index + 1} match</span>
        <strong>{title}</strong>
        <span>{[match.customer_name, match.jewellery_category].filter(Boolean).join(" · ") || "Registered pledge"}</span>
        <div className="match-score">{similarityPercent(match.similarity_score)}% similarity</div>
        <span className="match-details-hint">Click to view images and pledge details</span>
      </div>
    </button>
  );
}
