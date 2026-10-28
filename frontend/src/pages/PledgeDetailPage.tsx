import { useParams, Link } from "react-router-dom";
import { useState, useEffect } from "react";
import { type Pledge } from "../types/pledge";
import { getPledge } from "../services/pledgeService";
import { errorMessage } from "../services/apiClient";
import { LoaderCircle, ArrowLeft } from "lucide-react";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { PageHeading } from "../components/common/PageHeading";
import { formatDate } from "../utils/formatting";
import { imageUrl } from "../utils/imageUtils";

export function PledgeDetailPage() {
  const { id = "" } = useParams();
  const [record, setRecord] = useState<Pledge | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getPledge(id)
      .then((response) => active && setRecord(response))
      .catch((cause: unknown) => active && setError(errorMessage(cause)))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [id]);

  if (loading) return <div className="panel loading-state"><LoaderCircle className="spin" size={22} />Loading pledge…</div>;
  if (error || !record) return <section className="panel"><ErrorBanner message={error || "Pledge record not found."} /><Link className="text-link" to="/pledges"><ArrowLeft size={15} />Back to records</Link></section>;

  const images = record.items?.flatMap((item) => item.images) ?? [];
  return (
    <>
      <PageHeading eyebrow="Pledge details" title={record.pledge_id} description={`Registered ${formatDate(record.registered_at)}`} action={<Link to="/pledges" className="button button-quiet"><ArrowLeft size={16} />All records</Link>} />
      <section className="panel detail-panel">
        <div className="detail-grid">
          <div className="detail-block"><span>Customer</span><strong>{record.customer.full_name}</strong></div>
          <div className="detail-block"><span>Phone number</span><strong>{record.customer.phone_number}</strong></div>
          <div className="detail-block"><span>Aadhaar</span><strong>{record.customer.masked_aadhaar}</strong></div>
          <div className="detail-block"><span>Status</span><strong><span className={`status-pill status-${record.status.toLowerCase()}`}>{record.status.replaceAll("_", " ")}</span></strong></div>
          <div className="detail-block"><span>Pledge date</span><strong>{record.pledge_date ? formatDate(record.pledge_date) : formatDate(record.registered_at)}</strong></div>
          <div className="detail-block"><span>Jewellery category</span><strong>{record.items?.[0]?.category || "Not specified"}</strong></div>
        </div>
        <div className="detail-photos"><div className="panel-heading"><div><p className="eyebrow">Pledge photos</p><h2>{images.length} {images.length === 1 ? "image" : "images"}</h2></div></div>
          {images.length ? <div className="detail-image-grid">{images.map((image) => <figure key={image.id}><img src={imageUrl(image.thumbnail_url || image.image_url)} alt={image.original_filename || "Pledged jewellery"} /><figcaption>{image.image_type.toLowerCase()} · {image.embedding_status.toLowerCase()}</figcaption></figure>)}</div> : <p className="muted-copy">No image records are available.</p>}
        </div>
      </section>
    </>
  );
}
