import { test, expect } from '@playwright/test';

const APP_URL = 'http://localhost:5173';

test.describe('RailAI dashboard and ticket flow', () => {
  test('renders dashboard metrics and creates ticket through UI', async ({ page }) => {
    await page.goto(APP_URL, { waitUntil: 'networkidle' });
    await expect(page.locator('#page-dashboard')).toBeVisible();

    const openTicketsCard = page.locator('text=/Open Tickets|Open Tickets/i').first();
    await expect(openTicketsCard).toBeVisible();

    const openTicketsValue = await page.locator('#page-dashboard div').filter({ hasText: 'Open Tickets' }).locator('div').nth(1).textContent();
    expect(openTicketsValue).not.toBeNull();

    await page.locator('.nav-item').filter({ hasText: /Tickets|तिकीट/i }).first().click();

    await page.locator('#page-tickets button', { hasText: /New Ticket/i }).click();

    await page.locator('input[placeholder*="passenger"]').first().fill('Test Passenger');
    await page.locator('textarea[placeholder*="Describe the issue"]').fill('Train delayed and no update received.');
    await page.locator('button', { hasText: /Create Ticket/i }).click();

    await expect(page.locator('text=Ticket created with ID')).toBeVisible({ timeout: 15000 });
    const toastText = await page.locator('#toast-container').textContent();
    expect(toastText).toContain('Ticket created with ID');

    await page.goto(APP_URL, { waitUntil: 'networkidle' });
    await expect(page.locator('#page-dashboard')).toBeVisible();
    await expect(page.locator('text=/Open Tickets/')).toBeVisible();
  });

  test('chatbot interactive flow collects slots and creates ticket', async ({ page }) => {
    await page.goto(APP_URL, { waitUntil: 'networkidle' });
    
    // Navigate to Chat page
    await page.locator('.nav-item').filter({ hasText: /Assistant|सहायक/i }).click();
    await expect(page.locator('#page-ai')).toBeVisible();

    // Clear session to ensure clean state
    await page.locator('button[title*="Clear"]').first().click();
    await page.waitForTimeout(1000);

    const textarea = page.locator('textarea.input-field');
    const sendButton = page.locator('button', { hasText: /Send|पाठवा|भेजें/i });

    // Step 1: Initial complaint
    await textarea.fill('I want a refund for my ticket.');
    await sendButton.click();

    // Verify it presents troubleshooting menu first
    await expect(page.locator('.chat-bubble-ai').last()).toContainText('Suggested actions', { timeout: 10000 });
    await expect(page.locator('.chat-bubble-ai').last()).toContainText('Create support ticket');

    // Step 2: Choose option 3 (Create Ticket)
    await textarea.fill('3');
    await sendButton.click();

    // Verify it asks for missing slots
    await expect(page.locator('.chat-bubble-ai').last()).toContainText('Source station', { timeout: 10000 });
    await expect(page.locator('.chat-bubble-ai').last()).toContainText('Destination station');

    // Step 3: Combined slots
    await textarea.fill('Nagpur Pune 1234567890 22 June 2026');
    await sendButton.click();

    // Verify it asks for confirmation
    await expect(page.locator('.chat-bubble-ai').last()).toContainText('create a support ticket', { timeout: 10000 });

    // Step 4: Confirm YES
    await textarea.fill('YES');
    await sendButton.click();

    // Verify ticket registration
    await expect(page.locator('.chat-bubble-ai').last()).toContainText('registered successfully', { timeout: 10000 });
    await expect(page.locator('.chat-bubble-ai').last()).toContainText('Ticket ID');
  });
});
