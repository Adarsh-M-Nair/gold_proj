import { useParams, useNavigate, Link } from "react-router-dom";
import { useState, useEffect } from "react";
import { type MatchResponse } from "../types/matching";
import { PageHeading } from "../components/common/PageHeading";
import { ArrowLeft, Sparkles, Search, AlertCircle } from "lucide-react";
import { MatchResultCard } from "../components/jewellery/MatchResultCard";

export function MatchResultsPage() {
  const { searchId = "" } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState<MatchResponse | null>(null);
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
      <PageHeading eyebrow="Vision match engine" title="Identification results" description="Similarity results returned by the matching service." action={<Link to="/identify" className="button button-quiet"><ArrowLeft size={16} />New search</Link>} />
      {result ? (
        <section className="panel results-panel">
          <div className="results-summary"><div className="results-icon"><Sparkles size={20} /></div><div><strong>{result.matches?.length ?? 0} possible matches</strong><p>Search status: {result.status ?? "COMPLETED"}</p></div></div>
          {result.matches?.length ? <div className="match-grid">{result.matches.map((match, index) => (
            <MatchResultCard key={match.result_id ?? `${match.pledge_id}-${index}`} match={match} index={index} />
          ))}</div> : <div className="empty-state"><span className="empty-icon"><Search size={22} /></span><strong>No close matches found</strong><p>Try a clearer photo with good lighting and a plain background.</p></div>}
        </section>
      ) : (
        <section className="panel unavailable-panel">
          <span className="empty-icon"><AlertCircle size={22} /></span>
          <h2>Results aren’t available</h2>
          <p>This search may have expired from this browser session. The matching API is also not included in the current Django backend yet.</p>
          <button type="button" className="button button-primary" onClick={() => navigate("/identify")}>Back to identification</button>
        </section>
      )}
    </>
  );
}
