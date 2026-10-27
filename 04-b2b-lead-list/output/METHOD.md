# Method: verified lead list of Colombian higher-education institutions

Sample project built with public data. Organisation-level data only: no names, e-mails or phones of people.

## Sources
- MEN - Instituciones de Educación Superior (datos.gov.co, dataset n5yy-8nav, CC BY-SA 4.0): official registry with name, tax ID, type, sector, accreditation, address, phone and website. Record date in the source: 8 Jul 2022.
- MEN - Matrícula estadística de educación superior (datos.gov.co, dataset 5wck-szir, CC BY-SA 4.0): enrolled students per institution, semester 2021-1 (the latest published), aggregated with SoQL.
- Wikidata (CC0): official website (property P856), used only when the registry had no usable website and the name matched (similarity >= 0.90). One SPARQL query.

## Steps
- Institutions in the MEN registry (main + branch campuses): **361**
- Main campus records kept (one per institution): **300**
- Main records with no usable website in the registry: **17**
- Websites added from Wikidata (exact or near-exact name match): **2**
- Website values corrected (e-mail typed as website, 'wwww.', missing dot): **6**
- Institutions with a website that answered (verified online): **220**
- Phones normalised to +57 with the 2021 numbering plan (60 + area code of the department + 7 digits).
- Each website checked once, see below. The verified home page (after redirects) goes in `website`.

## How websites were checked (respectful by design)
- A descriptive User-Agent that names the project and links to the repository.
- robots.txt is read first; if it does not allow our agent to fetch the home page, the site is not requested.
- Normally 2 requests per site (robots.txt, then the home page after a 1.5-second pause). Only when the home page does not answer: the same address with or without 'www.', one retry 10 seconds later, and a second pass at the end, one site at a time. 6 different sites are checked in parallel; never the same site twice at once.
- Only the home page is requested; no links are followed and no forms are submitted. Only the first 300 KB are read, to get the page title.
- Checked on 2026-10-26. Results are cached, so re-running the script does not contact the sites again (use `--refresh` to re-check).

## Reading the status column
- **Online**: the home page answered with HTTP 2xx. **Online (redirects to another domain)**: the institution moved its site; `website` has the new address.
- **Online but blocks automated checks**: the server answered (HTTP 403/429) but blocks scripts; open it in a browser.
- **Site error**: the server answered with an error code (HTTP 4xx/5xx).
- **Not verified**: no answer reached our checking server (connection refused or closed, timeout, or TLS certificate rejected). Many Colombian institutional sites block traffic from foreign cloud servers, so this does not prove the site is down: re-check from a local connection before using these rows.
- **No website listed**: neither the registry nor Wikidata had a usable website.

## Limitations
- The registry records are dated 2022; institutions may have changed phone or address since then.
- Enrolment figures are from the latest semester MEN has published as open data, not the current one.
- Verification shows that a site answered at a point in time, not that the contact data inside it is current.
