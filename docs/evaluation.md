# SQ-021 — Avaliação offline de perguntas

O `Evaluation Framework` compara respostas salvas com material de referência e,
quando disponíveis, gabaritos **anotados manualmente**. Não chama a API Gemini.

## Execução

Após `pip install -e ".[dev]"`:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_questions.py --dataset datasets/evaluation/sample.json
.\.venv\Scripts\python.exe scripts/evaluate_questions.py --dataset datasets/evaluation/sample.json --json
```

Linux/macOS: substitua o executável por `./.venv/bin/python`.

## Formato do conjunto de avaliação

O arquivo JSON contém `version: 1` e `cases`. Cada caso possui:

- `id`: identificador único e estável;
- `source_text`: texto de origem **sintético ou autorizado**;
- `questions`: lista de objetos no mesmo formato de `Question` do projeto,
  incluindo perguntas inválidas que se deseja investigar;
- `expected_answers` (opcional): lista alinhada a `questions` com respostas
  de referência em texto ou `null` para itens sem anotação.

A exportação JSON de perguntas do Study Questions pode fornecer a lista
`questions`. Para avaliá-la, é necessário acrescentar o texto de origem e,
opcionalmente, respostas de referência anotadas por pessoas. Não versionar
materiais privados, chaves ou resultados de usuários.

## Métricas (sem combinar indevidamente as dimensões)

| Métrica | Numerador | Denominador |
| --- | --- | --- |
| `structure_valid_rate` | Perguntas compatíveis com `Question` | Perguntas recebidas |
| `excerpt_found_rate` | Citações textualmente encontradas no documento | Perguntas estruturalmente válidas |
| `unique_rate` | Enunciados únicos e com citação localizada | Perguntas com citação localizada |
| `answer_exact_match_rate` | Respostas iguais ao gabarito após normalização NFKC, espaços e caixa | Perguntas válidas, únicas e com gabarito anotado |

Uma taxa sem denominador é `null` (em JSON) ou `N/A` (no terminal).
Os denominadores são **contagens agregadas**, não médias das taxas dos casos.

O relatório inclui motivos por índice (`invalid_structure`, `excerpt_not_found`,
`duplicate_statement`, `answer_exact_mismatch`), sem copiar as perguntas.

### Limitações

- **Citação encontrada não comprova fidelidade factual**: um trecho pode
  existir no material e não sustentar a resposta proposta.
- **Correspondência exata não comprova correção semântica** e pode rejeitar
  paráfrases corretas. É uma aproximação verificável para gabaritos curtos.
- O sistema não pontua criatividade, dificuldade, qualidade pedagógica,
  verdade factual ou explicações sem anotação e revisão humana.
- Perguntas inválidas não são enviadas à aplicação nem corrigidas pelo avaliador.
- O conjunto `sample.json` é **sintético** e serve para testar a infraestrutura;
  não é evidência de qualidade do Gemini em dados reais.

Para comparar versões do prompt ou modelos, preserve o mesmo conjunto de casos,
os mesmos gabaritos e critérios. Salve resultados separados e registre modelo,
versão do prompt e data externamente; o avaliador só consome dados já produzidos.
