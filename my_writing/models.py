from typing import Literal

from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    provider: str = ""
    apiKey: str = ""
    baseUrl: str = ""
    model: str = ""


class FullConfig(BaseModel):
    text: ProviderConfig
    image: ProviderConfig


class SubmissionCreate(BaseModel):
    assignmentId: int
    content: str = Field(min_length=1)


class TestRequest(BaseModel):
    target: Literal["text", "image"]
