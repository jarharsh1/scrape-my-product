"""Offline integration tests: real HTTP contracts, no paid API calls."""

import copy
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.comparison import ComparisonDraft, Credentials, Source
from app.routes.compare import _visitors
from app.services.research import ResearchError, ResearchService, public_url, validate_evidence


def draft_data():
    def claim(pid):
        return {"text": "Suitable for office use", "source_ids": [f"{pid}-s1"]}
    return {
        "title": "Monitor Alpha vs Monitor Beta",
        "products": [{"id": pid, "name": f"Monitor {pid}", "variant_note": "27-inch",
                      "best_for": claim(pid), "strengths": [claim(pid)], "limitations": [],
                      "offers": []} for pid in ["p1", "p2"]],
        "rows": [{"attribute": "Panel", "values": [
            {"product_id": "p1", "value": "IPS", "source_ids": ["p1-s1"]},
            {"product_id": "p2", "value": "Not verified", "source_ids": []}]}],
        "recommendation": {"product_id": "p1", "verdict": "Choose Alpha for office use",
                           "reason": "Its documented IPS panel fits this use.", "source_ids": ["p1-s1"]},
        "caveats": ["No confirmed current prices."],
    }


def sources():
    return [Source(id=f"{pid}-s1", product_id=pid, title="Product page",
                   url=f"https://example.com/{pid}", excerpt="IPS", retrieved_at="2026-10-15T00:00:00Z",
                   kind="page") for pid in ["p1", "p2"]]


