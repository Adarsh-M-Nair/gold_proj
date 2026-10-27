import { Gem } from "lucide-react";
import type { MatchResponse } from "../../types/matching";

export function MatchResultCard({ match, index }: { match: NonNullable<MatchResponse["matches"]>[number]; index: number }) {
  return (
    <article className="match-card">
      {match.stored_image_url ? <img src={match.stored_image_url} alt={`Matched item for ${match.pledge_id ?? "pledge"}`} /> : <div className="match-placeholder"><Gem size={25} /></div>}
      <div className="match-card-content">
        <span className="match-rank">#{match.rank ?? index + 1} match</span>
        <strong>{match.pledge_id ?? "Pledge record"}</strong>
        <span>{match.customer_name ?? "Customer details unavailable"}</span>
        <div className="match-score">{Math.round((match.similarity_score ?? 0) * (match.similarity_score && match.similarity_score <= 1 ? 100 : 1))}% similarity</div>
      </div>
    </article>
  );
}
