"""Username / ID tracing powered by Maigret.

Maigret keeps a maintained database of ~3000 sites, each with its own detection
rule (status code, "not found" message, redirect target, or official API).
That is what removes the false positives we had with naive HTTP 200 checks
(login walls, JS anti-bot challenges, localized 404 pages...).

Important: the same username on two sites does NOT guarantee the same person.
"""
import asyncio
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .models import Result, Profile

TOP_SITES = 500        # most popular sites by Alexa rank
SITE_TIMEOUT = 10      # seconds per site
PROCESS_TIMEOUT = 240  # hard cap for the whole scan

_PROFILE_FIELDS = {
    "fullname": "name", "name": "name",
    "image": "avatar", "avatar": "avatar",
    "location": "location", "country": "location",
    "bio": "bio", "about": "bio", "description": "bio",
}
_DETAIL_LABELS = {
    "fullname": "Họ tên", "location": "Vị trí", "bio": "Giới thiệu",
    "created_at": "Ngày tạo", "follower_count": "Người theo dõi",
    "following_count": "Đang theo dõi", "company": "Công ty",
    "website": "Website", "uid": "ID nội bộ", "country": "Quốc gia",
}


def normalize_username(raw: str) -> str:
    q = raw.strip()
    # Accept pasted profile URLs: https://github.com/user -> user
    if q.startswith(("http://", "https://")):
        q = q.rstrip("/").split("/")[-1]
    q = q.lstrip("@")
    return re.sub(r"\s+", "", q)


def _run_maigret(username: str, out_dir: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "maigret", username,
         "--top-sites", str(TOP_SITES), "--timeout", str(SITE_TIMEOUT),
         "--no-recursion", "--no-progressbar", "--no-color",
         "-J", "simple", "--folderoutput", out_dir],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
        timeout=PROCESS_TIMEOUT,
    )


async def lookup_username(raw: str) -> dict:
    started = time.time()
    username = normalize_username(raw)
    warnings: list[str] = []
    results: list[Result] = []
    profile = Profile()

    with tempfile.TemporaryDirectory() as tmp:
        try:
            await asyncio.to_thread(_run_maigret, username, tmp)
        except subprocess.TimeoutExpired:
            warnings.append("Quét quá thời gian, kết quả có thể chưa đầy đủ.")
        report = Path(tmp) / f"report_{username}_simple.json"
        data = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {}

    if not data and not warnings:
        warnings.append("Không có kết quả từ Maigret (có thể do mất mạng).")

    for site_name, entry in data.items():
        status = entry.get("status") or {}
        if status.get("status") != "Claimed":
            continue
        ids = status.get("ids") or {}
        details = {
            _DETAIL_LABELS[k]: v for k, v in ids.items()
            if k in _DETAIL_LABELS and v not in (None, "", "None")
        }
        # Fill the aggregated profile from the first site that has each field.
        for key, attr in _PROFILE_FIELDS.items():
            if ids.get(key) and not getattr(profile, attr):
                setattr(profile, attr, str(ids[key])[:300])
                profile.source = profile.source or site_name

        results.append(Result(
            platform=site_name,
            url=status.get("url") or entry.get("url_user"),
            username=username,
            # Maigret flags fuzzy matches as "similar" -> not a confirmed hit.
            status="unverified" if entry.get("is_similar") else "confirmed",
            category="account", source="maigret",
            note=", ".join(status.get("tags") or [])[:80] or None,
            details=details or None,
        ))

    # Numeric IDs are commonly Facebook profile IDs; we cannot verify them
    # without logging in, so they are offered as an unverified lead.
    if username.isdigit() and len(username) >= 6:
        results.append(Result(
            platform="Facebook", url=f"https://www.facebook.com/profile.php?id={username}",
            status="unverified", category="account", source="pattern",
            note="ID dạng số – có thể là ID Facebook, cần mở để xác minh",
        ))

    # Rich profiles first, then by name.
    results.sort(key=lambda r: (r.status != "confirmed", not r.details, r.platform.lower()))

    has_profile = any(getattr(profile, f) for f in ("name", "avatar", "bio", "location"))
    return {
        "results": results,
        "profile": profile if has_profile else None,
        "stats": {"checked": TOP_SITES, "found": len(results),
                  "duration": round(time.time() - started, 1)},
        "warnings": warnings,
        "normalized": username,
    }
