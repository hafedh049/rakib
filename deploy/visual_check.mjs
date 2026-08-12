/**
 * Visual + runtime check against the deployed site. Run ON the VPS inside the
 * Playwright image (see deploy/visual_check.sh).
 *
 * Captures a screenshot per surface AND every console error / failed request,
 * because a page that renders can still be quietly broken.
 */
import { chromium } from 'playwright'

const BASE = process.env.BASE ?? 'https://reclamations.activiity.com'
const OUT = process.env.OUT ?? '/out'
const EMAIL = process.env.RAKIB_EMAIL ?? 'admin@rakib.tn'
const PASSWORD = process.env.RAKIB_PASSWORD ?? 'Rakib2026!'

const problems = []

async function shoot(page, name, { full = true } = {}) {
  await page.waitForTimeout(900) // let queries settle
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: full })
  console.log(`  captured ${name}`)
}

function watch(page, label) {
  page.on('console', (message) => {
    if (message.type() === 'error') problems.push(`[${label}] console: ${message.text()}`)
  })
  page.on('pageerror', (error) => problems.push(`[${label}] pageerror: ${error.message}`))
  page.on('requestfailed', (request) => {
    const failure = request.failure()?.errorText ?? 'failed'
    problems.push(`[${label}] request: ${request.url()} — ${failure}`)
  })
  page.on('response', (response) => {
    if (response.status() >= 400) {
      problems.push(`[${label}] http ${response.status()}: ${response.url()}`)
    }
  })
}

const browser = await chromium.launch()

// ---------------------------------------------------------------- portal, FR
{
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
  const page = await context.newPage()
  watch(page, 'portal-fr')
  await page.goto(`${BASE}/portal`, { waitUntil: 'domcontentloaded' })
  await shoot(page, '01-portal-fr')

  // Fill it in so the layout is checked with real content, not empty inputs.
  await page.fill('input#\\:r0\\:, input', 'Aucun reseau a Ezzahra').catch(() => {})
  await shoot(page, '02-portal-fr-filled', { full: false })
  await context.close()
}

// ---------------------------------------------------------- portal, Arabic RTL
{
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
  const page = await context.newPage()
  watch(page, 'portal-ar')
  await page.goto(`${BASE}/portal`, { waitUntil: 'domcontentloaded' })
  await page.evaluate(() => localStorage.setItem('rakib.locale', 'ar'))
  await page.reload({ waitUntil: 'domcontentloaded' })

  const dir = await page.evaluate(() => document.documentElement.dir)
  const lang = await page.evaluate(() => document.documentElement.lang)
  console.log(`  arabic: dir=${dir} lang=${lang}`)
  if (dir !== 'rtl') problems.push(`[portal-ar] expected dir=rtl, got ${dir}`)

  // Does the layout actually mirror, or is it just translated text?
  const box = await page.locator('h1').first().boundingBox()
  const width = await page.evaluate(() => window.innerWidth)
  if (box) {
    console.log(`  h1 box x=${Math.round(box.x)} w=${Math.round(box.width)} (viewport ${width})`)
  }
  await shoot(page, '03-portal-ar-rtl')
  await context.close()
}

// ------------------------------------------------------------------- console
{
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } })
  const page = await context.newPage()
  watch(page, 'console')

  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' })
  await page.getByLabel(/email/i).fill(EMAIL)
  await page.getByLabel(/mot de passe/i).fill(PASSWORD)
  await page.getByRole('button', { name: /se connecter/i }).click()
  await page.waitForURL(/inbox/, { timeout: 20000 })
  await page.waitForTimeout(1500)
  await shoot(page, '04-inbox')

  // First complaint in the queue -> the analysis panel, the demo centrepiece.
  const firstRow = page.locator('main a[href^="/inbox/"]').first()
  if (await firstRow.count()) {
    await firstRow.click()
    await page.waitForTimeout(1800)
    await shoot(page, '05-complaint-detail')
  } else {
    problems.push('[console] inbox had no rows to open')
  }

  await page.goto(`${BASE}/admin/rules`, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(800)
  const run = page.getByRole('button', { name: /^Analyser$/ })
  if (await run.count()) {
    await run.click()
    await page.waitForTimeout(1800)
  }
  await shoot(page, '06-rule-simulator')

  await page.goto(`${BASE}/analytics`, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(2000)
  await shoot(page, '07-analytics')

  await page.goto(`${BASE}/admin/ml`, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1500)
  await shoot(page, '08-model-health')

  await page.goto(`${BASE}/supervision`, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1200)
  await shoot(page, '09-supervision')

  // Light theme, since the console defaults to dark.
  await page.evaluate(() => localStorage.setItem('rakib.theme', 'light'))
  await page.goto(`${BASE}/inbox`, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1200)
  await shoot(page, '10-inbox-light')

  await context.close()
}

// ------------------------------------------------------------------- mobile
{
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  })
  const page = await context.newPage()
  watch(page, 'mobile')
  await page.goto(`${BASE}/portal`, { waitUntil: 'domcontentloaded' })
  await shoot(page, '11-portal-mobile')

  // Horizontal overflow is the classic responsive failure.
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  if (overflow > 1) problems.push(`[mobile] horizontal overflow of ${overflow}px`)
  await context.close()
}

await browser.close()

console.log('\n=== problems ===')
if (problems.length === 0) console.log('  none')
else for (const problem of [...new Set(problems)]) console.log(`  ${problem}`)
