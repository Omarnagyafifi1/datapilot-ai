from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str


class HealthResponse(BaseModel):
    status: str
