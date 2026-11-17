# Study Questions

Aplicação em Python que transforma materiais didáticos TXT, Markdown e PDF em perguntas de estudo com o Gemini. Inclui um quiz interativo em Streamlit, validação das perguntas com Pydantic e exportação para JSON e Anki.

## Funcionalidades

- Upload de materiais `.txt`, `.md` e `.pdf` com texto extraível.
- Divisão de textos longos em blocos, com sobreposição controlada.
- Geração de perguntas abertas e de múltipla escolha com a API Gemini.
- Validação estrutural de cada pergunta e conferência de citações no texto extraído.
- Remoção de questões duplicadas.
- Quiz com respostas, pontuação e paginação de cinco perguntas por página.
- Exportação das questões para JSON e TSV compatível com Anki.
- Métricas opcionais de tempo e número de chamadas, usadas internamente.

**Limitação importante:** o número solicitado é um máximo, não uma garantia. O modelo pode retornar menos perguntas, ou perguntas podem ser descartadas por não cumprirem as validações. A aplicação não efetua chamadas extras para completar a quantidade.

## Tecnologias

Python 3.11+, Streamlit, Google Gen AI SDK, Pydantic v2, pypdf, pytest, pytest-cov, Ruff, mypy e GitHub Actions.

## Instalação e execução (Windows / PowerShell)

```powershell
# Clone e acesse o repositório.
git clone https://github.com/Vivian-Duarte/study-questions.git
cd study-questions

# Crie o ambiente virtual e instale as dependências.
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Prepare a configuração local.
Copy-Item .env.example .env
```

No arquivo `.env`, configure **`GEMINI_API_KEY`** com uma chave válida. As variáveis `GEMINI_MODEL` e `MAX_CHUNK_WORDS` são opcionais conforme a configuração em `config.py`.

**Nunca publique `.env`, chaves de API ou materiais confidenciais em commits, issues ou ZIPs.** O conteúdo dos arquivos enviados à geração é transmitido à API Gemini. Verifique as regras de privacidade, o nível de faturamento e as cotas do projeto usado pela chave.

Para iniciar a interface:

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Abra o endereço local mostrado no terminal (normalmente `http://localhost:8501`).

## Utilização

1. Selecione um documento.
2. Escolha a quantidade máxima e os tipos de perguntas.
3. Clique em **Gerar perguntas**.
4. Responda às alternativas ou revele as respostas das questões abertas.
5. Exporte o resultado em JSON ou formato Anki.

## Qualidade e testes

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest -v
```

O projeto exige pelo menos 80% de cobertura dos módulos Python instrumentados. A integração contínua valida Python 3.11 e 3.12.

## Benchmarks reproduzíveis (sem Gemini)

Use o script abaixo para medir **chunking, exportação JSON/Anki, pontuação do quiz e extração de PDFs sintéticos**, sem chamar a API e sem consumir a cota Gemini.

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_core.py --words 10000 --questions 100 --pdf-pages 3 --repeat 5
```

Para gerar saída JSON e comparar duas revisões no mesmo computador:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_core.py --words 50000 --repeat 5 --json > benchmark-local.json
```

O benchmark exibe a **mediana do tempo de execução** e o **pico de alocações Python rastreado pelo `tracemalloc`**. Este pico não representa toda a memória RAM usada pelo processo. Resultados dependem do computador, do Python, do sistema operacional e da carga em segundo plano; não representam o tempo de resposta do Gemini nem devem ser usados como limite fixo para CI. Não é necessário versionar `benchmark-local.json`.

O código de navegação e pontuação do quiz está em `src/study_questions/quiz.py`, separado do Streamlit para facilitar testes e medições.

## Estrutura principal

```text
study-questions/
├── streamlit_app.py               # Aplicação Streamlit
├── assets/study_questions.css     # Estilos da interface
├── .streamlit/config.toml         # Tema
├── src/study_questions/
│   ├── models.py                  # Contratos Pydantic
│   ├── config.py                  # Configurações da API
│   ├── loaders.py                 # Leitura e limites dos documentos
│   ├── chunking.py                # Divisão do material em blocos
│   ├── prompts.py                 # Instruções de geração
│   ├── generation.py              # Provedor Gemini e validações
│   ├── pipeline.py                # Orquestração e deduplicação
│   ├── metrics.py                 # Métricas opcionais
│   ├── quiz.py                    # Paginação e pontuação (sem UI)
│   └── exporters.py               # JSON e Anki
├── scripts/benchmark_core.py      # Benchmarks offline
├── tests/                         # Testes unitários e integração
├── pyproject.toml
└── README.md
```

## Limitações e segurança

- PDFs digitalizados sem camada de texto não são processados por OCR.
- Documentos excessivamente grandes podem ser rejeitados pelos limites de leitura.
- Limites de arquivo, páginas e caracteres não substituem isolamento de processos ao lidar com PDFs não confiáveis.
- Questões produzidas por IA devem passar por revisão humana. Uma citação encontrada no PDF não garante, sozinha, que a resposta seja verdadeira.
- O volume de perguntas gerado pode ser menor do que o solicitado.
- O uso da API pode estar sujeito a cotas e custos, dependendo do plano e do projeto configurado no Google AI Studio.

## Licença

Licença ainda não definida.
