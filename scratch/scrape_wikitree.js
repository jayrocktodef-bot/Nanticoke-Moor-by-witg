const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-blink-features=AutomationControlled'
    ]
  });

  const page = await browser.newPage();
  await page.setUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

  console.log('Navigating to WikiTree Nanticoke Category...');
  await page.goto('https://www.wikitree.com/wiki/Category:Nanticoke', {
    waitUntil: 'networkidle2',
    timeout: 30000
  });

  // Wait a few seconds for AWS WAF token reload if needed
  await new Promise(r => setTimeout(r, 4000));

  const title = await page.title();
  console.log('Page Title:', title);

  const html = await page.content();
  fs.writeFileSync('/tmp/wikitree_rendered.html', html);
  console.log('Saved rendered HTML to /tmp/wikitree_rendered.html. Size:', html.length);

  await browser.close();
})();
