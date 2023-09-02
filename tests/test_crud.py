import sqlite3
import random
import pytest
from sqlalchemy.orm import Session
from typing import Generator, Any

from app.database import config
from app.data import crud
from app.models.schemas import SkillBase as skill_schema
from app.models.models import Skill as skill_model
from app.models import schemas


@pytest.fixture(scope="module")
def get_db_session() -> Generator[Session, Any, None]:
    db: Session = config.TestLocalSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function", autouse=True)
def setup_db(get_db_session: Session) -> Generator[Any, Any, None]:
    try:
        yield config.Base.metadata.create_all(bind=get_db_session.get_bind())
    finally:
        config.Base.metadata.drop_all(bind=get_db_session.get_bind())


@pytest.fixture(scope="function")
def random_number() -> Generator[int, Any, None]:
    yield int(random.random() * 100)


@pytest.fixture(scope="session")
def skill_1() -> Generator[skill_schema, Any, None]:
    yield schemas.SkillBase(
        skill_name="python", level_of_confidence=schemas.LevelOfConfidence.LEVEL_2
    )


@pytest.fixture(scope="session")
def skill_2():
    yield skill_schema(
        skill_name="typescript",
        level_of_confidence=schemas.LevelOfConfidence.LEVEL_1,
    )


@pytest.fixture(scope="function")
def create_one_skill(
    get_db_session: Session, skill_1: skill_schema
) -> Generator[skill_schema, Any, None]:
    _skill_1: skill_schema = skill_1
    crud.create_skill(session=get_db_session, skill=_skill_1)
    yield _skill_1


@pytest.fixture(scope="function")
def create_two_skill(
    get_db_session: Session, create_one_skill: skill_schema, skill_2: skill_schema
) -> Generator[tuple[skill_schema, skill_schema], Any, None]:
    _skill_1: skill_schema = create_one_skill
    _skill_2: skill_schema = skill_2
    crud.create_skill(session=get_db_session, skill=_skill_2)
    yield _skill_1, _skill_2


@pytest.fixture(scope="function")
def get_skill_id(
    get_db_session: Session, create_one_skill: skill_schema
) -> Generator[int, Any, None]:
    skill: skill_model | None = crud.get_skill_by_name(
        session=get_db_session, skill_name=create_one_skill.skill_name
    )
    if skill is not None:
        yield skill.skill_id


class TestGetSkillById:
    @staticmethod
    def test_get_skill_by_id(get_db_session: Session, get_skill_id) -> None:
        skill_id = get_skill_id
        skill_by_id = crud.get_skill_by_id(session=get_db_session, skill_id=skill_id)
        assert skill_by_id is not None
        assert skill_by_id.skill_id == 1

    @staticmethod
    def test_get_skill_by_id_none(get_db_session: Session, random_number: int) -> None:
        skill = crud.get_skill_by_id(session=get_db_session, skill_id=random_number)
        assert skill is None


class TestGetSkillByName:
    @staticmethod
    def test_get_skill_by_name(
        get_db_session: Session, create_one_skill: skill_schema
    ) -> None:
        skill: skill_model | None = crud.get_skill_by_name(
            session=get_db_session, skill_name=create_one_skill.skill_name
        )
        assert skill is not None
        assert skill.skill_name == create_one_skill.skill_name
        assert skill.level_of_confidence == create_one_skill.level_of_confidence

    @staticmethod
    def test_get_skill_by_name_none(
        get_db_session: Session, skill_1: skill_schema
    ) -> None:
        skill: skill_model | None = crud.get_skill_by_name(
            session=get_db_session, skill_name=skill_1.skill_name
        )
        assert skill is None


class TestCreateSkill:
    @staticmethod
    def test_create_skill(get_db_session: Session, skill_1: skill_schema) -> None:
        crud.create_skill(session=get_db_session, skill=skill_1)
        skill: skill_model | None = crud.get_skill_by_name(
            session=get_db_session, skill_name=skill_1.skill_name
        )
        assert skill is not None
        assert skill.skill_name == skill_1.skill_name
        assert skill.level_of_confidence == skill_1.level_of_confidence

    @staticmethod
    def test_create_skill_already_exist(get_db_session: Session, skill_1: skill_schema):
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            crud.create_skill(session=get_db_session, skill=skill_1)
            crud.create_skill(session=get_db_session, skill=skill_1)
        assert "The skill already exist" in str(exc_info.value)


class TestGetSkills:
    @staticmethod
    def test_get_zero_skills(get_db_session: Session) -> None:
        skill = crud.get_skills(get_db_session)
        assert skill == []
        assert len(skill) == 0

    @staticmethod
    def test_get_one_skill(
        get_db_session: Session, create_one_skill: skill_schema
    ) -> None:
        skills = crud.get_skills(get_db_session)
        assert len(skills) == 1
        assert skills[0].skill_name == create_one_skill.skill_name
        assert skills[0].level_of_confidence == create_one_skill.level_of_confidence

    @staticmethod
    def test_get_multiple_skills(
        get_db_session: Session, create_two_skill: tuple[skill_schema, skill_schema]
    ) -> None:
        skills = crud.get_skills(get_db_session)
        skill_1, skill_2 = create_two_skill
        assert len(skills) == 2
        assert skills[0].skill_name == skill_1.skill_name
        assert skills[0].level_of_confidence == skill_1.level_of_confidence
        assert skills[1].skill_name == skill_2.skill_name
        assert skills[1].level_of_confidence == skill_2.level_of_confidence


class TestDeleteSkill:
    @staticmethod
    def test_delete_skill(
        get_db_session: Session, create_one_skill: skill_schema
    ) -> None:
        skill: skill_model | None = crud.get_skill_by_name(
            session=get_db_session, skill_name=create_one_skill.skill_name
        )
        assert skill is not None
        crud.delete_skill(session=get_db_session, skill=skill)
        skill = crud.get_skill_by_name(
            session=get_db_session, skill_name=create_one_skill.skill_name
        )
        assert skill is None

    @staticmethod
    def test_delete_skill_non_existent(
        get_db_session: Session, skill_1: skill_schema
    ) -> None:
        skill: skill_model | None = crud.get_skill_by_name(
            session=get_db_session, skill_name=skill_1.skill_name
        )
        crud.delete_skill(session=get_db_session, skill=skill)
        skill = crud.get_skill_by_name(
            session=get_db_session, skill_name=skill_1.skill_name
        )
        assert skill is None


class TestUpdateSKill:
    @staticmethod
    def test_update_skill_name(
        get_db_session: Session, get_skill_id: int, skill_2: skill_schema
    ) -> None:
        skill_id: int = get_skill_id
        crud.update_skill_name(
            session=get_db_session, skill_id=skill_id, new_name=skill_2.skill_name
        )
        skill_updated = crud.get_skill_by_id(session=get_db_session, skill_id=skill_id)
        assert skill_updated is not None
        assert skill_updated.skill_name == skill_2.skill_name
        assert skill_updated.skill_id == skill_id

    @staticmethod
    def test_update_skill_name_none(get_db_session: Session) -> None:
        pass
