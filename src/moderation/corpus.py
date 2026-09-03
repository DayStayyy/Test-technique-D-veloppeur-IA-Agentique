"""Chargement des corpus de commentaires fournis.

Les deux fichiers CSV n'ont pas le meme schema. Les commentaires
d'articles portent un titre d'article et des thematiques, les
commentaires de posts portent le contenu du post. Ce module les
ramene a une representation unique, ou le contexte editorial occupe
un seul champ quel que soit le canal.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Source(StrEnum):
    """Canal d'origine d'un commentaire."""

    ARTICLE = "article"
    POST = "post"


@dataclass(frozen=True, slots=True)
class Comment:
    """Un commentaire et son contexte, independamment du canal.

    Attributes:
        text: Texte du commentaire, tel que publie.
        context: Contexte editorial auquel le commentaire repond.
            Titre de l'article pour un commentaire d'article,
            contenu du post pour un commentaire de post. Chaine vide
            si la source ne fournit pas de contexte.
        source: Canal d'origine du commentaire.
        tags: Thematiques associees a l'article. Toujours vide pour
            un commentaire de post.
    """

    text: str
    context: str
    source: Source
    tags: tuple[str, ...] = ()


class CorpusError(RuntimeError):
    """Corpus introuvable ou schema inattendu."""


class CorpusLoader:
    """Charge les CSV fournis vers une liste de `Comment`.

    Attributes:
        data_dir: Repertoire contenant les deux fichiers CSV.
    """

    ARTICLE_FILE = "article_comments.csv"
    POST_FILE = "post_comments.csv"

    _ARTICLE_COLUMNS = frozenset(
        {"text", "tags", "article_title", "source_type"}
    )
    _POST_COLUMNS = frozenset({"text", "post_content", "source_type"})

    def __init__(self, data_dir: Path) -> None:
        """Initialise le chargeur.

        Args:
            data_dir: Repertoire contenant les fichiers CSV fournis.
        """
        self.data_dir = data_dir

    def load_articles(self) -> list[Comment]:
        """Charge les commentaires d'articles.

        Le contexte retenu est le titre de l'article. Le corps de
        l'article n'est pas fourni dans le jeu de donnees.

        Returns:
            Les commentaires d'articles, dans l'ordre du fichier.

        Raises:
            CorpusError: Si le fichier est absent ou si une colonne
                attendue manque.
        """
        path = self.data_dir / self.ARTICLE_FILE
        rows = self._read_rows(path, self._ARTICLE_COLUMNS)
        return [
            Comment(
                text=row["text"],
                context=row["article_title"],
                source=Source.ARTICLE,
                tags=self._parse_tags(row["tags"]),
            )
            for row in rows
        ]

    def load_posts(self) -> list[Comment]:
        """Charge les commentaires de posts.

        Le contexte retenu est le contenu integral du post.

        Returns:
            Les commentaires de posts, dans l'ordre du fichier.

        Raises:
            CorpusError: Si le fichier est absent ou si une colonne
                attendue manque.
        """
        path = self.data_dir / self.POST_FILE
        rows = self._read_rows(path, self._POST_COLUMNS)
        return [
            Comment(
                text=row["text"],
                context=row["post_content"],
                source=Source.POST,
                tags=(),
            )
            for row in rows
        ]

    def load_all(self) -> list[Comment]:
        """Charge les deux corpus concatenes.

        Returns:
            Les commentaires d'articles suivis de ceux de posts.

        Raises:
            CorpusError: Si un fichier est absent ou mal forme.
        """
        return self.load_articles() + self.load_posts()

    def _read_rows(
        self, path: Path, expected: frozenset[str]
    ) -> Iterator[dict[str, str]]:
        """Lit un CSV en verifiant son schema.

        Args:
            path: Chemin du fichier CSV.
            expected: Colonnes que le fichier doit contenir.

        Yields:
            Les lignes du fichier, indexees par nom de colonne.

        Raises:
            CorpusError: Si le fichier est absent, vide, ou si une
                colonne attendue manque.
        """
        if not path.is_file():
            raise CorpusError(f"Corpus introuvable : {path}")

        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise CorpusError(f"Corpus vide : {path}")

            missing = expected - set(reader.fieldnames)
            if missing:
                raise CorpusError(
                    f"Colonnes manquantes dans {path.name} : "
                    f"{', '.join(sorted(missing))}"
                )

            yield from reader

    @staticmethod
    def _parse_tags(raw: str) -> tuple[str, ...]:
        """Decode la colonne `tags`, serialisee en JSON.

        Une valeur illisible est traitee comme une absence de tags :
        les thematiques ne servent qu'a echantillonner, une ligne
        mal formee ne doit pas interrompre le chargement.

        Args:
            raw: Contenu brut de la colonne.

        Returns:
            Les thematiques, ou un tuple vide si la valeur est vide
            ou illisible.
        """
        if not raw:
            return ()
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            return ()
        if not isinstance(decoded, list):
            return ()
        return tuple(str(tag) for tag in decoded)
