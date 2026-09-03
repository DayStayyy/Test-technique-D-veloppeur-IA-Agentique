"""Verifie que les modeles percoivent correctement les emojis.

Le profil des corpus a montre 132 commentaires sans aucune lettre,
reduits a des emojis. Un emoji n'est pas un ornement : il peut
porter a lui seul le sens d'un commentaire, y compris un sens
illicite. Avant de decider comment le pipeline les traite, il faut
savoir si les modeles les recoivent intacts.

On envoie donc des emojis choisis pour leurs difficultes d'encodage
et on demande au modele de nommer ce qu'il a recu, sans interpreter.

Usage :
    uv run python scripts/emoji_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

from moderation.llm import (
    ModelRequest,
    OpenRouterClient,
    OpenRouterError,
)

ROOT = Path(__file__).resolve().parent.parent

PROMPT_VERSION = "emoji-percept-v1"

SYSTEM_PROMPT = """\
Tu recois un message. Decris exactement ce que tu as recu, sans
interpreter le sens et sans commenter.

Pour chaque emoji, donne son nom en francais. Si tu ne recois aucun
emoji, renvoie une liste vide.

Reponds uniquement par un objet JSON, sans texte autour :
{"emojis": ["nom", ...], "texte": "le texte hors emojis"}
"""

MODELS = [
    "anthropic/claude-haiku-4.5",
    "openai/gpt-5.6-luna",
    "mistralai/ministral-14b-2512",
]

# Chaque cas isole une difficulte d'encodage differente : caractere
# simple, repetition, paire de substitution regionale, sequence
# jointe par ZWJ, modificateur de teinte, emoji a charge potentielle,
# et melange avec du texte.
CASES: list[tuple[str, str]] = [
    ("simple", "\U0001f346"),
    ("repetition", "\U0001f605\U0001f605\U0001f605"),
    ("drapeau", "\U0001f1eb\U0001f1f7"),
    ("sequence_zwj", "\U0001f468‍\U0001f469‍\U0001f467"),
    ("teinte", "\U0001f44d\U0001f3ff"),
    ("charge", "\U0001f412"),
    ("melange", "Bravo \U0001f44f quelle honte \U0001f92e"),
]


def main() -> int:
    """Soumet chaque cas a chaque modele et affiche les reponses.

    Returns:
        0 si la campagne a pu etre executee, 1 si aucune cle API
        n'est disponible.
    """
    load_dotenv(ROOT / ".env")

    try:
        client = OpenRouterClient()
    except OpenRouterError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    for model in MODELS:
        print(f"=== {model} ===")
        for case_id, payload in CASES:
            request = ModelRequest(
                model=model,
                system=SYSTEM_PROMPT,
                user=payload,
                prompt_version=PROMPT_VERSION,
            )
            try:
                answer = " ".join(client.complete(request).text.split())
            except OpenRouterError as error:
                answer = f"ERREUR {error}"
            print(f"  {case_id:<14} envoye : {payload}")
            print(f"  {'':<14} recu   : {answer[:200]}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
