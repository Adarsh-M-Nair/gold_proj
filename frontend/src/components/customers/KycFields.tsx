import { ChevronDown, Users } from "lucide-react";
import { formatAadhaar } from "../../utils/formatting";

interface KycFieldsProps {
  fullName: string;
  phone: string;
  aadhaar: string;
  category: string;
  onFullNameChange: (value: string) => void;
  onPhoneChange: (value: string) => void;
  onAadhaarChange: (value: string) => void;
  onCategoryChange: (value: string) => void;
}

export function KycFields({ fullName, phone, aadhaar, category, onFullNameChange, onPhoneChange, onAadhaarChange, onCategoryChange }: KycFieldsProps) {
  return (
    <section className="form-section">
      <div className="section-title"><span className="section-icon"><Users size={18} /></span><div><h2>Customer information</h2><p>Enter the customer’s verified KYC details.</p></div></div>
      <div className="form-grid">
        <label className="field field-wide">Customer full name
          <input autoComplete="name" required maxLength={255} value={fullName} onChange={(event) => onFullNameChange(event.target.value)} placeholder="e.g. Ramesh Kumar" />
        </label>
        <label className="field">Phone number
          <input autoComplete="tel" inputMode="numeric" required maxLength={10} value={phone} onChange={(event) => onPhoneChange(event.target.value.replace(/\D/g, "").slice(0, 10))} placeholder="10-digit mobile number" />
          <small>Enter the 10-digit Indian mobile number.</small>
        </label>
        <label className="field">Aadhaar number
          <input inputMode="numeric" required maxLength={14} value={formatAadhaar(aadhaar)} onChange={(event) => onAadhaarChange(event.target.value.replace(/\D/g, "").slice(0, 12))} placeholder="XXXX XXXX XXXX" />
          <small>Only the last four digits are shown in pledge records.</small>
        </label>
        <label className="field">Jewellery category
          <span className="select-wrap"><select value={category} onChange={(event) => onCategoryChange(event.target.value)}><option value="OTHER">Select category</option><option value="RING">Ring</option><option value="BANGLE">Bangle</option><option value="EARRING">Earring</option><option value="NECKLACE">Necklace</option><option value="CHAIN">Chain</option><option value="OTHER">Other</option></select><ChevronDown size={16} /></span>
        </label>
      </div>
    </section>
  );
}
