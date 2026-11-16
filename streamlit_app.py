"""Interface web do Study Questions com Streamlit."""

from hashlib import sha256

import streamlit as st

from study_questions.config import ConfigError, load_settings
from study_questions.exporters import export_anki_tsv, export_json
from study_questions.generation import GenerationError
from study_questions.loaders import DocumentError, parse_document
from study_questions.models import QuestionSet, QuestionType
from study_questions.pipeline import generate_from_text

QUESTION_TYPES = {
    "Aberta": QuestionType.OPEN,
    "Múltipla escolha": QuestionType.MULTIPLE_CHOICE,
}

type_signature = tuple[str, str, int, tuple[QuestionType, ...]]


def _request_signature(
    content: bytes,
    filename: str,
    question_count: int,
    question_types: tuple[QuestionType, ...],
) -> type_signature:
    """Identifica a combinação de documento e opções selecionadas.

    Args:
        content: Conteúdo do arquivo enviado.
        filename: Nome do arquivo.
        question_count: Quantidade solicitada.
        question_types: Tipos de perguntas selecionados.

    Returns:
        Identificador utilizado para evitar resultados desatualizados.
    """
    return (
        filename,
        sha256(content).hexdigest(),
        question_count,
        question_types,
    )


def _render_questions(question_set: QuestionSet) -> None:
    """Apresenta as perguntas e disponibiliza os arquivos.

    Args:
        question_set: Conjunto de perguntas validado.
    """
    st.subheader("Perguntas geradas")

    st.success(f"{len(question_set.questions)} pergunta(s) gerada(s).")

    for index, question in enumerate(question_set.questions, start=1):
        with st.expander(
            f"{index}. {question.statement}",
        ):
            if question.type == QuestionType.MULTIPLE_CHOICE:
                st.markdown("**Alternativas:**")

                for number, option in enumerate(question.options, start=1):
                    st.write(f"{number}. {option}")

            st.markdown("**Resposta:**")
            st.write(question.answer)

            if question.explanation:
                st.markdown("**Explicação:**")
                st.write(question.explanation)

            st.markdown("**Trecho de referência:**")
            st.write(question.source_excerpt)

    st.subheader("Exportar perguntas")

    left, right = st.columns(2)

    with left:
        st.download_button(
            label="Baixar JSON",
            data=export_json(question_set),
            file_name="questoes.json",
            mime="application/json; charset=utf-8",
            on_click="ignore",
            width="stretch",
        )

    with right:
        st.download_button(
            label="Baixar para Anki",
            data=export_anki_tsv(question_set),
            file_name="questoes_anki.txt",
            mime="text/plain; charset=utf-8",
            on_click="ignore",
            width="stretch",
        )


def main() -> None:
    """Inicializa a interface e coordena as ações do usuário."""
    st.set_page_config(
        page_title="Study Questions",
        page_icon="📚",
        layout="wide",
    )

    st.title("Study Questions")
    st.write("Transforme seus materiais de estudo em perguntas com IA.")

    st.subheader("Material de estudo")

    uploaded_file = st.file_uploader(
        "Envie um documento",
        type=["pdf", "txt", "md"],
        max_upload_size=10,
        help="Formatos aceitos: PDF, TXT e Markdown. Limite de 10 MB.",
    )

    st.subheader("Configurações")

    question_count = st.number_input(
        "Quantidade de perguntas",
        min_value=1,
        max_value=100,
        value=5,
        step=1,
    )

    selected_labels = st.multiselect(
        "Tipos de perguntas",
        options=list(QUESTION_TYPES),
        default=list(QUESTION_TYPES),
    )

    selected_types = tuple(QUESTION_TYPES[label] for label in selected_labels)

    content = uploaded_file.getvalue() if uploaded_file is not None else None

    signature = (
        _request_signature(
            content,
            uploaded_file.name,
            int(question_count),
            selected_types,
        )
        if content is not None and uploaded_file is not None
        else None
    )

    st.caption(
        "Ao gerar perguntas, o conteúdo do documento será enviado "
        "à API Gemini. O uso pode estar sujeito a cotas e custos."
    )

    if st.button("Gerar perguntas", type="primary"):
        st.session_state.pop("generated_questions", None)
        st.session_state.pop("generated_signature", None)

        if uploaded_file is None or content is None:
            st.warning("Envie um documento antes de gerar perguntas.")

        elif not selected_types:
            st.warning("Selecione pelo menos um tipo de pergunta.")

        else:
            try:
                with st.spinner("Gerando perguntas..."):
                    text = parse_document(
                        content,
                        uploaded_file.name,
                    )
                    settings = load_settings()

                    result = generate_from_text(
                        text,
                        settings,
                        question_count=int(question_count),
                        question_types=selected_types,
                    )

            except (
                ConfigError,
                DocumentError,
                GenerationError,
                ValueError,
            ) as exc:
                st.error(f"Não foi possível gerar as perguntas: {exc}")

            else:
                st.session_state["generated_questions"] = result
                st.session_state["generated_signature"] = signature

    stored_result = st.session_state.get("generated_questions")
    stored_signature = st.session_state.get("generated_signature")

    if isinstance(stored_result, QuestionSet) and stored_signature == signature:
        _render_questions(stored_result)


if __name__ == "__main__":
    main()
