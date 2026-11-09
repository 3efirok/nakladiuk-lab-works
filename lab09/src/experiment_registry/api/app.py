"""FastAPI application: REST API over the persistence layer of lab 7."""

import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import inspect

from experiment_registry import __version__
from experiment_registry.api.aggregation import collect_statistics
from experiment_registry.api.schemas import (
    AggregatedStatistics,
    ErrorResponse,
    ExperimentCreate,
    ExperimentRead,
    ExperimentUpdate,
    ExtendedStatisticsRead,
    ResearcherCreate,
    ResearcherRead,
    SortOrder,
    StatisticsRead,
)
from experiment_registry.exceptions import (
    DuplicateExperimentError,
    ExperimentNotFoundError,
    ExperimentValidationError,
)
from experiment_registry.persistence.database import (
    create_db_engine,
    create_session_factory,
    get_database_url,
    init_db,
)
from experiment_registry.persistence.orm import ExperimentORM
from experiment_registry.persistence.services import ExperimentRegistry

NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"model": ErrorResponse, "description": "Object not found"}}


def get_registry(request: Request) -> ExperimentRegistry:
    """Dependency: the service object stored in application state."""
    registry: ExperimentRegistry = request.app.state.registry
    return registry


Registry = Annotated[ExperimentRegistry, Depends(get_registry)]


def to_read(items: Sequence[ExperimentORM]) -> list[ExperimentRead]:
    return [ExperimentRead.model_validate(item) for item in items]


