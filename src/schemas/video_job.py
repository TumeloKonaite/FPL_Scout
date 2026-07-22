from pydantic import BaseModel


class VideoAnalysisJob(BaseModel):
    expert_name: str
    video_title: str
    published_at: str
    gameweek: int
    transcript: str
    video_url: str | None = None
    transcript_id: str | None = None
    transcript_revision_id: str | None = None
