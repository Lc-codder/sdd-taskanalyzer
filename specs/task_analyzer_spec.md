# Especificação SDD — TaskAnalyzer (v1.1)

Contrato executável do módulo TaskAnalyzer, transposto da Fase 1 e ajustado para a Fase 2 (métricas em **horas** e totais por status).

## 1. Visão geral e contrato de negócio

### 1.1 Propósito

O TaskAnalyzer recebe uma coleção de tarefas já existente, processa em memória e retorna métricas de produtividade: totais por status, tempo médio de conclusão (geral e por prioridade) e taxa de atraso. Não cria, edita nem armazena tarefas.

### 1.2 Interface pública

```python
def analyze_tasks(tasks: list[dict[str, Any]]) -> dict[str, Any]: ...

class TaskValidationError(ValueError): ...
```

### 1.3 Entradas

Cada tarefa é um dicionário com os campos:

| Campo | Tipo | Obrigatório | Restrições |
|---|---|---|---|
| `id_tarefa` | int | Sim | Inteiro > 0 e único na coleção |
| `titulo` | str | Sim | Não pode ser vazio ou só espaços |
| `prioridade` | str | Sim | `baixa`, `media` ou `alta` (case-insensitive) |
| `data_criacao` | datetime | Sim | Tratada em UTC |
| `data_conclusao` | datetime \| None | Não | Nulo se a tarefa não foi concluída |
| `prazo` | datetime | Sim | Limite previsto de conclusão |
| `status` | str | Sim | `pendente`, `concluida` ou `cancelada` (case-insensitive) |

### 1.4 Saídas

| Campo | Tipo | Descrição |
|---|---|---|
| `total_tarefas` | int | Total de tarefas recebidas (todos os status) |
| `total_concluidas` | int | Tarefas com status `concluida` |
| `total_pendentes` | int | Tarefas com status `pendente` |
| `tempo_medio_conclusao_horas` | float | Média (criação → conclusão), em horas, das concluídas |
| `taxa_atraso_percentual` | float | % de concluídas com `data_conclusao > prazo`, sobre o total de concluídas |
| `indicadores_por_prioridade` | dict | Para `baixa`, `media` e `alta`: `quantidade` (todas as tarefas da prioridade) e `tempo_medio_conclusao_horas` (das concluídas da prioridade) |

> Tarefas `cancelada` contam apenas em `total_tarefas` (por isso `total_tarefas` pode ser maior que `total_concluidas + total_pendentes`).

### 1.5 Regras de negócio

1. Apenas tarefas `concluida` entram no cálculo de tempo médio e taxa de atraso.
2. Tarefas `cancelada` são excluídas de todos os cálculos de tempo e atraso.
3. Uma tarefa é atrasada quando `data_conclusao > prazo` (conclusão exatamente no prazo **não** é atraso).
4. `data_conclusao < data_criacao` é inválido e dispara `TaskValidationError` (em qualquer status).
5. Tarefa `concluida` sem `data_conclusao` é inválida e dispara `TaskValidationError`.
6. Sem tarefas concluídas, médias e taxa de atraso retornam `0.0` (sem exceção).
7. Todas as datas são normalizadas para UTC; datas sem fuso são assumidas como UTC.
8. Valores numéricos são arredondados em 2 casas decimais.
9. Campos ausentes/inválidos, `id_tarefa` duplicado ou entrada que não seja lista disparam `TaskValidationError`.

## 2. Cenários de aceite e Test Harness

### Cenário 1 — Sucesso

- **Dado** um conjunto de tarefas válidas, com diferentes prioridades, prazos e status,
- **Quando** `analyze_tasks` for executado,
- **Então** deve retornar `total_tarefas`, `total_concluidas`, `total_pendentes`, `tempo_medio_conclusao_horas` (geral e por prioridade) e `taxa_atraso_percentual` corretos.

### Cenário 2 — Exceção / Erro

- **Dado** uma entrada com datas inconsistentes (`data_conclusao < data_criacao`),
- **Quando** `analyze_tasks` for executado,
- **Então** deve disparar `TaskValidationError` com mensagem clara.

### Casos de borda

- **Dado** uma lista vazia ou apenas tarefas pendentes, **quando** executado, **então** retorna `0.0` para médias e taxa, sem exceção não tratada.

### Planejamento do Test Harness

Cenários de aceite → casos de teste → testes automatizados (`pytest`, em `tests/test_harness.py`) → execução e validação → evidências (saída do `pytest`).

## 3. Governança

As regras para agentes de IA estão em [`CONTEXT_RULES.md`](../CONTEXT_RULES.md).

## 4. Estrutura do repositório

```
sdd-taskanalyzer/
├── README.md
├── CONTEXT_RULES.md
├── .gitignore
├── requirements.txt
├── specs/
│   └── task_analyzer_spec.md
├── tests/
│   └── test_harness.py
└── src/
    └── task_analyzer.py
```
