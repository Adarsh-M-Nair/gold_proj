import { useState } from "react";
import { Gem } from "lucide-react";
import { imageUrl } from "../../utils/imageUtils";

export function PledgeThumbnail({ path, name }: { path: string; name: string }) {
  const [failed, setFailed] = useState(false);
  if (!path || failed) return <span className="table-thumb placeholder"><Gem size={17} /></span>;
  return <img className="table-thumb" src={imageUrl(path)} alt={`${name} pledged jewellery`} onError={() => setFailed(true)} />;
}
