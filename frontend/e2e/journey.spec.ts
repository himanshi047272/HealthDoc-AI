import { expect, test } from '@playwright/test'
import path from 'node:path'

const PDF = path.resolve(__dirname, '../../backend/fixtures/docs/Northwind_Health_Policy.pdf')

test('upload, ask, abstain, search, delete', async ({ page }) => {
  await page.goto('/documents')
  await page.getByLabel('Upload documents').setInputFiles(PDF)
  await expect(page.getByText('ready').first()).toBeVisible({ timeout: 60_000 })

  await page.getByRole('link', { name: 'Northwind_Health_Policy.pdf' }).click()
  await expect(page.getByText('Page 1', { exact: true })).toBeVisible()
  await expect(page.getByText(/\$250,000/)).toBeVisible()

  await page.goto('/chat')
  await page.getByLabel('Your question').fill('What is the individual deductible?')
  await page.getByRole('button', { name: 'Ask' }).click()
  await page.getByRole('button', { name: 'Open source 1' }).click()
  await expect(page.getByText(/page 1/).first()).toBeVisible()
  await expect(page.getByText(/\$1,500/).first()).toBeVisible()

  await page.getByLabel('Your question').fill('Does the plan cover acupuncture?')
  await page.getByRole('button', { name: 'Ask' }).click()
  await expect(page.getByText(/couldn’t find enough supporting information/)).toBeVisible()

  await page.goto('/search?q=deductible')
  await expect(page.getByText(/Northwind_Health_Policy.pdf · page 1/)).toBeVisible()
  await page.getByRole('link', { name: /Open page 1/ }).first().click()
  await expect(page.locator('mark')).toBeVisible()

  await page.goto('/documents')
  page.once('dialog', (d) => d.accept())
  await page.getByRole('button', { name: 'Delete' }).first().click()
  await expect(page.getByText('No documents yet')).toBeVisible()
  await page.goto('/search?q=deductible')
  await expect(page.getByText('No matching passages')).toBeVisible()
  await page.goto('/')
  await expect(page.getByText('No documents yet.')).toBeVisible()
})
