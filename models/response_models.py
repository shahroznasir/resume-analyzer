from pydantic import BaseModel, Field

class ResumeResponse(BaseModel):
    candidate_name: str = Field(description="Full name of the candidate")
    experience_years: int = Field(description="Estimated years of professional work experience")
    skills: list[str] = Field(description="Key technical and soft skills identified")
    education: list[str] = Field(description="Educational degrees and certifications")
    strengths: list[str] = Field(description="Core strengths of the candidate based on work history")
    weaknesses: list[str] = Field(description="Areas of improvement, gaps in experience, or missing skills")
    overall_score: int = Field(description="Overall fit score between 0 and 100")