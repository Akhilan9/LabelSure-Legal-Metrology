from alembic import context

from app.core.config import Settings
from app.db.session import Base, build_engine
from app.models import ImageProcessingResult, Inspection, InspectionImage, OCRBlock, OCRRun, User  # noqa: F401: register metadata

config = context.config
settings = Settings()
target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = build_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            if engine.dialect.name == "sqlite":
                connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
                connection.commit()
            context.configure(connection=connection, target_metadata=target_metadata,
                              render_as_batch=engine.dialect.name == "sqlite")
            with context.begin_transaction():
                context.run_migrations()
                if engine.dialect.name == "sqlite":
                    violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
                    if violations:
                        raise RuntimeError("Migration left invalid foreign key references")
            if engine.dialect.name == "sqlite":
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    finally:
        engine.dispose()
