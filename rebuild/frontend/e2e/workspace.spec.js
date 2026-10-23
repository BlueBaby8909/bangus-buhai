import { test, expect } from "@playwright/test";
test.describe.configure({ mode: "serial" });
async function context(request) {
  return (await request.get("http://127.0.0.1:8019/__test/context")).json();
}
async function login(page) {
  await page.goto("/");
  await page.getByLabel("Email", { exact: true }).fill("operator@example.test");
  await page
    .getByLabel("Password", { exact: true })
    .fill("correct-test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Hatchery monitor" }),
  ).toBeVisible();
}
test("protected login, reload, hatchery isolation and logout", async ({
  page,
  request,
}) => {
  const info = await context(request);
  await page.setViewportSize({ width: 360, height: 900 });
  await page.goto("/tanks/" + info.tank);
  await expect(
    page.getByRole("heading", { name: "Welcome back" }),
  ).toBeVisible();
  await page.getByLabel("Email", { exact: true }).fill("operator@example.test");
  await page.getByLabel("Password", { exact: true }).fill("wrong");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page
    .getByLabel("Password", { exact: true })
    .fill("correct-test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Nursery A", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Nursery A", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Account and hatchery", exact: true })
    .click();
  await page.getByLabel("Hatchery", { exact: true }).selectOption(info.other);
  await page.getByRole("link", { name: "Dashboard", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Second hatchery tank" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Nursery A", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Account and hatchery", exact: true })
    .click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome back" }),
  ).toBeVisible();
});
test("live readings, explicit device choice, manual corrections and CSV", async ({
  page,
  request,
}) => {
  await page.addInitScript(() => {
    window.__testSockets = [];
    const Native = window.WebSocket;
    window.WebSocket = class extends Native {
      constructor(...args) {
        super(...args);
        window.__testSockets.push(this);
      }
    };
  });
  const info = await context(request);
  await login(page);
  await expect(
    page.getByText("Live feed connected", { exact: true }),
  ).toBeVisible();
  await request.post("http://127.0.0.1:8019/__test/reading", {
    data: { temperature: 29.1 },
  });
  await expect(page.locator(".metric-temperature strong")).toContainText(
    "29.1",
  );
  await page
    .getByLabel("Overview device")
    .selectOption({ label: "Second sensor" });
  await expect(page.locator(".metrics").getByText("No reading")).toHaveCount(3);
  await page.getByLabel("Overview device").selectOption(info.device);
  await expect(page.locator(".metric-temperature strong")).toContainText(
    "29.1",
  );
  await page.goto("/tanks/" + info.tank);
  await expect(
    page.getByText("Live feed connected", { exact: true }),
  ).toBeVisible();
  await expect(
    page.locator(".metrics").getByText("Default · unverified"),
  ).toBeVisible();
  await request.post("http://127.0.0.1:8019/__test/reading");
  await expect(page.locator(".metric-temperature strong")).toContainText(
    "29.4",
  );
  await page.evaluate(() => window.__testSockets.at(-1).close());
  await request.post("http://127.0.0.1:8019/__test/reading", {
    data: { temperature: 30.2 },
  });
  await expect(page.locator(".metric-temperature strong")).toContainText(
    "30.2",
  );
  await expect(
    page.getByText("Live feed connected", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Viewing device")
    .selectOption({ label: "Second sensor" });
  await expect(page.locator(".metrics").getByText("No reading")).toHaveCount(3);
  await expect(
    page.getByRole("button", { name: "ON", exact: true }),
  ).toBeDisabled();
  await page.getByLabel("Viewing device").selectOption(info.device);
  await page
    .getByRole("button", { name: "Add measurement", exact: true })
    .click();
  await page.getByRole("dialog").getByLabel("pH", { exact: true }).fill("7.8");
  await page.getByRole("dialog").getByLabel("Notes").fill(" =SUM(1,2)");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Add measurement", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const row = page.getByRole("row").filter({ hasText: "Manual entry" }).first();
  await expect(row).toContainText("7.8");
  await row.getByRole("button", { name: "Correct", exact: true }).click();
  await page.getByRole("dialog").getByLabel("pH", { exact: true }).fill("8.1");
  await page
    .getByRole("dialog")
    .getByLabel("Reason for this change")
    .fill("Correct test transcription");
  await page.getByRole("button", { name: "Save correction" }).click();
  await expect(row).toContainText("v2");
  await row.getByRole("button", { name: "Void", exact: true }).click();
  await page.getByLabel("Reason for this change").fill("Test void");
  await page.getByRole("button", { name: "Void entry" }).click();
  await page.getByLabel("Include voided").check();
  await expect(row).toContainText("voided");
  await row.getByRole("button", { name: "Restore", exact: true }).click();
  await page.getByLabel("Reason for this change").fill("Restore test");
  await page.getByRole("button", { name: "Restore entry" }).click();
  await expect(row).toContainText("v4");
  await row.getByRole("button", { name: "Revisions" }).click();
  await expect(page.getByRole("dialog")).toContainText("Version 1");
  await page.keyboard.press("Escape");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export CSV", exact: true }).click();
  const download = await downloadPromise;
  expect(await download.failure()).toBeNull();
  const stream = await download.createReadStream();
  let csv = "";
  for await (const part of stream) csv += part.toString();
  expect(csv).toContain("operator_reported_measurement");
  expect(csv).toContain("' =SUM");
});
test("relay intent stays pending until simulated device result; refresh recovers it", async ({
  page,
  request,
}) => {
  const info = await context(request);
  await login(page);
  await page.goto("/tanks/" + info.tank);
  await expect(
    page.getByRole("button", { name: "ON", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "ON", exact: true }).click();
  await page.getByRole("button", { name: "Send ON", exact: true }).click();
  await expect(page.getByText("queued", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("queued", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "ON", exact: true }),
  ).toBeDisabled();
  await request.post("http://127.0.0.1:8019/__test/apply");
  await expect(page.getByText(/Last command result: applied/)).toBeVisible();
  for (const action of ["OFF", "AUTO"]) {
    // This fixture freezes time; give successive intents distinct issue times.
    await request.post("http://127.0.0.1:8019/__test/advance", {
      data: { seconds: 1 },
    });
    await page.getByRole("button", { name: action, exact: true }).click();
    await page
      .getByRole("button", { name: "Send " + action, exact: true })
      .click();
    await expect(page.getByText("queued", { exact: true })).toBeVisible();
    await request.post("http://127.0.0.1:8019/__test/apply");
    await expect(page.getByText(/Last command result: applied/)).toBeVisible();
  }
});
test("tank lifecycle and device claim confirmation use actual backend states", async ({
  page,
  request,
}) => {
  const info = await context(request);
  await login(page);
  await expect(
    page
      .getByRole("navigation")
      .getByRole("link", { name: "Devices", exact: true }),
  ).toHaveCount(0);
  await page.goto("/devices");
  await expect(page).toHaveURL(/\/tanks$/);
  await page
    .getByText("Unassigned and archived devices", { exact: true })
    .click();
  await expect(page.getByLabel("Include archived devices")).toBeVisible();
  await page.getByRole("link", { name: "Tanks", exact: true }).click();
  await page.getByRole("button", { name: "New tank", exact: true }).click();
  await page.getByLabel("Tank name").fill("Browser nursery");
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Browser nursery", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("heading", { name: "Browser nursery", exact: true })
    .click();
  await page.getByRole("button", { name: "Edit tank", exact: true }).click();
  await page.getByLabel("Tank name").fill("Browser nursery renamed");
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Browser nursery renamed", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit tank", exact: true }).click();
  await page.getByRole("button", { name: "Archive tank", exact: true }).click();
  await expect(page.getByText("Archived", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Edit tank", exact: true }).click();
  await page.getByRole("button", { name: "Restore tank", exact: true }).click();
  await expect(page.getByText("Active tank", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Tanks", exact: true }).click();
  await page.getByRole("button", { name: "Add device", exact: true }).click();
  await page.getByLabel("Device ID", { exact: true }).fill(info.claim_device);
  await page.getByLabel("Private claim code").fill(info.claim_code);
  await page.getByLabel("Destination tank").selectOption(info.tank);
  await page.getByRole("button", { name: "Start device claim" }).click();
  await expect(page.getByText("pending proof", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Private claim code")).toHaveCount(0);
  await request.post("http://127.0.0.1:8019/__test/prove");
  await expect(
    page.getByText("Device assignment confirmed.", { exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
});
test("all pages, mobile header, account menu and keyboard dialogs", async ({
  page,
  request,
}) => {
  test.setTimeout(90000);
  const info = await context(request);
  await page.goto("/login");
  await expect(
    page.getByRole("heading", { name: "Welcome back" }),
  ).toBeVisible();
  for (const width of [360, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.screenshot({
      path: `../.verification/ui-all-login-${width}.png`,
      fullPage: true,
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
  }
  await login(page);
  const routes = [
    ["/", "dashboard", "Hatchery monitor"],
    ["/tanks", "tanks", "Tanks"],
    ["/tanks/" + info.tank, "tank", "Tank details"],
    ["/data", "data", "Data export"],
    ["/alerts", "alerts", "Alerts"],
  ];
  for (const width of [360, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    for (const [route, name, title] of routes) {
      await page.goto(route);
      const header = page.getByRole("banner");
      await expect(header.locator(".header-title")).toHaveText(title);
      if (name === "dashboard" || name === "tank")
        await expect(
          page.getByText("Live feed connected", { exact: true }),
        ).toBeVisible();
      if (name === "tanks")
        await expect(
          page.getByRole("heading", { name: "Nursery A", exact: true }),
        ).toBeVisible();
      if (name === "tank") {
        await expect(
          page.locator(".chart").getByRole("application"),
        ).toBeVisible();
        await expect(
          page.locator(".history-panel tbody tr").first(),
        ).toBeVisible();
      }
      if (name === "data") {
        await page
          .getByLabel("History tank", { exact: true })
          .selectOption(info.tank);
        await expect(
          page.getByRole("heading", { name: "Recent readings", exact: true }),
        ).toBeVisible();
        await expect(
          page.locator(".history-panel tbody tr").first(),
        ).toBeVisible();
        await expect(
          page.getByRole("button", { name: "Add measurement", exact: true }),
        ).toHaveCount(0);
      }
      if (name === "dashboard" || name === "tanks") {
        const image = page
          .getByAltText(name === "dashboard" ? "Device" : "Aquasense Pro")
          .first();
        await expect(image).toBeVisible();
        expect(
          await image.evaluate(
            (img) =>
              img.complete &&
              img.naturalWidth > 0 &&
              getComputedStyle(img).objectFit === "contain",
          ),
        ).toBeTruthy();
      }
      await page.screenshot({
        path: `../.verification/ui-all-${name}-${width}.png`,
        fullPage: true,
      });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBeTruthy();
      const trigger = header.getByRole("button", {
        name: "Account and hatchery",
        exact: true,
      });
      await trigger.click();
      await expect(page.getByLabel("Hatchery", { exact: true })).toBeVisible();
      await expect(
        page.getByRole("button", { name: "Sign out", exact: true }),
      ).toBeVisible();
      expect(
        await page.evaluate(() => {
          const r = document
            .querySelector(".account-panel")
            .getBoundingClientRect();
          return r.left >= 0 && r.right <= innerWidth;
        }),
      ).toBeTruthy();
      await page.keyboard.press("Escape");
      await expect(page.getByLabel("Hatchery", { exact: true })).toBeHidden();
      await expect(trigger).toBeFocused();
      if (name === "tank") {
        await page.evaluate(() => window.scrollTo(0, 500));
        expect(Math.round((await header.boundingBox()).y)).toBe(0);
        await header
          .getByRole("link", { name: "Back to tanks", exact: true })
          .click();
        await expect(page).toHaveURL(/\/tanks$/);
      }
    }
  }
  await page.setViewportSize({ width: 360, height: 900 });
  await page.goto("/tanks");
  const button = page.getByRole("button", { name: "New tank", exact: true });
  await button.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.screenshot({
    path: "../.verification/ui-all-tank-dialog-360.png",
    fullPage: true,
  });
  await page.keyboard.press("Shift+Tab");
  expect(
    await page.evaluate(
      () => document.activeElement.closest("dialog") !== null,
    ),
  ).toBeTruthy();
  await page.keyboard.press("Escape");
  await expect(button).toBeFocused();
  await page.goto("/data");
  await page.getByRole("button", { name: "Download CSV", exact: true }).click();
  await page.screenshot({
    path: "../.verification/ui-all-export-dialog-360.png",
    fullPage: true,
  });
  const downloadPromise = page.waitForEvent("download");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Download CSV", exact: true })
    .click();
  const download = await downloadPromise;
  expect(await download.failure()).toBeNull();
  await page.keyboard.press("Escape");
  await page.goto("/tanks/" + info.tank);
  await page
    .getByRole("button", { name: "Manage device", exact: true })
    .click();
  await page.screenshot({
    path: "../.verification/ui-all-device-dialog-360.png",
    fullPage: true,
  });
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", { name: "Add measurement", exact: true })
    .click();
  await page.screenshot({
    path: "../.verification/ui-all-manual-dialog-360.png",
    fullPage: true,
  });
  await page.keyboard.press("Escape");
  await page
    .getByRole("group", { name: "Chart metric", exact: true })
    .getByRole("button", { name: "pH", exact: true })
    .click();
  await expect(
    page
      .getByRole("group", { name: "Chart metric", exact: true })
      .getByRole("button", { name: "pH", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.goto("/tanks");
  await page.getByRole("button", { name: "Add device", exact: true }).click();
  await page.screenshot({
    path: "../.verification/ui-all-claim-dialog-360.png",
    fullPage: true,
  });
  await page.keyboard.press("Escape");
  await page.goto("/alerts");
  await expect(
    page.getByText("Not available yet", { exact: true }),
  ).toBeVisible();
});

test("passive checks expire the session without extending inactivity", async ({
  page,
  request,
}) => {
  const info = await context(request);
  await login(page);
  await page.goto("/tanks/" + info.tank);
  await expect(
    page.getByText("Live feed connected", { exact: true }),
  ).toBeVisible();
  await request.post("http://127.0.0.1:8019/__test/advance", {
    data: { seconds: 1801 },
  });
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible(
    { timeout: 10000 },
  );
  await expect(
    page.getByRole("heading", { name: "Nursery A", exact: true }),
  ).toHaveCount(0);
});
