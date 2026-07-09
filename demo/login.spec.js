const { test, expect } = require('@playwright/test');

// This test breaks the way real tests break: a coding agent tweaked the button
// copy from "Sign In" to "Sign in", so this exact-text selector went stale.
test('user can sign in', async ({ page }) => {
  await page.goto(process.env.DEMO_URL || 'http://localhost:8137');
  await page.locator("text='Sign in'").click(); // page now says "Sign in"
  await expect(page.locator('.ok')).toBeVisible();
});
