import { useNavigate, Link } from "react-router-dom";
import { useState, useEffect } from "react";
import { type Pledge } from "../types/pledge";
import { getPledges } from "../services/pledgeService";
import { errorMessage } from "../services/apiClient";
import { PageHeading } from "../components/common/PageHeading";
import { Plus, Search, Gem, Clock3, BadgeCheck, ArrowRight, Users, Sparkles } from "lucide-react";
import { StatCard } from "../components/dashboard/StatCard";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { CustomerTable } from "../components/customers/CustomerTable";

export function DashboardPage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [records, setRecords] = useState<Pledge[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getPledges({ page: 1, pageSize: 5 })
      .then((response) => {
        if (!active) return;
        setRecords(response.results);
        setTotal(response.count);
      })
      .catch((cause: unknown) => active && setError(errorMessage(cause)))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  return (
    <>
      <PageHeading
        eyebrow="Overview"
        title="Good day, team."
        description="A clear view of today’s customer pledges and jewellery activity."
        action={<Link className="button button-primary" to="/register"><Plus size={17} />Register Customer</Link>}
      />
      <form className="dashboard-search" onSubmit={(event) => {
        event.preventDefault();
        navigate(`/pledges${query.trim() ? `?search=${encodeURIComponent(query.trim())}` : ""}`);
      }}>
        <Search size={18} />
        <input aria-label="Search all customer records" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by customer, phone, Aadhaar, or pledge ID…" />
        <button className="button button-primary" type="submit">Search records</button>
      </form>
      <section className="metric-grid" aria-label="Pledge summary">
        <StatCard label="Total pledges" value={total ?? "—"} note="Non-archived records" icon={<Gem size={19} />} />
        <StatCard label="Recent records" value={records.length} note="Latest records loaded" icon={<Clock3 size={19} />} tone="gold" />
        <StatCard label="API status" value={error ? "Offline" : loading ? "Checking" : "Online"} note={error ? "Unable to reach Django" : "Django REST API"} icon={<BadgeCheck size={19} />} tone={error ? "red" : "green"} />
      </section>

      <section className="panel dashboard-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Latest activity</p>
            <h2>Recent pledge records</h2>
          </div>
          <Link className="text-link" to="/pledges">View all records <ArrowRight size={16} /></Link>
        </div>
        {error ? <ErrorBanner message={error} /> : (
          <CustomerTable records={records} loading={loading} emptyText="No pledge records yet. Register your first customer to get started." />
        )}
      </section>

      <section className="quick-actions">
        <Link to="/register" className="quick-action-card">
          <span className="quick-action-icon red"><Users size={20} /></span>
          <span><strong>Register a customer</strong><small>Capture KYC details and pledge photos</small></span>
          <ArrowRight size={18} />
        </Link>
        <Link to="/identify" className="quick-action-card">
          <span className="quick-action-icon gold"><Sparkles size={20} /></span>
          <span><strong>Identify jewellery</strong><small>Prepare a photo for similarity matching</small></span>
          <ArrowRight size={18} />
        </Link>
      </section>
    </>
  );
}
