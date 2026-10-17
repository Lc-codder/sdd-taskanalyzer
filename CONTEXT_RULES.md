# CONTEXT_RULES — Regras de Governança para Agentes de IA

Regras fornecidas a qualquer assistente de IA (Coding Agent) que gere código neste repositório. Elas garantem alinhamento, consistência e qualidade, reduzindo o risco de "alucinações" e de comportamentos fora do escopo.

**Fonte da verdade:** `specs/task_analyzer_spec.md`. Em caso de conflito ou dúvida, a especificação prevalece e a IA deve sinalizar a ambiguidade em vez de decidir sozinha.

## Escopo desta geração

- Arquivo a gerar: `src/task_analyzer.py`
- Função pública: `analyze_tasks(tasks: list[dict[str, Any]]) -> dict[str, Any]`
- Exceção customizada: `TaskValidationError`

## 1. Diretrizes Arquiteturais (obrigatórias)

- Utilizar Python 3.11 ou superior como versão mínima.
- Utilizar type hints em 100% das funções, métodos e parâmetros.
- Seguir o princípio Single Responsibility (SRP) e o PEP 8.
- Documentar módulos, classes, funções e parâmetros com Google style docstrings.
- Manter funções pequenas, coesas e com um único propósito.
- Tratar exceções de forma específica, com mensagens claras.
- Utilizar o módulo padrão `logging` (nunca `print`).
- Usar nomes de variáveis e funções descritivos, de forma consistente em todo o projeto.

## 2. Proibições Explícitas

- Não utilizar bibliotecas externas não autorizadas (apenas biblioteca padrão, e `pytest` para testes).
- Não alterar, remover ou adaptar os cenários de teste fornecidos na especificação.
- Não modificar a estrutura de pastas definida na especificação.
- Não persistir dados em arquivos ou bancos de dados (operação apenas em memória).
- Não alterar a assinatura (nome e parâmetros) das funções públicas sem autorização.
- Não gerar código sem os testes correspondentes para as novas funcionalidades.
- Não inserir código duplicado ou desnecessário (evitar over-engineering).
- Não assumir comportamentos não especificados no contrato de negócio.
- Não comentar código em excesso (apenas o necessário).
- Não retornar valores diferentes dos definidos no contrato (ex.: média sem dados deve ser `0.0`, nunca `None` ou `NaN`).

## 3. Regras de Interação com a IA

- Fornecer sempre o contexto completo (este arquivo + a especificação) antes de solicitar código.
- Validar se a IA compreendeu o contrato e os cenários de aceite antes de aceitar o código.
- Solicitar explicações sempre que houver dúvida sobre a solução proposta.
- Revisar criticamente todo código gerado antes de qualquer commit: a IA propõe, o desenvolvedor decide.
- Rejeitar e pedir nova geração sempre que a resposta violar qualquer proibição acima.

## 4. Checklist de homologação humana

- [ ] `pytest` executado com 100% de aprovação
- [ ] Conformidade com o contrato de negócio (`specs/task_analyzer_spec.md`)
- [ ] Conformidade com estas regras (type hints, docstrings, logging, sem libs externas)
- [ ] Tratamento de erros e casos de borda revisados
- [ ] Somente então: commit e Pull Request
