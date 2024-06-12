import logging
from logging.config import fileConfig

from flask import current_app
from alembic import context

config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

def get_engine():
    return current_app.extensions['migrate'].db.get_engine()

def get_engine_url():
    return get_engine().url.render_as_string(hide_password=False).replace('%', '%%')

config.set_main_option('sqlalchemy.url', get_engine_url())
target_metadata = current_app.extensions['migrate'].db.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
