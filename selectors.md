# Selectors used by scrape.py

These are the CSS selectors used to extract fields from each Naukri job
card rendered on the search-results page
(`https://www.naukri.com/python-developer-jobs-in-bangalore`).

| Field        | CSS selector               | Source                |
|--------------|----------------------------|-----------------------|
| Job card     | `.srp-jobtuple-wrapper`    | outer card container  |
| Title        | `a.title`                  | `<a>` text            |
| Company      | `a.comp-name`              | `<a>` text            |
| Location     | `.locWdth`                 | element text          |
| Link (href)  | `a.title`                  | `href` attribute      |

Notes
-----
- Each job card on the Naukri search page is wrapped in a
  `<div class="srp-jobtuple-wrapper">` (sometimes with extra utility
  classes). The job card itself is the unit we iterate over.
- The title element is the anchor with the `title` class; its `href`
  points at the detail page for that job.
- The company is a link with the `comp-name` class.
- The location is a plain element with the `locWdth` class (no link).
- We only emit a record when the title text is present and non-empty
  (cards with no title are skipped).

Why a headless browser?
----------------------
Naukri now serves its search-results page as a Next.js client-rendered
SPA. A plain HTTP GET returns a shell that does NOT contain any
`.srp-jobtuple-wrapper` cards — they are injected by JavaScript after
load. To get a DOM that actually contains the cards we drive
Chromium with Playwright, wait for `.srp-jobtuple-wrapper` to appear,
and then parse the rendered HTML with BeautifulSoup.
