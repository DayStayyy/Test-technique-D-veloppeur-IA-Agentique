"""Tests de niveau un pour l'objet de decision."""

from __future__ import annotations

import pytest

from moderation.decision import (
    Decision,
    DecisionError,
    Motif,
    Status,
    Verdict,
)


def _make(
    verdict: Verdict,
    motif: Motif | None,
    attempts: int = 1,
) -> Decision:
    """Construit une decision minimale pour les tests.

    Args:
        verdict: Decision binaire.
        motif: Motif legal, ou None.
        attempts: Nombre de tentatives.

    Returns:
        La decision construite.
    """
    return Decision(
        verdict=verdict,
        motif=motif,
        motifs_editoriaux=(),
        justification="test",
        incertain=False,
        status=Status.VALIDE,
        model="modele-test",
        prompt_version="v1",
        attempts=attempts,
    )


def test_rejete_avec_motif_est_valide() -> None:
    """Un rejet avec motif ne leve aucune erreur."""
    decision = _make(Verdict.REJETE, Motif.PROVOCATION_HAINE)
    assert decision.rejete is True


def test_acceptable_sans_motif_est_valide() -> None:
    """Une acceptation sans motif ne leve aucune erreur."""
    decision = _make(Verdict.ACCEPTABLE, None)
    assert decision.rejete is False


def test_rejete_sans_motif_leve() -> None:
    """Un rejet sans motif est une incohérence rejetée."""
    with pytest.raises(DecisionError):
        _make(Verdict.REJETE, None)


def test_acceptable_avec_motif_leve() -> None:
    """Une acceptation portant un motif est une incohérence."""
    with pytest.raises(DecisionError):
        _make(Verdict.ACCEPTABLE, Motif.APOLOGIE_TERRORISME)


def test_attempts_sous_un_leve() -> None:
    """Un nombre de tentatives nul ou négatif est rejeté."""
    with pytest.raises(DecisionError):
        _make(Verdict.ACCEPTABLE, None, attempts=0)
