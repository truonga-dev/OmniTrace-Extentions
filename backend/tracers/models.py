from typing import Literal, Optional
from pydantic import BaseModel

# status meanings (shown to the user as different badges):
#   confirmed  - account verified to exist by a site-specific detection rule
#   registered - email is registered on the site (username unknown)
#   unverified - plausible link that could not be verified automatically
#   search     - a search link the user has to check manually
Status = Literal["confirmed", "registered", "unverified", "search"]
Category = Literal["account", "search", "metadata"]


class Result(BaseModel):
    platform: str
    url: Optional[str] = None
    username: Optional[str] = None
    status: Status
    category: Category = "account"
    source: str
    note: Optional[str] = None
    details: Optional[dict] = None


class Profile(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
