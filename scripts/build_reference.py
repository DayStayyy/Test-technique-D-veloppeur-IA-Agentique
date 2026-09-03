"""Construit le jeu de reference a annoter.

Assemble les trois strates en un seul CSV de cent lignes : le
tirage aleatoire, la preselection par termes sensibles, et les cas
adverses ecrits a la main. Les cas adverses arrivent deja annotes,
puisqu'ils ont ete ecrits pour porter une qualification precise.

La repartition dev/test est tiree ici, avant toute annotation et
avant tout appel au modele.

Le script refuse d'ecraser un jeu deja annote. Repartir de zero se
demande explicitement.

Usage :
    uv run python scripts/build_reference.py
    uv run python scripts/build_reference.py --force
"""

from __future__ import annotations

import argparse
import random
import sys
import tomllib
from pathlib import Path

from moderation.corpus import CorpusError, CorpusLoader
from moderation.reference import (
    ReferenceError,
    ReferenceRow,
    ReferenceStore,
)
from moderation.sampling import ReferenceSampler

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
ADVERSE_FILE = DATA_DIR / "cas_adverses.toml"
OUTPUT_FILE = DATA_DIR / "jeu_reference.csv"

SEED = 20260903
RANDOM_SIZE = 40
PRESELECTED_SIZE = 40


def load_adverse_rows() -> list[ReferenceRow]:
    """Charge les cas adverses, deja annotes par construction.

    Returns:
        Les lignes correspondantes.

    Raises:
        ReferenceError: Si le fichier est absent, illisible, ou si
            un cas est incomplet.
    """
    if not ADVERSE_FILE.is_file():
        raise ReferenceError(f"Fichier absent : {ADVERSE_FILE}")

    try:
        document = tomllib.loads(ADVERSE_FILE.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ReferenceError(
            f"TOML illisible : {ADVERSE_FILE} ({error})"
        ) from error

    rows: list[ReferenceRow] = []
    for entry in document.get("cas", []):
        missing = {"id", "attendu", "motif", "texte"} - set(entry)
        if missing:
            raise ReferenceError(
                f"Cas adverse incomplet, champs manquants : "
                f"{', '.join(sorted(missing))}"
            )
        rows.append(
            ReferenceRow(
                id=str(entry["id"]),
                strate="adverse",
                split="",
                source="adverse",
                declencheur="",
                contexte=str(entry.get("contexte", "")).strip(),
                texte=str(entry["texte"]).strip(),
                annotation=str(entry["attendu"]),
                motif=str(entry["motif"]),
                doute="oui" if entry.get("doute") else "non",
                note=str(entry.get("pourquoi", "")),
            )
        )
    return rows


def assign_splits(rows: list[ReferenceRow], seed: int) -> None:
    """Repartit les lignes en moities dev et test.

    La repartition est stratifiee : chaque strate est coupee en deux
    separement, pour que les deux moities aient la meme composition.
    Sans cela, la moitie gelee pourrait contenir tous les cas
    adverses et ne mesurer que le rappel.

    Args:
        rows: Lignes du jeu, modifiees sur place.
        seed: Graine du tirage.
    """
    rng = random.Random(seed)
    by_stratum: dict[str, list[ReferenceRow]] = {}
    for row in rows:
        by_stratum.setdefault(row.strate, []).append(row)

    for stratum_rows in by_stratum.values():
        shuffled = list(stratum_rows)
        rng.shuffle(shuffled)
        half = len(shuffled) // 2
        for index, row in enumerate(shuffled):
            row.split = "dev" if index < half else "test"


def main() -> int:
    """Assemble le jeu de reference et l'ecrit sur disque.

    Returns:
        0 si le jeu a ete ecrit, 1 en cas d'erreur ou si un jeu
        annote existe deja sans `--force`.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="écrase un jeu déjà annoté",
    )
    args = parser.parse_args()

    store = ReferenceStore(OUTPUT_FILE)
    if OUTPUT_FILE.is_file() and not args.force:
        existing = store.read()
        done = sum(1 for row in existing if row.annotated)
        manual = sum(
            1 for row in existing if row.annotated and row.strate != "adverse"
        )
        if manual:
            print(
                f"Erreur : {OUTPUT_FILE.name} contient déjà "
                f"{manual} annotations manuelles ({done} lignes "
                "annotées au total). Reconstruire les effacerait. "
                "Utiliser --force pour repartir de zéro.",
                file=sys.stderr,
            )
            return 1

    try:
        corpus = CorpusLoader(DATA_DIR).load_all()
        adverse = load_adverse_rows()
    except (CorpusError, ReferenceError) as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    sampler = ReferenceSampler(seed=SEED)
    try:
        drawn = sampler.sample(corpus, RANDOM_SIZE, PRESELECTED_SIZE)
    except ValueError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    rows = [
        ReferenceRow(
            id=f"{selected.stratum[:4]}-{index:03d}",
            strate=selected.stratum,
            split="",
            source=str(selected.comment.source),
            declencheur=selected.trigger,
            contexte=selected.comment.context.strip(),
            texte=selected.comment.text.strip(),
        )
        for index, selected in enumerate(drawn, start=1)
    ]
    rows.extend(adverse)
    assign_splits(rows, SEED)

    try:
        store.write(rows)
    except ReferenceError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    matches = sampler.count_matches(corpus)
    print(f"Jeu écrit : {OUTPUT_FILE} ({len(rows)} lignes)")
    print(f"Graine : {SEED}")
    print(
        f"Candidats à la présélection sur {len(corpus)} "
        f"commentaires : {matches['avec_appel']} avec appel, "
        f"{matches['sans_appel']} sans appel"
    )
    print()
    for stratum in ("aleatoire", "preselection", "adverse"):
        group = [row for row in rows if row.strate == stratum]
        dev = sum(1 for row in group if row.split == "dev")
        todo = sum(1 for row in group if not row.annotated)
        print(
            f"  {stratum:<14} {len(group):>3} lignes, "
            f"{dev} dev / {len(group) - dev} test, "
            f"{todo} à annoter"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
