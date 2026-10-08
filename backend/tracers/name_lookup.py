"""Full-name tracing.

A name is not a unique identifier (thousands of people share it), so no tool can
"accurately" map a name to accounts automatically. We therefore return:
  - real candidates from GitHub's public user search (with name/location/avatar),
    clearly marked as unverified, and
  - ready-made people-search links on each social network for manual review.
"""
import asyncio
import time
from urllib.parse import quote_plus

import httpx

from .models import Result

_SEARCH_LINKS = {
    "Facebook":  "https://www.facebook.com/search/people/?q={q}",
    "LinkedIn":  "https://www.linkedin.com/search/results/people/?keywords={q}",
    "X (Twitter)": "https://x.com/search?q={q}&f=user",
    "TikTok":    "https://www.tiktok.com/search/user?q={q}",
    "Instagram": "https://www.google.com/search?q=site%3Ainstagram.com+%22{raw}%22",
    "YouTube":   "https://www.youtube.com/results?search_query={q}&sp=EgIQAg%253D%253D",
    "GitHub":    "https://github.com/search?q={q}&type=users",
    "Google":    "https://www.google.com/search?q=%22{raw}%22+(site%3Afacebook.com+OR+site%3Ainstagram.com+OR+site%3Alinkedin.com+OR+site%3Atiktok.com+OR+site%3Ax.com)",
}


async def _github_candidates(name: str, client: httpx.AsyncClient) -> tuple[list[Result], list[str]]:
    warnings: list[str] = []
    try:
        r = await client.get("https://api.github.com/search/users",
                             params={"q": f'"{name}" in:name', "per_page": 5}, timeout=10)
        if r.status_code == 403:
            return [], ["GitHub giới hạn số lần tìm kiếm, thử lại sau ít phút."]
        items = r.json().get("items", []) if r.status_code == 200 else []
        profiles = await asyncio.gather(
            *(client.get(f"https://api.github.com/users/{i['login']}", timeout=10) for i in items),
            return_exceptions=True,
        )
    except (httpx.HTTPError, ValueError):
        return [], ["Không kết nối được GitHub API."]

    results = []
    for item, p in zip(items, profiles):
        info = p.json() if isinstance(p, httpx.Response) and p.status_code == 200 else {}
        details = {k: v for k, v in (("Họ tên", info.get("name")), ("Vị trí", info.get("location")),
                                     ("Công ty", info.get("company")), ("Giới thiệu", info.get("bio"))) if v}
        results.append(Result(
            platform="GitHub", url=item["html_url"], username=item["login"],
            status="unverified", category="account", source="github-search",
            note="Trùng tên – cần xác minh có đúng người không", details=details or None,
        ))
    return results, warnings


async def lookup_name(name: str) -> dict:
    started = time.time()
    name = " ".join(name.split())
    async with httpx.AsyncClient(headers={"User-Agent": "OmniTrace/1.0",
                                          "Accept": "application/vnd.github+json"}) as client:
        results, warnings = await _github_candidates(name, client)

    for platform, tpl in _SEARCH_LINKS.items():
        results.append(Result(
            platform=platform, url=tpl.format(q=quote_plus(name), raw=quote_plus(name)),
            status="search", category="search", source="search-link",
            note="Mở để tìm người theo tên (có thể cần đăng nhập)",
        ))

    return {
        "results": results,
        "profile": None,
        "stats": {"checked": len(_SEARCH_LINKS) + 1,
                  "found": sum(r.category == "account" for r in results),
                  "duration": round(time.time() - started, 1)},
        "warnings": warnings + ["Họ tên không phải định danh duy nhất – mọi kết quả đều cần tự xác minh."],
    }
