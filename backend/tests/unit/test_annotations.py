import ast
import importlib
import inspect
from pathlib import Path
from typing import get_type_hints
from uuid import UUID

from src.schemas.users import DormChoice
from src.services.catalog_service import CatalogService

SOURCE = Path(__file__).resolve().parents[2] / "src"


def test_all_backend_functions_have_annotations() -> None:
    """Проверяет типы параметров и результатов всех функций src, кроме неявных self/cls."""
    missing = []
    for path in SOURCE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            args += [arg for arg in (node.args.vararg, node.args.kwarg) if arg]
            names = [arg.arg for arg in args if arg.arg not in {"self", "cls"} and arg.annotation is None]
            if node.returns is None:
                names.append("return")
            if names:
                missing.append(f"{path.relative_to(SOURCE)}:{node.lineno}: {', '.join(names)}")
    assert not missing, "Отсутствуют аннотации: " + "; ".join(missing)


def test_annotations_resolve_without_missing_imports() -> None:
    """Проверяет, что типы функций и методов разрешаются без NameError и циклических импортов."""
    for path in SOURCE.rglob("*.py"):
        # env.py Alembic запускает миграции при импорте; он не является обычным модулем API.
        if "migrations" in path.parts or path.name == "__init__.py":
            continue
        name = ".".join(path.relative_to(SOURCE.parent).with_suffix("").parts)
        module = importlib.import_module(name)
        for value in vars(module).values():
            if inspect.isfunction(value) and value.__module__ == name:
                get_type_hints(value)
            elif inspect.isclass(value) and value.__module__ == name:
                for method in vars(value).values():
                    if isinstance(method, (staticmethod, classmethod)):
                        method = method.__func__
                    if inspect.isfunction(method):
                        get_type_hints(method)


def test_dorm_choice_returns_uuid_not_integer() -> None:
    """Фиксирует контракт выбора общежития: на входе DormChoice, на выходе UUID из модели БД."""
    hints = get_type_hints(CatalogService.resolve)
    assert hints["data"] is DormChoice
    assert hints["return"] is UUID
