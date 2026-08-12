const puppeteer = require('puppeteer');
const fs = require('fs');

const profiles = [
    { name: 'Albert Clark', id: 'Clark-93439' },
    { name: 'Charles Clark', id: 'Clark-93440' },
    { name: 'Ella Clark', id: 'Clark-93433' },
    { name: 'Faunse Clark', id: 'Clark-93438' },
    { name: 'Ferdinand Clark', id: 'Clark-101192' },
    { name: 'George Clark', id: 'Clark-93430' },
    { name: 'George Clark', id: 'Clark-93432' },
    { name: 'James Clark', id: 'Clark-93419' },
    { name: 'Joseph Clark', id: 'Clark-93437' },
    { name: 'Linia Clark', id: 'Clark-93434' },
    { name: 'Robert Clark', id: 'Clark-101285' },
    { name: 'Rufus Clark', id: 'Clark-93431' },
    { name: 'Ruth Clark', id: 'Clark-93441' },
    { name: 'Sidney Clark', id: 'Clark-93435' },
    { name: 'William Clark', id: 'Clark-93421' },
    { name: 'William Daisey', id: 'Daisey-44' },
    { name: 'Bertha Harmon', id: 'Harmon-11398' },
    { name: 'Ephraim Harmon', id: 'Harmon-11449' },
    { name: 'Isaac Harmon', id: 'Harmon-10342' },
    { name: 'Levin Harmon', id: 'Harmon-5067' },
    { name: 'Marietta Harmon', id: 'Harmon-11596' },
    { name: 'Noah Harmon', id: 'Harmon-10344' },
    { name: 'Winona Jamison', id: 'Jamison-2998' },
    { name: 'Hetty Johnson', id: 'Johnson-158392' },
    { name: 'Whittington Johnson', id: 'Johnson-158164' },
    { name: 'Ann Norwood', id: 'Norwood-3012' },
    { name: 'Burton Street', id: 'Street-5264' },
    { name: 'Arthur Elwood Wright', id: 'Wright-72285' },
    { name: 'Bertha Wright', id: 'Wright-82172' },
    { name: 'Elizabeth Wright', id: 'Wright-82169' },
    { name: 'Oscar Wright', id: 'Wright-82474' },
    { name: 'Warren Wright', id: 'Wright-72283' }
];

(async () => {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

  // First hit main category page to set WAF cookie
  console.log('Initializing session with WikiTree...');
  await page.goto('https://www.wikitree.com/wiki/Category:Nanticoke', { waitUntil: 'networkidle2' });
  await new Promise(r => setTimeout(r, 3000));

  const results = [];

  for (let i = 0; i < profiles.length; i++) {
    const item = profiles[i];
    const url = `https://www.wikitree.com/wiki/${item.id}`;
    console.log(`[${i+1}/${profiles.length}] Fetching ${item.name} (${item.id})...`);

    try {
      await page.goto(url, { waitUntil: 'networkidle2', timeout: 15000 });
      await new Promise(r => setTimeout(r, 1000));

      const data = await page.evaluate((item, url) => {
        const title = document.title;
        
        // Extract birth / death details from metadata / text
        const bodyText = document.body.innerText;
        
        // Bio section
        const bioEl = document.querySelector('.VITALS') || document.querySelector('#main') || document.body;
        const text = bioEl ? bioEl.innerText : '';

        return {
          id: item.id,
          name: item.name,
          url: url,
          pageTitle: title,
          snippet: text.substring(0, 1500)
        };
      }, item, url);

      results.push(data);
    } catch (err) {
      console.error(`Error scraping ${item.id}:`, err.message);
    }
  }

  fs.writeFileSync('wikitree_profiles_scraped.json', JSON.stringify(results, null, 2));
  console.log(`Successfully scraped ${results.length} WikiTree profiles to scratch/wikitree_profiles_scraped.json`);

  await browser.close();
})();
