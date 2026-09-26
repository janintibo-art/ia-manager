"""Accès à internet pour les IA : recherche web et lecture de pages.

Moteurs, dans l'ordre (sans clé par défaut) :
  1. Brave Search (si une clé API gratuite est renseignée : le plus fiable)
  2. SearXNG (si l'adresse d'une instance est renseignée)
  3. DuckDuckGo (page HTML, sans clé)
  4. Wikipédia (secours : toujours disponible)
"""

import html as html_mod
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

import requests

from src.backend import settings

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/126.0 Safari/537.36")
DDG_HTML_URL = "https://html.duckduckgo.com/html/"
DDG_LITE_URL = "https://lite.duckduckgo.com/lite/"
WIKI_API = "https://{lang}.wikipedia.org/w/api.php"
BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
TIMEOUT = 12
PAGE_CHARS = 5000


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", html_mod.unescape(text)).strip()


# ------------------------------------------------------------------ moteurs
def _ddg_url(href: str) -> str:
    href = html_mod.unescape(href)
    if href.startswith("//"):
        href = "https:" + href
    q = parse_qs(urlparse(href).query)
    if "uddg" in q:
        return unquote(q["uddg"][0])
    return href


def parse_ddg_html(page: str) -> List[Dict]:
    results = []
    links = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S)
    if not links:
        links = re.findall(r'<a[^>]+href="([^"]+)"[^>]+class="result__a"[^>]*>(.*?)</a>', page, re.S)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</(?:a|div|td)>', page, re.S)
    for i, (href, title) in enumerate(links):
        url = _ddg_url(href)
        if not url.startswith("http") or "duckduckgo.com/y.js" in url:
            continue
        results.append({"title": _clean(title), "url": url,
                        "snippet": _clean(snippets[i]) if i < len(snippets) else ""})
    return results


def parse_ddg_lite(page: str) -> List[Dict]:
    results = []
    links = re.findall(r"<a[^>]+href=\"([^\"]+)\"[^>]+class=['\"]result-link['\"][^>]*>(.*?)</a>", page, re.S)
    snippets = re.findall(r"class=['\"]result-snippet['\"][^>]*>(.*?)</td>", page, re.S)
    for i, (href, title) in enumerate(links):
        url = _ddg_url(href)
        if url.startswith("http") and "duckduckgo.com/y.js" not in url:
            results.append({"title": _clean(title), "url": url,
                            "snippet": _clean(snippets[i]) if i < len(snippets) else ""})
    return results


def search_ddg(query: str, n: int) -> List[Dict]:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.6"}
    for url, parser in ((DDG_HTML_URL, parse_ddg_html), (DDG_LITE_URL, parse_ddg_lite)):
        try:
            r = requests.post(url, data={"q": query, "kl": "fr-fr"}, headers=headers, timeout=TIMEOUT)
            if r.status_code == 200:
                res = parser(r.text)
                if res:
                    return res[:n]
        except Exception:
            continue
    return []


def search_wikipedia(query: str, n: int, lang: str = "fr") -> List[Dict]:
    try:
        r = requests.get(WIKI_API.format(lang=lang), params={
            "action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": n,
            "utf8": 1}, headers={"User-Agent": "IA-Manager/1.0"}, timeout=TIMEOUT)
        items = r.json().get("query", {}).get("search", [])
    except Exception:
        return []
    base = WIKI_API.format(lang=lang).replace("/w/api.php", "/wiki/")
    return [{"title": it.get("title", ""), "url": base + it.get("title", "").replace(" ", "_"),
             "snippet": _clean(it.get("snippet", ""))} for it in items]


