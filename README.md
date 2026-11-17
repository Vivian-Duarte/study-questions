# Study Questions

**Transforme materiais de estudo em perguntas com inteligência artificial.**

O **Study Questions** é uma aplicação desenvolvida em Python que utiliza a API do **Google Gemini** para gerar questões a partir de documentos TXT, Markdown e PDF. Com uma interface interativa em **Streamlit**, o usuário pode estudar, acompanhar seus acertos e erros e exportar as perguntas para **JSON** ou **Anki**.

O projeto prioriza a rastreabilidade das questões ao conteúdo original, validação estruturada das respostas e uma arquitetura modular, com testes automatizados e métricas de desempenho.

## Funcionalidades

- **Importação de materiais:** arquivos `.txt`, `.md` e `.pdf` com texto extraível.
- **Processamento de documentos:** extração de texto e divisão de materiais longos em blocos com sobreposição controlada.
- **Geração com IA:** perguntas abertas e de múltipla escolha utilizando o Google Gemini.
- **Validação de qualidade:** validação individual com Pydantic, verificação dos trechos de referência e remoção de duplicatas.
- **Quiz interativo:** respostas, acompanhamento de acertos e erros e paginação de até cinco questões por página.
- **Exportação:** arquivos JSON e TSV compatível com importação no Anki.
- **Métricas e benchmarks:** acompanhamento interno das solicitações à IA e medições locais de desempenho, sem consumir a API.

> **Importante:** a quantidade de perguntas solicitada representa um limite máximo. O Gemini pode gerar menos questões, e respostas inválidas ou duplicadas podem ser descartadas. O projeto não realiza chamadas adicionais para completar automaticamente esse número.

## Stack tecnológica

| Categoria | Tecnologia | Utilização |
| --- | --- | --- |
| Linguagem | **Python 3.11+** | Lógica da aplicação e processamento dos materiais |
| Interface | **Streamlit** | Upload de documentos, configuração da geração e quiz |
| IA generativa | **Google Gemini API** + **Google Gen AI SDK** | Geração de perguntas a partir do conteúdo dos documentos |
| Modelagem e validação | **Pydantic v2** | Contratos de dados e validação das perguntas |
| Leitura de PDFs | **pypdf** | Extração de texto de documentos PDF |
| Testes e cobertura | **pytest** + **pytest-cov** | Testes automatizados e cobertura do código |
| Qualidade de código | **Ruff** + **mypy** | Lint, formatação e análise estática de tipos |
| Integração contínua | **GitHub Actions** | Execução das verificações automatizadas em Python 3.11 e 3.12 |
| Versionamento | **Git** + **GitHub** | Histórico de alterações e colaboração |

## Pré-requisitos

