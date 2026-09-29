from pydantic import BaseModel, Field


class AssistantAskRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    farm_id: int | None = None


class AssistantMessageOut(BaseModel):
    role: str
    content: str
    created_at: str


class AssistantAskResponse(BaseModel):
    session_id: int
    reply: AssistantMessageOut
    used_data: list[str]
    suggested_questions: list[str]


class AssistantHistoryResponse(BaseModel):
    session_id: int | None
    messages: list[AssistantMessageOut]
