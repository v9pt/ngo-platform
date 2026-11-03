import { expect, test } from "@playwright/test";
import { expectNoAxeViolations, loginAs, setLang } from "./helpers";

const PUBLIC = ["/", "/finder", "/schemes", "/schemes/SCH-014", "/donate", "/login", "/register", "/nope"];

for (const colorScheme of ["light", "dark"] as const) {
  for (const lang of ["hi", "en"] as const) {
    test(`public pages pass axe in ${lang}, ${colorScheme}`, async ({ page, context }) => {
      await setLang(context, lang);
      await page.emulateMedia({ colorScheme });
      for (const path of PUBLIC) {
        await page.goto(path);
        await expectNoAxeViolations(page);
      }
    });
  }
}

test("finder stages, donor and staff pages pass axe in both themes", async ({ page, context }) => {
  await setLang(context, "en");
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await page.goto("/finder");
    await page.getByRole("button", { name: "Answer questions instead" }).click();
    await expectNoAxeViolations(page);
    await page.goto("/finder");
    await page.getByLabel("Describe your situation").fill("मैं 45 साल की विधवा हूँ");
    await page.getByRole("button", { name: "Read what I wrote" }).click();
    await expectNoAxeViolations(page);
    await page.getByRole("button", { name: "Check schemes" }).click();
    await expect(page.getByRole("heading", { name: "Your results" })).toBeVisible();
    await expectNoAxeViolations(page);
  }
  await page.emulateMedia({ colorScheme: "light" });
  await loginAs(page, "donor");
  await expectNoAxeViolations(page);
  await page.goto("/donate");
  await expectNoAxeViolations(page);
  await page.goto("/account");
  await page.getByRole("button", { name: "Log out" }).click();
  await page.waitForURL("http://localhost:3000/");
  await loginAs(page, "admin");
  for (const path of ["/admin", "/admin/schemes/SCH-014", "/admin/schemes/SCH-090", "/admin/callbacks", "/admin/reports"]) {
    await page.goto(path);
    await expectNoAxeViolations(page);
  }
});

test("no page scrolls sideways on a 360px phone", async ({ page, context }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await setLang(context, "hi");
  await page.goto("/login");
  await page.getByLabel("ईमेल").fill("admin@demo.example");
  await page.getByLabel("पासवर्ड").fill("DemoPass#2026");
  await page.locator("main form").getByRole("button", { name: "लॉग इन" }).click();
  await page.waitForURL("**/admin");
  for (const path of [...PUBLIC, "/account", "/admin", "/admin/schemes/SCH-014", "/admin/callbacks", "/admin/reports"]) {
    await page.goto(path);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, path).toBeLessThanOrEqual(0);
  }
});

test("the theme control applies at once and survives a reload", async ({ page, context }) => {
  await setLang(context, "en");
  await page.goto("/");
  await page.getByRole("radio", { name: "Dark" }).first().check({ force: true });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("radio", { name: "Follow device" }).first().check({ force: true });
  await expect(page.locator("html")).not.toHaveAttribute("data-theme");
});
