import { type Pledge } from "../../types/pledge";
import { LoaderCircle, Gem, ArrowRight, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { PledgeThumbnail } from "./PledgeThumbnail";
import { formatDate } from "../../utils/formatting";

export function CustomerTable({
  records,
  loading,
  emptyText,
  onDelete,
}: {
  records: Pledge[];
  loading: boolean;
  emptyText: string;
  onDelete?: (record: Pledge) => void;
}) {
  if (loading) {
    return <div className="loading-state"><LoaderCircle className="spin" size={22} />Loading pledge records…</div>;
  }
  if (!records.length) {
    return <div className="empty-state"><span className="empty-icon"><Gem size={22} /></span><strong>No records found</strong><p>{emptyText}</p></div>;
  }
  return (
    <div className="table-scroll">
      <table className="pledge-table">
        <thead>
          <tr><th>Pledge ID</th><th>Customer</th><th>Phone</th><th>Aadhaar</th><th>Registered</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={record.id}>
              <td><Link className="pledge-code" to={`/pledges/${record.id}`}>{record.pledge_id}</Link></td>
              <td>
                <div className="customer-cell">
                  <PledgeThumbnail path={record.primary_photo} name={record.customer.full_name} />
                  <Link to={`/pledges/${record.id}`} className="customer-name">{record.customer.full_name}</Link>
                </div>
              </td>
              <td>{record.customer.phone_number}</td>
              <td><span className="masked-data">{record.customer.masked_aadhaar}</span></td>
              <td>{formatDate(record.registered_at)}</td>
              <td><span className={`status-pill status-${record.status.toLowerCase()}`}>{record.status.replaceAll("_", " ")}</span></td>
              <td className="row-actions">
                <Link className="icon-button" aria-label={`View ${record.pledge_id}`} to={`/pledges/${record.id}`}><ArrowRight size={16} /></Link>
                {onDelete && <button className="icon-button danger" type="button" aria-label={`Delete ${record.pledge_id}`} onClick={() => onDelete(record)}><Trash2 size={16} /></button>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
