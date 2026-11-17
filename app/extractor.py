"""Fetch a public HTML page without allowing DNS rebinding or unsafe redirects."""
import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import aiohttp
from aiohttp.abc import AbstractResolver
from bs4 import BeautifulSoup

MAX_BYTES = 1_000_000
MAX_TEXT = 24_000


class WebsiteError(Exception):
    pass


def validate_url(url):
    try:
        parts = urlsplit(url)
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username is not None or parts.password is not None:
            raise ValueError()
        if parts.port not in (None, 80, 443):
            raise ValueError()
        if parts.hostname.lower().rstrip('.').endswith(('.local', '.localhost')) or parts.hostname.lower().rstrip('.') == 'localhost':
            raise ValueError()
        try:
            address = ipaddress.ip_address(parts.hostname)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError()
    except ValueError:
        raise WebsiteError('URL must be a public HTTP(S) address on port 80 or 443 without credentials.')


class PublicResolver(AbstractResolver):
    async def resolve(self, host, port=0, family=socket.AF_UNSPEC):
        try:
            records = await asyncio.get_running_loop().getaddrinfo(host, port, family=family, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise WebsiteError('Website hostname could not be resolved.') from exc
        addresses = {record[4][0] for record in records}
        if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
            raise WebsiteError('Website resolves to a non-public address.')
        return [{'hostname': host, 'host': ip, 'port': port, 'family': socket.AF_INET6 if ':' in ip else socket.AF_INET, 'proto': 0, 'flags': socket.AI_NUMERICHOST} for ip in addresses]

    async def close(self):
        pass


async def extract(url):
    current = str(url)
    timeout = aiohttp.ClientTimeout(total=20, connect=5, sock_read=10)
    connector = aiohttp.TCPConnector(resolver=PublicResolver(), use_dns_cache=False)
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=timeout, trust_env=False, headers={'User-Agent': 'LinkAnalysisBot/1.0'}) as session:
            for _ in range(6):
                validate_url(current)
                async with session.get(current, allow_redirects=False) as response:
                    if response.status in (301, 302, 303, 307, 308):
                        location = response.headers.get('Location')
                        if not location:
                            raise WebsiteError('Website returned a redirect without a destination.')
                        current = urljoin(current, location)
                        continue
                    if response.status >= 400:
                        raise WebsiteError('Website returned HTTP {}.'.format(response.status))
                    if response.content_type not in ('text/html', 'application/xhtml+xml'):
                        raise WebsiteError('Website did not return HTML.')
                    body = bytearray()
                    async for chunk in response.content.iter_chunked(16384):
                        body.extend(chunk)
                        if len(body) > MAX_BYTES:
                            raise WebsiteError('Website HTML exceeds the size limit.')
                    html = bytes(body).decode(response.charset or 'utf-8', errors='replace')
                    return current, clean_html(html)
            raise WebsiteError('Website exceeded the redirect limit.')
    except WebsiteError:
        raise
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError, LookupError, UnicodeError) as exc:
        raise WebsiteError('Website could not be accessed safely.') from exc


def clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.get_text(' ', strip=True) if soup.title else ''
    description = soup.find('meta', attrs={'name': lambda x: x and x.lower() == 'description'})
    description = description.get('content', '') if description else ''
    for node in soup(['script', 'style', 'noscript', 'svg', 'nav', 'footer', 'header', 'form']):
        node.decompose()
    lines = []
    seen = set()
    for line in soup.stripped_strings:
        line = ' '.join(line.split())
        if line and line not in seen:
            seen.add(line)
            lines.append(line)
    result = ('Title: ' + title + '\nMeta description: ' + description + '\nPage text:\n' + '\n'.join(lines))[:MAX_TEXT]
    if sum(len(line) for line in lines) < 40:
        raise WebsiteError('Website contains too little readable HTML text to analyze.')
    return result
