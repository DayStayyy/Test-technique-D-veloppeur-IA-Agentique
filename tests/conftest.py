"""Fixtures partagees pour les tests de niveau un.

Niveau un, tel qu'acte dans CLAUDE.md : aucun appel reseau, aucune
ecriture sur le cache disque. `FakeClient` simule le seul point de
contact avec l'exterieur, `OpenRouterClient.complete`.
"""

from __future__ import annotations

from moderation.llm import ModelRequest, ModelResponse, OpenRouterError


class FakeClient:
    """Client factice rendant des reponses pre-enregistrees.

    Attributes:
        requests: Requetes recues, dans l'ordre, pour inspection par
            le test.
    """

    def __init__(self, responses: list[str | OpenRouterError]) -> None:
        """Initialise le client factice.

        Args:
            responses: Reponses a rendre, dans l'ordre de
                consommation. Un `OpenRouterError` est leve au lieu
                d'etre renvoye, pour simuler un echec d'appel.
        """
        self._responses = list(responses)
        self.requests: list[ModelRequest] = []

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Consomme la prochaine reponse de la file.

        Args:
            request: Requete recue.

        Returns:
            La reponse simulee correspondante.

        Raises:
            OpenRouterError: Si l'element consomme en est un.
            AssertionError: Si la file est vide : le test appelle le
                client plus de fois que prevu.
        """
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("FakeClient : plus de réponse en file")
        item = self._responses.pop(0)
        if isinstance(item, OpenRouterError):
            raise item
        return ModelResponse(text=item, model=request.model, from_cache=False)
