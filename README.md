# sdd-taskanalyzer

Módulo **TaskAnalyzer** desenvolvido com **Spec-Driven Development (SDD)** e assistido por IA (Bootcamp III — Fase 2).
A especificação é o contrato, a IA é a executora e o desenvolvedor é o homologador.

![status](https://img.shields.io/badge/testes-33%20passed-brightgreen)

> Status do build: testes executados localmente com `pytest` (33 passed). A automação com GitHub Actions (CI/CD) será adicionada na Fase 3.

## O que faz

Recebe uma lista de tarefas e retorna métricas de produtividade: `total_tarefas`, `total_concluidas`, `total_pendentes`, `tempo_medio_conclusao_horas` (geral e por prioridade) e `taxa_atraso_percentual`. Entradas inválidas (ex.: `data_conclusao < data_criacao`) disparam `TaskValidationError`.

## Estrutura

```
sdd-taskanalyzer/
├── README.md
├── CONTEXT_RULES.md        # Regras de governança para a IA
├── .gitignore
├── requirements.txt
├── specs/
│   └── task_analyzer_spec.md   # Contrato SDD
├── tests/
│   └── test_harness.py     # Test Harness (pytest)
└── src/
    └── task_analyzer.py    # Código gerado via IA e homologado
```

## Como executar

Requer Python 3.11+.

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
pytest -v
```

## Exemplo de uso

```python
from datetime import datetime, timezone
from src.task_analyzer import analyze_tasks

tarefas = [{
    "id_tarefa": 1,
    "titulo": "Escrever relatório",
    "prioridade": "alta",
    "data_criacao": datetime(2026, 1, 1, 8, tzinfo=timezone.utc),
    "data_conclusao": datetime(2026, 1, 1, 10, tzinfo=timezone.utc),
    "prazo": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
    "status": "concluida",
}]
print(analyze_tasks(tarefas)["tempo_medio_conclusao_horas"])  # 2.0
```

## Fluxo de trabalho

- Branch principal: `main`; funcionalidades em `feature/*` e integração via Pull Request.
- Todo código gerado por IA passa por homologação humana (ver checklist em `CONTEXT_RULES.md`).

## Autor

Lucas Daniel Silva Guimarães — Ciência da Computação (CEUB) — Bootcamp III
