"""Interface Study Questions: dashboard escuro e quiz interativo."""

from hashlib import sha256
from pathlib import Path

import streamlit as st

from study_questions.config import ConfigError, load_settings
from study_questions.exporters import export_anki_tsv, export_json
from study_questions.generation import GenerationError
from study_questions.loaders import DocumentError, parse_document
from study_questions.models import Question, QuestionSet, QuestionType
from study_questions.pipeline import generate_from_text

QUESTION_TYPES = {
    "Aberta": QuestionType.OPEN,
    "Múltipla escolha": QuestionType.MULTIPLE_CHOICE,
}

APP_DIR = Path(__file__).resolve().parent
RequestSignature = tuple[str, str, int, tuple[QuestionType, ...]]


def _request_signature(
    content: bytes,
    filename: str,
    question_count: int,
    question_types: tuple[QuestionType, ...],
) -> RequestSignature:
    """Identifica o documento e as configurações da geração."""
    return (
        filename,
        sha256(content).hexdigest(),
        question_count,
        question_types,
    )


def _apply_styles() -> None:
    """Carrega somente o CSS local do projeto (sem conteúdo dos PDFs)."""
    css = (APP_DIR / "assets" / "study_questions.css").read_text(encoding="utf-8")
    st.markdown(f"<style>\n{css}\n</style>", unsafe_allow_html=True)


def _answers() -> dict[int, str]:
    """Obtém as respostas da sessão atual."""
    answers: dict[int, str] = st.session_state.setdefault("quiz_answers", {})
    return answers


def _revealed() -> set[int]:
    """Obtém as perguntas abertas já reveladas."""
    revealed: set[int] = st.session_state.setdefault("quiz_revealed", set())
    return revealed


def _select_answer(index: int, option: str) -> None:
    """Registra a alternativa escolhida sem refazer a chamada ao Gemini."""
    if index not in _answers():
        _answers()[index] = option


def _reveal_answer(index: int) -> None:
    """Mostra a resposta esperada de uma questão aberta."""
    _revealed().add(index)


def _grade_open_answer(index: int, correct: bool) -> None:
    """Registra a autoavaliação de uma questão aberta."""
    _answers()[index] = "__open_correct__" if correct else "__open_wrong__"


def _is_correct(index: int, question: Question) -> bool | None:
    """Retorna acerto/erro, ou None se a questão está sem resposta."""
    given = _answers().get(index)
    if given is None:
        return None
    if question.type == QuestionType.MULTIPLE_CHOICE:
        return given == question.answer
    return given == "__open_correct__"


def _choice_styles(question_set: QuestionSet) -> None:
    """Aplica destaque verde/vermelho apenas às alternativas respondidas."""
    styles: list[str] = []
    for i, question in enumerate(question_set.questions):
        if question.type != QuestionType.MULTIPLE_CHOICE:
            continue
        selected = _answers().get(i)
        for j, option in enumerate(question.options):
            selector = f".st-key-choice_{i}_{j} button"
            letter = chr(65 + j)
            styles.append(f'{selector}::before {{ content: "{letter}"; }}')
            if selected is None:
                continue
            if option == question.answer:
                styles.append(
                    f"{selector} {{ background: #123a2a !important; "
                    "border-color: #25c77a !important; color: #e4fff0 !important; }}"
                )
                styles.append(f'{selector}::after {{ content: "✓"; color: #4ade80; }}')
                styles.append(
                    f"{selector}::before {{ background: #34d399 !important; "
                    "color: #09281a !important; }}"
                )
            elif option == selected:
                styles.append(
                    f"{selector} {{ background: #421c25 !important; "
                    "border-color: #fb5268 !important; color: #fff0f2 !important; }}"
                )
                styles.append(f'{selector}::after {{ content: "✕"; color: #fb7185; }}')
                styles.append(
                    f"{selector}::before {{ background: #fb7185 !important; "
                    "color: #401018 !important; }}"
                )
    if styles:
        st.markdown("<style>" + "\n".join(styles) + "</style>", unsafe_allow_html=True)


def _question_card(index: int, total: int, question: Question) -> None:
    """Exibe uma pergunta como cartão com opções clicáveis."""
    answered_correctly = _is_correct(index, question)
    with st.container(border=True, key=f"question_card_{index}"):
        title_col, badge_col = st.columns([4, 1], vertical_alignment="center")
        with title_col:
            st.markdown(
                f'<p class="question-eyebrow">PERGUNTA {index + 1} DE {total}</p>',
                unsafe_allow_html=True,
            )
        with badge_col:
            if answered_correctly is True:
                st.markdown(
                    '<p class="question-badge badge-correct">Correta</p>',
                    unsafe_allow_html=True,
                )
            elif answered_correctly is False:
                st.markdown(
                    '<p class="question-badge badge-wrong">Incorreta</p>',
                    unsafe_allow_html=True,
                )
        st.markdown(f"**{question.statement}**")

        if question.type == QuestionType.MULTIPLE_CHOICE:
            for j, option in enumerate(question.options):
                st.button(
                    option,
                    key=f"choice_{index}_{j}",
                    width="stretch",
                    disabled=index in _answers(),
                    on_click=_select_answer,
                    args=(index, option),
                )
        else:
            if index not in _revealed():
                st.button(
                    "Revelar resposta",
                    key=f"reveal_{index}",
                    on_click=_reveal_answer,
                    args=(index,),
                )
            else:
                st.markdown("**Resposta esperada**")
                st.write(question.answer)
                if answered_correctly is None:
                    yes, no = st.columns(2)
                    with yes:
                        st.button(
                            "Acertei",
                            key=f"self_correct_{index}",
                            width="stretch",
                            on_click=_grade_open_answer,
                            args=(index, True),
                        )
                    with no:
                        st.button(
                            "Errei",
                            key=f"self_wrong_{index}",
                            width="stretch",
                            on_click=_grade_open_answer,
                            args=(index, False),
                        )

        if answered_correctly is not None:
            if question.type == QuestionType.MULTIPLE_CHOICE:
                st.markdown("**Resposta correta**")
                st.write(question.answer)
            if question.explanation:
                st.markdown("**Explicação**")
                st.write(question.explanation)
            with st.expander("Ver trecho de referência"):
                st.write(question.source_excerpt)


