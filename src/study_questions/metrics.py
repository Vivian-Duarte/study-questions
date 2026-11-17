"""Contadores de execução sem armazenar conteúdo ou credenciais."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class GenerationMetrics:
    """Mede requisições, reaproveitamento e latência de uma geração.

    Os tempos incluem a solicitação ao provedor e a validação da resposta.
    Os contadores representam chamadas do pipeline ao provedor, não
    necessariamente chamadas de rede quando o provedor é simulado.
    """

    requests_attempted: int = 0
    requests_succeeded: int = 0
    requests_insufficient: int = 0
    requests_failed: int = 0
    questions_validated: int = 0
    questions_unique: int = 0
    duplicates_removed: int = 0
    request_durations_seconds: list[float] = field(default_factory=list)
    total_generation_seconds: float = 0.0
