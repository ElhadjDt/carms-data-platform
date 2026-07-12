# api/schemas.py

from pydantic import BaseModel, Field

class DisciplineRead(BaseModel):
    discipline_id: int
    discipline_name: str

    model_config = {"from_attributes": True}


class SchoolRead(BaseModel):
    school_id: int
    school_name: str

    model_config = {"from_attributes": True}


class SiteRead(BaseModel):
    site_id: int
    site_name: str

    model_config = {"from_attributes": True}


class StreamName(BaseModel):
    program_stream: str

    model_config = {"from_attributes": True}


class ProgramSummary(BaseModel):
    program_stream_id: int
    program_name: str
    program_url: str

    model_config = {"from_attributes": True}


class ProgramRead(BaseModel):
    discipline_id: int
    discipline_name: str

    school_id: int
    school_name: str

    program_stream_id: int
    program_stream: str
    program_stream_name: str

    program_site: str

    program_name: str
    program_url: str


class QARequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class SourceRef(BaseModel):
    program_name: str
    program_url: str


class QAResponse(BaseModel):
    answer: str
    sources: list[SourceRef] = []