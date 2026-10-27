import { AlertCircle } from "lucide-react";

export function ErrorBanner({ message }: { message: string }) {
  return <div className="error-banner" role="alert"><AlertCircle size={17} /><span>{message}</span></div>;
}
