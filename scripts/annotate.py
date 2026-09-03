"""Annotation manuelle du jeu de reference.

Affiche un commentaire a la fois et attend une reponse. Quatre
reponses sont possibles, croisant la decision et le doute de
l'annotateur. Ce doute sera ensuite compare a l'incertitude declaree
par le modele, pour mesurer si celui-ci hesite la ou un humain
hesite.

L'annotation doit etre faite AVANT tout appel au modele. La
regarder apres reviendrait a ajuster la verite terrain sur les
reponses obtenues, et priverait de sens toutes les mesures.

Le fichier est reecrit apres chaque reponse : interrompre la session
ne perd rien, et la relancer reprend ou elle s'etait arretee.

Usage :
    uv run python scripts/annotate.py
    uv run python scripts/annotate.py --strate preselection
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

from moderation.reference import (
    LEGAL_MOTIFS,
    ReferenceError,
    ReferenceRow,
    ReferenceStore,
)

ROOT = Path(__file__).resolve().parent.parent
REFERENCE_FILE = ROOT / "data" / "jeu_reference.csv"

WIDTH = 72

AIDE = """\
LES TROIS TESTS

1. Y a-t-il un appel ?
   La loi punit la provocation : un appel ou une exhortation a
   agir ou a hair. L'appel peut etre voile, il compte quand meme
   si son sens ne fait aucun doute. Mais un propos seulement
   hostile, meprisant ou outrageant, sans aucun appel, n'est PAS
   une provocation.

2. La cible, personnes ou idee ?
   Sont protegees les personnes visees pour leur origine, ethnie,
   nationalite, religion, sexe, orientation, identite de genre ou
   handicap. Ne sont pas proteges : les religions, ideologies,
   partis, gouvernements, institutions, professions,
   personnalites publiques.

3. Apologie ou constat ?
   Presenter un crime comme legitime ou glorieux est une
   apologie. L'expliquer ou le dire previsible n'en est pas une,
   meme dit de facon indecente.

EN CAS DE DOUTE
   Le standard est « MANIFESTEMENT illicite ». Si tu hesites, la
   reponse est licite, avec le doute signale (touche 4).

NE SONT JAMAIS REJETES
   La vulgarite, les insultes, la critique virulente d'une
   religion, d'un parti ou d'un elu, les opinions hostiles a
   l'immigration, l'ironie, la diffamation et l'injure envers une
   personne identifiee, le spam.
