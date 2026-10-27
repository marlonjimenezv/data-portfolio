// Browser test for the dashboard: loads the page, applies filters and checks the KPI tiles
// against the expected values computed with pandas (passed as JSON in argv[3]).
// Usage: node tests/test_dashboard.js output/dashboard.html '<expected json>'
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const file = 'file://' + path.resolve(process.argv[2]);
  const cases = JSON.parse(process.argv[3]);
  const browser = await chromium.launch();
  const failures = [];
  for (const [viewport, scheme] of [[{ width: 1440, height: 900 }, 'light'], [{ width: 390, height: 844 }, 'dark']]) {
    const page = await browser.newPage({ viewport, colorScheme: scheme });
    const errors = [];
    page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('pageerror', (e) => errors.push(String(e)));
    await page.goto(file, { waitUntil: 'networkidle' });
    for (const c of cases) {
      await page.click('#reset');
      for (const [sel, label] of Object.entries(c.filters)) {
        await page.selectOption(sel, { label });
      }
      await page.waitForTimeout(150);
      const got = await page.evaluate(() => ({
        n: document.getElementById('kN').textContent,
        v: document.getElementById('kV').textContent,
        dir: document.getElementById('kDir').textContent,
        rows: document.querySelectorAll('#tEnt tbody tr').length,
        bars: document.querySelectorAll('#cEnt .bars path').length,
      }));
      const ok = got.n === c.expect.n && got.v === c.expect.v && got.dir === c.expect.dir;
      console.log(`${ok ? 'OK ' : 'BAD'} [${viewport.width}px ${scheme}] ${c.name}: ${JSON.stringify(got)}`);
      if (!ok) failures.push(c.name);
    }
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    if (overflow > 0) failures.push(`horizontal overflow ${overflow}px at ${viewport.width}px`);
    if (errors.length) failures.push(`console errors: ${errors.join(' | ')}`);
    await page.close();
  }
  await browser.close();
  if (failures.length) { console.error('FAILED: ' + failures.join('; ')); process.exit(1); }
  console.log('Dashboard test: OK (no console errors, no horizontal overflow, KPIs match pandas)');
})();
