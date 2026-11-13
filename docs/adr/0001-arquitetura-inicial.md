
# ADR 0001 — Arquitetura inicial

**Status:** Aceita

**Projeto:** Study Questions

## Contexto

O projeto tem como objetivo gerar perguntas de estudo
a partir de materiais didáticos utilizando LLMs.

A arquitetura deve ser simples, testável, extensível
e de fácil manutenção.

## Decisão

Foi escolhida uma arquitetura modular em Python,
utilizando o layout src/.

As regras de negócio serão mantidas separadas
das integrações externas e da interface.

O projeto utilizará:

- Python 3.11+
- Pydantic v2 para validação.
- Pytest para testes automatizados.
- Ruff para lint e formatação.
- mypy para análise estática.
- GitHub Actions para integração contínua.

## Integração com LLMs

Os provedores de inteligência artificial serão
isolados por uma interface baseada em Protocol.

A implementação inicial prevista utilizará Gemini.

Essa decisão permitirá adicionar outros provedores
sem modificar as regras centrais da aplicação.

## Persistência

Não será utilizado banco de dados inicialmente.

Os modelos Pydantic representam contratos de dados,
e não tabelas de banco de dados.

A necessidade de persistência será reavaliada
quando surgirem requisitos de histórico e usuários.

## Qualidade

Todo código deverá possuir tipagem rigorosa.

As funções deverão seguir o padrão de documentação
Google e ter testes compatíveis com sua criticidade.

A cobertura global mínima inicial é de 80%.

## Riscos

- Dependência de serviços externos de IA.
- Respostas incorretas ou inconsistentes do LLM.
- Aumento desnecessário da complexidade.
- Mudanças nas APIs dos provedores.

## Consequências

A arquitetura permite iniciar o desenvolvimento
sem infraestrutura desnecessária.

Também facilita testes automatizados e futuras
mudanças no provedor de inteligência artificial.

A principal limitação é que ainda não existe
persistência ou interface web implementada.
