import { useParams, useNavigate, Link } from "react-router-dom";
import { useState, useEffect } from "react";
import { type MatchResponse, type PledgeMatch } from "../types/matching";
import { PageHeading } from "../components/common/PageHeading";
import { ArrowLeft, Sparkles, Search, AlertCircle } from "lucide-react";
import { MatchResultCard } from "../components/jewellery/MatchResultCard";
import { MatchDetailsDialog } from "../components/jewellery/MatchDetailsDialog";

export function MatchResultsPage() {
  const { searchId = "" } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState<MatchResponse | null>(null);
  const [selectedMatch, setSelectedMatch] = useState<PledgeMatch | null>(null);
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(`goldsafe-search-${searchId}`);
      if (stored) setResult(JSON.parse(stored) as MatchResponse);
    } catch {
      setResult(null);
    }
  }, [searchId]);

  return (
    <>
      <PageHeading eyebrow="Vision match engine" title="Identification results" description="Pledge records whose saved jewellery images are most similar to your photo." action={<Link to="/identify" className="button button-quiet"><ArrowLeft size={16} />New search</Link>} />
      {result ? (
        <section className="panel results-panel">
          <div className="results-summary"><div className="results-icon"><Sparkles size={20} /></div><div><strong>{result.matches?.length ?? 0} matching pledge records</strong><p>Search status: {result.status ?? "COMPLETED"}</p></div></div>
          {result.matches?.length ? <div className="match-grid">{result.matches.map((match, index) => (
            <MatchResultCard
              key={match.result_id ?? `${match.pledge_uuid ?? match.pledge_id}-${index}`}
              match={match}
              index={index}
              onSelect={() => setSelectedMatch(match)}
            />
          ))}</div> : <div className="empty-state"><span className="empty-icon"><Search size={22} /></span><strong>No matching pledge records found</strong><p>Try a clearer photo with good lighting and a plain background. Only pledge images that have been indexed can be matched.</p></div>}
        </section>
      ) : (
        <section className="panel unavailable-panel">
          <span className="empty-icon"><AlertCircle size={22} /></span>
          <h2>Results aren’t available</h2>
          <p>This search may have expired from this browser session. Start a new search to identify another item.</p>
          <button type="button" className="button button-primary" onClick={() => navigate("/identify")}>Back to identification</button>
        </section>
      )}
      {selectedMatch && <MatchDetailsDialog match={selectedMatch} onClose={() => setSelectedMatch(null)} />}
    </>
  );
}
