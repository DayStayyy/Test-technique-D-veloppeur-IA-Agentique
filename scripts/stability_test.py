"""Mesure la stabilite du modele sur des executions repetees.

Une reponse mise en cache est un seul tirage : elle ne dit rien de
ce que le modele repondrait une autre fois. Ce script force
plusieurs appels reels et independants sur les memes commentaires,
grace au numero de repetition qui differencie la cle de cache, et
mesure le taux d'accord entre ces appels.

Chaque appel est lui-meme mis en cache : relancer ce script sans
rien changer relit les memes N x K reponses sans payer de nouveau.
Ce qui n'est pas cache, c'est la premiere collecte des K reponses
independantes par commentaire — c'est elle qui mesure l'alea reel du
modele, pas le fait de la rejouer ensuite.

Usage :
    uv run python scripts/stability_test.py
    uv run python scripts/stability_test.py --n 20 --k 5
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from moderation.llm import OpenRouterClient, OpenRouterError
from moderation.moderator import DEFAULT_MODEL, Moderator
from moderation.prompts import LEGAL_PROMPT_VERSION
from moderation.reference import ReferenceError, ReferenceRow, ReferenceStore

ROOT = Path(__file__).resolve().parent.parent
REFERENCE_FILE = ROOT / "data" / "jeu_reference.csv"
RESULTS_DIR = ROOT / "results"

DEFAULT_SAMPLE_SIZE = 15
DEFAULT_REPEATS = 5
DEFAULT_SEED = 20260903

OUTPUT_COLUMNS = ["id", "strate", "run", "verdict", "motif", "status"]


def sample_rows(
    rows: list[ReferenceRow], size: int, seed: int
) -> list[ReferenceRow]:
    """Tire un sous-echantillon reproductible du jeu fourni.

    Args:
        rows: Lignes parmi lesquelles tirer.
        size: Nombre de lignes a tirer.
        seed: Graine du tirage.

    Returns:
        Les lignes tirees.

    Raises:
        ValueError: Si `rows` en contient moins que `size`.
    """
    if len(rows) < size:
        raise ValueError(
            f"Échantillon impossible : {len(rows)} lignes disponibles "
            f"pour {size} demandées."
        )
    return random.Random(seed).sample(rows, size)


def run(
    rows: list[ReferenceRow], moderator: Moderator, repeats: int
) -> list[dict[str, object]]:
    """Fait juger chaque ligne plusieurs fois, independamment.

    Args:
        rows: Lignes a soumettre.
        moderator: Moderateur a interroger.
        repeats: Nombre d'appels independants par ligne.

    Returns:
        Une entree par couple (ligne, repetition).
    """
    results: list[dict[str, object]] = []
    total = len(rows) * repeats
    done = 0
    for row in rows:
        for repeat in range(1, repeats + 1):
            decision = moderator.moderate(row.texte, row.contexte, run=repeat)
            results.append(
                {
                    "id": row.id,
                    "strate": row.strate,
                    "run": repeat,
                    "verdict": decision.verdict.value,
                    "motif": decision.motif.value if decision.motif else "",
                    "status": decision.status.value,
                }
            )
            done += 1
            print(
                f"[{done}/{total}] {row.id} run {repeat} -> "
                f"{decision.verdict.value}"
            )
    return results


def write_results(path: Path, results: list[dict[str, object]]) -> None:
    """Ecrit les resultats sur disque.

    Args:
        path: Chemin du fichier de sortie.
        results: Resultats a ecrire.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(results)


def print_summary(results: list[dict[str, object]], repeats: int) -> None:
    """Affiche le taux d'accord par commentaire et dans l'ensemble.

    Le taux d'accord d'un commentaire est la part de ses repetitions
    qui tombent sur le verdict majoritaire. Un commentaire dont les
    K reponses sont identiques vaut 100 % ; un commentaire partage
    en deux verdicts a parts egales vaut 50 %.

    Args:
        results: Resultats de l'execution.
        repeats: Nombre de repetitions par commentaire.
    """
    by_id: dict[str, list[str]] = {}
    for entry in results:
        by_id.setdefault(str(entry["id"]), []).append(str(entry["verdict"]))

    unanimous = 0
    agreement_rates: list[float] = []
    print("\nAccord par commentaire :")
    for comment_id, verdicts in by_id.items():
        majority_count = Counter(verdicts).most_common(1)[0][1]
        rate = majority_count / repeats
        agreement_rates.append(rate)
        if rate == 1.0:
            unanimous += 1
        else:
            print(f"  {comment_id} : {verdicts} -> {rate:.0%} d'accord")

    overall = sum(agreement_rates) / len(agreement_rates)
    print(f"\n{len(by_id)} commentaires, {repeats} appels chacun.")
    print(f"Unanimes sur les {repeats} appels : {unanimous}/{len(by_id)}")
    print(f"Taux d'accord moyen : {overall:.1%}")


def main() -> int:
    """Mesure la stabilite sur un echantillon de la moitie dev.

    Returns:
        0 si la mesure a pu etre executee, 1 en cas d'erreur.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--n",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"nombre de commentaires (défaut : {DEFAULT_SAMPLE_SIZE})",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=DEFAULT_REPEATS,
        help=f"appels indépendants par commentaire (défaut : "
        f"{DEFAULT_REPEATS})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"identifiant OpenRouter du modèle (défaut : {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="graine du tirage de l'échantillon",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")

    try:
        rows = ReferenceStore(REFERENCE_FILE).read()
    except ReferenceError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    dev_rows = [row for row in rows if row.split == "dev"]
    try:
        sample = sample_rows(dev_rows, args.n, args.seed)
    except ValueError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    try:
        client = OpenRouterClient()
    except OpenRouterError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    moderator = Moderator(client, model=args.model)
    results = run(sample, moderator, args.k)

    slug = args.model.replace("/", "_")
    path = RESULTS_DIR / f"{slug}_{LEGAL_PROMPT_VERSION}_stabilite.csv"
    write_results(path, results)
    print(f"\nRésultats écrits : {path}")
    print_summary(results, args.k)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
