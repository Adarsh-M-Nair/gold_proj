import { useSearchParams, Link } from "react-router-dom";
import { useState, useEffect } from "react";
import { type Pledge } from "../types/pledge";
import { getPledges, deletePledge } from "../services/pledgeService";
import { errorMessage } from "../services/apiClient";
import { PageHeading } from "../components/common/PageHeading";
import { Plus, Search, X, Check, ChevronLeft, ChevronRight } from "lucide-react";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { CustomerTable } from "../components/customers/CustomerTable";
import { ConfirmDialog } from "../components/common/ConfirmDialog";
import { useDebounce } from "../hooks/useDebounce";

export function PledgeRecordsPage() {
  const [searchParams] = useSearchParams();
  const [records, setRecords] = useState<Pledge[]>([]);
  const [count, setCount] = useState(0);
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Pledge | null>(null);
  const [notice, setNotice] = useState("");
  const debouncedSearch = useDebounce(search, search ? 250 : 0);

  useEffect(() => {
    if (search !== debouncedSearch) return;
    let active = true;
    setLoading(true);
    setError("");
    getPledges({ search: debouncedSearch.trim(), page, pageSize })
      .then((response) => {
        if (!active) return;
        setRecords(response.results);
        setCount(response.count);
      })
      .catch((cause: unknown) => active && setError(errorMessage(cause)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [page, search, debouncedSearch]);

  const pages = Math.max(1, Math.ceil(count / pageSize));

  async function confirmDelete() {
    if (!pendingDelete) return;
    setDeletingId(pendingDelete.id);
    setError("");
    try {
      await deletePledge(pendingDelete.id);
      setNotice(`${pendingDelete.pledge_id} was archived.`);
      setPendingDelete(null);
      if (records.length === 1 && page > 1) setPage(page - 1);
      else {
        const response = await getPledges({ search: search.trim(), page, pageSize });
        setRecords(response.results);
        setCount(response.count);
      }
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <>
      <PageHeading
        eyebrow="Customer database"
        title="Pledge records"
        description="Search, review, and manage registered customer pledges."
        action={<Link className="button button-primary" to="/register"><Plus size={17} />New customer</Link>}
      />
      <section className="panel records-panel">
        <div className="records-toolbar">
          <div>
            <h2>All pledges <span className="count-pill">{count}</span></h2>
            <p>Search by customer name, phone, Aadhaar, or pledge ID.</p>
          </div>
          <label className="search-field">
            <Search size={17} />
            <input
              aria-label="Search pledge records"
              placeholder="Search records…"
              value={search}
              onChange={(event) => { setSearch(event.target.value); setPage(1); setNotice(""); }}
            />
            {search && <button type="button" aria-label="Clear search" onClick={() => setSearch("")}><X size={15} /></button>}
          </label>
        </div>
        {notice && <div className="success-banner"><Check size={17} />{notice}<button type="button" onClick={() => setNotice("")}><X size={15} /></button></div>}
        {error && <ErrorBanner message={error} />}
        <CustomerTable
          records={records}
          loading={loading}
          emptyText={search ? "No records match that search. Try a name, phone number, Aadhaar, or pledge ID." : "No pledge records are available yet."}
          onDelete={setPendingDelete}
        />
        <div className="pagination">
          <span>Showing {count === 0 ? 0 : (page - 1) * pageSize + 1}–{Math.min(page * pageSize, count)} of {count}</span>
          <div className="pagination-controls">
            <button type="button" aria-label="Previous page" disabled={page <= 1 || loading} onClick={() => setPage(page - 1)}><ChevronLeft size={17} />Previous</button>
            <span>Page <strong>{page}</strong> of {pages}</span>
            <button type="button" aria-label="Next page" disabled={page >= pages || loading} onClick={() => setPage(page + 1)}>Next<ChevronRight size={17} /></button>
          </div>
        </div>
      </section>
      {pendingDelete && (
        <ConfirmDialog
          title="Archive this pledge?"
          description={`${pendingDelete.pledge_id} for ${pendingDelete.customer.full_name} will be hidden from the active pledge list. This action can’t be undone here.`}
          busy={deletingId === pendingDelete.id}
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => void confirmDelete()}
        />
      )}
    </>
  );
}

const pageSize = 10;