"""

CHOICES = {
    "1": ("rejete", "non"),
    "2": ("rejete", "oui"),
    "3": ("acceptable", "non"),
    "4": ("acceptable", "oui"),
}

MENU = """\
  1  illegal                 2  illegal, mais doute
  3  licite                  4  licite, mais doute
  n  ajouter une note        p  revenir au precedent
  s  sauter                  ?  rappel des regles
  q  quitter et sauvegarder"""


class Annotator:
    """Session d'annotation sur un jeu de reference.

    Attributes:
        store: Depot du jeu de reference.
        rows: Toutes les lignes du jeu.
        worklist: Lignes restant a annoter, dans l'ordre.
    """

    def __init__(
        self, store: ReferenceStore, rows: list[ReferenceRow]
    ) -> None:
        """Initialise la session.

        Args:
            store: Depot ou reecrire le jeu apres chaque reponse.
            rows: Toutes les lignes du jeu.
        """
        self.store = store
        self.rows = rows
        self.worklist: list[ReferenceRow] = []

    def run(self, worklist: list[ReferenceRow]) -> None:
        """Deroule la session sur les lignes fournies.

        Args:
            worklist: Lignes a annoter, dans l'ordre de traitement.
        """
        self.worklist = worklist
        index = 0
        while index < len(self.worklist):
            row = self.worklist[index]
            self._show(row, index)
            action = self._ask(row)
            if action == "quit":
                break
            if action == "back":
                index = max(0, index - 1)
                continue
            index += 1

        done = sum(1 for row in self.rows if row.annotated)
        print(f"\n{done} lignes annotées sur {len(self.rows)}.")
        remaining = len(self.worklist) - sum(
            1 for row in self.worklist if row.annotated
        )
        if remaining:
            print(f"{remaining} restent à faire.")

    def _show(self, row: ReferenceRow, index: int) -> None:
        """Affiche un commentaire et son contexte.

        Args:
            row: Ligne a presenter.
            index: Position dans la liste de travail.
        """
        position = f"{index + 1}/{len(self.worklist)}"
        print("\n" + "=" * WIDTH)
        header = f"{position}   {row.strate}   {row.source}"
        if row.declencheur:
            header += f"   terme : {row.declencheur}"
        print(header)
        print("=" * WIDTH)

        if row.contexte:
            print("\nCONTEXTE")
            print(self._wrap(row.contexte, limit=300))

        print("\nCOMMENTAIRE")
        print(self._wrap(row.texte))
        print()

    def _ask(self, row: ReferenceRow) -> str:
        """Recueille la reponse de l'annotateur pour une ligne.

        Args:
            row: Ligne en cours d'annotation.

        Returns:
            `next` pour avancer, `back` pour revenir, `quit` pour
            arreter la session.
        """
        while True:
            print(MENU)
            try:
                answer = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return "quit"

            if answer == "q":
                return "quit"
            if answer == "p":
                return "back"
            if answer == "s":
                return "next"
            if answer == "?":
                print("\n" + AIDE)
                continue
            if answer == "n":
                row.note = input("note : ").strip()
                self._save()
                continue
            if answer in CHOICES:
                decision, doubt = CHOICES[answer]
                motif = ""
                if decision == "rejete":
                    motif = self._ask_motif()
                    if not motif:
                        continue
                row.annotation = decision
                row.motif = motif
                row.doute = doubt
                self._save()
                return "next"

            print("Réponse inconnue.")

    def _ask_motif(self) -> str:
        """Demande le motif legal d'un rejet.

        Returns:
            Le motif choisi, ou une chaine vide si l'annotateur
            renonce et revient au menu.
        """
        print()
        for number, motif in enumerate(LEGAL_MOTIFS, start=1):
            print(f"  {number}  {motif}")
        print("  0  annuler")
        while True:
            try:
                answer = input("motif > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return ""
            if answer == "0":
                return ""
            if answer.isdigit() and 1 <= int(answer) <= len(LEGAL_MOTIFS):
                return LEGAL_MOTIFS[int(answer) - 1]
            print("Motif inconnu.")

    def _save(self) -> None:
        """Reecrit le jeu complet sur disque.

        Raises:
            ReferenceError: Si l'ecriture echoue.
        """
        self.store.write(self.rows)

    @staticmethod
    def _wrap(text: str, limit: int = 2000) -> str:
        """Met un texte en forme pour l'affichage.

        Args:
            text: Texte a presenter.
            limit: Longueur maximale avant troncature.

        Returns:
            Le texte replie a la largeur d'affichage, tronque si
            necessaire.
        """
        shortened = text[:limit]
        if len(text) > limit:
            shortened += " […]"
        lines = []
        for paragraph in shortened.splitlines():
            lines.extend(textwrap.wrap(paragraph, width=WIDTH) or [""])
        return "\n".join(f"  {line}" for line in lines)


def main() -> int:
    """Ouvre le jeu de reference et lance l'annotation.

    Returns:
        0 si la session s'est deroulee, 1 si le jeu est introuvable
        ou incoherent.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strate",
        choices=["aleatoire", "preselection", "adverse"],
        help="n'annoter qu'une seule strate",
    )
    parser.add_argument(
        "--tout",
        action="store_true",
        help="repasser aussi sur les lignes déjà annotées",
    )
    args = parser.parse_args()

    store = ReferenceStore(REFERENCE_FILE)
    try:
        rows = store.read()
    except ReferenceError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    worklist = [
        row
        for row in rows
        if (args.tout or not row.annotated)
        and (args.strate is None or row.strate == args.strate)
    ]
    if not worklist:
        print("Rien à annoter.")
        return 0

    print(f"{len(worklist)} lignes à annoter.")
    print("Tape ? pour revoir les règles, q pour arrêter.")
    Annotator(store, rows).run(worklist)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
