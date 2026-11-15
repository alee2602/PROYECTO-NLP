"""Límite de llamadas al LLM por ejecución (SEC: abuso de recursos / bucles
agénticos). Complementa los límites top_k/max_claims de src/limits.py."""

MAX_LLM_CALLS = 120
GRAPH_RECURSION_LIMIT = 200
# Anteproyecto sección 13: máximo 3 iteraciones del agente y 10 llamadas
# externas por afirmación.
MAX_AGENT_ITERATIONS = 3
MAX_EXTERNAL_CALLS_PER_CLAIM = 10


class BudgetExceeded(RuntimeError):
    pass


class BudgetedClient:
    """Envuelve un cliente LLM y falla de forma dura al pasar el límite."""

    def __init__(self, client, max_calls: int = MAX_LLM_CALLS):
        self._client = client
        self.max_calls = max_calls
        self.calls = 0
        self.total_tokens = 0

    @property
    def exhausted(self) -> bool:
        return self.calls >= self.max_calls

    def chat(self, **kwargs):
        if self.exhausted:
            raise BudgetExceeded(f"Límite de {self.max_calls} llamadas al LLM alcanzado")
        self.calls += 1
        response = self._client.chat(**kwargs)
        usage = response.get("usage") if isinstance(response, dict) else None
        if usage:
            self.total_tokens += int(usage.get("total_tokens", 0))
        return response


class ExternalCallBudget:
    """Contador de llamadas externas (Crossref/OpenAlex) por afirmación."""

    def __init__(self, max_calls: int = MAX_EXTERNAL_CALLS_PER_CLAIM):
        self.max_calls = max_calls
        self.calls = 0

    def consume(self) -> bool:
        """True si la llamada está permitida (y la cuenta); False si no."""
        if self.calls >= self.max_calls:
            return False
        self.calls += 1
        return True