def _render_questions(question_set: QuestionSet, requested_count: int) -> None:
    """Renderiza o quiz e os downloads mantendo o estado das respostas."""
    questions = question_set.questions
    correct = sum(_is_correct(i, q) is True for i, q in enumerate(questions))
    wrong = sum(_is_correct(i, q) is False for i, q in enumerate(questions))

    title_col, score_col = st.columns([4, 2], vertical_alignment="center")
    with title_col:
        st.subheader("Perguntas geradas")
    with score_col:
        st.markdown(
            '<div class="score-row">'
            f'<span class="score-chip score-correct">{correct} acerto(s)</span>'
            f'<span class="score-chip score-wrong">{wrong} erro(s)</span>'
            "</div>",
            unsafe_allow_html=True,
        )

    st.success(f"{len(questions)} pergunta(s) gerada(s).")
    if len(questions) < requested_count:
        st.caption(
            f"Você solicitou {requested_count}, mas foram geradas "
            f"{len(questions)} perguntas válidas."
        )

    _choice_styles(question_set)
    for i, question in enumerate(questions):
        _question_card(i, len(questions), question)

    st.subheader("Exportar perguntas")
    left, right = st.columns(2)
    with left:
        st.download_button(
            "Baixar JSON",
            export_json(question_set),
            file_name="questoes.json",
            mime="application/json; charset=utf-8",
            on_click="ignore",
            key="download_json",
            width="stretch",
        )
    with right:
        st.download_button(
            "Baixar para Anki",
            export_anki_tsv(question_set),
            file_name="questoes_anki.txt",
            mime="text/plain; charset=utf-8",
            on_click="ignore",
            key="download_anki",
            width="stretch",
        )


def main() -> None:
    """Exibe o painel e aciona a geração quando solicitado."""
    st.set_page_config(
        page_title="Perguntas de estudo | Study Questions",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _apply_styles()

    st.title("Perguntas de estudo")
    st.caption("Transforme seus materiais de estudo em perguntas com IA.")

    left, right = st.columns([3.2, 7], gap="large", vertical_alignment="top")
    with left:
        with st.container(border=True, key="material_card"):
            st.subheader("Material de estudo")
            uploaded_file = st.file_uploader(
                "Envie um documento",
                type=["pdf", "txt", "md"],
                max_upload_size=10,
                help="Formatos aceitos: PDF, TXT e Markdown. Limite de 10 MB.",
                key="study_file",
            )

        with st.container(border=True, key="settings_card"):
            st.subheader("Configurações")
            question_count = st.number_input(
                "Quantidade de perguntas",
                min_value=1,
                max_value=100,
                value=5,
                step=1,
                key="question_count",
            )
            selected_labels = st.multiselect(
                "Tipos de perguntas",
                options=list(QUESTION_TYPES),
                default=list(QUESTION_TYPES),
                key="question_types",
            )
            selected_types = tuple(QUESTION_TYPES[label] for label in selected_labels)
            st.caption(
                "Ao gerar perguntas, o conteúdo do documento será enviado "
                "à API Gemini. O uso pode estar sujeito a cotas e custos."
            )
            generate = st.button(
                "Gerar perguntas",
                type="primary",
                icon=":material/auto_awesome:",
                key="generate_button",
                width="stretch",
            )
            feedback_slot = st.empty()

    content = uploaded_file.getvalue() if uploaded_file is not None else None
    signature = (
        _request_signature(
            content,
            uploaded_file.name,
            int(question_count),
            selected_types,
        )
        if uploaded_file is not None and content is not None
        else None
    )

    if generate:
        st.session_state.pop("generated_questions", None)
        st.session_state.pop("generated_signature", None)
        st.session_state["quiz_answers"] = {}
        st.session_state["quiz_revealed"] = set()

        if uploaded_file is None or content is None:
            feedback_slot.warning("Envie um documento antes de gerar perguntas.")
        elif not selected_types:
            feedback_slot.warning("Selecione pelo menos um tipo de pergunta.")
        else:
            try:
                with st.spinner("Gerando perguntas com Gemini..."):
                    text = parse_document(content, uploaded_file.name)
                    settings = load_settings()
                    result = generate_from_text(
                        text,
                        settings,
                        question_count=int(question_count),
                        question_types=selected_types,
                    )
            except (ConfigError, DocumentError, GenerationError, ValueError) as exc:
                feedback_slot.error(f"Não foi possível gerar as perguntas: {exc}")
            else:
                st.session_state["generated_questions"] = result
                st.session_state["generated_signature"] = signature
                st.session_state["requested_count"] = int(question_count)

    with right:
        result = st.session_state.get("generated_questions")
        stored_signature = st.session_state.get("generated_signature")
        if isinstance(result, QuestionSet) and stored_signature == signature:
            _render_questions(result, st.session_state["requested_count"])
        else:
            with st.container(border=True, key="empty_card"):
                st.subheader("Perguntas geradas")
                st.write("Suas perguntas aparecerão aqui depois da geração.")
                st.caption(
                    "Responda às alternativas, acompanhe os acertos e erros "
                    "e baixe suas perguntas em JSON ou Anki."
                )


if __name__ == "__main__":
    main()
