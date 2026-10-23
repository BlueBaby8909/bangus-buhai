// Offline visual review of the production bundle. Every request is intercepted.
const { chromium, expect } = require("@playwright/test");
const fs = require("node:fs/promises");
const path = require("node:path");
const dist = path.resolve(__dirname, "../dist");
const output = path.resolve(__dirname, "../../.verification");
const now = new Date().toISOString();
const tank = { id: "tank-a", name: "Nursery A", version: 1, archived_at: null };
const device = {
  id: "device-a",
  device_id: "BB-AABBCC112233",
  display_name: "Nursery sensor",
  verified: true,
  archived_at: null,
  version: 1,
  binding: { id: "binding-a", tank_id: tank.id },
  configuration: { status: "confirmed" },
};
const manual = {
  id: "manual-a",
  origin: "manual",
  version: 1,
  measured_at: now,
  received_at: now,
  temperature_c: 28.2,
  ph: 7.4,
  turbidity_ntu: 12,
  voided: false,
};
const reading = {
  id: "capture-a",
  origin: "device",
  device_id: device.device_id,
  binding_id: "binding-a",
  measured_at: now,
  received_at: now,
  telemetry: {
    relay: { on: false, mode: "auto" },
    readings: {
      temperature: {
        value: 28.3,
        source: "sensor",
        validity: "valid",
        sample_age_ms: 0,
      },
      ph: { value: 7, source: "default", validity: "valid" },
      turbidity: { value: 11, source: "sensor", validity: "valid" },
    },
  },
};
const errors = [];
(async () => {
  const browser = await chromium.launch({ channel: "msedge", headless: true });
  try {
    const page = await browser.newPage({ reducedMotion: "reduce" });
    page.on("pageerror", (e) => errors.push(e.message));
    await page.routeWebSocket("**/stream?**", (socket) =>
      socket.send(JSON.stringify({ v: 1, type: "ready", cursor: "preview" })),
    );
    await page.route("**/*", async (route) => {
      const url = new URL(route.request().url());
      if (url.origin !== "http://127.0.0.1:5199") return route.abort();
      const p = url.pathname;
      if (p.startsWith("/api/v1")) {
        let json;
        if (p.endsWith("/me"))
          json = {
            csrf_token: "preview",
            hatcheries: [{ id: "hatchery-a", name: "Test hatchery" }],
          };
        else if (p.includes("/tank-summaries"))
          json = {
            items: [
              { tank, devices: [{ ...device, latest_reading: reading }] },
            ],
            server_time: now,
            next_cursor: null,
          };
        else if (p.includes("/commands/latest"))
          json = {
            command_id: "command-a",
            status: "applied",
            command: { type: "relay.auto" },
            attempts: [],
            results: [
              { result: "applied", reason: "applied", observed_on: false },
            ],
          };
        else if (
          p.endsWith("/device-claims") &&
          route.request().method() === "POST"
        )
          json = {
            id: "claim-a",
            device_id: device.device_id,
            state: "pending_proof",
            expires_at: now,
          };
        else if (p.includes("/device-claims/"))
          json = {
            id: "claim-a",
            device_id: device.device_id,
            state: "pending_proof",
            expires_at: now,
          };
        else if (p.endsWith("/readings"))
          json = {
            items: [reading, manual],
            next_cursor: null,
            stream_cursor: "preview",
          };
        else if (p.includes("/revisions"))
          json = {
            items: [
              {
                ...manual,
                revision_id: "revision-a",
                changed_at: now,
                actor_id: "operator-a",
              },
            ],
          };
        else if (p.endsWith("/tanks/tank-a")) json = tank;
        else if (p.endsWith("/tanks"))
          json = { items: [tank], next_cursor: null };
        else if (p.endsWith("/devices"))
          json = { items: [device], next_cursor: null };
        else
          throw new Error(
            "Unexpected preview request: " + route.request().method() + " " + p,
          );
        return route.fulfill({ json });
      }
      const name = p.startsWith("/assets/")
        ? decodeURIComponent(p.slice(1))
        : "index.html";
      const file = path.resolve(dist, name);
      if (!file.startsWith(dist + path.sep))
        throw new Error("Unexpected asset path");
      const types = {
        ".js": "text/javascript",
        ".css": "text/css",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".html": "text/html",
      };
      await route.fulfill({
        body: await fs.readFile(file),
        contentType: types[path.extname(file)],
      });
    });
    async function shot(name, width) {
      const dialog = page.getByRole("dialog");
      if (await dialog.count()) {
        await expect(dialog.locator("h2")).toHaveCSS(
          "font-size",
          width >= 768 ? "24px" : "20px",
        );
        await expect(dialog).toHaveCSS(
          "padding",
          width >= 768 ? "32px" : "24px",
        );
      }
      await page.screenshot({
        path: path.join(output, `style-${name}-${width}.png`),
        fullPage: !(await dialog.count()),
      });
      const bounds = await page.evaluate(() => ({
        doc: document.documentElement.scrollWidth,
        width: innerWidth,
        dialog: (() => {
          const e = document.querySelector("dialog[open]");
          if (!e) return null;
          const r = e.getBoundingClientRect();
          return {
            left: r.left,
            right: r.right,
            width: r.width,
            scroll: e.scrollWidth,
            client: e.clientWidth,
          };
        })(),
      }));
      if (bounds.doc > bounds.width)
        throw new Error("Page overflow: " + name + JSON.stringify(bounds));
      if (
        bounds.dialog &&
        (bounds.dialog.left < 0 ||
          bounds.dialog.right > width ||
          bounds.dialog.scroll > bounds.dialog.client + 1)
      )
        throw new Error("Dialog overflow: " + name + JSON.stringify(bounds));
      if (
        bounds.dialog &&
        Math.abs((width - bounds.dialog.width) / 2 - bounds.dialog.left) > 2
      )
        throw new Error("Uncentered dialog");
    }
    for (const width of [360, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("http://127.0.0.1:5199/tanks/tank-a");
      await expect(
        page.getByRole("heading", { name: "Relay control" }),
      ).toBeVisible();
      await expect(
        page.getByText("Manual entry", { exact: true }),
      ).toBeVisible();
      await expect(page.locator(".history-panel")).toHaveCSS(
        "padding",
        width >= 768 ? "28px" : "24px",
      );
      await expect(
        page.locator(".chart").getByRole("application"),
      ).toBeVisible();
      await shot("tank", width);
      await page.getByRole("button", { name: "ON", exact: true }).click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await shot("relay", width);
      await page.keyboard.press("Escape");
      await expect(
        page.getByRole("button", { name: "ON", exact: true }),
      ).toBeFocused();
      await page
        .getByRole("button", { name: "Add measurement", exact: true })
        .click();
      await shot("manual", width);
      await page
        .getByRole("dialog")
        .getByRole("button", { name: "Add measurement", exact: true })
        .scrollIntoViewIfNeeded();
      await expect(
        page
          .getByRole("dialog")
          .getByRole("button", { name: "Add measurement", exact: true }),
      ).toBeInViewport();
      await page.keyboard.press("Escape");
      await page
        .getByRole("button", { name: "Revisions", exact: true })
        .click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await shot("revisions", width);
      await page.keyboard.press("Escape");
      await page.goto("http://127.0.0.1:5199/data");
      await page
        .getByRole("button", { name: "Download CSV", exact: true })
        .click();
      await shot("export", width);
      await page.keyboard.press("Escape");
      await page.goto("http://127.0.0.1:5199/tanks");
      await page
        .getByRole("button", { name: "Add device", exact: true })
        .click();
      await shot("claim", width);
      await page
        .getByLabel("Device ID", { exact: true })
        .fill(device.device_id);
      await page
        .getByLabel("Private claim code", { exact: true })
        .fill("x".repeat(43));
      await page.getByLabel("Destination tank").selectOption(tank.id);
      await page.getByRole("button", { name: "Start device claim" }).click();
      await expect(
        page.getByText("Waiting for the device to prove its identity."),
      ).toBeVisible();
      await expect(
        page.getByLabel("Private claim code", { exact: true }),
      ).toHaveCount(0);
      await shot("claim-progress", width);
      await page.keyboard.press("Escape");
      console.log(
        `${width}px: history, manual, revisions, CSV, claim/progress, relay; centered dialogs, no overflow, Escape/focus PASS`,
      );
    }
    if (errors.length) throw new Error(errors.join("\n"));
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
