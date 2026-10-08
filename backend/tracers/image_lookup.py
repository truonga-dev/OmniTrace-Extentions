"""Image tracing.

What this does (all real data):
  - Reads EXIF metadata embedded in the file: camera, capture time, software and
    GPS coordinates (if the photo still has them - most social networks strip it).
  - Reverse image search: finds pages where the same/similar image is published,
    which often leads to the profile that posted it.

What this deliberately does NOT do: face recognition to identify a person.
"""
import io
import time
from typing import Optional
from urllib.parse import quote

import httpx
from PIL import Image, ExifTags

from .models import Result

MAX_BYTES = 10 * 1024 * 1024
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _to_deg(v) -> float:
    d, m, s = (float(x) for x in v)
    return d + m / 60 + s / 3600


def extract_exif(data: bytes) -> tuple[dict, Optional[tuple[float, float]]]:
    info: dict = {}
    gps_point = None
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:
        return {"Lỗi": "File không phải ảnh hợp lệ"}, None

    info["Định dạng"] = f"{img.format} · {img.width}×{img.height}px"
    exif = img.getexif()
    if not exif:
        info["EXIF"] = "Không có (ảnh đã bị xóa metadata, thường gặp với ảnh tải từ mạng xã hội)"
        return info, None

    tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
    tags.update({ExifTags.TAGS.get(k, k): v for k, v in exif.get_ifd(0x8769).items()})  # Exif IFD
    labels = {"Make": "Hãng máy", "Model": "Thiết bị", "DateTimeOriginal": "Thời điểm chụp",
              "DateTime": "Thời điểm sửa", "Software": "Phần mềm", "Artist": "Tác giả",
              "Copyright": "Bản quyền", "LensModel": "Ống kính"}
    for key, label in labels.items():
        if tags.get(key):
            info[label] = str(tags[key]).strip("\x00 ")

    gps = exif.get_ifd(0x8825)  # GPS IFD
    if gps and 2 in gps and 4 in gps:
        try:
            lat, lon = _to_deg(gps[2]), _to_deg(gps[4])
            if gps.get(1) == "S":
                lat = -lat
            if gps.get(3) == "W":
                lon = -lon
            gps_point = (round(lat, 6), round(lon, 6))
            info["Tọa độ GPS"] = f"{gps_point[0]}, {gps_point[1]}"
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    return info, gps_point


async def _yandex_upload(data: bytes, filename: str) -> tuple[Optional[str], Optional[str]]:
    """Upload the image to Yandex reverse search.

    Returns (yandex_results_url, public_url_of_uploaded_image). The public URL
    lets us build direct result links for the other engines as well.
    """
    try:
        async with httpx.AsyncClient(headers={"User-Agent": _UA}, timeout=20) as c:
            r = await c.post(
                "https://yandex.com/images/search",
                params={"rpt": "imageview", "format": "json",
                        "request": '{"blocks":[{"block":"b-page_type_search-by-image__link"}]}'},
                files={"upfile": (filename or "image.jpg", data, "image/jpeg")},
            )
            params = r.json()["blocks"][0]["params"]
            if params.get("url"):  # older response format
                return f"https://yandex.com/images/search?{params['url']}", params.get("originalImageUrl")
            cbir = params.get("cbirId")
            results_url = (f"https://yandex.com/images/search?rpt=imageview&cbir_id={quote(cbir, safe='')}"
                           if cbir else None)
            return results_url, params.get("originalImageUrl")
    except Exception:
        return None, None


def _url_engines(image_url: str) -> list[Result]:
    u = quote(image_url, safe="")
    engines = {
        "Google Lens": f"https://lens.google.com/uploadbyurl?url={u}",
        "Yandex Images": f"https://yandex.com/images/search?rpt=imageview&url={u}",
        "Bing Visual Search": f"https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{u}",
        "TinEye": f"https://tineye.com/search?url={u}",
    }
    return [Result(platform=n, url=link, status="search", category="search", source="reverse-image",
                   note="Kết quả tìm ngược ảnh – xem trang nào đăng ảnh này") for n, link in engines.items()]


async def lookup_image(data: Optional[bytes], filename: str, image_url: Optional[str]) -> dict:
    started = time.time()
    warnings: list[str] = []
    results: list[Result] = []

    if image_url and not data:
        try:
            async with httpx.AsyncClient(headers={"User-Agent": _UA}, follow_redirects=True, timeout=15) as c:
                r = await c.get(image_url)
                if r.status_code == 200 and len(r.content) <= MAX_BYTES:
                    data = r.content
                else:
                    warnings.append("Không tải được ảnh từ URL để đọc metadata.")
        except httpx.HTTPError:
            warnings.append("Không tải được ảnh từ URL để đọc metadata.")

    metadata: dict = {}
    if data:
        metadata, gps = extract_exif(data)
        if gps:
            results.append(Result(
                platform="Google Maps", url=f"https://www.google.com/maps?q={gps[0]},{gps[1]}",
                status="confirmed", category="metadata", source="exif",
                note="Vị trí chụp lấy từ GPS trong ảnh",
            ))

    if image_url:
        results.extend(_url_engines(image_url))
    elif data:
        yandex_url, hosted_url = await _yandex_upload(data, filename)
        if hosted_url:
            # Image now has a public URL -> every engine can search it directly.
            engines = _url_engines(hosted_url)
            if yandex_url:
                engines = [e for e in engines if e.platform != "Yandex Images"]
                engines.insert(0, Result(platform="Yandex Images", url=yandex_url, status="search",
                                         category="search", source="reverse-image",
                                         note="Kết quả tìm ngược ảnh – xem trang nào đăng ảnh này"))
            results.extend(engines)
            warnings.append("Ảnh đã được tải lên máy chủ Yandex để tìm kiếm ngược.")
        else:
            warnings.append("Không tự tải ảnh lên công cụ tìm kiếm được; hãy mở trang và kéo thả ảnh vào.")
            for name, link in {"Google Lens": "https://lens.google.com/",
                               "Yandex Images": "https://yandex.com/images/",
                               "Bing Visual Search": "https://www.bing.com/visualsearch",
                               "TinEye": "https://tineye.com/"}.items():
                results.append(Result(platform=name, url=link, status="search", category="search",
                                      source="reverse-image", note="Mở trang rồi kéo thả ảnh vào để tìm"))

    return {
        "results": results,
        "profile": None,
        "metadata": metadata,
        "stats": {"checked": len(results), "found": sum(r.status == "confirmed" for r in results),
                  "duration": round(time.time() - started, 1)},
        "warnings": warnings,
    }
