import { type Pledge } from "../types/pledge";
import { type RegisterCustomerPayload } from "../types/customer";
import { request } from "./apiClient";

export function registerCustomer(payload: RegisterCustomerPayload): Promise<Pledge> {
  return request("/onboarding/register-customer/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
