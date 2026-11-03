import { expect, test } from "@playwright/test";
import { loginAs, setLang } from "./helpers";

test.beforeEach(async ({ context }) => setLang(context, "en"));

async function register(page: import("@playwright/test").Page) {
  await page.goto("/donate");
  await page.locator("main").getByRole("link", { name: "Create account" }).click();
  await page.getByLabel("Full name").fill("Test Donor");
  await page.getByLabel("Email").fill(`e2e-${Date.now()}@demo.example`);
  await page.getByLabel("Password").fill("a-long-password-1");
  await page.locator("main form").getByRole("button", { name: "Create account" }).click();
  await page.waitForURL("**/donate");
}

test("register, add PAN, a declined card, a retry, then an instant 80G certificate", async ({ page }) => {
  await register(page);
  await page.getByLabel("Or enter your own amount").fill("50");
  await page.getByRole("button", { name: "Go to payment" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("Minimum");
  await page.getByRole("button", { name: "₹2,500" }).click();
  await page.getByLabel("PAN").fill("BADPAN");
  await page.getByRole("button", { name: "Go to payment" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("ABCDE1234F");
  await expect(page.getByLabel("PAN")).toHaveValue("BADPAN"); // kept for correction
  await page.getByLabel("PAN").fill("abcpe1234f");
  await page.getByRole("button", { name: "Go to payment" }).click();
  await page.waitForURL("**/donate/pay/**");
  await expect(page.getByText("no real money moves")).toBeVisible();

  await page.getByRole("button", { name: /Bank declines/ }).click();
  await page.getByRole("button", { name: "Donate ₹2,500" }).click();
  await expect(page.locator("main").getByRole("alert").filter({ hasText: "declined" })).toBeVisible();

  await page.getByRole("button", { name: /Payment succeeds/ }).click();
  await page.getByRole("button", { name: "Donate ₹2,500" }).click();
  await expect(page.getByRole("heading", { name: "Thank you" })).toBeVisible();
  await expect(page.getByText(/^RCPT\/\d{4}-\d{2}\/\d{6}$/)).toBeVisible();
  await expect(page.getByText("This is also your 80G certificate")).toBeVisible();

  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("link", { name: "Download receipt" }).click()]);
  expect(download.suggestedFilename()).toMatch(/^RCPT-.*\.pdf$/);

  await page.goto("/account");
  await expect(page.getByText("80G certificate").first()).toBeVisible();
  await expect(page.locator("main")).not.toContainText("ABCPE1234F");
});

test("a foreign card is blocked, and with no PAN the receipt is honestly plain", async ({ page }) => {
  await register(page);
  await page.getByRole("button", { name: "₹500" }).click();
  await page.getByRole("button", { name: "Go to payment" }).click();
  await page.waitForURL("**/donate/pay/**");
  await page.getByRole("button", { name: /Payment succeeds/ }).click();
  await page.getByLabel("Country that issued the card").selectOption("XX");
  await page.getByRole("button", { name: "Donate ₹500" }).click();
  await expect(page.locator("main").getByRole("alert").filter({ hasText: "Foreign cards" })).toBeVisible();
  await page.getByLabel("Country that issued the card").selectOption("IN");
  await page.getByRole("button", { name: "Donate ₹500" }).click();
  await expect(page.getByText("With no PAN this is a plain receipt")).toBeVisible();
});

test("a real-looking card number is refused", async ({ page }) => {
  await register(page);
  await page.getByRole("button", { name: "Go to payment" }).click();
  await page.waitForURL("**/donate/pay/**");
  await page.getByLabel("Card number").fill("5500 0055 5555 5559");
  await page.getByRole("button", { name: /^Donate/ }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("test card");
});

test("monthly giving starts, shows in the account and can be stopped", async ({ page }) => {
  await register(page);
  await page.getByLabel("Every month").check();
  await page.getByRole("button", { name: "Go to payment" }).click();
  await page.waitForURL("**/donate/pay/**");
  await page.getByRole("button", { name: /Payment succeeds/ }).click();
  await page.getByRole("button", { name: /^Donate/ }).click();
  await expect(page.getByText("Monthly giving has started")).toBeVisible();
  await page.goto("/account");
  await page.getByRole("button", { name: "Stop monthly giving" }).click();
  await page.getByRole("button", { name: "Yes, stop it" }).click();
  await expect(page.getByText("Stopped")).toBeVisible();
});

test("a signed-out visitor sees campaigns and returns to donating after login", async ({ page }) => {
  await page.goto("/donate");
  await expect(page.getByText("raised").first()).toBeVisible();
  await page.locator("main").getByRole("link", { name: "Log in" }).click();
  await page.getByRole("button", { name: /donor@demo.example/ }).click();
  await page.locator("main form").getByRole("button", { name: "Log in" }).click();
  await page.waitForURL("**/donate");
  await expect(page.getByText("Your PAN on file")).toBeVisible();
});

test("the seeded donor has a history and receipts", async ({ page }) => {
  await loginAs(page, "donor");
  await expect(page.getByRole("heading", { name: "My donations" })).toBeVisible();
  await expect(page.getByRole("link", { name: /RCPT\// }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Try payment again" }).first()).toBeVisible();
});
