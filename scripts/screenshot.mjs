// Gera as capturas do painel para o README (docs/).
// Uso: node scripts/screenshot.mjs [url-base]   (sem argumento usa reports/ local)
// Requer Node.js e Playwright: npm i --no-save playwright && npx playwright install chromium
import { chromium } from 'playwright';
import { resolve } from 'node:path';

const base = process.argv[2] || 'file://' + resolve('reports') + '/';
const alvos = [
  ['index.html', 'docs/painel.png', 1280, 1100, false],
  ['index.html', 'docs/telas.png', 1280, 820, 'ct-10'],
];
const browser = await chromium.launch();
for (const [caminho, saida, w, h, ancora] of alvos) {
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1.5 });
  await page.goto(base + caminho, { waitUntil: 'networkidle' });
  if (ancora) await page.evaluate((id) => document.getElementById(id).scrollIntoView({ block: 'start' }), ancora);
  await page.waitForTimeout(600);
  await page.screenshot({ path: saida, fullPage: false });
  console.log('Captura salva em', saida);
  await page.close();
}
await browser.close();
