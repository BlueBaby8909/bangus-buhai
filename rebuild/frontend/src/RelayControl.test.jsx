import { it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RelayControl from "./RelayControl";
import { request } from "./api";
vi.mock("./api", async () => ({
  ...(await vi.importActual("./api")),
  request: vi.fn(),
}));
afterEach(() => vi.clearAllMocks());
const device = {
  device_id: "BB-AABBCC112233",
  verified: true,
  binding: { id: "binding" },
  configuration: { status: "confirmed" },
};
it("retries uncertain delivery with the same idempotency key without optimistic output", async () => {
  let posts = 0;
  request.mockImplementation((url, options) => {
    if (options?.method === "POST") {
      posts++;
      return posts === 1
        ? Promise.reject(new TypeError("network unavailable"))
        : Promise.resolve({
            command_id: "c",
            status: "queued",
            attempts: [],
            results: [],
          });
    }
    return Promise.resolve(null);
  });
  const user = userEvent.setup();
  render(
    <RelayControl
      hatchery="h"
      device={device}
      reading={{ telemetry: { relay: { on: false, mode: "demo" } } }}
    />,
  );
  await user.click(screen.getByRole("button", { name: "ON", exact: true }));
  await user.click(
    screen.getByRole("button", { name: "Send ON", exact: true }),
  );
  await user.click(
    await screen.findByRole("button", { name: "Retry the same command" }),
  );
  const calls = request.mock.calls.filter(
    ([, options]) => options?.method === "POST",
  );
  expect(calls).toHaveLength(2);
  expect(calls[0][1].key).toBe(calls[1][1].key);
  expect(calls[0][1].body).toEqual({ type: "relay.set", desired_on: true });
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "ON", exact: true }),
    ).toBeDisabled(),
  );
  expect(screen.getByText("OFF", { selector: "strong" })).toBeInTheDocument();
});
it("shows uncertainty and keeps telemetry separate from an older applied command", async () => {
  request.mockResolvedValue({
    command_id: "c",
    status: "timed_out",
    timed_out_at: "now",
    attempts: [],
    results: [{ result: "applied", reason: "applied", observed_on: true }],
  });
  render(
    <RelayControl
      hatchery="h"
      device={device}
      reading={{ telemetry: { relay: { on: false, mode: "demo" } } }}
    />,
  );
  expect(
    await screen.findByText("Timed out · outcome uncertain"),
  ).toBeInTheDocument();
  expect(screen.getByText("OFF", { selector: "strong" })).toBeInTheDocument();
  expect(
    screen.getByText(/GPIO ON confirmed for this command/),
  ).toBeInTheDocument();
});
