"""Smoke tests for every OSINT module. Run: python test_modules.py [email|name|image|username]"""
import asyncio
import io
import sys

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

from tracers.email_lookup import lookup_email
from tracers.image_lookup import lookup_image
from tracers.name_lookup import lookup_name
from tracers.username_lookup import lookup_username


def show(title, data):
    rs = data["results"]
    print(f"\n=== {title}: {len(rs)} results, {data['stats']} ===")
    if data.get("profile"):
        print("  PROFILE:", data["profile"].model_dump(exclude_none=True))
    for r in rs[:8]:
        print(f"  [{r.status}] {r.platform} -> {r.url} {r.details or ''}")
    for w in data.get("warnings", []):
        print("  WARN:", w)
    if data.get("metadata"):
        print("  META:", data["metadata"])


async def main():
    which = sys.argv[1:] or ["email", "name", "image", "username"]
    if "email" in which:
        show("email test@gmail.com", await lookup_email("test@gmail.com"))
    if "name" in which:
        show("name Linus Torvalds", await lookup_name("Linus Torvalds"))
    if "image" in which:
        buf = io.BytesIO()
        Image.new("RGB", (64, 64), "red").save(buf, "JPEG")
        show("image (generated)", await lookup_image(buf.getvalue(), "t.jpg", None))
    if "username" in which:
        show("username torvalds", await lookup_username("torvalds"))
        show("username fake", await lookup_username("zxqv9182736fakeuser"))


asyncio.run(main())