def structured_response(data):
    return {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": json.dumps(data)}]}]}


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _visitors.clear()


def test_home_and_missing_keys():
    with TestClient(app) as client:
        home = client.get("/")
        assert home.status_code == 200 and "Compare products." in home.text
        assert client.get("/legacy").status_code == 200
        result = client.post("/api/compare", json={"query": "Monitor Alpha vs Monitor Beta"})
        assert result.status_code == 503
        assert result.json()["detail"]["code"] == "setup_required"


def test_status_only_returns_presence(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-TEST-SECRET")
    with TestClient(app) as client:
        response = client.get("/api/compare/status")
        assert response.json() == {"tavily_configured": True, "openai_configured": False}
        assert "SECRET" not in response.text


@pytest.mark.asyncio
async def test_full_research_pipeline():
    calls = []
    async def transport(request):
        payload = json.loads(request.content)
        calls.append((str(request.url), payload))
        assert request.headers["Authorization"].startswith("Bearer ")
        if request.url.host == "api.openai.com":
            assert payload["store"] is False
            if payload["text"]["format"]["name"] == "ResearchPlan":
                return httpx.Response(200, json=structured_response({"products": ["Monitor Alpha", "Monitor Beta"], "focus": "office", "assumptions": []}))
            assert "p1-s1" in payload["input"]
            return httpx.Response(200, json=structured_response(draft_data()))
        if request.url.path == "/search":
            pid = "p1" if "Alpha" in payload["query"] else "p2"
            return httpx.Response(200, json={"results": [{"url": f"https://example.com/{pid}", "title": "Product", "content": "An IPS monitor for office use."},
                                                         {"url": "javascript:alert(1)", "content": "bad link"}]})
        return httpx.Response(200, json={"results": [{"url": u, "raw_content": "An IPS monitor for office use."} for u in payload["urls"]]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        service = ResearchService(client, Credentials(tavily="test", openai="test"))
        result = await service.compare("Monitor Alpha vs Monitor Beta", "India")
    assert len(calls) == 10  # two OpenAI calls, four searches, two extracts
    assert len(result.sources) == 2  # duplicate URLs collapsed per product
    assert all(s.kind == "page" for s in result.sources)
    assert result.products[0].offers == []
    assert result.rows[0].values[1].value == "Not verified"


@pytest.mark.parametrize("mutation", ["fake_source", "wrong_product", "missing_citation", "missing_cell", "fake_pick"])
def test_rejects_invalid_evidence(mutation):
    data = copy.deepcopy(draft_data())
    if mutation == "fake_source": data["products"][0]["strengths"][0]["source_ids"] = ["invented"]
    if mutation == "wrong_product": data["products"][0]["best_for"]["source_ids"] = ["p2-s1"]
    if mutation == "missing_citation": data["rows"][0]["values"][0]["source_ids"] = []
    if mutation == "missing_cell": data["rows"][0]["values"].pop()
    if mutation == "fake_pick": data["recommendation"]["product_id"] = "p9"
    with pytest.raises(ResearchError):
        validate_evidence(ComparisonDraft.model_validate(data), sources(), 2)


@pytest.mark.asyncio
async def test_provider_error_does_not_leak_secrets():
    async def transport(request):
        return httpx.Response(401, json={"error": "secret-value"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        service = ResearchService(client, Credentials(tavily="secret-value", openai="secret-value"))
        with pytest.raises(ResearchError) as caught:
            await service.search("monitor")
        assert caught.value.status == 401
        assert "secret-value" not in str(caught.value)


@pytest.mark.asyncio
async def test_extraction_failure_uses_labelled_excerpts():
    async def transport(request):
        if request.url.path == "/search":
            return httpx.Response(200, json={"results": [{"url": "https://example.com/p1", "content": "IPS", "title": "Monitor"}]})
        return httpx.Response(500, json={})
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        service = ResearchService(client, Credentials(tavily="test", openai="test"))
        found, evidence, warnings = await service.discover(0, "Monitor", "India")
    assert found[0].kind == "search_excerpt" and warnings and evidence


@pytest.mark.asyncio
async def test_single_product_is_not_silently_expanded():
    async def transport(request):
        return httpx.Response(200, json=structured_response({"products": [], "focus": "", "assumptions": []}))
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        service = ResearchService(client, Credentials(tavily="test", openai="test"))
        with pytest.raises(ResearchError) as caught:
            await service.compare("Monitor Alpha", "India")
    assert caught.value.status == 422


def test_endpoint_uses_owner_keys_ignoring_visitor_headers(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "owner-tavily-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "owner-openai-secret")
    seen = []
    async def fake_compare(self, query, country):
        seen.append(self.credentials.tavily.get_secret_value())
        return __import__('app.models.comparison', fromlist=['ComparisonResult']).ComparisonResult(
            **draft_data(), query=query, country=country, assumptions=[], sources=sources(), checked_at="2026-10-15T00:00:00Z", warnings=[])
    monkeypatch.setattr(ResearchService, "compare", fake_compare)
    with TestClient(app) as client:
        response = client.post("/api/compare", json={"query": "Monitor Alpha vs Monitor Beta"},
                               headers={"X-Tavily-Api-Key": "test-tavily-secret", "X-OpenAI-Api-Key": "test-openai-secret"})
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert "secret" not in response.text
        assert client.get("/api/compare/status").json()["tavily_configured"] is True
    assert seen == ["owner-tavily-secret"]


def test_link_safety():
    assert public_url("javascript:alert(1)") is None
    assert public_url("https://user:secret@example.com") is None
    assert public_url("https://example.com/product#reviews") == "https://example.com/product"


def test_omits_unverified_price_without_losing_comparison():
    data = draft_data()
    data["products"][0]["offers"] = [{"price_text": "₹9,999", "source_id": "p1-s1", "amount": 9999, "currency": "INR", "variant": "27-inch", "condition": "new", "availability": "in_stock", "shipping": "Not verified", "evidence_quote": "₹9,999"}]
    draft = ComparisonDraft.model_validate(data)
    validate_evidence(draft, sources(), 2,
                      [{"id": "p1-s1", "content": "An IPS monitor. Price unavailable."}])
    assert draft.products[0].offers == []
    assert any("unverified price was omitted" in note for note in draft.caveats)
    assert draft.rows


def test_rate_limit_prevents_unbounded_provider_calls(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    calls = []
    async def fake_compare(self, query, country):
        calls.append(query)
        raise ResearchError("Mock unavailable")
    monkeypatch.setattr(ResearchService, "compare", fake_compare)
    with TestClient(app) as client:
        for _ in range(5):
            assert client.post("/api/compare", json={"query": "Alpha vs Beta"},
                               headers={"X-Tavily-Api-Key": "test", "X-OpenAI-Api-Key": "test"}).status_code == 502
        assert client.post("/api/compare", json={"query": "Alpha vs Beta"},
                           headers={"X-Tavily-Api-Key": "test", "X-OpenAI-Api-Key": "test"}).status_code == 429
    assert len(calls) == 5


def test_ad_config_requires_valid_publisher(monkeypatch):
    monkeypatch.delenv("ADSENSE_PUBLISHER_ID", raising=False)
    with TestClient(app) as client:
        assert "adsbygoogle.js" not in client.get("/").text
        assert client.get("/ads.txt").status_code == 404
        monkeypatch.setenv("ADSENSE_PUBLISHER_ID", "ca-pub-1234567890123456")
        assert "adsbygoogle.js?client=ca-pub-1234567890123456" in client.get("/").text
        assert client.get("/ads.txt").text == "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0\n"
        monkeypatch.setenv("ADSENSE_PUBLISHER_ID", "invalid")
        assert "adsbygoogle.js" not in client.get("/").text


@pytest.mark.asyncio
async def test_source_images_are_filtered_and_attributed():
    async def transport(request):
        if request.url.path == "/search":
            return httpx.Response(200, json={"results": [{"url": "https://example.com/alpha", "content": "Alpha specs", "title": "Alpha"}]})
        return httpx.Response(200, json={"results": [{"url": "https://example.com/alpha", "raw_content": "Alpha specs", "images": ["https://example.com/alpha.jpg", "https://example.com/alpha-logo.png", "javascript:alpha()"]}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        found, _, _ = await ResearchService(client, Credentials(tavily="test", openai="test")).discover(0, "Alpha", "India")
    assert found[0].image_urls == ["https://example.com/alpha.jpg"]
    assert found[0].url == "https://example.com/alpha"


@pytest.mark.parametrize("kind,amount,quote,expected", [
    ("page", 9999, "Price INR 9,999", 1),
    ("search_excerpt", 9999, "Price INR 9,999", 1),
    ("page", 99, "Price INR 9,999", 0),
    ("page", 9999, "Invented INR 9,999", 0),
])
def test_seller_price_requires_exact_source_evidence(kind, amount, quote, expected):
    data = draft_data()
    data["products"][0]["offers"] = [{"price_text": "INR 9,999", "source_id": "p1-s1", "amount": amount, "currency": "INR", "variant": "27-inch", "condition": "new", "availability": "unknown", "shipping": "Not verified", "evidence_quote": quote}]
    draft = ComparisonDraft.model_validate(data)
    refs = sources()
    refs[0].kind = kind
    validate_evidence(draft, refs, 2, [{"id": "p1-s1", "content": "Monitor Alpha. Price INR 9,999"}])
    assert len(draft.products[0].offers) == expected


def test_price_tracker_is_not_a_buying_offer():
    data = draft_data()
    data["products"][0]["offers"] = [{"price_text": "INR 9999", "source_id": "p1-s1", "amount": 9999, "currency": "INR", "variant": "27-inch", "condition": "new", "availability": "in_stock", "shipping": "Not verified", "evidence_quote": "INR 9999"}]
    draft = ComparisonDraft.model_validate(data)
    refs = sources()
    refs[0].url = "https://pricehistory.app/p/monitor"
    validate_evidence(draft, refs, 2, [{"id": "p1-s1", "content": "INR 9999"}])
    assert draft.products[0].offers == []


def test_images_reject_wrong_generation_and_review_banner():
    from app.services.research import matching_product_image
    assert matching_product_image("https://cdn.example.com/sony-wh-1000xm5.jpg", "Sony WH-1000XM5")
    assert not matching_product_image("https://cdn.example.com/sony-wh-1000xm4.jpg", "Sony WH-1000XM5")
    assert not matching_product_image("https://cdn.example.com/sony-wh-1000xm5-review.jpg", "Sony WH-1000XM5")
    assert not matching_product_image("https://cdn.example.com/momentum-3.jpg", "Sennheiser Momentum 4 Wireless")


def test_described_images_allow_opaque_cdn_urls():
    from app.services.research import image_candidates
    items = [{"url": "https://cdn.example.com/a8f9.jpg", "description": "Sony WH-1000XM5 black headphones product photo"},
             {"url": "https://cdn.example.com/other.jpg", "description": "Sony WH-1000XM4 headphones"},
             {"url": "https://cdn.example.com/banner.jpg", "description": "Sony WH-1000XM5 comparison collage"}]
    assert image_candidates(items, "Sony WH-1000XM5") == ["https://cdn.example.com/a8f9.jpg"]


def test_optional_image_metadata_is_safe():
    from app.services.research import image_candidates
    assert image_candidates(None, "Sony WH-1000XM5") == []
    assert image_candidates([{"url":"https://cdn.example.com/random.jpg", "description":None}], "Sony WH-1000XM5") == []
