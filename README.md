# onionavailable.com
a little site to track adoption of onion services via the Onion-Location header

## Adding new sites

Please, no personal sites / blogs.

To include a new site, add the site to `watched.txt`, and submit a PR.

## Development

Logic for scanning and rebuilding the static site is in `scan.py`. `scan.json` contains the latest scan results, and `docs/index.html` is the main page.

```
python3 -m http.server
```
