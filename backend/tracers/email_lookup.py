"""Email tracing.

Two real data sources:
1. holehe  - checks whether the email is *registered* on ~120 sites by probing
   signup / password-recovery endpoints. It confirms existence only; it can NOT
   reveal the username on that site (the site does not expose it).
2. Gravatar - if the email owner created a public Gravatar profile, it can
   contain display name, avatar, location and linked social accounts.
"""
import asyncio
import hashlib
import time

import httpx

from .models import Result, Profile

# Map holehe domains to friendly platform names used by the frontend icons.
_FRIENDLY = {
    "twitter.com": "X (Twitter)",
    "instagram.com": "Instagram",
    "facebook.com": "Facebook",
    "github.com": "GitHub",
    "spotify.com": "Spotify",
    "discord.com": "Discord",
    "pinterest.com": "Pinterest",
    "tumblr.com": "Tumblr",
    "snapchat.com": "Snapchat",
    "office365.com": "Microsoft 365",
    "amazon.com": "Amazon",
}


def _run_holehe_sync(email: str) -> list[dict]:
    """holehe is built on trio; run it in its own thread with its own trio loop
    so it never conflicts with FastAPI's asyncio loop."""
    import trio
    from holehe.core import import_submodules, get_functions, launch_module

    modules = import_submodules("holehe.modules")
    websites = get_functions(modules)

    async def _main():
        out: list[dict] = []
        client = httpx.AsyncClient(timeout=12)
        try:
            async with trio.open_nursery() as nursery:
                for site in websites:
                    nursery.start_soon(launch_module, site, email, client, out)
        finally:
            await client.aclose()
        return out

    return trio.run(_main)


async def _gravatar(email: str, client: httpx.AsyncClient) -> tuple[Profile | None, list[Result]]:
    md5 = hashlib.md5(email.strip().lower().encode()).hexdigest()
    results: list[Result] = []
    profile: Profile | None = None
    try:
        r = await client.get(f"https://en.gravatar.com/{md5}.json", timeout=10)
        if r.status_code == 200:
            entry = (r.json().get("entry") or [{}])[0]
            name = (entry.get("name") or {}).get("formatted") or entry.get("displayName")
            profile = Profile(
                name=name,
                avatar=entry.get("thumbnailUrl"),
                bio=entry.get("aboutMe"),
                location=entry.get("currentLocation"),
                source="Gravatar",
            )
            results.append(Result(
                platform="Gravatar", url=entry.get("profileUrl"),
                status="confirmed", category="account", source="gravatar",
                note="Hồ sơ Gravatar công khai gắn với email này",
            ))
            # Accounts the owner *personally* linked on Gravatar -> high confidence.
            for acc in entry.get("accounts", []) or []:
                results.append(Result(
                    platform=acc.get("name") or acc.get("shortname") or "Liên kết",
                    url=acc.get("url"), username=acc.get("username"),
                    status="confirmed", category="account", source="gravatar",
                    note="Chủ email tự liên kết trên Gravatar",
                ))
            for u in entry.get("urls", []) or []:
                results.append(Result(
                    platform=u.get("title") or "Website", url=u.get("value"),
                    status="confirmed", category="account", source="gravatar",
                    note="Website do chủ email khai báo",
                ))
        elif r.status_code != 404:
            # Profile may be private; avatar alone still proves an account exists.
            a = await client.get(f"https://www.gravatar.com/avatar/{md5}?d=404", timeout=10)
            if a.status_code == 200:
                profile = Profile(avatar=f"https://www.gravatar.com/avatar/{md5}?s=200", source="Gravatar")
    except (httpx.HTTPError, ValueError):
        pass
    return profile, results


async def lookup_email(email: str) -> dict:
    started = time.time()
    warnings: list[str] = []
    results: list[Result] = []

    async with httpx.AsyncClient(headers={"User-Agent": "OmniTrace/1.0"}) as client:
        holehe_task = asyncio.to_thread(_run_holehe_sync, email)
        gravatar_task = _gravatar(email, client)
        holehe_out, (profile, grav_results) = await asyncio.gather(
            holehe_task, gravatar_task, return_exceptions=False
        )

    results.extend(grav_results)

    rate_limited = 0
    for item in holehe_out:
        if item.get("rateLimit"):
            rate_limited += 1
            continue
        if item.get("exists") is True:
            domain = item.get("domain", "")
            note = "Email đã được dùng để đăng ký tài khoản"
            # Some modules leak a partially-masked recovery email / phone.
            extras = {k: v for k, v in (("Email khôi phục", item.get("emailrecovery")),
                                         ("SĐT", item.get("phoneNumber"))) if v}
            results.append(Result(
                platform=_FRIENDLY.get(domain, domain), url=f"https://{domain}",
                status="registered", category="account", source="holehe",
                note=note, details=extras or None,
            ))

    if rate_limited:
        warnings.append(f"{rate_limited} trang chặn tần suất truy vấn (rate limit) nên không kiểm tra được.")

    return {
        "results": results,
        "profile": profile,
        "stats": {"checked": len(holehe_out) + 1, "found": len(results),
                  "duration": round(time.time() - started, 1)},
        "warnings": warnings,
    }
