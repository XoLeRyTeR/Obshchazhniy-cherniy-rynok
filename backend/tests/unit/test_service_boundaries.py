import ast
from pathlib import Path


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
