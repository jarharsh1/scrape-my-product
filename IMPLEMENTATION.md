# Automatic product comparison MVP

The home page is now **Side by Side** (a working name). Enter two to four
product names in one input. There are no required URLs or merchant selections.
The previous search interface is still available at `/legacy`.

## Run locally

Requires Python 3.11+ (the comparison timeout uses `asyncio.timeout`).

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:8000. Choose **Connections** and enter Tavily and OpenAI
keys. Keys entered here remain in tab memory and are sent to the local server
with each comparison. Clearing keys or closing the tab removes them. Do not
use this development UI over unencrypted remote HTTP.

Alternatively copy `.env.example` to `.env` and fill the two keys. `.env` is
ignored by Git. Environment keys stay on the server; `/api/compare/status`
only exposes whether each is configured. `OPENAI_MODEL` is configurable and
defaults to `gpt-4.1-mini`; the selected model must support Responses API
structured outputs. OpenAI API billing is separate from a ChatGPT subscription.

## Pipeline and boundaries

1. OpenAI parses the names and any optional buying priorities into a plan.
2. Tavily searches twice per product: specifications/reviews and regional prices.
3. Deduplicate URLs per product; retain up to six sources per product.
4. Tavily Extract attempts up to two full pages per product. Search excerpts are
   explicitly labelled when full pages are unavailable.
5. OpenAI returns a structured comparison based on the collected evidence.
6. Server validation rejects invented source IDs, product/source mismatches,
missing product cells and uncited factual cells. Offer price text must appear
in its cited evidence. Unknown cells must read
   `Not verified`. These checks validate provenance structure, not factual
   entailment: human evaluation of real comparisons is still necessary.

One comparison makes two OpenAI calls, four to eight Tavily searches, and two
to four extraction calls. Requests have timeouts and output limits. No search
results or credentials are cached or written by the comparison service. No
affiliate links or simulated live prices are injected. Unsupported requests
(one product, more than four products, incompatible categories) return an
actionable error instead of silently selecting alternatives.

Provider failures are sanitized. Partial discovery/extraction failures are
reported. Empty evidence for any product stops the comparison. Source pages
are treated as untrusted data in prompts. This server only calls fixed Tavily
and OpenAI endpoints; it never directly opens a user/discovered URL.

## Verification

```bash
python -m pytest tests -q
node --check app/static/js/compare.js
```

Tests use mocked provider HTTP responses and require no API keys or paid calls.
Before launch, run real-product evaluations for ambiguous generations, variants,
conflicting specifications, misleading prices, missing evidence and unsupported
categories. Verify that recommendations are supported by their cited sources.

## Before public launch

### Vercel deployment

The repository includes a FastAPI Vercel configuration targeting `app/main.py`,
Python 3.12, and a 240-second function duration (the application stops research
after 180 seconds). Connect the GitHub repository with `main` as the production
branch, or use `vercel --prod` from the repository root. `.vercelignore` excludes
local environment files and tests from deployment uploads.

Set `TAVILY_API_KEY` and `OPENAI_API_KEY` in Vercel environment settings if you
want server-managed credentials; otherwise the Connections panel accepts keys
for the current tab. No API keys are included in this repository.

This is a local MVP, not a publicly hardened service. Add HTTPS, shared rate
limits, usage budgets and monitoring, and configure server credentials in a
secret manager. The current guard allows five comparisons/minute per observed
client IP and two concurrent research jobs per process; it is not distributed
and should not rely on untrusted forwarded headers. Browser cancellation stops
waiting but already-issued provider requests may still be billed. The legacy
scraping API retains its original behavior and needs a separate review before
public exposure. Live price accuracy, affiliate/data licensing and provider
coverage require verification; arbitrary websites cannot be guaranteed.

No actual provider requests are performed by the automated test suite. The
first live evaluation needs both API keys.
