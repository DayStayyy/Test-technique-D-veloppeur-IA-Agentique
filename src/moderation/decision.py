"""Objet de decision retourne par la fonction de moderation.

Cinq champs, actes en phase 2 : decision binaire, motif legal issu
d'une liste fermee, motifs editoriaux, justification en une phrase,
indicateur d'incertitude en metadonnee qui n'influence jamais la
decision.

Le perimetre etant reduit au legal (phase 2), les motifs editoriaux
restent toujours vides et ne sont pas demandes au modele. Le champ
est conserve pour marquer la frontiere de ce qu'on a choisi de ne
pas faire.

La taxonomie definie ici est la source unique du projet : le prompt
legal, le jeu de reference et le parsing des reponses s'y referent
tous, pour qu'une correction de la liste ne se fasse qu'a un seul
endroit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Motif(StrEnum):
    """Motif legal de rejet, liste fermee.

    Fondee sur le standard « manifestement illicite ». L'ordre suit
    celui du prompt legal, sans signification particuliere.
    """

    PROVOCATION_HAINE = "provocation_haine"
    INJURE_RACIALE = "injure_raciale"
    CONTESTATION_CRIMES_HUMANITE = "contestation_crimes_humanite"
    APOLOGIE_TERRORISME = "apologie_terrorisme"
    PEDOPORNOGRAPHIE = "pedopornographie"


class Verdict(StrEnum):
    """Decision binaire rendue sur un commentaire."""

    ACCEPTABLE = "acceptable"
    REJETE = "rejete"


class Status(StrEnum):
    """Etat de la reponse du modele ayant produit la decision.

    Quatre etats, actes en phase 2 pour le premier niveau de tests.
    Une decision au statut autre que VALIDE n'a pas ete jugee par le
    modele : sa valeur `verdict` est alors une valeur par defaut
    documentee, jamais un verdict que le modele aurait rendu.
    """

    VALIDE = "valide"
    MAL_FORME = "mal_forme"
    REFUS = "refus"
    ERREUR = "erreur"


class DecisionError(ValueError):
    """Objet de decision incoherent."""


@dataclass(frozen=True, slots=True)
class Decision:
    """Verdict rendu sur un commentaire, avec sa tracabilite.

    Attributes:
        verdict: Decision binaire. Vaut `Verdict.ACCEPTABLE` par
            defaut quand `status` n'est pas `Status.VALIDE` : un
            systeme qui n'a pas pu obtenir de jugement ne doit pas
            devenir plus restrictif que la loi de son propre chef.
        motif: Motif legal si `verdict` est `REJETE`, sinon None.
        motifs_editoriaux: Toujours vide tant que le perimetre est
            reduit au legal. Conserve pour marquer la frontiere de
            ce qui n'est pas traite.
        justification: Justification en une phrase. Vide si
            `status` n'est pas `Status.VALIDE`.
        incertain: Incertitude declaree par le modele. N'influence
            jamais `verdict`. Vaut False quand `status` n'est pas
            `Status.VALIDE`, faute de valeur produite par le modele.
        status: Etat de la reponse ayant produit cette decision.
        model: Identifiant OpenRouter du modele interroge.
        prompt_version: Version du prompt legal utilise.
        attempts: Nombre de tentatives effectuees, au moins 1.
        raw_text: Dernier texte brut renvoye par le modele, pour
            audit. Vide si aucun appel n'a abouti.
    """

    verdict: Verdict
    motif: Motif | None
    motifs_editoriaux: tuple[str, ...]
    justification: str
    incertain: bool
    status: Status
    model: str
    prompt_version: str
    attempts: int
    raw_text: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        """Verifie la coherence interne de la decision.

        Raises:
            DecisionError: Si le motif contredit le verdict, ou si
                `attempts` est inferieur a 1.
        """
        if self.verdict == Verdict.REJETE and self.motif is None:
            raise DecisionError(
                "Un verdict rejete doit porter un motif légal."
            )
        if self.verdict == Verdict.ACCEPTABLE and self.motif is not None:
            raise DecisionError(
                f"Un verdict acceptable ne peut pas porter de motif "
                f"(trouvé « {self.motif} »)."
            )
        if self.attempts < 1:
            raise DecisionError(
                f"attempts doit être au moins 1 (trouvé {self.attempts})."
            )

    @property
    def rejete(self) -> bool:
        """Indique si le commentaire est rejeté.

        Returns:
            True si `verdict` vaut `Verdict.REJETE`.
        """
        return self.verdict == Verdict.REJETE
