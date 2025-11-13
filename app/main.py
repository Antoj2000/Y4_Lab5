from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database import engine, get_db
from .schemas import (
    UserCreate, UserRead,
    UserUpdate,
    CourseCreate, CourseRead,
    ProjectCreate, ProjectRead,
    ProjectUpdate,
    ProjectReadWithOwner, ProjectCreateForUser
)
from .models import Base, UserDB, CourseDB, ProjectDB


#Replacing @app.on_event("startup")

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine) 
    yield

app = FastAPI(lifespan=lifespan)

#CORS (add this block)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # dev-friendly; tighten in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

def commit_or_rollback(db: Session, error_msg: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        HTTPException(status_code=409, detail=error_msg)

@app.get("/health")
def health():
    return {"status" : "ok"}

# --- Courses ---
# Add a course
@app.post("/api/courses", response_model=CourseRead, status_code=201, summary="Create a course")
def create_course(course: CourseCreate, db: Session = Depends(get_db)):
    db_course = CourseDB(**course.model_dump())
    db.add(db_course)
    commit_or_rollback(db, "Course already exists")
    db.refresh(db_course)
    return db_course

# List all courses
@app.get("/api/courses", response_model=list[CourseRead])
def list_courses(limit: int = 10, offset: int = 0, db: Session = Depends(get_db)):
    stmt = select(CourseDB).order_by(CourseDB.id).limit(limit).offset(offset)
    return db.execute(stmt).scalars().all()


# --- Projects ---
# Create a project
@app.post("/api/projects", response_model=ProjectRead, status_code=201)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    user = db.get(UserDB, project.owner_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    proj = ProjectDB(
        name=project.name,
        description=project.description,
        owner_id=project.owner_id,
    )
    db.add(proj)
    commit_or_rollback(db, "Project creation failed")
    db.refresh(proj)
    return proj

# List all projects
@app.get("/api/projects", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    stmt = select(ProjectDB).order_by(ProjectDB.id)
    return db.execute(stmt).scalars().all()


# Get projects by projectID
@app.get("/api/projects/{project_id}", response_model=ProjectReadWithOwner)
def get_project_with_owner(project_id: int, db: Session = Depends(get_db)):
    stmt = select(ProjectDB).where(ProjectDB.id ==
                                   project_id).options(selectinload(ProjectDB.owner))
    proj = db.execute(stmt).scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj

# Update Project
@app.put("/api/projects/update/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectCreate, db: Session = Depends(get_db)):
    proj = db.get(ProjectDB, project_id)
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    for key, value in payload.model_dump().items():
        setattr(proj, key, value)
    try: 
        db.commit()
        db.refresh(proj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project already exists")
    return proj

# Patch Project
@app.patch("/api/projects/patch/{project_id}", response_model=ProjectRead)
def patch_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    proj = db.get(ProjectDB, project_id)
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(proj, key, value)
    try:
        db.commit()
        db.refresh(proj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Project already exists")

    return proj


# --- Nested Routes --- 

# Get users with their related projects
@app.get("/api/users/{users_id}/projects", response_model=list[ProjectRead])
def get_user_projects(users_id: int, db: Session = Depends(get_db)):
    stmt = select(ProjectDB).where(ProjectDB.owner_id == users_id)
    #space it out for debugging
    result = db.execute(stmt)
    rows = result.scalars().all()
    return rows
    #return db.execute(stmt).scalars().all()

# Add a project to a user
@app.post("/api/users/{user_id}/projects", response_model=ProjectRead, status_code=201)
def create_user_project(users_id: int, project: ProjectCreateForUser, db: Session = Depends(get_db)):
    user = db.get(UserDB, users_id)
    if not user: 
        raise HTTPException(status_code=404, detail="User not found")
    proj = ProjectDB(
        name=project.name,
        description=project.description,
        owner_id=users_id
    )
    db.add(proj)
    commit_or_rollback(db, "Project creation failed")
    db.refresh(proj)
    return proj

# --- Users

#Get all users
@app.get("/api/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    # stmt is a python representation of a SQL query
    stmt = select(UserDB).order_by(UserDB.id)
    # scalars pulls the UserDB object out of the rows
    return list(db.execute(stmt).scalars())

#Get user by id
@app.get("/api/users/{users_id}", response_model=UserRead)
def get_user(users_id: int, db: Session = Depends(get_db)):
    user = db.get(UserDB, users_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

#Create user 
@app.post("/api/users", status_code=status.HTTP_201_CREATED)
def add_user(payload: UserCreate, db: Session = Depends(get_db)):
    user = UserDB(**payload.model_dump())
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    # Unique fields in models.py are the ones used to verify if a student exists 
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    return user

# Update User
@app.put("/api/users/update/{users_id}", response_model=UserRead)
def update_user(users_id: int, payload: UserCreate, db: Session = Depends(get_db)):
    user = db.get(UserDB, users_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    for key, value in payload.model_dump().items():
        setattr(user, key, value)
    try: 
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or Student ID already exists")
    return user

# Patch User
@app.patch("/api/users/patch/{users_id}", response_model=UserRead)
def patch_user(users_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    user = db.get(UserDB, users_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email or Student ID already exists")

    return user

    
#Delete User
@app.delete("/api/users/delete/{users_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(users_id: int, db: Session = Depends(get_db)):
    user = db.get(UserDB, users_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(user)
    db.commit()
