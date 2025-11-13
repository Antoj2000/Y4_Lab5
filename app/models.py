from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint

class Base(DeclarativeBase):
    pass

class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    student_id: Mapped[str] = mapped_column (String, unique=True, nullable=False)
    # 'projects' tells SQLalchemy that one UserDB object can have many related projectDB objects
    projects: Mapped[list["ProjectDB"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


# A) Related table (one-to-many relationship with UserDB -one user could have many projects)
# UniqueConstraint is added to ensure users cannot have more than 1 project with the same name
class ProjectDB(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    # 'owner_id' is a foreignkey column that links each project to a specific user 
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # Each projectDB has one userDB as its owner
    owner: Mapped["UserDB"] = relationship(back_populates="projects")


# B) Independent table
class CourseDB(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(nullable=False) # required field
    credits: Mapped[int] = mapped_column(nullable=False) # required field