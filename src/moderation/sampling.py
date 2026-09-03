"""Selection des commentaires du jeu de reference.

Deux strates sont tirees du corpus. La strate aleatoire mesure le
comportement du systeme en conditions reelles. La strate
preselectionnee enrichit en cas limites : un tirage au hasard n'en
contient presque aucun, ces espaces etant deja moderes en amont.

Les listes de termes ne servent qu'a cette preselection. Elles ne
sont jamais un verdict : un commentaire n'est pas suspect parce
qu'il contient un mot, il est seulement plus interessant a faire
annoter. Beaucoup de ceux qu'elles remontent sont parfaitement
licites, et c'est precisement ce qu'on cherche a mesurer.

Trois listes, parce qu'un mot seul ne veut rien dire. « Dehors »
dans « en dehors d'une journee pluvieuse » n'a aucun interet. Un
terme d'action ne compte donc que s'il accompagne une cible.
"""

from __future__ import annotations

import random
import re
import unicodedata
from dataclasses import dataclass

from moderation.corpus import Comment

# Groupes et caracteristiques proteges, plus le vocabulaire des
# debats ou se concentrent les commentaires choquants mais licites.
# Un terme de cette liste suffit a retenir un commentaire.
TARGET_TERMS: tuple[str, ...] = (
    "arabe",
    "arabes",
    "africain",
    "africains",
    "maghrebin",
    "maghrebins",
    "rom",
    "roms",
    "tsigane",
    "tsiganes",
    "gitan",
    "gitans",
    "migrant",
    "migrants",
    "immigre",
    "immigres",
    "immigration",
    "clandestin",
    "clandestins",
    "sans-papiers",
    "etranger",
    "etrangers",
    "musulman",
    "musulmans",
    "islam",
    "mosquee",
    "mosquees",
    "voile",
    "niqab",
    "burqa",
    "coran",
    "juif",
    "juifs",
    "juive",
    "juives",
    "catholique",
    "catholiques",
    "chretien",
    "chretiens",
    "pede",
    "pedes",
    "tapette",
    "homo",
    "homosexuel",
    "homosexuels",
    "trans",
    "handicape",
    "handicapes",
    "mongol",
)

# Appels a agir et vocabulaire de la violence. Ces termes ne
# retiennent jamais un commentaire a eux seuls : ils ne comptent que
# combines a une cible.
ACTION_TERMS: tuple[str, ...] = (
    "tuer",
    "buter",
    "crever",
    "flingue",
    "fusil",
    "balle",
    "pendre",
    "bruler",
    "gazer",
    "exterminer",
    "expulser",
    "renvoyer",
    "nettoyer",
    "eliminer",
    "massacre",
    "dehors",
    "virer",
    "degager",
    "cogner",
    "tabasser",
)

# Termes assez specifiques pour retenir un commentaire a eux seuls,
# quel que soit le reste de la phrase.
STANDALONE_TERMS: tuple[str, ...] = (
    "racaille",
    "racailles",
    "grand remplacement",
    "envahisseur",
    "envahisseurs",
    "charia",
    "islamiste",
    "islamistes",
    "sioniste",
    "sionistes",
    "attentat",
    "attentats",
    "terroriste",
    "terroristes",
    "daech",
    "djihad",
    "jihad",
    "bataclan",
    "kalash",
    "shoah",
    "nazi",
    "nazis",
    "hitler",
    "chambre a gaz",
    "chambres a gaz",
    "genocide",
    "holocauste",
    "negationniste",
    "deportation",
    "pedophile",
    "pedophiles",
    "pedo",
    "pedocriminel",
    "pedocriminels",
)


def normalize(text: str) -> str:
    """Met un texte en minuscules et retire ses accents.

    La comparaison doit ignorer la casse et les accents : un
    commentaire ecrit sans accent doit remonter comme un autre.

    Args:
        text: Texte a normaliser.

    Returns:
        Le texte en minuscules, sans signes diacritiques.
    """
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )


def _compile(terms: tuple[str, ...]) -> re.Pattern[str]:
    """Compile une liste de termes en expression a frontieres.

    Les termes sont tries du plus long au plus court pour que les
    expressions composees soient reconnues avant leurs composants.

    Args:
        terms: Termes a reconnaitre.

    Returns:
        L'expression compilee, destinee a un texte normalise.
    """
    ordered = sorted(terms, key=len, reverse=True)
    joined = "|".join(re.escape(term) for term in ordered)
    return re.compile(rf"\b(?:{joined})\b")


@dataclass(frozen=True, slots=True)
class SelectedComment:
    """Un commentaire retenu pour le jeu de reference.

    Attributes:
        comment: Le commentaire selectionne.
        stratum: Strate d'origine, `aleatoire` ou `preselection`.
        trigger: Termes ayant declenche la selection, separes par
            un plus. Vide pour la strate aleatoire.
    """

    comment: Comment
    stratum: str
    trigger: str


