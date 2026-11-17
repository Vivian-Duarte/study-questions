"""Regras puras de navegação e pontuação do quiz, independentes do Streamlit."""

from collections.abc import Mapping, Sequence

from study_questions.models import Question, QuestionType

QUESTIONS_PER_PAGE = 5
OPEN_CORRECT_ANSWER = "__open_correct__"
OPEN_WRONG_ANSWER = "__open_wrong__"


def page_bounds(
    total: int,
    requested_page: int,
    *,
    per_page: int = QUESTIONS_PER_PAGE,
) -> tuple[int, int, int, int]:
    """Retorna (início, fim exclusivo, página válida, número de páginas).

    Args:
        total: Quantidade de perguntas, não negativa.
        requested_page: Página pedida, começando em zero.
        per_page: Quantidade positiva de perguntas por página.

    Returns:
        Limites ajustados sem ultrapassar o total de perguntas.

    Raises:
        ValueError: Se total for negativo ou per_page não for positivo.
    """
    if total < 0:
        raise ValueError("total não pode ser negativo.")
    if per_page <= 0:
        raise ValueError("per_page deve ser maior que zero.")

    pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(requested_page, pages - 1))
    start = page * per_page
    return start, min(start + per_page, total), page, pages


def answer_result(question: Question, answer: str | None) -> bool | None:
    """Classifica uma resposta como correta, incorreta ou não respondida.

    Args:
        question: Pergunta original validada.
        answer: Alternativa escolhida ou marcador de autoavaliação.

    Returns:
        True quando correta, False quando incorreta, None sem resposta.
    """
    if answer is None:
        return None
    if question.type == QuestionType.MULTIPLE_CHOICE:
        return answer == question.answer
    return answer == OPEN_CORRECT_ANSWER


def score_answers(questions: Sequence[Question], answers: Mapping[int, str]) -> tuple[int, int]:
    """Conta acertos e erros sem modificar as perguntas nem as respostas.

    Args:
        questions: Sequência de perguntas mostradas no quiz.
        answers: Respostas da sessão indexadas pela posição da pergunta.

    Returns:
        Par (acertos, erros), ignorando questões ainda não respondidas.
    """
    correct = 0
    wrong = 0
    for index, question in enumerate(questions):
        result = answer_result(question, answers.get(index))
        if result is True:
            correct += 1
        elif result is False:
            wrong += 1
    return correct, wrong
