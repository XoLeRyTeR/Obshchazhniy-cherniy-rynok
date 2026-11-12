import ast
import inspect
from collections.abc import Callable
from pathlib import Path

import pytest

from src.services.catalog_service import CatalogService
from src.services.listing_service import ListingService
from src.services.user_service import UserService


def test_services_do_not_access_database_directly():
    """Запрещает сервисам импортировать SQLAlchemy/слой БД и обращаться к сессии или движку напрямую."""
    services = Path(__file__).resolve().parents[2] / "src" / "services"
    violations = []
    for path in services.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                modules = []
            direct_import = any(
                module == "sqlalchemy" or module.startswith("sqlalchemy.")
                or module == "src.db" or module.startswith("src.db.")
                for module in modules
            )
            direct_session = isinstance(node, ast.Attribute) and node.attr in {"session", "engine", "connection"}
            if direct_import or direct_session:
                violations.append(f"{path.name}:{node.lineno}")
    assert not violations, "Прямой доступ к БД в сервисах: " + ", ".join(violations)


def test_backend_has_no_unused_arguments() -> None:
    """Не даёт добавлять лишние параметры; обязательные неиспользуемые аргументы фреймворка помечаются подчёркиванием."""
    source = Path(__file__).resolve().parents[2] / "src"
    violations = []
    for path in source.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            arguments += [arg for arg in (node.args.vararg, node.args.kwarg) if arg]
            used = {
                value.id for statement in node.body for value in ast.walk(statement)
                if isinstance(value, ast.Name) and isinstance(value.ctx, ast.Load)
            }
            for argument in arguments:
                name = argument.arg
                if name not in {"self", "cls"} and not name.startswith("_") and name not in used:
                    violations.append(f"{path.relative_to(source)}:{node.lineno} {name}")
    assert not violations, "Неиспользуемые параметры: " + "; ".join(violations)


@pytest.mark.parametrize("method,parameters", [
    (ListingService.feed, ["self", "params"]),
    (CatalogService.__init__, ["self", "db"]),
    (UserService.__init__, ["self", "db"]),
])
def test_services_accept_only_required_parameters(method: Callable[..., object], parameters: list[str]) -> None:
    """Фиксирует отсутствие лишнего user_id у общей ленты и неиспользуемых настроек у сервисов профиля/справочников."""
    assert list(inspect.signature(method).parameters) == parameters
