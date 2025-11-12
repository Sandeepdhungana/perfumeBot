from pydantic import BaseModel
from typing import Optional, List

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    device_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    matched_perfumes: Optional[List[str]] = None
    returned_count: Optional[int] = None
    remaining_count: Optional[int] = None

class PerfumeFilter(BaseModel):
    top_notes: Optional[str] = None
    middle_notes: Optional[str] = None
    base_notes: Optional[str] = None
    main_accords: Optional[str] = None
    gender: Optional[str] = None

class PerfumeDetails(BaseModel):
    name: str
    top_notes: List[str]
    middle_notes: List[str]
    base_notes: List[str]
    main_accords: List[str]
    gender: List[str]