def search_searxng(query: str, n: int, base: str) -> List[Dict]:
    try:
        r = requests.get(base.rstrip("/") + "/search", params={"q": query, "format": "json", "language": "fr"},
                         headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        items = r.json().get("results", [])
    except Exception:
        return []
    return [{"title": it.get("title", ""), "url": it.get("url", ""), "snippet": _clean(it.get("content", ""))}
            for it in items if it.get("url")][:n]


def search_brave(query: str, n: int, key: str) -> List[Dict]:
    try:
        r = requests.get(BRAVE_URL, params={"q": query, "count": n, "search_lang": "fr"},
                         headers={"X-Subscription-Token": key, "Accept": "application/json"}, timeout=TIMEOUT)
        items = (r.json().get("web") or {}).get("results", [])
    except Exception:
        return []
    return [{"title": _clean(it.get("title", "")), "url": it.get("url", ""),
             "snippet": _clean(it.get("description", ""))} for it in items if it.get("url")][:n]


def search(query: str, n: int = 5) -> Tuple[List[Dict], str]:
    """(résultats, nom du moteur utilisé)"""
    query = (query or "").strip()[:300]
    if not query:
        return [], ""
    brave = (settings.get("brave_key") or "").strip()
    if brave:
        res = search_brave(query, n, brave)
        if res:
            return res, "Brave"
    searx = (settings.get("searxng_url") or "").strip()
    if searx:
        res = search_searxng(query, n, searx)
        if res:
            return res, "SearXNG"
    res = search_ddg(query, n)
    if res:
        return res, "DuckDuckGo"
    res = search_wikipedia(query, n) or search_wikipedia(query, n, "en")
    return res, "Wikipédia" if res else ""


# ------------------------------------------------------------------ lecture de pages
class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form", "aside", "iframe"}
    BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "tr", "section", "article", "pre"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.skip = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip:
            self.parts.append(data)


def html_to_text(page: str) -> Tuple[str, str]:
    ex = _TextExtractor()
    try:
        ex.feed(page)
    except Exception:
        pass
    text = "".join(ex.parts)
    lines = [re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if len(ln) > 1]
    return ex.title.strip(), "\n".join(lines)


def fetch_page(url: str, max_chars: int = PAGE_CHARS) -> Dict:
    """Texte lisible d'une page web (tronqué). Ne lève pas d'exception : renvoie {"error": …}."""
    if not url.startswith(("http://", "https://")):
        return {"url": url, "error": "adresse invalide"}
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9"},
                         timeout=TIMEOUT)
        ctype = r.headers.get("Content-Type", "")
        if r.status_code != 200:
            return {"url": url, "error": f"réponse {r.status_code}"}
        if "html" not in ctype and "text" not in ctype:
            return {"url": url, "error": f"contenu non lisible ({ctype.split(';')[0] or 'inconnu'})"}
        r.encoding = r.encoding or r.apparent_encoding
        title, text = html_to_text(r.text) if "html" in ctype else ("", r.text)
        return {"url": url, "title": title, "text": text[:max_chars], "truncated": len(text) > max_chars}
    except Exception as e:
        return {"url": url, "error": str(e)[:200]}


# ------------------------------------------------------------------ contexte prêt pour l'IA
def today() -> str:
    days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
              "octobre", "novembre", "décembre"]
    d = datetime.now()
    return f"{days[d.weekday()]} {d.day} {months[d.month - 1]} {d.year}"


def format_results(query: str, results: List[Dict], pages: Optional[List[Dict]] = None, engine: str = "") -> str:
    if not results:
        return f"Aucun résultat trouvé sur internet pour « {query} »."
    out = [f"Résultats de recherche web ({engine or 'web'}, {today()}) pour « {query} » :"]
    by_url = {p["url"]: p for p in pages or [] if not p.get("error")}
    for i, r in enumerate(results, 1):
        out.append(f"\n[{i}] {r['title']}\n{r['url']}\n{r['snippet']}")
        page = by_url.get(r["url"])
        if page and page.get("text"):
            out.append(f"Contenu de la page :\n{page['text']}")
    return "\n".join(out)


def research(query: str, n_results: int = 5, n_pages: int = 2) -> Dict:
    """Recherche + lecture des premières pages, en parallèle. Renvoie {context, sources, engine}."""
    results, engine = search(query, n_results)
    pages: List[Dict] = []
    if results and n_pages:
        with ThreadPoolExecutor(max_workers=n_pages) as ex:
            pages = list(ex.map(lambda r: fetch_page(r["url"], 3000), results[:n_pages]))
    return {"context": format_results(query, results, pages, engine),
            "sources": [{"title": r["title"], "url": r["url"]} for r in results], "engine": engine}


def sources_markdown(sources: List[Dict]) -> str:
    seen, lines = set(), []
    for s in sources:
        if s["url"] in seen:
            continue
        seen.add(s["url"])
        lines.append(f"- [{s['title'] or s['url']}]({s['url']})")
    return ("\n\n**Sources :**\n" + "\n".join(lines)) if lines else ""
