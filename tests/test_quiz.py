"""Testes das regras puras de navegação e pontuação."""

import pytest

from study_questions.models import Question, QuestionType
from study_questions.quiz import (
    OPEN_CORRECT_ANSWER,
    OPEN_WRONG_ANSWER,
    answer_result,
    page_bounds,
    score_answers,
)


def _multiple_choice() -> Question:
    return Question(
        type=QuestionType.MULTIPLE_CHOICE,
        statement="Qual linguagem é mencionada no texto?",
        answer="Python",
        source_excerpt="Python é uma linguagem de programação.",
        options=["Java", "Python", "Ruby"],
    )


def _open_question() -> Question:
    return Question(
        type=QuestionType.OPEN,
        statement="O que é Python?",
        answer="Linguagem de programação",
        source_excerpt="Python é uma linguagem de programação.",
    )


@pytest.mark.parametrize(
    ("total", "requested_page", "per_page", "expected"),
    [
        (0, 0, 5, (0, 0, 0, 1)),
        (0, 7, 5, (0, 0, 0, 1)),
        (5, 0, 5, (0, 5, 0, 1)),
        (7, 0, 5, (0, 5, 0, 2)),
        (7, 1, 5, (5, 7, 1, 2)),
        (7, 100, 5, (5, 7, 1, 2)),
        (7, -3, 5, (0, 5, 0, 2)),
        (7, 1, 3, (3, 6, 1, 3)),
    ],
)
def test_page_bounds(
    total: int,
    requested_page: int,
    per_page: int,
    expected: tuple[int, int, int, int],
) -> None:
    assert page_bounds(total, requested_page, per_page=per_page) == expected


@pytest.mark.parametrize(
    ("total", "per_page"),
    [(-1, 5), (5, 0), (5, -2)],
)
def test_page_bounds_reject_invalid_limits(total: int, per_page: int) -> None:
    with pytest.raises(ValueError):
        page_bounds(total, 0, per_page=per_page)


def test_multiple_choice_grading() -> None:
    question = _multiple_choice()
    assert answer_result(question, None) is None
    assert answer_result(question, "Python") is True
    assert answer_result(question, "Java") is False


def test_open_question_grading() -> None:
    question = _open_question()
    assert answer_result(question, None) is None
    assert answer_result(question, OPEN_CORRECT_ANSWER) is True
    assert answer_result(question, OPEN_WRONG_ANSWER) is False


def test_score_ignores_unanswered_and_unknown_indices() -> None:
    questions = [_multiple_choice(), _open_question(), _multiple_choice()]
    answers = {0: "Python", 2: "Java", 99: "Python"}
    snapshot = dict(answers)
    assert score_answers(questions, answers) == (1, 1)
    assert answers == snapshot


def test_score_combines_open_and_multiple_choice() -> None:
    questions = [_open_question(), _multiple_choice(), _open_question()]
    assert score_answers(
        questions,
        {0: OPEN_CORRECT_ANSWER, 1: "Ruby", 2: OPEN_WRONG_ANSWER},
    ) == (1, 2)


def test_score_empty_questions() -> None:
    assert score_answers([], {}) == (0, 0)
