"""Profil descriptif d'un corpus de commentaires.

Le profil sert deux decisions ulterieures : quelles regles
mecaniques valent la peine d'etre codees dans le pre-filtre, et
comment echantillonner le jeu de reference. Il ne porte aucun
jugement de moderation.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from moderation.corpus import Comment

_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class CorpusProfile:
    """Mesures descriptives sur un ensemble de commentaires.

    Attributes:
        total: Nombre de commentaires examines.
        by_source: Effectif par canal d'origine.
        empty: Commentaires vides une fois les espaces retires.
        duplicates: Occurrences redondantes d'un texte deja vu.
        without_letters: Commentaires sans lettre ni chiffre, donc
            reduits a des emojis ou de la ponctuation.
        link_only: Commentaires reduits a une ou plusieurs URL.
        with_context: Commentaires dont le contexte est renseigne.
        length_quantiles: Longueur en caracteres aux quantiles 50,
            90 et 99, et maximum observe.
    """

    total: int
    by_source: dict[str, int]
    empty: int
    duplicates: int
    without_letters: int
    link_only: int
    with_context: int
    length_quantiles: dict[str, int]


class CorpusProfiler:
    """Calcule le profil descriptif d'un corpus."""

    def profile(self, comments: list[Comment]) -> CorpusProfile:
        """Mesure un ensemble de commentaires.

        Args:
            comments: Commentaires a examiner.

        Returns:
            Le profil correspondant. Un corpus vide donne des
            compteurs nuls et des quantiles a zero.
        """
        seen: set[str] = set()
        by_source: Counter[str] = Counter()
        empty = 0
        duplicates = 0
        without_letters = 0
        link_only = 0
        with_context = 0
        lengths: list[int] = []

        for comment in comments:
            by_source[str(comment.source)] += 1
            stripped = comment.text.strip()
            lengths.append(len(stripped))

            if not stripped:
                empty += 1
            if stripped in seen:
                duplicates += 1
            else:
                seen.add(stripped)
            if stripped and not self._has_letter_or_digit(stripped):
                without_letters += 1
            if stripped and self._is_link_only(stripped):
                link_only += 1
            if comment.context.strip():
                with_context += 1

        return CorpusProfile(
            total=len(comments),
            by_source=dict(by_source),
            empty=empty,
            duplicates=duplicates,
            without_letters=without_letters,
            link_only=link_only,
            with_context=with_context,
            length_quantiles=self._quantiles(lengths),
        )

    def format_report(self, profile: CorpusProfile) -> str:
        """Met un profil en forme pour l'affichage terminal.

        Args:
            profile: Profil a presenter.

        Returns:
            Un rapport multiligne, sans couleur ni mise en forme.
        """
        if profile.total == 0:
            return "Corpus vide."

        lines = [f"Commentaires             {profile.total}"]
        for source, count in sorted(profile.by_source.items()):
            lines.append(f"  dont {source:<18} {count}")
        lines.append("")

        for label, count in (
            ("Vides", profile.empty),
            ("Doublons exacts", profile.duplicates),
            ("Sans lettre ni chiffre", profile.without_letters),
            ("Liens seuls", profile.link_only),
            ("Avec contexte", profile.with_context),
        ):
            share = 100 * count / profile.total
            lines.append(f"{label:<24} {count:>7} ({share:5.2f} %)")

        lines.append("")
        lines.append("Longueur en caracteres")
        for label, value in profile.length_quantiles.items():
            lines.append(f"  {label:<22} {value}")
        return "\n".join(lines)

    @staticmethod
    def _has_letter_or_digit(text: str) -> bool:
        """Indique si un texte contient une lettre ou un chiffre.

        Args:
            text: Texte a examiner.

        Returns:
            True si au moins un caractere est alphanumerique.
        """
        return any(char.isalnum() for char in text)

    @staticmethod
    def _is_link_only(text: str) -> bool:
        """Indique si un texte se reduit a des URL.

        Args:
            text: Texte a examiner, deja debarrasse des espaces de
                bord.

        Returns:
            True si le texte ne contient rien d'autre que des URL et
            de la ponctuation.
        """
        without_urls = _URL_PATTERN.sub("", text)
        return not any(char.isalnum() for char in without_urls)

    @staticmethod
    def _quantiles(lengths: list[int]) -> dict[str, int]:
        """Calcule les quantiles de longueur.

        Args:
            lengths: Longueurs observees, dans un ordre quelconque.

        Returns:
            Les quantiles 50, 90 et 99 et le maximum. Toutes les
            valeurs sont nulles si la liste est vide.
        """
        if not lengths:
            return {"mediane": 0, "q90": 0, "q99": 0, "maximum": 0}

        ordered = sorted(lengths)
        last = len(ordered) - 1
        return {
            "mediane": ordered[last // 2],
            "q90": ordered[int(last * 0.90)],
            "q99": ordered[int(last * 0.99)],
            "maximum": ordered[last],
        }
