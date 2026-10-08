import re
import unicodedata
from typing import List

def normalize_name(name: str) -> str:
    """Loại bỏ dấu tiếng Việt, ký tự đặc biệt, chuyển thành chữ thường."""
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    name = re.sub(r'[^a-zA-Z0-9 ]', '', name).lower()
    return name.strip()

def generate_emails(full_name: str, domain: str) -> List[str]:
    """
    Tạo danh sách các định dạng email phổ biến dựa trên họ tên và domain công ty.
    Ví dụ: Nguyen Van A, công ty abc.com -> nva@abc.com, nguyen.a@abc.com...
    """
    if not full_name or not domain:
        return []

    name = normalize_name(full_name)
    parts = name.split()
    if not parts:
        return []

    first_name = parts[-1]  # Trong tiếng Việt, tên nằm cuối
    last_name = parts[0]    # Họ nằm đầu
    middle_names = "".join(parts[1:-1]) if len(parts) > 2 else ""
    
    # Đối với tên người nước ngoài (vd: John Doe), First = John, Last = Doe
    # Ở đây ta ưu tiên tạo chung các pattern để vét cạn:
    # 1: Tiếng Việt (Nguyễn Văn A) -> last: nguyen, mid: van, first: a
    # 2: Tiếng Anh (John Doe) -> last: john, first: doe (nếu xét theo thứ tự từ, nhưng pattern sẽ sinh đủ)

    # Chỉnh sửa logic: parts[0] (từ 1), parts[-1] (từ cuối)
    word1 = parts[0]
    word2 = parts[-1] if len(parts) > 1 else ""
    mid = "".join([p[0] for p in parts[1:-1]]) if len(parts) > 2 else ""

    patterns = []
    
    if word1 and word2:
        # Giả sử word1 = nguyen, word2 = a, mid = v (Văn)
        
        # Format tiếng Việt:
        # anv@domain
        patterns.append(f"{word2}{mid}{word1[0]}")
        # anguyen@domain
        patterns.append(f"{word2}{word1}")
        # a.nguyen@domain
        patterns.append(f"{word2}.{word1}")
        # nguyen.a@domain
        patterns.append(f"{word1}.{word2}")
        # nguyenvana@domain
        patterns.append(f"{word1}{''.join(parts[1:-1])}{word2}")

        # Format quốc tế (Nếu word1 là First, word2 là Last)
        patterns.append(f"{word1[0]}{word2}")
        patterns.append(f"{word1}{word2[0]}")
        patterns.append(f"{word1}_{word2}")
        patterns.append(f"{word2}_{word1}")
        patterns.append(f"{word1}.{word2[0]}")

    # Chỉ có 1 từ
    patterns.append(word1)
    patterns.append(word2)

    domain = domain.strip().lower()
    if domain.startswith("www."):
        domain = domain[4:]

    emails = []
    for p in patterns:
        if p:
            emails.append(f"{p}@{domain}")

    # Xóa trùng lặp nhưng giữ nguyên thứ tự
    seen = set()
    result = []
    for email in emails:
        if email not in seen:
            seen.add(email)
            result.append(email)

    return result
