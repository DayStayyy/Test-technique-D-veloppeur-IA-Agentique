"""Tests de niveau un pour le parsing des reponses de modele.

Couvre les quatre etats de sortie actes en phase 2 : valide, mal
formee, refus, erreur. Le quatrieme, erreur reseau, n'a pas de texte
a interpreter et est donc couvert cote `Moderator`, pas ici.
"""

from __future__ import annotations

from moderation.decision import Motif, Status, Verdict
from moderation.parsing import (
    extract_json,
    looks_like_refusal,
    parse_legal_response,
)

_KWARGS = {
    "model": "modele-test",
    "prompt_version": "legal-v1",
    "attempts": 1,
}


def test_reponse_valide_acceptable() -> None:
    """Un JSON conforme, décision acceptable, est reconnu."""
    text = (
        '{"decision": "acceptable", "motif": null, '
        '"justification": "aucun appel", "incertain": false}'
    )
    decision = parse_legal_response(text, **_KWARGS)
    assert decision.status == Status.VALIDE
    assert decision.verdict == Verdict.ACCEPTABLE
    assert decision.motif is None
    assert decision.incertain is False


def test_reponse_valide_rejete() -> None:
    """Un JSON conforme, décision rejetée, porte son motif."""
    text = (
        '{"decision": "rejete", "motif": "apologie_terrorisme", '
        '"justification": "appel explicite", "incertain": true}'
    )
    decision = parse_legal_response(text, **_KWARGS)
    assert decision.status == Status.VALIDE
    assert decision.verdict == Verdict.REJETE
    assert decision.motif == Motif.APOLOGIE_TERRORISME
    assert decision.incertain is True


def test_reponse_sous_balises_markdown() -> None:
    """Un JSON entouré de balises ```json est extrait correctement.

    Haiku et Ministral produisent systématiquement ce format.
    """
    text = (
        "```json\n"
        '{"decision": "acceptable", "motif": null, '
        '"justification": "ok", "incertain": false}\n'
        "```"
    )
    decision = parse_legal_response(text, **_KWARGS)
    assert decision.status == Status.VALIDE
    assert decision.verdict == Verdict.ACCEPTABLE


def test_json_absent_est_mal_forme() -> None:
    """Une réponse sans JSON exploitable est mal formée."""
    decision = parse_legal_response("Je pense que oui.", **_KWARGS)
    assert decision.status == Status.MAL_FORME
    assert decision.verdict == Verdict.ACCEPTABLE


def test_motif_hors_taxonomie_est_mal_forme() -> None:
    """Un motif absent de la liste fermée est une réponse mal formée."""
    text = (
        '{"decision": "rejete", "motif": "diffamation", '
        '"justification": "x", "incertain": false}'
    )
    decision = parse_legal_response(text, **_KWARGS)
    assert decision.status == Status.MAL_FORME


def test_rejete_sans_motif_est_mal_forme() -> None:
    """Un rejet sans motif contredit le schéma, donc mal formé."""
    text = (
        '{"decision": "rejete", "motif": null, '
        '"justification": "x", "incertain": false}'
    )
    decision = parse_legal_response(text, **_KWARGS)
    assert decision.status == Status.MAL_FORME


def test_acceptable_avec_motif_est_mal_forme() -> None:
    """Une acceptation portant un motif contredit le schéma."""
    text = (
        '{"decision": "acceptable", "motif": "provocation_haine", '
        '"justification": "x", "incertain": false}'
    )
    decision = parse_legal_response(text, **_KWARGS)
    assert decision.status == Status.MAL_FORME


def test_reponse_vide_est_un_refus() -> None:
    """Une réponse vide est traitée comme un refus.

    C'est ainsi que se manifeste un filtre déclenché en amont du
    modèle, avant même qu'il ne voie le texte.
    """
    decision = parse_legal_response("   ", **_KWARGS)
    assert decision.status == Status.REFUS
    assert decision.verdict == Verdict.ACCEPTABLE


def test_marqueur_de_refus_explicite() -> None:
    """Une réponse portant un marqueur de refus est reconnue comme telle."""
    decision = parse_legal_response(
        "Je ne peux pas vous aider avec cette demande.", **_KWARGS
    )
    assert decision.status == Status.REFUS


def test_decision_par_defaut_reste_acceptable() -> None:
    """Quel que soit l'état non valide, le verdict par défaut est acceptable.

    Rejeter par défaut rendrait le système plus restrictif que la loi
    dès qu'un appel échoue, ce que la consigne interdit.
    """
    for text in ("", "texte sans JSON", "je ne peux pas répondre"):
        decision = parse_legal_response(text, **_KWARGS)
        assert decision.verdict == Verdict.ACCEPTABLE
        assert decision.motif is None


def test_extract_json_avec_texte_autour() -> None:
    """Le JSON est retrouvé même entouré de texte explicatif."""
    payload = extract_json('Voici : {"a": 1} merci')
    assert payload == {"a": 1}


def test_extract_json_absent() -> None:
    """L'absence de JSON renvoie None plutôt que de lever."""
    assert extract_json("aucun json ici") is None


def test_looks_like_refusal_insensible_a_la_casse() -> None:
    """La détection de refus ignore la casse."""
    assert looks_like_refusal("JE NE PEUX PAS vous aider") is True
    assert looks_like_refusal("Ceci est un commentaire normal.") is False
