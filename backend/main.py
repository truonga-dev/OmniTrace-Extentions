"""OmniTrace OSINT API.

Endpoints
  GET  /api/health          -> liveness check used by the UI status badge
  POST /api/trace           -> {"type": "username"|"email"|"name", "query": "..."}
  POST /api/trace/image     -> multipart form: file=<image> and/or url=<image url>
"""
import re
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from tracers.email_lookup import lookup_email
from tracers.image_lookup import MAX_BYTES, lookup_image
from tracers.name_lookup import lookup_name
from tracers.username_lookup import lookup_username

app = FastAPI(title="OmniTrace OSINT API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")


class TraceRequest(BaseModel):
    type: Literal["username", "email", "name"]
    query: str


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": app.version}


@app.post("/api/trace")
async def trace_target(req: TraceRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(400, "Vui lòng nhập dữ liệu cần truy vết.")

    if req.type == "email":
        if not _EMAIL_RE.match(query):
            raise HTTPException(400, "Email không hợp lệ.")
        data = await lookup_email(query.lower())
    elif req.type == "username":
        data = await lookup_username(query)
    else:
        if len(query.split()) < 2:
            raise HTTPException(400, "Vui lòng nhập đầy đủ họ và tên (ít nhất 2 từ).")
        data = await lookup_name(query)

    return {"query": query, "type": req.type, **data}


@app.post("/api/trace/image")
async def trace_image(file: Optional[UploadFile] = File(None), url: Optional[str] = Form(None)):
    if not file and not url:
        raise HTTPException(400, "Hãy chọn ảnh hoặc nhập URL ảnh.")
    data = None
    filename = "image.jpg"
    if file:
        data = await file.read()
        filename = file.filename or filename
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "Ảnh vượt quá 10MB.")
    url = url.strip() if url else None
    if url and not url.startswith(("http://", "https://")):
        raise HTTPException(400, "URL ảnh không hợp lệ.")

    result = await lookup_image(data, filename, url)
    return {"query": filename if file else url, "type": "image", **result}

class EmailGenRequest(BaseModel):
    name: str
    domain: str

@app.post("/api/trace/email-gen")
async def trace_email_gen(req: EmailGenRequest):
    if not req.name or not req.domain:
         raise HTTPException(400, "Vui lòng nhập tên và domain.")
         
    from tracers.email_generator import generate_emails
    from tracers.smtp_verifier import verify_email_list
    
    generated_emails = generate_emails(req.name, req.domain)
    
    if not generated_emails:
        return {"query": f"{req.name} @ {req.domain}", "type": "email-gen", "results": []}
        
    verification_results = await verify_email_list(generated_emails)
    
    results = []
    for email, status in verification_results.items():
        results.append({
            "platform": "SMTP",
            "url": None,
            "username": email,
            "status": "confirmed" if status == "valid" else ("unverified" if status in ["unknown", "catch-all"] else "search"),
            "category": "metadata",
            "source": "SMTP Verifier",
            "note": f"SMTP status: {status}"
        })
        
    return {
        "query": f"{req.name} @ {req.domain}",
        "type": "email-gen",
        "results": results,
        "stats": {
            "checked": len(generated_emails),
            "found": sum(1 for s in verification_results.values() if s == "valid"),
            "duration": 0
        },
        "warnings": []
    }
