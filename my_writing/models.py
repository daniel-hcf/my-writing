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


class RSSSourceCreate(BaseModel):
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    channel: Literal["social", "story"]
    enabled: bool = True


class RSSSourceUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    channel: Literal["social", "story"] | None = None
    enabled: bool | None = None


class SMTPConfigUpdate(BaseModel):
    host: str = ""
    port: int = 465
    username: str = ""
    password: str = ""
    fromEmail: str = ""
    toEmail: str = ""
    useTls: bool = True


class EditorialScheduleUpdate(BaseModel):
    sendTime: str = "08:00"
    autoSend: bool = True
