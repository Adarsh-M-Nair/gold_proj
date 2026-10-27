import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeading } from "../components/common/PageHeading";
import { CustomerForm } from "../components/customers/CustomerForm";

export function RegisterCustomerPage() {
  return (
    <>
      <PageHeading
        eyebrow="Client onboarding"
        title="Register a customer"
        description="Create a pledge record with customer KYC details and clear jewellery photos."
        action={<Link className="button button-quiet" to="/pledges"><ArrowLeft size={16} />Pledge records</Link>}
      />
      <CustomerForm />
    </>
  );
}
