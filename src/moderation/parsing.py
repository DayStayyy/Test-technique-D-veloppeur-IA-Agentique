"""Interpretation des reponses brutes renvoyees par les modeles.

Une reponse de modele se range dans l'un de quatre etats, actes en
phase 2 : valide (JSON conforme au schema attendu), mal formee (JSON
absent, invalide ou incoherent avec la taxonomie), refus (le modele
ou un filtre en amont n'a rien produit d'exploitable), ou erreur
(l'appel reseau lui-meme a echoue). Ce module construit une
`Decision` a partir des trois premiers etats ; le quatrieme est
constate au niveau du client et n'a pas de texte a interpreter.

Le test de refus (phase 1) utilise un schema plus simple que l'etage
legal et garde son propre parsing, mais partage avec ce module la
detection du refus et l'extraction du JSON sous balises Markdown :
deux des trois modeles candidats en entourent systematiquement leur
reponse.
"""

from __future__ import annotations

import json
import re

from moderation.decision import Decision, Motif, Status, Verdict

_MARKDOWN_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

REFUSAL_MARKERS: tuple[str, ...] = (
    "je ne peux pas",
    "je ne peux pas t'aider",
    "je ne peux pas vous aider",
    "je suis desole",
    "je suis désolé",
    "desole, je",
    "désolé, je",
    "i can't",
    "i cannot",
    "i'm sorry",
    "i am sorry",
    "as an ai",
    "en tant qu'ia",
)


def parse_legal_response(
    text: str,
    *,
    model: str,
    prompt_version: str,
    attempts: int,
) -> Decision:
    """Interprete la reponse de l'etage legal en objet de decision.

    Ne leve jamais d'exception : une reponse inexploitable produit
    une decision au statut `MAL_FORME` ou `REFUS` plutot que
    d'interrompre le traitement du lot en cours.

    Args:
        text: Texte brut renvoye par le modele.
        model: Identifiant OpenRouter du modele interroge.
        prompt_version: Version du prompt legal utilise.
        attempts: Nombre de tentatives effectuees jusqu'ici.

    Returns:
        La decision correspondante.
    """
    stripped = text.strip()
    if not stripped or looks_like_refusal(stripped):
        return fallback_decision(
            Status.REFUS,
            model=model,
            prompt_version=prompt_version,
            attempts=attempts,
            raw_text=text,
        )

    payload = extract_json(stripped)
    if payload is None:
        return fallback_decision(
            Status.MAL_FORME,
            model=model,
            prompt_version=prompt_version,
            attempts=attempts,
            raw_text=text,
        )

    try:
        return _decision_from_payload(
            payload,
            model=model,
            prompt_version=prompt_version,
            attempts=attempts,
            raw_text=text,
        )
    except (KeyError, ValueError):
        return fallback_decision(
            Status.MAL_FORME,
            model=model,
            prompt_version=prompt_version,
            attempts=attempts,
            raw_text=text,
        )


def fallback_decision(
    status: Status,
    *,
    model: str,
    prompt_version: str,
    attempts: int,
    raw_text: str = "",
) -> Decision:
    """Construit la decision par defaut d'un etat non exploitable.

    Le verdict par defaut est toujours ACCEPTABLE, quel que soit
    l'etat : un systeme qui n'a pas pu obtenir de jugement du modele
    ne doit pas devenir plus restrictif que la loi de son propre
    chef. C'est ce qui distingue `status`, qui rend visible qu'aucun
    jugement n'a eu lieu, de `verdict`, qui reste conservateur.

    Args:
        status: Etat constate : `MAL_FORME`, `REFUS` ou `ERREUR`.
        model: Identifiant OpenRouter du modele interroge.
        prompt_version: Version du prompt legal utilise.
        attempts: Nombre de tentatives effectuees.
        raw_text: Dernier texte brut obtenu, vide si l'appel a
            echoue avant toute reponse.

    Returns:
        La decision par defaut correspondante.
    """
    return Decision(
        verdict=Verdict.ACCEPTABLE,
        motif=None,
        motifs_editoriaux=(),
        justification="",
        incertain=False,
        status=status,
        model=model,
        prompt_version=prompt_version,
        attempts=attempts,
        raw_text=raw_text,
    )


def looks_like_refusal(text: str) -> bool:
    """Indique si un texte porte les marqueurs usuels d'un refus.

    Args:
        text: Texte deja debarrasse des espaces de bord.

    Returns:
        True si un marqueur de refus y est present.
    """
    lowered = text.lower()
    return any(marker in lowered for marker in REFUSAL_MARKERS)


def extract_json(text: str) -> object | None:
    """Decode un objet JSON, y compris entoure de balises Markdown.

    Args:
        text: Texte renvoye par le modele.

    Returns:
        L'objet decode, ou None si aucun JSON exploitable n'y est
        trouve.
    """
    fenced = _MARKDOWN_FENCE.search(text)
    candidate = fenced.group(1) if fenced else text

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(candidate[start : end + 1])
    except json.JSONDecodeError:
        return None


def _decision_from_payload(
    payload: object,
    *,
    model: str,
    prompt_version: str,
    attempts: int,
    raw_text: str,
) -> Decision:
    """Construit une decision valide a partir d'un objet JSON decode.

    Args:
        payload: Objet decode, attendu comme un dictionnaire.
        model: Identifiant OpenRouter du modele interroge.
        prompt_version: Version du prompt legal utilise.
        attempts: Nombre de tentatives effectuees.
        raw_text: Texte brut d'origine, conserve pour audit.

    Returns:
        La decision correspondante, au statut `VALIDE`.

    Raises:
        KeyError: Si le champ `decision` manque.
        ValueError: Si un champ prend une valeur hors schema, ou si
            le motif contredit la decision.
    """
    if not isinstance(payload, dict):
        raise ValueError("réponse JSON qui n'est pas un objet")

    decision_raw = payload["decision"]
    if decision_raw not in ("acceptable", "rejete"):
        raise ValueError(f"décision inconnue : {decision_raw!r}")
    verdict = Verdict(decision_raw)

    motif_raw = payload.get("motif")
    try:
        motif = Motif(motif_raw) if motif_raw else None
    except ValueError as error:
        raise ValueError(f"motif hors taxonomie : {motif_raw!r}") from error

    if verdict == Verdict.REJETE and motif is None:
        raise ValueError("décision rejetée sans motif")
    if verdict == Verdict.ACCEPTABLE and motif is not None:
        raise ValueError("décision acceptable avec un motif")

    justification = payload.get("justification", "")
    if not isinstance(justification, str):
        raise ValueError("justification qui n'est pas une chaîne")

    incertain = payload.get("incertain", False)
    if not isinstance(incertain, bool):
        raise ValueError("incertain qui n'est pas un booléen")

    return Decision(
        verdict=verdict,
        motif=motif,
        motifs_editoriaux=(),
        justification=justification,
        incertain=incertain,
        status=Status.VALIDE,
        model=model,
        prompt_version=prompt_version,
        attempts=attempts,
        raw_text=raw_text,
    )
