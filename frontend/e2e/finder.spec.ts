import { expect, test } from "@playwright/test";
import { setLang } from "./helpers";

test.beforeEach(async ({ context }) => setLang(context, "en"));

test("a typed Hindi question pre-fills answers that can be changed, then rules give reasons", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Describe your situation").fill("मैं 45 साल की विधवा हूँ, भोपाल में रहती हूँ, बीपीएल कार्ड है");
  await page.getByRole("button", { name: "Read what I wrote" }).click();
  await expect(page.getByRole("heading", { name: "Check your answers" })).toBeVisible();
  await expect(page.getByLabel("How old are you?")).toHaveValue("45");
  await expect(page.getByLabel("What is your marital status?")).toHaveValue("widow");
  await page.getByRole("button", { name: "Check schemes" }).click();
  await expect(page.getByRole("heading", { name: "Your results" })).toBeVisible();
  const pension = page.locator("article", { hasText: "State widow pension" });
  await expect(pension.getByText("Likely eligible")).toBeVisible();
  await expect(pension.getByText("Aged 18 to 79")).toBeVisible();
  await expect(pension.getByText("Has a BPL card")).toBeVisible();
  await expect(page.locator("main")).not.toContainText("between");
  await page.getByRole("button", { name: "Change answers" }).first().click();
  await page.getByLabel("How old are you?").fill("85");
  await page.getByRole("button", { name: "Check schemes" }).click();
  await page.getByText(/^Not suitable right now/).click();
  await expect(page.locator("article", { hasText: "State widow pension" }).getByText("Not eligible")).toBeVisible();
});

test("text with nothing in it says so, and the person can still answer", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Describe your situation").fill("नमस्ते मुझे मदद चाहिए");
  await page.getByRole("button", { name: "Read what I wrote" }).click();
  await expect(page.getByText("We could not find answers")).toBeVisible();
  await expect(page.getByLabel("What is your marital status?")).toHaveValue("");
});

test("the step-by-step path skips what cannot apply and says what is unknown", async ({ page }) => {
  await page.goto("/finder");
  await page.getByRole("button", { name: "Answer questions instead" }).click();
  await page.getByLabel("How old are you?").fill("200");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("0 to 120");
  await page.getByLabel("How old are you?").fill("28");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Married" }).click();
  await page.getByRole("button", { name: "Bhopal" }).click();
  await page.getByRole("button", { name: "Yes" }).click(); // BPL
  await page.getByRole("button", { name: "No" }).click(); // pregnant: first-child question is skipped
  await expect(page.getByRole("heading", { name: "Is this your first child?" })).toHaveCount(0);
  await page.getByRole("button", { name: "Not sure" }).click(); // SHG
  await page.getByRole("button", { name: "Not sure" }).click();
  await page.getByRole("button", { name: "Not sure" }).click();
  await page.getByRole("button", { name: "Check schemes" }).click();
  await expect(page.locator("article", { hasText: "Self-help group loan" }).getByText("Possibly eligible")).toBeVisible();
  await expect(page.locator("article", { hasText: "Self-help group loan" }).getByText("Not answered")).toBeVisible();
});

test("every result offers a call-back, with validation and consent", async ({ page }) => {
  await page.goto("/finder");
  await page.getByRole("button", { name: "Answer questions instead" }).click();
  for (let i = 0; i < 1; i += 1) await page.getByRole("button", { name: "Skip" }).click();
  for (let i = 0; i < 7; i += 1) await page.getByRole("button", { name: "Not sure" }).click();
  await page.getByRole("button", { name: "Check schemes" }).click();
  const row = page.locator("article", { hasText: "State widow pension" });
  await row.getByText("Ask the helpline to call you").click();
  await row.getByLabel("Mobile number").fill("12345");
  await row.getByRole("button", { name: "Request a call" }).click();
  await expect(row.getByRole("alert")).toContainText("10-digit");
  await row.getByLabel("Mobile number").fill("+91 98765 43210");
  await row.getByRole("button", { name: "Request a call" }).click();
  await expect(row.getByRole("alert")).toContainText("agree");
  await row.getByLabel("I want the trust to call me").check();
  await row.getByRole("button", { name: "Request a call" }).click();
  await expect(row.getByRole("status")).toContainText("Request received");
});

test("browse filters by need and district, with a way out of an empty result", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /Work and livelihood/ }).click();
  await expect(page).toHaveURL(/need=livelihood/);
  await expect(page.getByRole("link", { name: "Skill training stipend" })).toBeVisible();
  await expect(page.getByRole("link", { name: "State widow pension" })).toHaveCount(0);
  await page.goto("/schemes?need=safety&district=Dewas");
  await expect(page.getByText("No schemes for this choice")).toBeVisible();
  await page.getByRole("link", { name: "Clear the choice" }).click();
  await expect(page.getByRole("link", { name: "State widow pension" })).toBeVisible();
});

test("Hindi is the default and a scheme page is Hindi throughout", async ({ page, context }) => {
  await context.clearCookies();
  await page.goto("/schemes/SCH-014");
  await expect(page.locator("html")).toHaveAttribute("lang", "hi");
  await expect(page.getByRole("heading", { name: "राज्य विधवा पेंशन" })).toBeVisible();
  await expect(page.getByText("18 से 79 वर्ष की विधवा महिला")).toBeVisible();
  await expect(page.getByText("पति का मृत्यु प्रमाण पत्र")).toBeVisible();
  await expect(page.getByText("सरल शब्दों में")).toBeVisible();
});

test("an unknown scheme gets a helpful page", async ({ page }) => {
  await page.goto("/schemes/SCH-999");
  await expect(page.getByText("This scheme was not found")).toBeVisible();
  await page.getByRole("link", { name: "See all schemes" }).click();
  await expect(page).toHaveURL(/\/schemes$/);
});
