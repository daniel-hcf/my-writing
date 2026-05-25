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


class AssignmentDraftUpdate(BaseModel):
    content: str = ""


class OutlineProjectCreate(BaseModel):
    title: str = Field(min_length=1)
    genre: str = ""
    premise: str = ""
    mainGoal: str = ""
    corePayoff: str = ""


class OutlineProjectUpdate(BaseModel):
    title: str | None = None
    genre: str | None = None
    premise: str | None = None
    mainGoal: str | None = None
    corePayoff: str | None = None
    currentStep: str | None = None


class OutlineCharactersUpdate(BaseModel):
    protagonistIdentity: str | None = None
    protagonistGoal: str | None = None
    protagonistWeakness: str | None = None
    protagonistGrowth: str | None = None
    antagonistIdentity: str | None = None
    antagonistReason: str | None = None
    antagonistPressure: str | None = None


class OutlineVolumeUpdate(BaseModel):
    title: str | None = None
    goal: str | None = None
    pressure: str | None = None
    payoff: str | None = None
    endingHook: str | None = None
    openingHook: str | None = None
    midpointEscalation: str | None = None
    finalExplosion: str | None = None


class OutlineChapterUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    payoff: str | None = None
    hook: str | None = None
    draft: str | None = None


class OutlineReviewRequest(BaseModel):
    scope: Literal["core", "characters", "volume"] = "core"


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
