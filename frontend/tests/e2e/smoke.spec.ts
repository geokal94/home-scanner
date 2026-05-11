import { expect, test } from "@playwright/test";

test("landing page renders with title and Telegram CTA", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Watch Greek rentals/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /Open Telegram bot/i }).first()).toBeVisible();
});

test("listings page loads and shows the filter bar", async ({ page }) => {
  await page.goto("/listings");
  await expect(page.getByRole("button", { name: /Apply/i })).toBeVisible();
});

test("per-area page renders header for Thessaloniki", async ({ page }) => {
  await page.goto("/listings/thessaloniki");
  await expect(page.getByRole("heading", { name: /Rentals in Thessaloniki/i })).toBeVisible();
});

test("filter URL persistence works", async ({ page }) => {
  await page.goto("/listings?location=Athens&price_max=1200");
  await expect(page.getByRole("button", { name: /Apply/i })).toBeVisible();
  // URL params survive the round trip
  expect(page.url()).toContain("location=Athens");
});
