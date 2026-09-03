"""Jeu de reference annote a la main.

Le jeu tient dans un seul fichier CSV de cent lignes. Chaque ligne
porte le commentaire, son contexte, sa strate d'origine, la moitie
dev ou test a laquelle elle appartient, et l'annotation manuelle.

L'annotation porte deux informations distinctes : la decision, et un
indicateur de doute de l'annotateur. Ce doute sera croise avec
l'incertitude declaree par le modele, pour mesurer si celui-ci
hesite la ou un humain hesite.

La repartition dev/test est fixee a la construction, avant toute
annotation et avant tout appel au modele. Personne ne peut donc la
choisir apres coup en fonction des resultats.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, fields
from pathlib import Path

LEGAL_MOTIFS: tuple[str, ...] = (
    "provocation_haine",
    "injure_raciale",
    "contestation_crimes_humanite",
    "apologie_terrorisme",
    "pedopornographie",
)

DECISIONS: tuple[str, ...] = ("acceptable", "rejete")

DEV_SPLIT = "dev"
TEST_SPLIT = "test"


class ReferenceError(RuntimeError):
    """Jeu de reference introuvable, mal forme ou incoherent."""


@dataclass(slots=True)
class ReferenceRow:
    """Une ligne du jeu de reference.

    Attributes:
        id: Identifiant stable de la ligne.
        strate: `aleatoire`, `preselection` ou `adverse`.
        split: `dev` pour le cadrage du prompt, `test` pour la
            moitie gelee.
        source: Canal d'origine, ou `adverse` pour un cas ecrit a la
            main.
        declencheur: Terme sensible ayant motive la preselection.
            Vide pour les autres strates.
        contexte: Titre d'article ou contenu du post.
        texte: Texte du commentaire a juger.
        annotation: Decision manuelle, `acceptable` ou `rejete`.
            Vide tant que la ligne n'est pas annotee.
        motif: Motif legal retenu si la decision est `rejete`.
        doute: `oui` si l'annotateur n'est pas certain, sinon `non`.
            Vide tant que la ligne n'est pas annotee.
        note: Commentaire libre de l'annotateur.
    """

    id: str
    strate: str
    split: str
    source: str
    declencheur: str
    contexte: str
    texte: str
    annotation: str = ""
    motif: str = ""
    doute: str = ""
    note: str = ""

    @property
    def annotated(self) -> bool:
        """Indique si la ligne porte deja une annotation.

        Returns:
            True si la decision manuelle est renseignee.
        """
        return bool(self.annotation)

    def validate(self) -> None:
        """Verifie la coherence interne de la ligne annotee.

        Une ligne non annotee est toujours valide : elle est
        simplement en attente.

        Raises:
            ReferenceError: Si la decision, le motif ou le doute
                prennent une valeur interdite, ou si le motif
                contredit la decision.
        """
        if not self.annotated:
            return
        if self.annotation not in DECISIONS:
            raise ReferenceError(
                f"{self.id} : décision « {self.annotation} » "
                f"inconnue, attendu {' ou '.join(DECISIONS)}."
            )
        if self.doute not in ("oui", "non"):
            raise ReferenceError(
                f"{self.id} : doute « {self.doute} » inconnu, "
                "attendu oui ou non."
            )
        if self.annotation == "rejete":
            if self.motif not in LEGAL_MOTIFS:
                raise ReferenceError(
                    f"{self.id} : motif « {self.motif} » absent de "
                    "la taxonomie fermée."
                )
        elif self.motif:
            raise ReferenceError(
                f"{self.id} : décision acceptable, le motif doit "
                f"rester vide (trouvé « {self.motif} »)."
            )


class ReferenceStore:
    """Lecture et ecriture du jeu de reference sur disque.

    Le fichier est ecrit en UTF-8 avec marque d'ordre, pour qu'un
    tableur l'ouvre sans casser les accents.

    Attributes:
        path: Chemin du fichier CSV.
    """

    ENCODING = "utf-8-sig"

    def __init__(self, path: Path) -> None:
        """Initialise le depot.

        Args:
            path: Chemin du fichier CSV du jeu de reference.
        """
        self.path = path

    @property
    def columns(self) -> list[str]:
        """Donne l'ordre des colonnes du fichier.

        Returns:
            Les noms de colonnes, dans l'ordre d'ecriture.
        """
        return [field.name for field in fields(ReferenceRow)]

    def write(self, rows: list[ReferenceRow]) -> None:
        """Ecrit le jeu complet, en remplacant le fichier existant.

        Args:
            rows: Lignes a ecrire.

        Raises:
            ReferenceError: Si l'ecriture sur disque echoue.
        """
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open(
                "w", encoding=self.ENCODING, newline=""
            ) as handle:
                writer = csv.DictWriter(handle, self.columns)
                writer.writeheader()
                for row in rows:
                    writer.writerow(asdict(row))
        except OSError as error:
            raise ReferenceError(
                f"Écriture impossible : {self.path}"
            ) from error

    def read(self) -> list[ReferenceRow]:
        """Relit le jeu depuis le disque.

        Returns:
            Les lignes du fichier, dans l'ordre.

        Raises:
            ReferenceError: Si le fichier est absent, si une colonne
                manque, ou si une ligne annotee est incoherente.
        """
        if not self.path.is_file():
            raise ReferenceError(f"Jeu de référence introuvable : {self.path}")

        with self.path.open(encoding=self.ENCODING, newline="") as fh:
            reader = csv.DictReader(fh)
            missing = set(self.columns) - set(reader.fieldnames or [])
            if missing:
                raise ReferenceError(
                    "Colonnes manquantes dans "
                    f"{self.path.name} : {', '.join(sorted(missing))}"
                )
            rows = [
                ReferenceRow(**{key: entry[key] for key in self.columns})
                for entry in reader
            ]

        for row in rows:
            row.validate()
        return rows
