import { type CustomerSummary } from "./customer";
import { type JewelleryItem } from "./jewellery";

export interface Pledge {
  id: string;
  pledge_id: string;
  pledge_code: string;
  customer: CustomerSummary;
  registered_at: string;
  status: string;
  primary_photo: string;
  branch_id?: string | null;
  pledge_date?: string;
  total_weight_grams?: string | null;
  estimated_value?: string | null;
  items?: JewelleryItem[];
}
