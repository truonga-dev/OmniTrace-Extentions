import dns.resolver
import smtplib
import socket
import asyncio

async def verify_email_smtp(email: str, sender_email: str = "ping@omnitrace.local", timeout: int = 5) -> str:
    """
    Xác minh email qua giao thức SMTP (RCPT TO).
    Trả về: 'valid', 'invalid', 'catch-all', hoặc 'unknown'.
    """
    try:
        domain = email.split('@')[1]
    except IndexError:
        return "invalid"

    # 1. Tìm bản ghi MX của domain
    try:
        # Chạy đồng bộ vì dnspython cơ bản là block (có thể dùng thread)
        mx_records = dns.resolver.resolve(domain, 'MX')
        # Sắp xếp theo mức độ ưu tiên (preference)
        mx_records = sorted(mx_records, key=lambda rec: rec.preference)
        mx_record = str(mx_records[0].exchange)
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, Exception):
        return "unknown"

    # 2. Kết nối SMTP để kiểm tra (chạy trong thread_pool để không block asyncio loop)
    def _check():
        try:
            server = smtplib.SMTP(timeout=timeout)
            server.set_debuglevel(0)
            server.connect(mx_record)
            server.helo(server.local_hostname or socket.gethostname())
            server.mail(sender_email)
            code, message = server.rcpt(email)
            server.quit()

            if code == 250:
                return "valid"
            elif code == 550:
                return "invalid"
            else:
                return "unknown"
        except Exception:
            return "unknown"

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _check)
    return result

async def verify_email_list(emails: list[str]) -> dict[str, str]:
    """
    Xác minh một danh sách email song song.
    Trả về dictionary {email: status}
    """
    tasks = [verify_email_smtp(email) for email in emails]
    results = await asyncio.gather(*tasks)
    return dict(zip(emails, results))
