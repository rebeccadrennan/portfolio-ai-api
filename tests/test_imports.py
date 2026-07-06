from importlib import import_module


def test_import_main_app() -> None:
    module = import_module("app.main")
    assert getattr(module, "app", None) is not None


def test_import_knowledge_service() -> None:
    module = import_module("app.services.knowledge_service")
    assert hasattr(module, "get_portfolio_context")


def test_import_gemini_service() -> None:
    module = import_module("app.services.gemini_service")
    assert hasattr(module, "GeminiService")
