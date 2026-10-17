"""Módulo TaskAnalyzer.

Recebe uma coleção de tarefas em memória e calcula métricas de produtividade:
totais por status, tempo médio de conclusão (geral e por prioridade) e taxa
de atraso. O módulo não cria, edita nem persiste tarefas.

Este código foi gerado via assistente de IA seguindo o contrato definido em
``specs/task_analyzer_spec.md`` e as regras de ``CONTEXT_RULES.md``, e
homologado por revisão humana.
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

PRIORIDADES_VALIDAS: tuple[str, ...] = ("baixa", "media", "alta")
STATUS_VALIDOS: tuple[str, ...] = ("pendente", "concluida", "cancelada")
CAMPOS_OBRIGATORIOS: tuple[str, ...] = (
    "id_tarefa",
    "titulo",
    "prioridade",
    "data_criacao",
    "prazo",
    "status",
)
SEGUNDOS_POR_HORA: float = 3600.0
CASAS_DECIMAIS: int = 2


class TaskValidationError(ValueError):
    """Erro lançado quando os dados de entrada violam o contrato de negócio."""


@dataclass(frozen=True)
class _Tarefa:
    """Representação interna, já validada e normalizada, de uma tarefa.

    Attributes:
        id_tarefa: Identificador único positivo da tarefa.
        prioridade: Prioridade normalizada ("baixa", "media" ou "alta").
        status: Status normalizado ("pendente", "concluida" ou "cancelada").
        data_criacao: Data/hora de criação em UTC.
        prazo: Data/hora limite em UTC.
        data_conclusao: Data/hora de conclusão em UTC, ou None se em aberto.
    """

    id_tarefa: int
    prioridade: str
    status: str
    data_criacao: datetime
    prazo: datetime
    data_conclusao: datetime | None


def _para_utc(valor: Any, campo: str, id_tarefa: Any) -> datetime:
    """Converte um datetime para UTC, assumindo UTC quando não houver fuso.

    Args:
        valor: Valor recebido, que deve ser uma instância de ``datetime``.
        campo: Nome do campo (usado na mensagem de erro).
        id_tarefa: Identificador da tarefa (usado na mensagem de erro).

    Returns:
        O datetime normalizado para UTC (com fuso informado).

    Raises:
        TaskValidationError: Se ``valor`` não for um ``datetime``.
    """
    if not isinstance(valor, datetime):
        raise TaskValidationError(
            f"Tarefa {id_tarefa}: o campo '{campo}' deve ser um datetime."
        )
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _validar_id(valor: Any) -> int:
    """Valida o identificador da tarefa.

    Args:
        valor: Valor recebido para ``id_tarefa``.

    Returns:
        O identificador validado.

    Raises:
        TaskValidationError: Se não for um inteiro maior que zero.
    """
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise TaskValidationError(
            f"id_tarefa inválido ({valor!r}): deve ser um inteiro maior que zero."
        )
    return valor


def _validar_titulo(valor: Any, id_tarefa: int) -> None:
    """Valida o título da tarefa.

    Args:
        valor: Valor recebido para ``titulo``.
        id_tarefa: Identificador da tarefa (usado na mensagem de erro).

    Raises:
        TaskValidationError: Se não for texto ou for vazio/apenas espaços.
    """
    if not isinstance(valor, str) or not valor.strip():
        raise TaskValidationError(
            f"Tarefa {id_tarefa}: 'titulo' não pode ser vazio."
        )


def _validar_opcao(
    valor: Any, campo: str, validos: tuple[str, ...], id_tarefa: int
) -> str:
    """Valida e normaliza (minúsculas, sem espaços) um campo enumerado.

    Args:
        valor: Valor recebido.
        campo: Nome do campo (usado na mensagem de erro).
        validos: Valores aceitos.
        id_tarefa: Identificador da tarefa (usado na mensagem de erro).

    Returns:
        O valor normalizado.

    Raises:
        TaskValidationError: Se o valor não estiver entre os aceitos.
    """
    normalizado = valor.strip().lower() if isinstance(valor, str) else valor
    if normalizado not in validos:
        raise TaskValidationError(
            f"Tarefa {id_tarefa}: '{campo}' inválido ({valor!r}). "
            f"Valores aceitos: {', '.join(validos)}."
        )
    return str(normalizado)


def _validar_tarefa(bruta: Any) -> _Tarefa:
    """Valida uma tarefa bruta e a converte para a representação interna.

    Args:
        bruta: Dicionário com os campos da tarefa.

    Returns:
        A tarefa validada e normalizada.

    Raises:
        TaskValidationError: Se algum campo violar o contrato de negócio.
    """
    if not isinstance(bruta, Mapping):
        raise TaskValidationError("Cada tarefa deve ser um dicionário.")

    ausentes = [c for c in CAMPOS_OBRIGATORIOS if c not in bruta]
    if ausentes:
        raise TaskValidationError(
            f"Campos obrigatórios ausentes: {', '.join(ausentes)}."
        )

    id_tarefa = _validar_id(bruta["id_tarefa"])
    _validar_titulo(bruta["titulo"], id_tarefa)
    prioridade = _validar_opcao(
        bruta["prioridade"], "prioridade", PRIORIDADES_VALIDAS, id_tarefa
    )
    status = _validar_opcao(bruta["status"], "status", STATUS_VALIDOS, id_tarefa)
    data_criacao = _para_utc(bruta["data_criacao"], "data_criacao", id_tarefa)
    prazo = _para_utc(bruta["prazo"], "prazo", id_tarefa)

    bruta_conclusao = bruta.get("data_conclusao")
    data_conclusao = (
        None
        if bruta_conclusao is None
        else _para_utc(bruta_conclusao, "data_conclusao", id_tarefa)
    )
    _validar_conclusao(status, data_criacao, data_conclusao, id_tarefa)

    return _Tarefa(id_tarefa, prioridade, status, data_criacao, prazo, data_conclusao)


def _validar_conclusao(
    status: str,
    data_criacao: datetime,
    data_conclusao: datetime | None,
    id_tarefa: int,
) -> None:
    """Valida a consistência entre status e data de conclusão.

    Args:
        status: Status normalizado da tarefa.
        data_criacao: Data de criação em UTC.
        data_conclusao: Data de conclusão em UTC, se houver.
        id_tarefa: Identificador da tarefa (usado na mensagem de erro).

    Raises:
        TaskValidationError: Se a conclusão for anterior à criação, ou se uma
            tarefa concluída não tiver data de conclusão.
    """
    if data_conclusao is not None and data_conclusao < data_criacao:
        raise TaskValidationError(
            f"Tarefa {id_tarefa}: data_conclusao anterior à data_criacao."
        )
    if status == "concluida" and data_conclusao is None:
        raise TaskValidationError(
            f"Tarefa {id_tarefa}: tarefa concluída sem data_conclusao."
        )


def _validar_colecao(tarefas: Any) -> list[_Tarefa]:
    """Valida a coleção inteira e garante unicidade dos identificadores.

    Args:
        tarefas: Lista de dicionários de tarefas.

    Returns:
        Lista de tarefas validadas.

    Raises:
        TaskValidationError: Se a entrada não for uma lista, se alguma tarefa
            for inválida ou se houver ``id_tarefa`` duplicado.
    """
    if not isinstance(tarefas, list):
        raise TaskValidationError("A entrada deve ser uma lista de tarefas.")

    validadas = [_validar_tarefa(t) for t in tarefas]
    ids = [t.id_tarefa for t in validadas]
    if len(ids) != len(set(ids)):
        raise TaskValidationError("Há id_tarefa duplicado na coleção.")
    return validadas


def _duracao_em_horas(tarefa: _Tarefa) -> float:
    """Calcula a duração (criação até conclusão) de uma tarefa concluída.

    Args:
        tarefa: Tarefa concluída (com ``data_conclusao`` preenchida).

    Returns:
        Duração em horas.
    """
    assert tarefa.data_conclusao is not None
    segundos = (tarefa.data_conclusao - tarefa.data_criacao).total_seconds()
    return segundos / SEGUNDOS_POR_HORA


def _media_horas(concluidas: list[_Tarefa]) -> float:
    """Calcula o tempo médio de conclusão, tratando a divisão por zero.

    Args:
        concluidas: Tarefas concluídas.

    Returns:
        Média em horas (arredondada), ou 0.0 se a lista for vazia.
    """
    if not concluidas:
        return 0.0
    total = sum(_duracao_em_horas(t) for t in concluidas)
    return round(total / len(concluidas), CASAS_DECIMAIS)


def _taxa_atraso(concluidas: list[_Tarefa]) -> float:
    """Calcula o percentual de tarefas concluídas após o prazo.

    Args:
        concluidas: Tarefas concluídas.

    Returns:
        Percentual (arredondado), ou 0.0 se não houver tarefas concluídas.
    """
    if not concluidas:
        return 0.0
    atrasadas = sum(
        1 for t in concluidas if t.data_conclusao is not None and t.data_conclusao > t.prazo
    )
    return round(atrasadas / len(concluidas) * 100, CASAS_DECIMAIS)


def _indicadores_por_prioridade(
    tarefas: list[_Tarefa],
) -> dict[str, dict[str, float | int]]:
    """Gera os indicadores agregados por prioridade.

    Args:
        tarefas: Todas as tarefas validadas.

    Returns:
        Dicionário com, para cada prioridade, a quantidade total de tarefas e
        o tempo médio de conclusão em horas (das concluídas daquela prioridade).
    """
    indicadores: dict[str, dict[str, float | int]] = {}
    for prioridade in PRIORIDADES_VALIDAS:
        da_prioridade = [t for t in tarefas if t.prioridade == prioridade]
        concluidas = [t for t in da_prioridade if t.status == "concluida"]
        indicadores[prioridade] = {
            "quantidade": len(da_prioridade),
            "tempo_medio_conclusao_horas": _media_horas(concluidas),
        }
    return indicadores


def analyze_tasks(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Analisa uma coleção de tarefas e calcula métricas de produtividade.

    Apenas tarefas com status ``concluida`` entram nos cálculos de tempo médio
    e taxa de atraso. Tarefas ``cancelada`` contam apenas em ``total_tarefas``.
    Uma tarefa é atrasada quando ``data_conclusao > prazo``.

    Args:
        tasks: Lista de dicionários com os campos ``id_tarefa``, ``titulo``,
            ``prioridade``, ``data_criacao``, ``prazo``, ``status`` e,
            opcionalmente, ``data_conclusao``.

    Returns:
        Dicionário com as chaves ``total_tarefas``, ``total_concluidas``,
        ``total_pendentes``, ``tempo_medio_conclusao_horas``,
        ``taxa_atraso_percentual`` e ``indicadores_por_prioridade``.

    Raises:
        TaskValidationError: Se a entrada violar o contrato de negócio (datas
            inconsistentes, campos inválidos ou ausentes, ids duplicados).
    """
    validadas = _validar_colecao(tasks)
    concluidas = [t for t in validadas if t.status == "concluida"]
    pendentes = [t for t in validadas if t.status == "pendente"]

    resultado: dict[str, Any] = {
        "total_tarefas": len(validadas),
        "total_concluidas": len(concluidas),
        "total_pendentes": len(pendentes),
        "tempo_medio_conclusao_horas": _media_horas(concluidas),
        "taxa_atraso_percentual": _taxa_atraso(concluidas),
        "indicadores_por_prioridade": _indicadores_por_prioridade(validadas),
    }
    logger.info(
        "Análise concluída: %d tarefas (%d concluídas, %d pendentes).",
        resultado["total_tarefas"],
        resultado["total_concluidas"],
        resultado["total_pendentes"],
    )
    return resultado
