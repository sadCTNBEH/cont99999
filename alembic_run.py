from alembic import command
from alembic.config import Config


def run_migration():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
