import assert from "node:assert/strict";
import { after, test } from "node:test";
import { createServer } from "vite";

const server = await createServer({
  server: { middlewareMode: true, hmr: false, watch: null },
});
after(() => server.close());

const { ApiError, errorMessage, request } = await server.ssrLoadModule("/src/services/apiClient.ts");
const { getPledges, getPledge, deletePledge } = await server.ssrLoadModule("/src/services/pledgeService.ts");
const { registerCustomer } = await server.ssrLoadModule("/src/services/customerService.ts");
const { uploadImage } = await server.ssrLoadModule("/src/services/imageService.ts");
const { searchMatches } = await server.ssrLoadModule("/src/services/matchingService.ts");
const { getCatalogueItem } = await server.ssrLoadModule("/src/services/catalogueService.ts");
const { imageUrl, supportedTypes, maxImageBytes } = await server.ssrLoadModule("/src/utils/imageUtils.ts");
const { formatAadhaar, formatDate } = await server.ssrLoadModule("/src/utils/formatting.ts");

test("pledge service preserves search and pagination parameters", async (t) => {
  const result = { count: 0, next: null, previous: null, results: [] };
  const fetch = t.mock.method(globalThis, "fetch", async () => Response.json(result));
  assert.deepEqual(await getPledges({ search: "A & B", page: 2, pageSize: 5 }), result);
  const [url] = fetch.mock.calls[0].arguments;
  assert.equal(url, "/api/v1/pledges/?search=A+%26+B&page=2&page_size=5");
  await getPledges();
  assert.equal(fetch.mock.calls[1].arguments[0], "/api/v1/pledges/?page=1&page_size=10");
});

test("pledge detail and archive encode IDs and handle empty responses", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async (_, init) =>
    init?.method === "DELETE" ? new Response(null, { status: 204 }) : Response.json({ id: "a/b" }),
  );
  assert.deepEqual(await getPledge("a/b"), { id: "a/b" });
  assert.equal(await deletePledge("a/b"), undefined);
  assert.equal(fetch.mock.calls[0].arguments[0], "/api/v1/pledges/a%2Fb/");
  assert.deepEqual(fetch.mock.calls[1].arguments, ["/api/v1/pledges/a%2Fb/", { method: "DELETE" }]);
});

test("customer service preserves the onboarding payload", async (t) => {
  const payload = {
    customer: { full_name: "Test Customer", phone_number: "9876543210", aadhaar_number: "123456789012" },
    jewellery_item: { category: "RING" },
    images: [{ object_key: "test.jpg", capture_source: "UPLOAD", image_type: "FRONT" }],
  };
  const fetch = t.mock.method(globalThis, "fetch", async () => Response.json({ id: "pledge-1" }));
  assert.deepEqual(await registerCustomer(payload), { id: "pledge-1" });
  const [url, init] = fetch.mock.calls[0].arguments;
  assert.equal(url, "/api/v1/onboarding/register-customer/");
  assert.equal(init.method, "POST");
  assert.equal(init.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(init.body), payload);
});

test("image and matching services submit multipart images", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => Response.json({ status: "COMPLETED" }));
  const file = new File(["image"], "ring.jpg", { type: "image/jpeg" });
  await uploadImage(file);
  await searchMatches(file);
  assert.deepEqual(fetch.mock.calls.map(({ arguments: [url] }) => url), [
    "/api/v1/uploads/", "/api/v1/matching/search/",
  ]);
  for (const { arguments: [, init] } of fetch.mock.calls) {
    assert.equal(init.method, "POST");
    assert.equal(init.body.get("image").name, "ring.jpg");
    assert.equal(await init.body.get("image").text(), "image");
  }
});

test("matching service surfaces backend errors", async (t) => {
  t.mock.method(globalThis, "fetch", async () => Response.json({ detail: "Not found." }, { status: 404 }));
  await assert.rejects(searchMatches(new File(["image"], "ring.jpg")), {
    message: "Not found.",
    status: 404,
  });
});

test("catalogue service loads details for an encoded reference item", async (t) => {
  const details = {
    category: "Ring",
    item_id: "Ring_001",
    images: [{ filename: "1.webp", url: "/api/v1/catalogue/Ring/Ring_001/images/1.webp" }],
  };
  const fetch = t.mock.method(globalThis, "fetch", async () => Response.json(details));
  assert.deepEqual(await getCatalogueItem("Ring", "Ring/001"), details);
  assert.equal(fetch.mock.calls[0].arguments[0], "/api/v1/catalogue/Ring/Ring%2F001/");
});

test("API client surfaces network errors", async (t) => {
  t.mock.method(globalThis, "fetch", async () => { throw new TypeError("fetch failed"); });
  await assert.rejects(request("/pledges/"), (error) =>
    error instanceof ApiError && error.status === 0 && /Could not reach/.test(error.message),
  );
});

test("API client preserves server validation messages", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () =>
    Response.json({ phone_number: ["Invalid phone number."] }, { status: 400 }),
  );
  await assert.rejects(request("/pledges/"), { message: "Invalid phone number.", status: 400 });
  fetch.mock.mockImplementation(async () => new Response("unavailable", { status: 503 }));
  await assert.rejects(request("/pledges/"), { message: "The API request failed (503).", status: 503 });
});

test("image helpers retain supported formats, size limit, and legacy paths", () => {
  assert.deepEqual(supportedTypes, ["image/jpeg", "image/png", "image/webp"]);
  assert.equal(maxImageBytes, 10 * 1024 * 1024);
  assert.equal(imageUrl("https://example.test/ring.jpg"), "https://example.test/ring.jpg");
  assert.equal(imageUrl("/media/ring.jpg"), "/media/ring.jpg");
  assert.equal(imageUrl("static/uploads/ring.jpg"), "/static/uploads/ring.jpg");
  assert.equal(imageUrl("pledges/ring.jpg"), "/media/pledges/ring.jpg");
});

test("formatting and user-facing errors are preserved", () => {
  assert.equal(formatAadhaar("1234-5678-9012"), "1234 5678 9012");
  assert.equal(formatAadhaar("123456789012345"), "1234 5678 9012");
  assert.equal(formatDate("invalid"), "invalid");
  assert.match(formatDate("2026-10-27T12:00:00Z"), /27.*Oct.*2026/);
  assert.equal(errorMessage(new Error("Upload failed")), "Upload failed");
  assert.equal(errorMessage(null), "Something went wrong. Please try again.");
});
