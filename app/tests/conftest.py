from collections.abc import Callable, Iterator, Sequence
from typing import Any

import pytest
from _pytest import logging
from loguru import logger
import sqlmodel

from app import main
from app.data import crud, dependencies
from app.database import config
from app.models import models


@pytest.fixture(scope="function")
def get_db_session() -> Iterator[sqlmodel.Session]:
    """Gets a database session fixture.

    Yields:
        db: The database session.

    This is a module scoped fixture that yields a database session.
    The session is closed after the test finishes executing.
    """
    with sqlmodel.Session(config.testing_engine) as session:
        yield session


@pytest.fixture(scope="function")
def override_get_db_session() -> Any:
    """Override get_db_session dependecy.

    This is a module scoped fixture that overrides the get_db_session
    dependency for a function tailored for testing purposes.
    The sesion is closed after the test finishes executing.
    """

    def get_db_session() -> Iterator[sqlmodel.Session]:
        with sqlmodel.Session(config.testing_engine) as session:
            yield session

    main.app.dependency_overrides[dependencies.get_db_session] = get_db_session
    try:
        yield config.Base.metadata.create_all(bind=config.testing_engine)
    finally:
        config.Base.metadata.drop_all(bind=config.testing_engine)


@pytest.fixture(scope="function", autouse=True)
def setup_db(get_db_session: sqlmodel.Session) -> Any:
    """Sets up and tears down the database for tests.

    Args:
        get_db_session: The database session fixture.

    This fixture will create all tables before each test runs
    and drop all tables after each test finishes using the
    provided database session. It is function scoped and
    auto-used to setup/teardown the database for all tests.
    """
    try:
        yield config.Base.metadata.create_all(bind=get_db_session.get_bind())
    finally:
        config.Base.metadata.drop_all(bind=get_db_session.get_bind())


@pytest.fixture(scope="session")
def skill_factory() -> (
    Iterator[Callable[[str, models.LevelOfConfidence], models.SkillBase]]
):
    """Gets a skill factory fixture.

    Yields:
        The skill factory.

    This is a session scoped fixture that yields a skill factory.
    The skill factory is reset after the test finishes executing.
    """

    def _skill_factory(
        skill_name: str, level_of_confidence: models.LevelOfConfidence
    ) -> models.SkillBase:
        """Creates a Skill model object.

        Args:
            skill_name: The name of the skill.
            level_of_confidence: The level of confidence for the skill.

        Returns:
            The created Skill model object.

        This function takes in a skill name and level of confidence and returns a
        Skill model object with those values. It is used as a factory function to
        create Skill objects for testing.
        """
        skill = models.SkillBase(
            skill_name=skill_name, level_of_confidence=level_of_confidence
        )
        return skill

    yield _skill_factory


@pytest.fixture(scope="session")
def skill_1(
    skill_factory: Callable[[str, models.LevelOfConfidence], models.SkillBase],
) -> Iterator[models.SkillBase]:
    """Gets a skill_1 fixture.

    Args:
        skill_factory: The skill factory fixture.

    Yields:
        skill_1: The skill_1 object.

    This is a session scoped fixture that uses the skill factory to create
    a skill_1 object with name 'python' and confidence level 'LEVEL_2'. It yields
    the created skill_1 object.
    """
    yield skill_factory("python", models.LevelOfConfidence.LEVEL_2)


@pytest.fixture(scope="session")
def skill_2(
    skill_factory: Callable[[str, models.LevelOfConfidence], models.SkillBase],
) -> Iterator[models.SkillBase]:
    """Gets a skill_2 fixture.

    Args:
        skill_factory: The skill factory fixture.

    Yields:
        skill_2: The skill_2 object.

    This is a session scoped fixture that uses the skill factory to create
    a skill_2 object with name 'typescript' and confidence level 'LEVEL_1'. It yields
    the created skill_2 object.
    """
    yield skill_factory("typescript", models.LevelOfConfidence.LEVEL_1)


@pytest.fixture(scope="session")
def skills_json() -> Iterator[Sequence[dict[str, str]]]:
    """Gets a list of skills in dict/json form.

    Args:
        skill_1: The skill_1 fixture
        skill_2: The skill_2 fixture

    Yields:
        A sequence of skills.

    This is a session scope fixture that uses the skill_1 and skill_2 fixtures
    to create a sequence of skills dicts/json. It yields the created sequence.
    """
    # yield [
    #     {
    #         "skill_name": skill_1.skill_name,
    #         "level_of_confidence": skill_1.level_of_confidence.value,
    #     },
    #     {
    #         "skill_name": skill_2.skill_name,
    #         "level_of_confidence": skill_2.level_of_confidence.value,
    #     },
    # ]
    skills_names = [f"python_{x}" for x in range(16)]
    level_of_confidence: list[str] = []
    skill_json: list[dict[str, str]] = []
    for _ in range(16):
        level_of_confidence.append(models.LevelOfConfidence.LEVEL_1.value)
    for num in range(16):
        keys = ("skill_name", "level_of_confidence")
        value = (skills_names[num], level_of_confidence[num])
        skill_json.append(dict(zip(keys, value, strict=True)))
    yield skill_json


@pytest.fixture(scope="function")
def create_one_skill(
    get_db_session: sqlmodel.Session, skill_1: models.SkillBase
) -> Iterator[models.SkillBase]:
    """Creates one skill in the database.

    Args:
        get_db_session: The database session fixture.
        skill_1: The skill_1 fixture.

    Yields:
        _skill_1: The created skill.

    This fixture uses the skill_1 fixture and database session
    to create one skill in the database. It yields the created
    skill object.
    """
    _skill_1: models.SkillBase = skill_1
    crud.create_skill(session=get_db_session, skill=_skill_1)
    yield _skill_1


@pytest.fixture
def reportlog(pytestconfig: Any):
    logging_plugin = pytestconfig.pluginmanager.getplugin("logging-plugin")
    handler_id = logger.add(logging_plugin.report_handler, format="{message}")
    yield
    logger.remove(handler_id)


@pytest.fixture
def caplog(caplog: logging.LogCaptureFixture) -> Iterator[logging.LogCaptureFixture]:
    handler_id = logger.add(
        caplog.handler,
        format="{message}",
        level=0,
        filter=lambda record: record["level"].no >= caplog.handler.level,
        enqueue=False,  # Set to 'True' if your test is spawning child processes.
    )
    yield caplog
    logger.remove(handler_id)