def create_app(database_url: str | None = None, create_schema: bool = True) -> FastAPI:
    url = database_url or get_database_url()
    engine = create_db_engine(url)
    if create_schema and not inspect(engine).has_table("experiments"):
        init_db(engine)  # development convenience; production uses `alembic upgrade head`

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    app = FastAPI(
        title="Experiment Registry API",
        version=__version__,
        description="REST API for scientific experiment results (variant 15, Professional Python).",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.registry = ExperimentRegistry(create_session_factory(engine))

    # ---------------------------------------------------------- error handlers
    @app.exception_handler(ExperimentNotFoundError)
    async def not_found(_: Request, error: ExperimentNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(ExperimentValidationError)
    async def invalid(_: Request, error: ExperimentValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.exception_handler(DuplicateExperimentError)
    async def conflict(_: Request, error: DuplicateExperimentError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(error)})

    # ------------------------------------------------------------------ root
    @app.get("/", tags=["service"])
    def root() -> dict[str, str]:
        return {"name": "experiment-registry", "version": __version__, "docs": "/docs"}

    # ------------------------------------------------------------ researchers
    @app.get("/researchers", response_model=list[ResearcherRead], tags=["researchers"])
    def list_researchers(registry: Registry) -> list[ResearcherRead]:
        return [ResearcherRead.model_validate(r) for r in registry.list_researchers()]

    @app.post("/researchers", response_model=ResearcherRead, status_code=status.HTTP_201_CREATED,
              responses={409: {"model": ErrorResponse}}, tags=["researchers"])
    def create_researcher(body: ResearcherCreate, registry: Registry) -> ResearcherRead:
        return ResearcherRead.model_validate(
            registry.create_researcher(body.full_name, body.email, body.department))

    @app.get("/researchers/{researcher_id}", response_model=ResearcherRead, responses=NOT_FOUND,
             tags=["researchers"])
    def get_researcher(researcher_id: int, registry: Registry) -> ResearcherRead:
        return ResearcherRead.model_validate(registry.get_researcher(researcher_id))

    @app.get("/researchers/{researcher_id}/experiments", response_model=list[ExperimentRead],
             responses=NOT_FOUND, tags=["researchers"])
    def researcher_experiments(researcher_id: int, registry: Registry,
                               sort: SortOrder = "date") -> list[ExperimentRead]:
        return to_read(registry.researcher_experiments(researcher_id, sort))

    # ------------------------------------------------------------ experiments
    @app.get("/experiments", response_model=list[ExperimentRead], tags=["experiments"])
    def list_experiments(
        registry: Registry,
        researcher_id: Annotated[int | None, Query(gt=0)] = None,
        parameter: str | None = None,
        min_result: float | None = None,
        max_result: float | None = None,
        sort: SortOrder = "date",
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[ExperimentRead]:
        if min_result is not None and max_result is not None and min_result > max_result:
            raise HTTPException(status_code=422, detail="min_result must be <= max_result")
        return to_read(registry.list_experiments(
            researcher_id=researcher_id, parameter=parameter, min_result=min_result,
            max_result=max_result, sort=sort, limit=limit, offset=offset))

    # declared before /experiments/{experiment_id} so that "statistics" is not parsed as an ID
    @app.get("/experiments/statistics", response_model=StatisticsRead, responses=NOT_FOUND,
             tags=["statistics"])
    async def experiment_statistics(registry: Registry, parameter: str | None = None,
                                    researcher_id: Annotated[int | None, Query(gt=0)] = None
                                    ) -> StatisticsRead:
        summary = await asyncio.to_thread(registry.summary, parameter, researcher_id)
        return StatisticsRead(count=summary.count, average=summary.average, minimum=summary.minimum,
                              maximum=summary.maximum, parameter=parameter, researcher_id=researcher_id)

    @app.get("/experiments/statistics/extended", response_model=ExtendedStatisticsRead, tags=["statistics"])
    def extended_statistics(registry: Registry, parameter: str | None = None) -> ExtendedStatisticsRead:
        """mean, std, median, p95 via NumPy; cached until the next write (lab 9)."""
        hits = registry.cache_hits
        result = ExtendedStatisticsRead.model_validate(registry.extended_statistics(parameter))
        result.cached = registry.cache_hits > hits
        return result

    @app.get("/experiments/statistics/by-researcher", response_model=AggregatedStatistics,
             tags=["statistics"])
    async def statistics_by_researcher(
        registry: Registry,
        ids: Annotated[list[int], Query(min_length=1, max_length=20)],
        max_concurrency: Annotated[int, Query(ge=1, le=10)] = 3,
        timeout: Annotated[float, Query(gt=0, le=10)] = 2.0,
    ) -> AggregatedStatistics:
        """Statistics for several researchers computed concurrently (Task + gather + Semaphore)."""
        return await collect_statistics(lambda rid: registry.summary(researcher_id=rid), ids,
                                        max_concurrency, timeout)

    @app.get("/experiments/{experiment_id}", response_model=ExperimentRead, responses=NOT_FOUND,
             tags=["experiments"])
    def get_experiment(experiment_id: int, registry: Registry) -> ExperimentRead:
        return ExperimentRead.model_validate(registry.get_experiment(experiment_id))

    @app.post("/experiments", response_model=ExperimentRead, status_code=status.HTTP_201_CREATED,
              responses=NOT_FOUND, tags=["experiments"])
    def create_experiment(body: ExperimentCreate, registry: Registry) -> ExperimentRead:
        created = registry.create_experiment(body.researcher_id, body.name, body.parameter, body.result,
                                             body.date, body.notes)
        return ExperimentRead.model_validate(registry.get_experiment(created.id))

    @app.patch("/experiments/{experiment_id}", response_model=ExperimentRead, responses=NOT_FOUND,
               tags=["experiments"])
    def update_experiment(experiment_id: int, body: ExperimentUpdate, registry: Registry) -> ExperimentRead:
        registry.update_experiment(experiment_id, body.model_dump(exclude_unset=True))
        return ExperimentRead.model_validate(registry.get_experiment(experiment_id))

    @app.delete("/experiments/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT,
                responses=NOT_FOUND, tags=["experiments"])
    def delete_experiment(experiment_id: int, registry: Registry) -> Response:
        registry.delete(experiment_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app
