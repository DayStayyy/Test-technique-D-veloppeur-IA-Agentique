"""Tests de niveau un pour la fonction de moderation.

Aucun appel reseau : `FakeClient` (conftest.py) rend des reponses
pre-enregistrees. Couvre le retry sur reponse mal formee et son
absence sur refus ou erreur reseau.
"""

from __future__ import annotations

import pytest

from moderation.decision import Status, Verdict
from moderation.llm import OpenRouterError
from moderation.moderator import Moderator
from tests.conftest import FakeClient

_VALIDE_ACCEPTABLE = (
    '{"decision": "acceptable", "motif": null, '
    '"justification": "aucun appel", "incertain": false}'
)
_VALIDE_REJETE = (
    '{"decision": "rejete", "motif": "provocation_haine", '
    '"justification": "appel explicite", "incertain": false}'
)


def test_reponse_valide_du_premier_coup() -> None:
    """Une réponse valide ne déclenche qu'un seul appel."""
    client = FakeClient([_VALIDE_ACCEPTABLE])
    moderator = Moderator(client, model="modele-test")

    decision = moderator.moderate("un commentaire")

    assert decision.status == Status.VALIDE
    assert decision.verdict == Verdict.ACCEPTABLE
    assert decision.attempts == 1
    assert len(client.requests) == 1


def test_rejet_valide_porte_son_motif() -> None:
    """Un rejet valide conserve son motif et son statut."""
    client = FakeClient([_VALIDE_REJETE])
    moderator = Moderator(client, model="modele-test")

    decision = moderator.moderate("un commentaire illicite")

    assert decision.verdict == Verdict.REJETE
    assert decision.motif is not None
    assert decision.motif.value == "provocation_haine"


def test_retry_sur_reponse_mal_formee_puis_succes() -> None:
    """Une réponse mal formée est retentée une fois, avec succès."""
    client = FakeClient(["ceci n'est pas du JSON", _VALIDE_ACCEPTABLE])
    moderator = Moderator(client, model="modele-test", max_attempts=2)

    decision = moderator.moderate("un commentaire")

    assert decision.status == Status.VALIDE
    assert decision.attempts == 2
    assert len(client.requests) == 2
    # Chaque tentative porte un numero distinct, pour que le cache
    # ne renvoie pas la premiere reponse mal formee a la seconde.
    assert client.requests[0].attempt == 1
    assert client.requests[1].attempt == 2


def test_retry_epuise_reste_mal_forme() -> None:
    """Deux réponses mal formées de suite épuisent les tentatives."""
    client = FakeClient(["pas de json", "toujours pas de json"])
    moderator = Moderator(client, model="modele-test", max_attempts=2)

    decision = moderator.moderate("un commentaire")

    assert decision.status == Status.MAL_FORME
    assert decision.verdict == Verdict.ACCEPTABLE
    assert decision.attempts == 2
    assert len(client.requests) == 2


def test_max_attempts_un_desactive_le_retry() -> None:
    """Avec max_attempts=1, une réponse mal formée n'est pas retentée."""
    client = FakeClient(["pas de json"])
    moderator = Moderator(client, model="modele-test", max_attempts=1)

    decision = moderator.moderate("un commentaire")

    assert decision.status == Status.MAL_FORME
    assert len(client.requests) == 1


def test_refus_n_est_jamais_retente() -> None:
    """Un refus explicite du modèle n'est pas retenté.

    Le modèle referait le même refus : le retry ne sert que la
    réponse mal formée.
    """
    client = FakeClient(["Je ne peux pas vous aider.", _VALIDE_ACCEPTABLE])
    moderator = Moderator(client, model="modele-test", max_attempts=3)

    decision = moderator.moderate("un commentaire")

    assert decision.status == Status.REFUS
    assert decision.attempts == 1
    assert len(client.requests) == 1


def test_erreur_reseau_n_est_pas_retentee() -> None:
    """Une erreur réseau produit un statut ERREUR sans nouvel appel."""
    client = FakeClient([OpenRouterError("panne simulée")])
    moderator = Moderator(client, model="modele-test", max_attempts=3)

    decision = moderator.moderate("un commentaire")

    assert decision.status == Status.ERREUR
    assert decision.verdict == Verdict.ACCEPTABLE
    assert len(client.requests) == 1


def test_max_attempts_sous_un_leve() -> None:
    """max_attempts doit être au moins 1."""
    client = FakeClient([])
    with pytest.raises(ValueError):
        Moderator(client, max_attempts=0)
