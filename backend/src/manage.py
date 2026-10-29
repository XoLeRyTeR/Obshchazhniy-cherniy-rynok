"""Explicit maintenance commands, never executed during API startup."""
import argparse
import asyncio

from sqlalchemy.dialects.postgresql import insert

from src.core.config import Settings
from src.db.database import Database
from src.models import University
from src.repositories.db_repository import DbRepository
from src.services.photo_service import PhotoService


async def run(args):
    settings = Settings()
    db = Database(settings.database_url.get_secret_value())
    try:
        async with db.sessions() as session:
            if args.command == "seed-universities":
                for name in args.names:
                    name = " ".join(name.split())
                    if not 1 <= len(name) <= 200:
                        raise ValueError("Название вуза должно содержать от 1 до 200 символов")
                    await session.execute(insert(University).values(name=name).on_conflict_do_nothing())
                await session.commit()
                print("University catalog updated")
            else:
                settings.media_dir.mkdir(parents=True, exist_ok=True)
                removed = await PhotoService(DbRepository(session), settings).cleanup()
                print(f"Removed orphan images: {removed}")
    finally:
        await db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    seed = sub.add_parser("seed-universities")
    seed.add_argument("names", nargs="+")
    sub.add_parser("cleanup-media")
    asyncio.run(run(parser.parse_args()))