- **Git** instalado.
- **Python 3.11 ou superior** (recomendado: Python 3.12).
- Uma **chave de API do Gemini**, obtida no [Google AI Studio](https://aistudio.google.com/app/apikey).
- Conexão com a internet para gerar questões utilizando a API.

## Instalação e execução

### 1. Clonar o repositório

```bash
git clone https://github.com/Vivian-Duarte/study-questions.git
cd study-questions
```

### 2. Criar o ambiente virtual e instalar as dependências

**Windows — PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

**Linux / macOS**

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
```

> Os exemplos utilizam diretamente o interpretador do ambiente virtual, sem exigir sua ativação. Se você utiliza Python 3.11 no Windows, substitua `py -3.12` por `py -3.11`.

### 3. Configurar a chave do Gemini

Crie seu arquivo `.env` a partir do exemplo fornecido pelo projeto:

**Windows — PowerShell**

```powershell
Copy-Item .env.example .env
```

**Linux / macOS**

```bash
cp .env.example .env
```

Abra o arquivo `.env` e configure:

```dotenv
GEMINI_API_KEY=sua_chave_aqui
```

O modelo Gemini e o tamanho dos blocos de texto podem ser personalizados com `GEMINI_MODEL` e `MAX_CHUNK_WORDS`, conforme as configurações do projeto.

> **Segurança:** não publique o arquivo `.env` nem sua chave de API. O texto utilizado na geração é enviado ao serviço Gemini; evite utilizar materiais confidenciais sem autorização.

### 4. Iniciar a aplicação

**Windows — PowerShell**

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

**Linux / macOS**

```bash
./.venv/bin/python -m streamlit run streamlit_app.py
```

Abra o endereço informado pelo Streamlit no terminal, geralmente **http://localhost:8501**.

## Como utilizar

1. Envie um arquivo TXT, Markdown ou PDF com conteúdo textual.
2. Defina a quantidade máxima e os tipos de perguntas desejados.
3. Clique em **Gerar perguntas**.
4. Responda às questões de múltipla escolha ou revele as respostas das questões abertas.
5. Acompanhe seus acertos e erros e navegue pelas páginas do quiz.
6. Exporte as perguntas para **JSON** ou **Anki (TSV)**, se desejar.

## Estrutura do projeto

```text
study-questions/
├── streamlit_app.py               # Interface e navegação do quiz
├── assets/
│   └── study_questions.css        # Estilos da interface
├── .streamlit/
│   └── config.toml                 # Configuração visual do Streamlit
├── src/
│   └── study_questions/
│       ├── config.py              # Configurações da aplicação
│       ├── models.py              # Modelos e validações com Pydantic
│       ├── loaders.py             # Leitura e limites de documentos
│       ├── chunking.py            # Divisão do texto em blocos
│       ├── prompts.py             # Instruções enviadas ao Gemini
│       ├── generation.py          # Integração com Gemini e validações
│       ├── pipeline.py            # Orquestração da geração e deduplicação
│       ├── metrics.py             # Métricas de geração
│       ├── quiz.py                # Pontuação e paginação independentes da UI
│       └── exporters.py           # Exportação JSON e Anki
├── scripts/
│   └── benchmark_core.py          # Benchmarks offline
├── tests/                         # Testes automatizados
├── pyproject.toml                 # Dependências e ferramentas
└── README.md
```

## Testes e qualidade de código

O projeto utiliza **pytest**, **Ruff** e **mypy**. A cobertura mínima configurada é de **80%** dos módulos instrumentados.

**Windows — PowerShell**

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest -v
```

**Linux / macOS**

```bash
./.venv/bin/python -m ruff check .
./.venv/bin/python -m ruff format --check .
./.venv/bin/python -m mypy
./.venv/bin/python -m pytest -v
```

O **GitHub Actions** executa verificações automatizadas nas versões Python 3.11 e 3.12.

## Benchmarks de desempenho

O projeto inclui benchmarks para **divisão de texto, exportação JSON/Anki, pontuação e extração de PDFs sintéticos**. Eles não dependem do Gemini e **não consomem cota da API**.

**Windows — PowerShell**

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_core.py --words 10000 --questions 100 --pdf-pages 3 --repeat 5
```

Para salvar os resultados em JSON:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_core.py --words 50000 --repeat 5 --json > benchmark-local.json
```

O benchmark apresenta a **mediana dos tempos de execução** e o **pico de alocações Python monitoradas pelo `tracemalloc`**. Esses valores não equivalem ao consumo total de RAM nem ao tempo de resposta do Gemini. Compare resultados somente em condições semelhantes.

## Limitações e considerações de segurança

- **PDFs digitalizados:** arquivos sem camada textual não são processados por OCR.
- **Limites de processamento:** documentos grandes podem ser rejeitados de acordo com os limites de arquivo, páginas e caracteres.
- **Conteúdo de terceiros:** limites de leitura não substituem isolamento de processos para PDFs não confiáveis.
- **Qualidade das respostas:** toda questão gerada por IA pode conter erros e deve ser revisada; a presença de uma citação no documento não garante a correção da resposta.
- **Quantidade de questões:** a quantidade gerada pode ser inferior ao número solicitado.
- **Uso da API:** limites, cotas e eventuais custos dependem da configuração do projeto no Google AI Studio.

## Licença

A licença do projeto ainda não foi definida. Consulte os responsáveis pelo repositório antes de reutilizar ou redistribuir o código.
