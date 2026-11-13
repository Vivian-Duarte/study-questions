"""Testes básicos de inicialização do pacote."""

import study_questions


def test_package_exposes_version() -> None:
    """Verifica se a versão do pacote está disponível."""
    assert study_questions.__version__ == "0.1.0"
