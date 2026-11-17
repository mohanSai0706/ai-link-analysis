# AI-powered website link analysis

FastAPI endpoint that extracts readable text from a public website and uses Ollama or OpenAI structured output to provide brand, competitor, search query, SEO, services and audience insights.

## Setup

Python 3.10+ and [Ollama](https://ollama.com/download) are required for the default local provider. No API key or per-request API fee is needed. From this directory:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Install and start Ollama, then download the default model once with `ollama pull llama3`. This requires storage and internet access; model inference runs locally. Copy `.env.example` to `.env` if you want to change settings. The default is `LLM_PROVIDER=ollama` and `OLLAMA_MODEL=llama3:latest`. For OpenAI instead, set `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and optionally `OPENAI_MODEL`. Never commit `.env`. Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Open http://localhost:4000/docs or run:

```bash
curl -X POST http://localhost:4000/link-analysis -H "Content-Type: application/json" -d '{"url":"https://example.com"}'
```

Windows PowerShell users can instead run:

```powershell
Invoke-RestMethod -Method Post http://localhost:4000/link-analysis -ContentType 'application/json' -Body '{"url":"https://example.com"}'
```

The response includes `success`, `website`, `final_url`, `brand`, and `analysis` with `competitor_analysis`, `target_search_queries`, `seo_improvements`, `top_services`, and `target_audience`; each service has a `basis` of `website` or `inferred`. The model is asked to generate five queries in Google, Facebook, Instagram, LinkedIn, X order; the application assigns these platform labels by position to ensure coverage. Relevance still requires review. `limitations` identifies unverified competitor suggestions and the lack of search-volume data. Results depend on the page and model. A 422 indicates malformed input, 400 indicates an unsafe or inaccessible site, 503 indicates missing configuration, and 502 indicates an LLM failure. The automated endpoint test in `tests/test_api.py` demonstrates a complete representative response with a mocked provider.

The `examples/` folder contains a real Shopify analysis response and a screenshot of an earlier successful Shopify request. Generated claims and platform relevance require human review. The recorded response identified three services, illustrating that the local model may return fewer than five even when the page contains additional offerings.

Illustrative abbreviated response (arrays shortened for readability):

```json
{
  "success": true,
  "website": "https://example.com/",
  "final_url": "https://example.com/",
  "brand": {"name": "Example", "category": "Consulting", "summary": "Business consulting", "products_and_services": ["Consulting"]},
  "analysis": {
    "competitor_analysis": {"brand_overview": "Business consulting", "competitors": [], "brand_advantages": [], "positioning_opportunities": []},
    "target_search_queries": [{"query": "business consulting services", "platforms": ["Google", "LinkedIn"], "intent": "Service discovery", "business_relevance": "Relevant to consulting", "target_audience": "Businesses"}],
    "seo_improvements": {"primary_keyword": "business consulting", "secondary_keywords": [], "long_tail_keywords": [], "business_keywords": [], "recommended_title": "Business Consulting | Example", "meta_description": "Explore business consulting.", "supporting_content": []},
    "top_services": [{"name": "Consulting", "description": "Business advice", "target_industry": "Business", "target_customer": "Business owners", "main_benefit": "Expert guidance", "basis": "website"}],
    "target_audience": {"primary_audience": ["Businesses"], "secondary_audience": [], "industries": [], "business_types": [], "customer_profiles": [], "geographic_focus": null, "customer_needs": [], "interests": [], "recommended_segments": []}
  },
  "limitations": ["Competitor suggestions are unverified."]
}
```

```bash
python -m pytest -q
```

## Model selection and cost

Prices checked 17 November 2026, USD per million tokens, standard paid API text rates. They can change. Context sizes are provider specifications, not a guarantee of usable output quality. No model was benchmarked for this assignment; latency and accuracy must be measured on representative pages.

| Provider / model | Input / output | Context | JSON | Speed and suitability |
| --- | --- | --- | --- | --- |
| [OpenAI GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) | $0.10 / $0.50 | 1,050,000 | Structured output | Designed for efficient high-volume work; selected for the implementation. Accuracy and actual latency unmeasured. |
| [Anthropic Claude Haiku 5.5](https://platform.claude.com/docs/en/models/haiku-5-5/overview) | $0.10 / $0.50 up to 100k input | 1M | [Structured output](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) | Provider describes it as fast; alternative worth evaluating. Accuracy and actual latency unmeasured. |
| [Google Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) | $0.75 / $3.75 through 2026-12-31; $1.50 / $7.50 afterwards | 1,048,576 input | Structured output | Potential option for more complex analysis; [pricing](https://ai.google.dev/gemini-api/docs/pricing) changes on 2027-01-01. Accuracy and actual latency unmeasured. |

For an illustrative 6,000 input and 2,000 billable output tokens, Luna costs approximately **$0.0016 per analysis**: `(6000 × 0.10 + 2000 × 0.50) / 1,000,000`. This assumes standard non-cached pricing and includes any reasoning tokens within the assumed output total; actual usage varies. A planning assumption of 5–30 seconds for the LLM plus website fetch is **not measured or guaranteed**. Haiku is a candidate fallback, but is not implemented; changing providers needs a separate adapter. Compare factual grounding, schema validity, service extraction, search query quality, human-reviewed competitor suggestions, p50/p95 latency, and token spend across a representative test set before production selection.

Ollama with `llama3:latest` is the default for a no-API-fee local demonstration, using local compute and storage. Its speed and accuracy depend on hardware and are unmeasured; it should be benchmarked against hosted models before production use. The OpenAI recommendation above is a hosted alternative, not a claim that a paid service is required. The implementation removes scripts and duplicate text, caps HTML and extracted content, and makes one model call. Further savings could come from caching content hashes and model/prompt versions with an expiry, batching noninteractive jobs, and measuring whether smaller models meet quality requirements. Caching and automatic fallback are not implemented.

## Boundaries

Only the requested page and its redirect chain are fetched, not linked pages or JavaScript-rendered content. Only public HTTP(S) addresses on ports 80/443 are allowed. DNS is resolved and checked in the connector used for the actual connection, and redirects are checked again; responses have size and time limits. This is a local assignment implementation: public deployment also requires authentication, rate limiting, outbound network controls, monitoring, privacy review, and evaluation. Website content is untrusted and is sent to the configured LLM provider (local Ollama by default). Competitor statements are suggestions, not independently researched facts; review before relying on them.
