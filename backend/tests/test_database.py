from sqlalchemy import create_engine, inspect

from backend.app.db.session import init_database
from backend.app.models import Item, ItemType


def test_database_initialization_creates_items_table() -> None:
    database_engine = create_engine("sqlite://")

    init_database(database_engine)

    assert "items" in inspect(database_engine).get_table_names()


def test_item_defaults_and_explicit_type_are_persisted() -> None:
    database_engine = create_engine("sqlite://")
    init_database(database_engine)

    with database_engine.begin() as connection:
        connection.execute(
            Item.__table__.insert().values(title="Finish DBMS Lab 4", type=ItemType.TODO)
        )
        item = connection.execute(Item.__table__.select()).one()

    assert item.title == "Finish DBMS Lab 4"
    assert item.type == ItemType.TODO
    assert item.content == ""
    assert item.completed is False
    assert item.created_at is not None
    assert item.updated_at is not None