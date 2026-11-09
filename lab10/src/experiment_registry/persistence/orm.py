"""ORM models: tables `researchers` and `experiments` (one-to-many)."""

from datetime import date

from sqlalchemy import CheckConstraint, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from experiment_registry.persistence.database import Base


class ResearcherORM(Base):
    __tablename__ = "researchers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    department: Mapped[str] = mapped_column(String(80), nullable=False, default="Physics")

    experiments: Mapped[list["ExperimentORM"]] = relationship(
        back_populates="researcher",
        cascade="all, delete-orphan",
        order_by="ExperimentORM.date",
    )

    def __repr__(self) -> str:
        return f"ResearcherORM(id={self.id}, full_name={self.full_name!r})"


class ExperimentORM(Base):
    __tablename__ = "experiments"
    __table_args__ = (
        CheckConstraint("length(name) > 0", name="ck_experiments_name_not_empty"),
        CheckConstraint("length(parameter) > 0", name="ck_experiments_parameter_not_empty"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    researcher_id: Mapped[int] = mapped_column(
        ForeignKey("researchers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parameter: Mapped[str] = mapped_column(String(50), nullable=False)
    result: Mapped[float] = mapped_column(Float, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)  # migration 0002

    researcher: Mapped[ResearcherORM] = relationship(back_populates="experiments")

    def __repr__(self) -> str:
        return f"ExperimentORM(id={self.id}, name={self.name!r}, result={self.result})"
