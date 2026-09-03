"""Fait juger un lot du jeu de reference par un modele.

Chaque ligne passe par `Moderator.moderate`, adosse au cache disque :
relancer sans rien changer ne coute rien. Le resultat est ecrit dans
`results/`, un fichier par couple modele-version de prompt-split,
pour que la phase d'evaluation compare les decisions du modele a
l'annotation manuelle sans avoir a rejouer les appels.

Ce script ne calcule aucune metrique : il ne fait qu'executer le
lot et compter les statuts obtenus. L'analyse relève de la phase 5.

Usage :
    uv run python scripts/run_batch.py
    uv run python scripts/run_batch.py --split test
    uv run python scripts/run_batch.py --model anthropic/claude-haiku-4.5
    uv run python scripts/run_batch.py --limit 5
"""

from __future__ import annotations

import argparse
import csv
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

OUTPUT_COLUMNS = [
    "id",
    "strate",
    "split",
    "source",
    "contexte",
    "texte",
    "annotation",
    "motif_annotation",
    "doute_annotation",
    "verdict",
    "motif",
    "incertain",
    "justification",
    "status",
    "attempts",
]


def output_path(model: str, split: str) -> Path:
    """Calcule le chemin de sortie d'une execution.

    Args:
        model: Identifiant OpenRouter du modele interroge.
        split: Moitie du jeu traitee.

    Returns:
        Le chemin du fichier de resultats, sous `results/`.
    """
    slug = model.replace("/", "_")
    return RESULTS_DIR / f"{slug}_{LEGAL_PROMPT_VERSION}_{split}.csv"


def run(
    rows: list[ReferenceRow], moderator: Moderator
) -> list[dict[str, object]]:
    """Fait juger chaque ligne par le moderateur.

    Args:
        rows: Lignes du jeu de reference a traiter.
        moderator: Moderateur a interroger.

    Returns:
        Une entree de resultat par ligne, dans l'ordre.
    """
    results: list[dict[str, object]] = []
    for index, row in enumerate(rows, start=1):
        decision = moderator.moderate(row.texte, row.contexte)
        results.append(
            {
                "id": row.id,
                "strate": row.strate,
                "split": row.split,
                "source": row.source,
                "contexte": row.contexte,
                "texte": row.texte,
                "annotation": row.annotation,
                "motif_annotation": row.motif,
                "doute_annotation": row.doute,
                "verdict": decision.verdict.value,
                "motif": decision.motif.value if decision.motif else "",
                "incertain": decision.incertain,
                "justification": decision.justification,
                "status": decision.status.value,
                "attempts": decision.attempts,
            }
        )
        print(
            f"[{index}/{len(rows)}] {row.id} -> "
            f"{decision.verdict.value} ({decision.status.value})"
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


def print_summary(results: list[dict[str, object]]) -> None:
    """Affiche le decompte des statuts et des verdicts obtenus.

    Args:
        results: Resultats de l'execution.
    """
    statuses = Counter(str(r["status"]) for r in results)
    verdicts = Counter(str(r["verdict"]) for r in results)
    attempts = sum(int(r["attempts"]) for r in results)

    print(f"\n{len(results)} lignes traitées, {attempts} appels au total.")
    print("Statuts :", dict(statuses))
    print("Verdicts :", dict(verdicts))


def main() -> int:
    """Execute un lot du jeu de reference et ecrit les resultats.

    Returns:
        0 si le lot a ete traite, 1 en cas d'erreur.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--split",
        choices=["dev", "test"],
        default="dev",
        help="moitié du jeu à traiter (défaut : dev)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"identifiant OpenRouter du modèle (défaut : {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="ne traiter que les N premières lignes du split",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")

    try:
        rows = ReferenceStore(REFERENCE_FILE).read()
    except ReferenceError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    rows = [row for row in rows if row.split == args.split]
    if not rows:
        print(
            f"Erreur : aucune ligne pour le split « {args.split} ».",
            file=sys.stderr,
        )
        return 1
    if args.limit is not None:
        rows = rows[: args.limit]

    try:
        client = OpenRouterClient()
    except OpenRouterError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    moderator = Moderator(client, model=args.model)
    results = run(rows, moderator)

    path = output_path(args.model, args.split)
    write_results(path, results)
    print(f"\nRésultats écrits : {path}")
    print_summary(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
