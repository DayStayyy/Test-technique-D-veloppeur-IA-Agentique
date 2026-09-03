"""Affiche le profil descriptif des deux corpus fournis.

Usage :
    uv run python scripts/profile_corpus.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from moderation.corpus import CorpusError, CorpusLoader
from moderation.profiling import CorpusProfiler

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main() -> int:
    """Charge les corpus et affiche leur profil.

    Returns:
        0 si le profil a pu etre calcule, 1 si un corpus est absent
        ou mal forme.
    """
    loader = CorpusLoader(DATA_DIR)
    profiler = CorpusProfiler()

    try:
        corpora = {
            "articles": loader.load_articles(),
            "posts": loader.load_posts(),
        }
    except CorpusError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    for name, comments in corpora.items():
        print(f"=== {name} ===")
        print(profiler.format_report(profiler.profile(comments)))
        print()

    print("=== ensemble ===")
    everything = corpora["articles"] + corpora["posts"]
    print(profiler.format_report(profiler.profile(everything)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
