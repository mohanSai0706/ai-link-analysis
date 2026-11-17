import asyncio
import socket
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.extractor import PublicResolver, WebsiteError, clean_html, validate_url
from app.main import app
from app.schemas import ModelResult


@pytest.mark.parametrize('url', ['http://127.0.0.1', 'http://169.254.169.254/', 'http://[::1]/', 'http://localhost/', 'http://example.com:8080', 'http://user:pass@example.com'])
def test_rejects_unsafe_urls(url):
    with pytest.raises(WebsiteError):
        validate_url(url)


def test_resolver_rejects_mixed_public_private_answers():
    records = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 80)), (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.1', 80))]
    async def run():
        loop = asyncio.get_running_loop()
        with patch.object(loop, 'getaddrinfo', return_value=records):
            with pytest.raises(WebsiteError):
                await PublicResolver().resolve('example.com', 80)
    asyncio.run(run())


def test_cleaning_removes_script_and_duplicates():
    text = clean_html('<title>Example</title><script>secret</script><main><p>We provide practical technology services for small businesses.</p><p>We provide practical technology services for small businesses.</p></main>')
    assert 'secret' not in text
    assert text.count('We provide practical') == 1


def test_endpoint_validation_and_blocked_site():
    client = TestClient(app)
    assert client.post('/link-analysis', json={'url': 'invalid'}).status_code == 422
    response = client.post('/link-analysis', json={'url': 'http://127.0.0.1/'})
    assert response.status_code == 400


def test_endpoint_returns_structured_result(monkeypatch):
    import app.main as main
    result = ModelResult.model_validate({
        'brand': {'name': 'Example', 'category': 'Services', 'summary': 'Example service', 'products_and_services': ['Consulting']},
        'analysis': {
            'competitor_analysis': {'brand_overview': 'Example', 'competitors': [], 'brand_advantages': [], 'positioning_opportunities': []},
            'target_search_queries': [{'query': 'example query '+str(i), 'platforms': ['Google'], 'intent': 'Discovery', 'business_relevance': 'Relevant', 'target_audience': 'Businesses'} for i in range(5)],
            'seo_improvements': {'primary_keyword': 'consulting', 'secondary_keywords': [], 'long_tail_keywords': [], 'business_keywords': [], 'recommended_title': 'Consulting', 'meta_description': 'Consulting services', 'supporting_content': []},
            'top_services': [],
            'target_audience': {'primary_audience': [], 'secondary_audience': [], 'industries': [], 'business_types': [], 'customer_profiles': [], 'geographic_focus': None, 'customer_needs': [], 'interests': [], 'recommended_segments': []}
        }})
    async def fake_extract(url): return url, 'A website about consulting.'
    async def fake_analyze(content): return result
    monkeypatch.setattr(main, 'extract', fake_extract)
    monkeypatch.setattr(main, 'analyze', fake_analyze)
    response = TestClient(app).post('/link-analysis', json={'url': 'https://example.com'})
    assert response.status_code == 200
    assert len(response.json()['analysis']['target_search_queries']) == 5
    assert response.json()['brand']['name'] == 'Example'


def test_ollama_connection_error_is_reported(monkeypatch):
    import httpx
    import app.main as main
    from fastapi import HTTPException

    class BrokenClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            raise httpx.ConnectError('connection refused')

    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    monkeypatch.setattr(main.httpx, 'AsyncClient', BrokenClient)
    with pytest.raises(HTTPException) as error:
        asyncio.run(main.analyze('Some content'))
    assert error.value.status_code == 502


def test_query_platforms_cover_all_five():
    from app.main import normalize_analysis, PLATFORMS
    from types import SimpleNamespace
    queries = [SimpleNamespace(platforms=['Google', 'Google']) for _ in range(5)]
    result = SimpleNamespace(analysis=SimpleNamespace(target_search_queries=queries))
    normalize_analysis(result)
    assert [query.platforms for query in queries] == [[platform] for platform in PLATFORMS]
