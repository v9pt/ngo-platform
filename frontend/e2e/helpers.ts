import AxeBuilder from "@axe-core/playwright";
import { type BrowserContext, expect, type Page } from "@playwright/test";

export const PASSWORD = "DemoPass#2026";

export async function setLang(context: BrowserContext, lang: "hi" | "en") {
  await context.addCookies([{ name: "lang", value: lang, url: "http://localhost:3000" }]);
}

export async function loginAs(page: Page, who: "donor" | "editor" | "admin") {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`${who}@demo.example`);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.locator("main form").getByRole("button", { name: "Log in" }).click();
  await page.waitForURL(who === "donor" ? "**/account" : "**/admin");
}

export async function expectNoAxeViolations(page: Page) {
  const results = await new AxeBuilder({ page: page as never }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  const summary = results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).slice(0, 4).join(" | ")}`);
  expect(summary).toEqual([]);
}
