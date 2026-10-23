import { afterEach, it, expect, vi } from "vitest";
import { configureApi, request, query, message } from "./api";
afterEach(() => vi.unstubAllGlobals());
it("explains the backend's sign-in failures without a generic request error", () => {
  expect(message({ code: "authentication_failed", status: 401 })).toBe(
    "Email or password was not accepted.",
  );
  expect(message({ code: "authentication_unavailable", status: 503 })).toContain(
    "sign-in service is unavailable",
  );
  expect(message({ code: "authentication_not_configured", status: 503 })).toContain(
    "not configured",
  );
  expect(message({ code: "invalid_token", status: 401 })).toContain(
    "could not be verified",
  );
});
it("uses protected cookies, CSRF, passive marker and the same command key", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    });
  vi.stubGlobal("fetch", fetch);
  configureApi("csrf", () => {});
  await request("/commands", {
    method: "POST",
    body: { type: "relay.auto" },
    key: "same-key",
    passive: true,
  });
  expect(fetch.mock.calls[0][0]).toBe("/api/v1/commands");
  expect(fetch.mock.calls[0][1]).toMatchObject({
    credentials: "include",
    headers: {
      "X-CSRF-Token": "csrf",
      "X-BB-Passive": "1",
      "Idempotency-Key": "same-key",
    },
  });
});
it("revokes local access on background authorization loss", async () => {
  const lost = vi.fn();
  configureApi("csrf", lost);
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ error: { code: "session_expired" } }),
      }),
  );
  await expect(request("/me", { passive: true })).rejects.toMatchObject({
    code: "session_expired",
  });
  expect(lost).toHaveBeenCalledOnce();
});
it("does not persist empty export filters", () =>
  expect(query({ tank_id: "", include_voided: false, origin: "all" })).toBe(
    "include_voided=false&origin=all",
  ));
