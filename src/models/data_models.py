from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Activity:
    name: str
    min_participants: int
    max_participants: int
    is_cancelled: bool = False

@dataclass
class Person:
    name: str
    preferences: List[str]
    assigned_activity: Optional[str] = None
    preference_level: Optional[int] = None
    original_preference: Optional[int] = None 