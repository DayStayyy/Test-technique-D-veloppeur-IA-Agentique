"""Execute le test de refus sur les modeles candidats.

Usage :
    uv run python scripts/refusal_test.py

Necessite OPENROUTER_API_KEY, lu depuis le fichier .env a la racine.
Les reponses sont mises en cache : une seconde execution ne
declenche aucun appel reseau.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from moderation.llm import OpenRouterClient, OpenRouterError
from moderation.refusal import (
    Outcome,
    RefusalResult,
    RefusalTester,
    load_cases,
)

ROOT = Path(__file__).resolve().parent.parent
CASES_FILE = ROOT / "data" / "test_refus.toml"

CANDIDATE_MODELS = [
    "anthropic/claude-haiku-4.5",
    "openai/gpt-5.6-luna",
    "mistralai/ministral-14b-2512",
]


def format_summary(results: list[RefusalResult]) -> str:
    """Met en forme le decompte des issues par modele.

    Args:
        results: Resultats de la campagne.

    Returns:
        Un tableau texte, une ligne par modele.
    """
    per_model: dict[str, Counter[str]] = {}
    for result in results:
        per_model.setdefault(result.model, Counter())
        per_model[result.model][str(result.outcome)] += 1

    columns = [str(outcome) for outcome in Outcome]
    header = f"{'modele':<32}" + "".join(f"{name:>11}" for name in columns)
    lines = [header, "-" * len(header)]
    for model, counts in per_model.items():
        row = f"{model:<32}" + "".join(
            f"{counts[name]:>11}" for name in columns
        )
        lines.append(row)
    return "\n".join(lines)


def format_details(results: list[RefusalResult]) -> str:
    """Met en forme le detail de chaque appel.

    Args:
        results: Resultats de la campagne.

    Returns:
        Une ligne par appel, avec la reponse tronquee.
    """
    lines: list[str] = []
    for result in results:
        origin = "cache" if result.from_cache else "reseau"
        lines.append(
            f"[{result.model}] {result.case_id} -> {result.outcome} ({origin})"
        )
        lines.append(f"    {result.detail}")
    return "\n".join(lines)


def main() -> int:
    """Lance le test de refus et affiche les resultats.

    Returns:
        0 si la campagne a pu etre executee, 1 si les cas sont
        illisibles ou si aucune cle API n'est disponible.
    """
    load_dotenv(ROOT / ".env")

    try:
        cases = load_cases(CASES_FILE)
    except (FileNotFoundError, ValueError) as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    try:
        client = OpenRouterClient()
    except OpenRouterError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    results = RefusalTester(client).run(CANDIDATE_MODELS, cases)

    print(f"{len(cases)} cas x {len(CANDIDATE_MODELS)} modeles\n")
    print(format_summary(results))
    print()
    print(format_details(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
