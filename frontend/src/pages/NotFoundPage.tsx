import { Search } from "lucide-react";
import { Link } from "react-router-dom";

export function NotFoundPage() {
  return <section className="panel unavailable-panel"><span className="empty-icon"><Search size={22} /></span><h2>Page not found</h2><p>The page you’re looking for doesn’t exist.</p><Link className="button button-primary" to="/">Return to dashboard</Link></section>;
}
