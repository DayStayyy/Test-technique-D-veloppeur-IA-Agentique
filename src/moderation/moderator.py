"""Fonction de moderation de commentaires.

Le livrable central du projet : recevoir un commentaire et son
contexte eventuel, et retourner une decision. Un seul etage,
puisque le perimetre est reduit au legal (phase 2). Pas de retry
sur refus ou erreur reseau : seule une reponse mal formee est
retentee, une fois, l'echec des deux tentatives etant lui-meme un
resultat a mesurer plutot qu'a masquer.

Quel que soit ce qui empeche d'obtenir un jugement du modele, la
decision par defaut est ACCEPTABLE. Rejeter par defaut rendrait le
systeme plus restrictif que la loi des qu'un appel echoue, ce que
la consigne interdit justement. Le statut de la decision indique
alors explicitement qu'aucun jugement n'a eu lieu.
"""

from __future__ import annotations

from moderation.decision import Decision, Status
from moderation.llm import ModelRequest, ModerationClient, OpenRouterError
from moderation.parsing import fallback_decision, parse_legal_response
from moderation.prompts import (
    LEGAL_PROMPT_VERSION,
    LEGAL_SYSTEM_PROMPT,
    build_legal_user_message,
)

DEFAULT_MODEL = "openai/gpt-5.6-luna"
DEFAULT_MAX_ATTEMPTS = 2


class Moderator:
    """Juge des commentaires au regard de la seule ligne legale.

    Attributes:
        client: Client interrogeant le modele, normalement adosse au
            cache disque.
        model: Identifiant OpenRouter du modele interroge.
        max_attempts: Nombre maximal de tentatives par commentaire.
    """

    def __init__(
        self,
        client: ModerationClient,
        model: str = DEFAULT_MODEL,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        """Initialise le moderateur.

        Args:
            client: Client servant a interroger le modele.
            model: Identifiant OpenRouter du modele a interroger.
            max_attempts: Nombre maximal de tentatives par
                commentaire, au moins 1.

        Raises:
            ValueError: Si `max_attempts` est inferieur a 1.
        """
        if max_attempts < 1:
            raise ValueError(
                f"max_attempts doit être au moins 1 (trouvé {max_attempts})."
            )
        self.client = client
        self.model = model
        self.max_attempts = max_attempts

    def moderate(self, text: str, context: str = "") -> Decision:
        """Juge un commentaire au regard de la ligne legale.

        Une reponse mal formee est retentee une fois. Un refus ou
        une erreur reseau ne sont jamais retentes : le modele qui
        refuse de repondre le refera, et une erreur reseau merite
        d'etre visible plutot que masquee par une nouvelle tentative
        silencieuse.

        Args:
            text: Texte du commentaire a juger.
            context: Titre de l'article ou contenu du post. Une
                chaine vide signifie que le contexte est inconnu.

        Returns:
            La decision rendue, avec sa tracabilite complete.
        """
        user_message = build_legal_user_message(text, context)

        attempt = 1
        while True:
            request = ModelRequest(
                model=self.model,
                system=LEGAL_SYSTEM_PROMPT,
                user=user_message,
                prompt_version=LEGAL_PROMPT_VERSION,
                attempt=attempt,
            )
            try:
                response = self.client.complete(request)
            except OpenRouterError as error:
                return fallback_decision(
                    Status.ERREUR,
                    model=self.model,
                    prompt_version=LEGAL_PROMPT_VERSION,
                    attempts=attempt,
                    raw_text=str(error),
                )

            decision = parse_legal_response(
                response.text,
                model=self.model,
                prompt_version=LEGAL_PROMPT_VERSION,
                attempts=attempt,
            )

            if decision.status != Status.MAL_FORME:
                return decision
            if attempt >= self.max_attempts:
                return decision
            attempt += 1