class ReferenceSampler:
    """Tire les strates aleatoire et preselectionnee du corpus.

    La strate preselectionnee est elle-meme coupee en deux moities.
    L'une reunit les commentaires ou une cible cotoie un appel a
    agir : ce sont les candidats a la provocation, ils mesurent le
    rappel. L'autre reunit les commentaires ou une cible apparait
    sans aucun appel : hostiles, souvent choquants, presque toujours
    licites, ils mesurent les faux positifs. Sans cette coupe, le
    tirage privilegierait mecaniquement la seconde categorie, bien
    plus frequente, et le jeu ne testerait qu'une moitie du
    probleme.

    Attributes:
        seed: Graine du tirage, pour que l'echantillon soit
            reproductible par un tiers.
    """

    RANDOM_STRATUM = "aleatoire"
    PRESELECTED_STRATUM = "preselection"

    def __init__(self, seed: int = 20260903) -> None:
        """Initialise le tireur.

        Args:
            seed: Graine du generateur aleatoire.
        """
        self.seed = seed
        self._targets = _compile(TARGET_TERMS)
        self._actions = _compile(ACTION_TERMS)
        self._standalone = _compile(STANDALONE_TERMS)

    def sample(
        self,
        comments: list[Comment],
        random_size: int,
        preselected_size: int,
    ) -> list[SelectedComment]:
        """Tire les deux strates dans le corpus.

        Les doublons exacts et les commentaires vides sont ecartes :
        annoter deux fois le meme texte n'apporte rien. En revanche
        les liens seuls et les commentaires reduits a des emojis
        sont conserves dans la strate aleatoire, sans quoi celle-ci
        ne refleterait plus la distribution reelle.

        Args:
            comments: Corpus complet.
            random_size: Effectif de la strate aleatoire.
            preselected_size: Effectif de la strate
                preselectionnee, reparti a parts egales entre les
                commentaires avec appel et ceux sans appel.

        Returns:
            Les commentaires retenus, strate aleatoire d'abord.

        Raises:
            ValueError: Si le corpus ne contient pas assez de
                commentaires distincts pour honorer les effectifs.
        """
        pool = self._deduplicate(comments)
        rng = random.Random(self.seed)

        if len(pool) < random_size:
            raise ValueError(
                f"Corpus insuffisant : {len(pool)} commentaires "
                f"distincts pour {random_size} demandes."
            )

        drawn = rng.sample(pool, random_size)
        selected = [
            SelectedComment(comment, self.RANDOM_STRATUM, "")
            for comment in drawn
        ]

        already = {comment.text for comment in drawn}
        with_call: list[tuple[Comment, str]] = []
        without_call: list[tuple[Comment, str]] = []
        for comment in pool:
            if comment.text in already:
                continue
            trigger = self.trigger_of(comment.text)
            if not trigger:
                continue
            if "+" in trigger:
                with_call.append((comment, trigger))
            else:
                without_call.append((comment, trigger))

        half = preselected_size // 2
        chosen = self._draw_balanced(
            rng, with_call, without_call, half, preselected_size
        )
        selected.extend(
            SelectedComment(comment, self.PRESELECTED_STRATUM, trigger)
            for comment, trigger in chosen
        )
        return selected

    def trigger_of(self, text: str) -> str:
        """Donne les termes ayant retenu un commentaire.

        Un terme autonome suffit. Une cible suffit egalement. Un
        terme d'action ne compte que s'il accompagne une cible : il
        est alors joint a celle-ci par un plus, ce qui distingue les
        candidats a la provocation des simples propos hostiles.

        Args:
            text: Texte du commentaire.

        Returns:
            Le declencheur, ou une chaine vide si le commentaire
            n'est pas retenu.
        """
        normalized = normalize(text)
        target = self._targets.search(normalized)
        standalone = self._standalone.search(normalized)

        if target:
            action = self._actions.search(normalized)
            if action:
                return f"{target.group(0)}+{action.group(0)}"
            return target.group(0)
        if standalone:
            return standalone.group(0)
        return ""

    def count_matches(self, comments: list[Comment]) -> dict[str, int]:
        """Compte les commentaires retenus par la preselection.

        Args:
            comments: Commentaires a examiner.

        Returns:
            Le nombre de commentaires avec appel et sans appel.
        """
        counts = {"avec_appel": 0, "sans_appel": 0}
        for comment in comments:
            trigger = self.trigger_of(comment.text)
            if not trigger:
                continue
            key = "avec_appel" if "+" in trigger else "sans_appel"
            counts[key] += 1
        return counts

    @staticmethod
    def _draw_balanced(
        rng: random.Random,
        with_call: list[tuple[Comment, str]],
        without_call: list[tuple[Comment, str]],
        half: int,
        total: int,
    ) -> list[tuple[Comment, str]]:
        """Tire a parts egales dans les deux sous-ensembles.

        Si l'un des deux est trop petit, l'autre comble le manque :
        mieux vaut une strate desequilibree qu'une strate amputee.

        Args:
            rng: Generateur aleatoire deja ensemence.
            with_call: Candidats melant cible et appel.
            without_call: Candidats sans appel.
            half: Effectif vise dans chaque sous-ensemble.
            total: Effectif total vise.

        Returns:
            Les candidats retenus.

        Raises:
            ValueError: Si les deux sous-ensembles reunis ne
                suffisent pas.
        """
        if len(with_call) + len(without_call) < total:
            raise ValueError(
                f"Preselection insuffisante : "
                f"{len(with_call) + len(without_call)} candidats "
                f"pour {total} demandes."
            )
        take_call = min(half, len(with_call))
        take_other = min(total - take_call, len(without_call))
        take_call = total - take_other

        return rng.sample(with_call, take_call) + rng.sample(
            without_call, take_other
        )

    @staticmethod
    def _deduplicate(comments: list[Comment]) -> list[Comment]:
        """Retire les doublons exacts et les commentaires vides.

        Args:
            comments: Corpus complet.

        Returns:
            Les commentaires distincts et non vides, dans l'ordre
            d'apparition.
        """
        seen: set[str] = set()
        kept: list[Comment] = []
        for comment in comments:
            stripped = comment.text.strip()
            if not stripped or stripped in seen:
                continue
            seen.add(stripped)
            kept.append(comment)
        return kept
