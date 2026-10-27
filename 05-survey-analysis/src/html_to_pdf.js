// Print an HTML report to an A4 PDF with Chromium. Usage: node html_to_pdf.js in.html out.pdf
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve(process.argv[2]), { waitUntil: 'networkidle' });
  await page.emulateMedia({ media: 'screen' });
  await page.pdf({
    path: process.argv[3], format: 'A4', printBackground: true,
    margin: { top: '14mm', bottom: '16mm', left: '12mm', right: '12mm' },
    displayHeaderFooter: true, headerTemplate: '<span></span>',
    footerTemplate: '<div style="font-size:8px;color:#898781;width:100%;padding:0 12mm;display:flex;' +
      'justify-content:space-between"><span>Sample project built with public data · GSS 2024</span>' +
      '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
  });
  await browser.close();
})();
