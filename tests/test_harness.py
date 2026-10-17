"""Test Harness do TaskAnalyzer (pytest).

Traduz diretamente os cenários de aceite da especificação SDD:
    - Cenário 1: sucesso (métricas corretas).
    - Cenário 2: exceção (datas inconsistentes -> TaskValidationError).
    - Casos de borda: entrada vazia e apenas tarefas pendentes.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.task_analyzer import TaskValidationError, analyze_tasks  # noqa: E402


def _dt(dia: int, hora: int) -> datetime:
    """Cria um datetime UTC em janeiro de 2026.

    Args:
        dia: Dia do mês.
        hora: Hora do dia.

    Returns:
        Datetime com fuso UTC.
    """
    return datetime(2026, 1, dia, hora, 0, tzinfo=timezone.utc)


def _tarefa(
    id_tarefa: int,
    prioridade: str,
    status: str,
    data_criacao: datetime,
    prazo: datetime,
    data_conclusao: datetime | None = None,
) -> dict[str, Any]:
    """Monta um dicionário de tarefa válido para os testes.

    Args:
        id_tarefa: Identificador da tarefa.
        prioridade: Prioridade da tarefa.
        status: Status da tarefa.
        data_criacao: Data de criação.
        prazo: Prazo limite.
        data_conclusao: Data de conclusão, se houver.

    Returns:
        Dicionário no formato esperado por ``analyze_tasks``.
    """
    return {
        "id_tarefa": id_tarefa,
        "titulo": f"Tarefa {id_tarefa}",
        "prioridade": prioridade,
        "data_criacao": data_criacao,
        "data_conclusao": data_conclusao,
        "prazo": prazo,
        "status": status,
    }


@pytest.fixture
def tarefas_validas() -> list[dict[str, Any]]:
    """Conjunto válido com concluídas (no prazo e atrasada), pendente e cancelada.

    Returns:
        Lista de 5 tarefas.
    """
    return [
        _tarefa(1, "alta", "concluida", _dt(1, 8), _dt(1, 12), _dt(1, 10)),  # 2h, no prazo
        _tarefa(2, "alta", "concluida", _dt(2, 8), _dt(2, 12), _dt(2, 16)),  # 8h, atrasada
        _tarefa(3, "media", "concluida", _dt(3, 9), _dt(3, 18), _dt(3, 13)),  # 4h, no prazo
        _tarefa(4, "baixa", "pendente", _dt(4, 9), _dt(10, 9)),
        _tarefa(5, "baixa", "cancelada", _dt(5, 9), _dt(11, 9)),
    ]


# --------------------------------------------------------------------------
# Cenário 1 — Sucesso
# --------------------------------------------------------------------------
class TestCenario1Sucesso:
    """Dado tarefas válidas, o analisador retorna as métricas corretas."""

    def test_totais(self, tarefas_validas: list[dict[str, Any]]) -> None:
        resultado = analyze_tasks(tarefas_validas)
        assert resultado["total_tarefas"] == 5
        assert resultado["total_concluidas"] == 3
        assert resultado["total_pendentes"] == 1

    def test_tempo_medio_geral(self, tarefas_validas: list[dict[str, Any]]) -> None:
        resultado = analyze_tasks(tarefas_validas)
        # (2 + 8 + 4) / 3 = 4.67 horas
        assert resultado["tempo_medio_conclusao_horas"] == pytest.approx(4.67)

    def test_taxa_atraso(self, tarefas_validas: list[dict[str, Any]]) -> None:
        resultado = analyze_tasks(tarefas_validas)
        # 1 atrasada em 3 concluídas = 33.33%
        assert resultado["taxa_atraso_percentual"] == pytest.approx(33.33)

    def test_indicadores_por_prioridade(
        self, tarefas_validas: list[dict[str, Any]]
    ) -> None:
        indicadores = analyze_tasks(tarefas_validas)["indicadores_por_prioridade"]
        assert indicadores["alta"] == {
            "quantidade": 2,
            "tempo_medio_conclusao_horas": pytest.approx(5.0),
        }
        assert indicadores["media"] == {
            "quantidade": 1,
            "tempo_medio_conclusao_horas": pytest.approx(4.0),
        }
        assert indicadores["baixa"] == {
            "quantidade": 2,
            "tempo_medio_conclusao_horas": pytest.approx(0.0),
        }

    def test_conclusao_exatamente_no_prazo_nao_e_atraso(self) -> None:
        tarefas = [_tarefa(1, "alta", "concluida", _dt(1, 8), _dt(1, 12), _dt(1, 12))]
        assert analyze_tasks(tarefas)["taxa_atraso_percentual"] == 0.0

    def test_todas_atrasadas(self) -> None:
        tarefas = [
            _tarefa(1, "alta", "concluida", _dt(1, 8), _dt(1, 9), _dt(1, 12)),
            _tarefa(2, "baixa", "concluida", _dt(2, 8), _dt(2, 9), _dt(2, 12)),
        ]
        assert analyze_tasks(tarefas)["taxa_atraso_percentual"] == 100.0

    def test_prioridade_e_status_case_insensitive(self) -> None:
        tarefas = [_tarefa(1, "ALTA", "Concluida", _dt(1, 8), _dt(1, 12), _dt(1, 10))]
        resultado = analyze_tasks(tarefas)
        assert resultado["total_concluidas"] == 1
        assert resultado["indicadores_por_prioridade"]["alta"]["quantidade"] == 1

    def test_datas_com_fuso_diferente_sao_normalizadas_para_utc(self) -> None:
        brasilia = timezone(timedelta(hours=-3))
        criacao = datetime(2026, 1, 1, 5, 0, tzinfo=brasilia)  # 08:00 UTC
        conclusao = datetime(2026, 1, 1, 7, 0, tzinfo=brasilia)  # 10:00 UTC
        tarefas = [_tarefa(1, "alta", "concluida", criacao, _dt(1, 12), conclusao)]
        assert analyze_tasks(tarefas)["tempo_medio_conclusao_horas"] == 2.0

    def test_datas_sem_fuso_sao_tratadas_como_utc(self) -> None:
        criacao = datetime(2026, 1, 1, 8, 0)
        conclusao = datetime(2026, 1, 1, 10, 0)
        prazo = datetime(2026, 1, 1, 12, 0)
        tarefas = [_tarefa(1, "alta", "concluida", criacao, prazo, conclusao)]
        assert analyze_tasks(tarefas)["tempo_medio_conclusao_horas"] == 2.0


# --------------------------------------------------------------------------
# Cenário 2 — Exceção / Erro
# --------------------------------------------------------------------------
class TestCenario2Excecao:
    """Dado entradas inválidas, o analisador dispara TaskValidationError."""

    def test_conclusao_anterior_a_criacao(self) -> None:
        tarefas = [_tarefa(1, "alta", "concluida", _dt(2, 8), _dt(2, 12), _dt(1, 8))]
        with pytest.raises(TaskValidationError, match="anterior"):
            analyze_tasks(tarefas)

    def test_conclusao_anterior_a_criacao_mesmo_em_tarefa_pendente(self) -> None:
        tarefas = [_tarefa(1, "alta", "pendente", _dt(2, 8), _dt(2, 12), _dt(1, 8))]
        with pytest.raises(TaskValidationError):
            analyze_tasks(tarefas)

    def test_tarefa_concluida_sem_data_de_conclusao(self) -> None:
        tarefas = [_tarefa(1, "alta", "concluida", _dt(1, 8), _dt(1, 12))]
        with pytest.raises(TaskValidationError, match="sem data_conclusao"):
            analyze_tasks(tarefas)

    def test_prioridade_invalida(self) -> None:
        tarefas = [_tarefa(1, "urgente", "pendente", _dt(1, 8), _dt(1, 12))]
        with pytest.raises(TaskValidationError, match="prioridade"):
            analyze_tasks(tarefas)

    def test_status_invalido(self) -> None:
        tarefas = [_tarefa(1, "alta", "em_andamento", _dt(1, 8), _dt(1, 12))]
        with pytest.raises(TaskValidationError, match="status"):
            analyze_tasks(tarefas)

    def test_id_duplicado(self) -> None:
        tarefas = [
            _tarefa(1, "alta", "pendente", _dt(1, 8), _dt(1, 12)),
            _tarefa(1, "baixa", "pendente", _dt(2, 8), _dt(2, 12)),
        ]
        with pytest.raises(TaskValidationError, match="duplicado"):
            analyze_tasks(tarefas)

    @pytest.mark.parametrize("id_invalido", [0, -3, "7", 1.5, True])
    def test_id_invalido(self, id_invalido: Any) -> None:
        tarefa = _tarefa(1, "alta", "pendente", _dt(1, 8), _dt(1, 12))
        tarefa["id_tarefa"] = id_invalido
        with pytest.raises(TaskValidationError, match="id_tarefa"):
            analyze_tasks([tarefa])

    @pytest.mark.parametrize("titulo_invalido", ["", "   ", None, 42])
    def test_titulo_invalido(self, titulo_invalido: Any) -> None:
        tarefa = _tarefa(1, "alta", "pendente", _dt(1, 8), _dt(1, 12))
        tarefa["titulo"] = titulo_invalido
        with pytest.raises(TaskValidationError, match="titulo"):
            analyze_tasks([tarefa])

    def test_campo_obrigatorio_ausente(self) -> None:
        tarefa = _tarefa(1, "alta", "pendente", _dt(1, 8), _dt(1, 12))
        del tarefa["prazo"]
        with pytest.raises(TaskValidationError, match="prazo"):
            analyze_tasks([tarefa])

    def test_data_que_nao_e_datetime(self) -> None:
        tarefa = _tarefa(1, "alta", "pendente", _dt(1, 8), _dt(1, 12))
        tarefa["data_criacao"] = "2026-01-01"
        with pytest.raises(TaskValidationError, match="data_criacao"):
            analyze_tasks([tarefa])

    def test_entrada_que_nao_e_lista(self) -> None:
        with pytest.raises(TaskValidationError, match="lista"):
            analyze_tasks("não é uma lista")  # type: ignore[arg-type]

    def test_item_que_nao_e_dicionario(self) -> None:
        with pytest.raises(TaskValidationError, match="dicionário"):
            analyze_tasks(["não é um dicionário"])  # type: ignore[list-item]


# --------------------------------------------------------------------------
# Casos de borda
# --------------------------------------------------------------------------
class TestCasosDeBorda:
    """Entradas vazias ou só com pendentes retornam 0.0 sem exceção."""

    def test_entrada_vazia(self) -> None:
        resultado = analyze_tasks([])
        assert resultado["total_tarefas"] == 0
        assert resultado["total_concluidas"] == 0
        assert resultado["total_pendentes"] == 0
        assert resultado["tempo_medio_conclusao_horas"] == 0.0
        assert resultado["taxa_atraso_percentual"] == 0.0
        for indicador in resultado["indicadores_por_prioridade"].values():
            assert indicador == {"quantidade": 0, "tempo_medio_conclusao_horas": 0.0}

    def test_apenas_tarefas_pendentes(self) -> None:
        tarefas = [
            _tarefa(1, "alta", "pendente", _dt(1, 8), _dt(5, 8)),
            _tarefa(2, "media", "pendente", _dt(2, 8), _dt(6, 8)),
        ]
        resultado = analyze_tasks(tarefas)
        assert resultado["total_tarefas"] == 2
        assert resultado["total_concluidas"] == 0
        assert resultado["total_pendentes"] == 2
        assert resultado["tempo_medio_conclusao_horas"] == 0.0
        assert resultado["taxa_atraso_percentual"] == 0.0

    def test_apenas_tarefas_canceladas(self) -> None:
        tarefas = [_tarefa(1, "alta", "cancelada", _dt(1, 8), _dt(5, 8))]
        resultado = analyze_tasks(tarefas)
        assert resultado["total_tarefas"] == 1
        assert resultado["total_concluidas"] == 0
        assert resultado["total_pendentes"] == 0
        assert resultado["tempo_medio_conclusao_horas"] == 0.0

    def test_uma_unica_tarefa_concluida(self) -> None:
        tarefas = [_tarefa(1, "baixa", "concluida", _dt(1, 8), _dt(1, 12), _dt(1, 11))]
        resultado = analyze_tasks(tarefas)
        assert resultado["tempo_medio_conclusao_horas"] == 3.0
        assert resultado["taxa_atraso_percentual"] == 0.0

    def test_entrada_nao_e_modificada(
        self, tarefas_validas: list[dict[str, Any]]
    ) -> None:
        copia = [dict(t) for t in tarefas_validas]
        analyze_tasks(tarefas_validas)
        assert tarefas_validas == copia
