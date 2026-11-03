import { expect, test } from "@playwright/test";
import { loginAs, setLang } from "./helpers";

test.beforeEach(async ({ context }) => setLang(context, "en"));

test("an editor creates a scheme, is told what is missing, then sends it for review", async ({ page }) => {
  await loginAs(page, "editor");
  const title = `E2E scheme ${Date.now()}`;
  await page.getByLabel("Title in English").fill(title);
  await page.getByLabel("Title in Hindi").fill("जाँच योजना");
  await page.getByRole("button", { name: "Create draft" }).click();
  await page.waitForURL("**/admin/schemes/SCH-*");
  await page.getByRole("button", { name: "Send for review" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("Add at least one eligibility rule");

  await page.getByLabel("Benefit in English").fill("Rs 1,000 a month");
  await page.getByLabel("Who can apply, in English").fill("Women aged 30 or above");
  await page.getByLabel("Official source link").fill("https://example.org/notices/e2e");
  await page.getByRole("button", { name: "Add a rule" }).click();
  await page.getByLabel("Minimum age").fill("30");
  await expect(page.getByText("उम्र 30 वर्ष या उससे अधिक हो")).toBeVisible();
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.locator("main").getByRole("status")).toContainText("Saved");
  await page.getByRole("button", { name: "Send for review" }).click();
  await expect(page.getByText("In review").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Publish" })).toHaveCount(0); // admin only
});

test("with no model the editor gets a clear message, writes by hand, and bad numbers block approval", async ({ page }) => {
  await loginAs(page, "editor");
  await page.goto("/admin/schemes/SCH-050");
  await page.getByRole("button", { name: "Draft with AI" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("write the summary by hand");
  await page.getByText("Write a summary by hand").click();
  await page.getByLabel("Summary in Hindi").first().fill("30 वर्ष और उससे अधिक उम्र की महिलाओं को हर साल ₹9,999 की मुफ़्त स्वास्थ्य जाँच मिलती है।");
  await page.getByRole("button", { name: "Save as draft" }).click();
  await expect(page.getByText("Numbers not in the notice: 9999")).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve" }).first()).toBeDisabled();
  await page.getByRole("button", { name: "Reject" }).first().click();
  await expect(page.getByText("Numbers not in the notice: 9999")).toHaveCount(0);
});

test("the admin reviews a scheme, downloads the report and runs monthly charges", async ({ page }) => {
  await loginAs(page, "admin");
  await page.goto("/admin/schemes/SCH-060");
  const publish = page.getByRole("button", { name: "Publish" });
  if (await publish.count()) {
    await publish.click();
    await expect(page.getByRole("link", { name: "See the public page" })).toBeVisible();
    await page.getByRole("button", { name: "Unpublish to edit" }).click();
    await page.getByRole("button", { name: "Send for review" }).click();
  }
  await page.goto("/admin/reports");
  await expect(page.getByText("Women's Livelihood Fund")).toBeVisible();
  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("link", { name: "Download CSV" }).first().click()]);
  expect(download.suggestedFilename()).toMatch(/donations\.csv$/);
  await page.getByRole("button", { name: /monthly charges/ }).click();
  await expect(page.locator("main").getByRole("status")).toContainText(/Charged|Nothing was due/);
});

test("staff can work through the call-back queue", async ({ page }) => {
  await loginAs(page, "editor");
  await page.goto("/admin/callbacks");
  const before = await page.getByRole("button", { name: "Mark as called" }).count();
  expect(before).toBeGreaterThan(0);
  await page.getByRole("button", { name: "Mark as called" }).first().click();
  await expect(page.getByRole("button", { name: "Mark as called" })).toHaveCount(before - 1);
});

test("roles hold: donors cannot reach staff pages and editors cannot reach reports", async ({ page, request }) => {
  await loginAs(page, "donor");
  await page.goto("/admin");
  await page.waitForURL("**/account");
  expect((await page.request.get("/api/v1/admin/schemes")).status()).toBe(403);
  await page.goto("/account");
  await page.getByRole("button", { name: "Log out" }).click();
  await page.waitForURL("http://localhost:3000/");
  await loginAs(page, "editor");
  await page.goto("/admin/reports");
  await page.waitForURL("**/admin");
  await expect(page.getByRole("link", { name: "Campaign reports" })).toHaveCount(0);
  expect((await request.get("/api/v1/admin/campaigns")).status()).toBe(401);
});

test("a wrong password gets a clear message and keeps the email", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("donor@demo.example");
  await page.getByLabel("Password").fill("wrong-password");
  await page.locator("main form").getByRole("button", { name: "Log in" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("not right");
  await expect(page.getByLabel("Email")).toHaveValue("donor@demo.example");
});
