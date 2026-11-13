
# Study Questions

Gerador de perguntas de estudo a partir de materiais didáticos
utilizando modelos de linguagem (LLMs).

## Sobre o projeto

O Study Questions é uma aplicação Python desenvolvida para
auxiliar estudantes na criação de perguntas de revisão.

O objetivo é permitir que materiais de estudo sejam
processados por inteligência artificial para gerar perguntas
abertas e de múltipla escolha.

O projeto está sendo desenvolvido de forma incremental,
com foco em qualidade, testes automatizados, tipagem
estática e organização do código.

## Estado atual

**Sprint 1 — Fundação técnica**

Funcionalidades implementadas:

- Estrutura modular Python com layout src/.
- Modelos de domínio validados com Pydantic v2.
- Suporte estrutural a perguntas abertas e de múltipla escolha.
- Validação de respostas e alternativas.
- Validação de conjuntos de perguntas.
- Testes automatizados com Pytest.
- Análise de código com Ruff e mypy.
- Configuração de integração contínua com GitHub Actions.

A geração real de perguntas por IA ainda não foi implementada.

## Tecnologias

| Tecnologia | Finalidade |
|------------|------------|
| Python 3.11+ | Linguagem principal |
| Pydantic v2 | Validação dos modelos |
| Pytest | Testes automatizados |
| pytest-cov | Cobertura de testes |
| Ruff | Lint e formatação |
| mypy | Análise estática de tipos |
| GitHub Actions | Integração contínua |
| Hatchling | Empacotamento Python |

Tecnologias previstas para etapas futuras:

- Gemini API
- Streamlit
- pypdf

## Estrutura do projeto

    study-questions/
    ├── .github/
    │   └── workflows/
    │       └── ci.yml
    ├── src/
    │   └── study_questions/
    │       ├── __init__.py
    │       └── models.py
    ├── tests/
    │   ├── test_package.py
    │   ├── test_models.py
    │   └── test_models_contract.py
    ├── pyproject.toml
    ├── .env.example
    ├── .gitignore
    └── README.md

## Instalação

### Requisitos

- Python 3.11 ou superior
- Git
- VS Code (recomendado)

### Clonar o repositório

```powershell
git clone https://github.com/Vivian-Duarte/study-questions.git

cd study-questions
```

### Criar o ambiente virtual

No Windows:

```powershell
python -m venv .venv
```

### Instalar as dependências

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Executar os testes

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

A configuração atual exige cobertura global mínima de 80%.

## Verificar qualidade do código

### Lint

```powershell
.\.venv\Scripts\python.exe -m ruff check .
```

### Formatação

```powershell
.\.venv\Scripts\python.exe -m ruff format --check .
```

### Tipagem

```powershell
.\.venv\Scripts\python.exe -m mypy
```

## Modelos de domínio

A aplicação possui três componentes principais:

### QuestionType

Define os tipos de perguntas:

- multiple_choice
- open

### Question

Representa uma pergunta contendo:

- Tipo
- Enunciado
- Resposta correta
- Explicação
- Trecho-fonte
- Alternativas, quando aplicável

### QuestionSet

Agrupa uma ou mais perguntas validadas.

## Regras de validação

- Perguntas de múltipla escolha exigem 3 a 5 alternativas.
- A resposta correta deve corresponder a uma alternativa.
- Alternativas duplicadas não são permitidas.
- Perguntas abertas não podem possuir alternativas.
- Campos obrigatórios não podem estar vazios.
- Campos desconhecidos são rejeitados.
- Conjuntos de perguntas não podem estar vazios.

## Integração contínua

A pipeline GitHub Actions está definida em:

`.github/workflows/ci.yml`

Ela foi configurada para executar:

1. Instalação das dependências.
2. Análise de lint com Ruff.
3. Verificação de formatação.
4. Análise estática com mypy.
5. Testes e cobertura com Pytest.

A matriz utiliza Python 3.11 e 3.12.

## Padrões de desenvolvimento

O projeto utiliza:

- Tipagem estática rigorosa.
- Docstrings no padrão Google.
- Princípios de Clean Code e SOLID.
- Testes automatizados.
- Separação de responsabilidades.
- Commits no padrão Conventional Commits.

O desenvolvimento ocorre em branches específicas
para cada tarefa, integradas à main por Pull Requests.

## Próximas funcionalidades

- Carregamento de documentos TXT, MD e PDF.
- Configuração de variáveis de ambiente.
- Divisão de documentos extensos em blocos.
- Integração com o Gemini.
- Geração automática de perguntas.
- Validação das respostas produzidas pelo LLM.
- Exportação em JSON e formato para Anki.
- Interface web com Streamlit.

## Segurança e limitações

A integração com APIs externas ainda não está disponível.

Quando implementada, as credenciais serão fornecidas
por variáveis de ambiente, sem armazenamento no Git.

Os materiais enviados ao provedor de IA deverão
respeitar os requisitos de privacidade e direitos de uso.


O projeto utiliza versionamento semântico e ainda está
em fase de desenvolvimento.

## Licença

Licença ainda não definida.
