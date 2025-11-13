# app/schemas.py
from pydantic import BaseModel, EmailStr, Field, StringConstraints, constr, conint, ConfigDict
from typing import Annotated, Optional, List
from annotated_types import Ge, Le


# ---------- Reusable type aliases ----------
NameStr = Annotated[str, StringConstraints(min_length=2, max_length=50)]
StudentID = Annotated[str, StringConstraints(pattern=r'^S\d{7}$')]
CodeStr = Annotated[str, StringConstraints(min_length=1, max_length=32)]
CourseNameStr = Annotated[str, StringConstraints(min_length=1, max_length=255)]
ProjectNameStr = Annotated[str, StringConstraints(min_length=1, max_length=255)]
DescStr = Annotated[str, StringConstraints(min_length=0, max_length=2000)]

AgeInt = Annotated[int, Ge(18), Le(150)]
CreditsInt = Annotated[int, Ge(1), Le(120)]


class UserCreate(BaseModel):
    
    student_id: StudentID # used pattern instead of regex as python v2 no longer uses regex
    name: NameStr
    email: EmailStr
    age: int = Field(gt=18)

class UserRead(BaseModel):
    id: int
    student_id: StudentID
    name: NameStr
    email: EmailStr
    age: int
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    student_id: Optional[StudentID] = None
    name: Optional[NameStr] = None
    email: Optional[EmailStr] = None
    age: Optional[AgeInt] = None


 # Optionally return users with their projects
class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: ProjectNameStr
    description: Optional[DescStr] = None
    owner_id: int

class UserReadWithProjects(UserRead):
    projects: List[ProjectRead] = []

# ---------- Projects ----------
# Flat route: POST /api/projects (owner_id in body)
class ProjectCreate(BaseModel):
    name: ProjectNameStr
    description: Optional[DescStr] = None
    owner_id: int

# Nested route: POST /api/users/{user_id}/projects (owner implied by path)
class ProjectCreateForUser(BaseModel):
    name: ProjectNameStr
    description: Optional[DescStr] = None

class ProjectReadWithOwner(ProjectRead):
    owner: Optional["UserRead"] = None # use selectinload(ProjectDB.owner) when querying

class ProjectUpdate(BaseModel):
    name: Optional[ProjectNameStr] = None
    description: Optional[DescStr] = None

# ---------- Courses ----------
class CourseCreate(BaseModel):
    code: CodeStr
    name: CourseNameStr
    credits: CreditsInt

class CourseRead(CourseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int