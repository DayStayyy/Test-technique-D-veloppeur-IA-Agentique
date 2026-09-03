"""Appel des modeles via OpenRouter, avec cache disque.

Toute reponse de modele est ecrite sur disque, indexee par modele,
version de prompt et texte d'entree. Relancer une evaluation sans
rien changer ne declenche aucun appel reseau et ne coute rien. Une
reecriture de prompt change la version, donc la cle, donc invalide
les reponses concernees sans avoir a vider le cache.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_CACHE_DIR = Path(".cache") / "openrouter"


class OpenRouterError(RuntimeError):
    """Appel a OpenRouter impossible ou reponse inexploitable."""


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """Une requete adressee a un modele.

    Attributes:
        model: Identifiant OpenRouter du modele.
        system: Consigne systeme.
        user: Contenu soumis au jugement du modele.
        prompt_version: Version de la consigne. Elle entre dans la
            cle de cache pour qu'une reecriture de prompt invalide
            les reponses obtenues avec l'ancienne.
        temperature: Temperature demandee au modele.
    """

    model: str
    system: str
    user: str
    prompt_version: str
    temperature: float = 0.0

    def cache_key(self) -> str:
        """Calcule la cle de cache de la requete.

        Returns:
            Empreinte SHA-256 hexadecimale des champs de la requete.
        """
        payload = json.dumps(
            {
                "model": self.model,
                "system": self.system,
                "user": self.user,
                "prompt_version": self.prompt_version,
                "temperature": self.temperature,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """La reponse brute d'un modele.

    Le contenu n'est pas interprete a ce stade : l'analyse des
    quatre etats de sortie possibles releve de l'etage de parsing.

    Attributes:
        text: Contenu textuel renvoye par le modele.
        model: Modele ayant repondu.
        from_cache: True si la reponse vient du cache disque.
    """

    text: str
    model: str
    from_cache: bool


class ResponseCache:
    """Cache disque des reponses de modeles.

    Attributes:
        directory: Repertoire ou sont ecrites les reponses.
    """

    def __init__(self, directory: Path = DEFAULT_CACHE_DIR) -> None:
        """Initialise le cache.

        Args:
            directory: Repertoire de stockage. Il est cree au
                premier enregistrement.
        """
        self.directory = directory

    def get(self, key: str) -> str | None:
        """Lit une reponse en cache.

        Une entree illisible est traitee comme absente : un cache
        corrompu doit provoquer un nouvel appel, pas une erreur.

        Args:
            key: Cle de cache de la requete.

        Returns:
            Le contenu textuel memorise, ou None si absent.
        """
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        text = payload.get("text")
        return text if isinstance(text, str) else None

    def put(self, key: str, request: ModelRequest, text: str) -> None:
        """Enregistre une reponse.

        La requete est memorisee a cote de la reponse pour que le
        contenu du cache reste lisible et verifiable a la main.

        Args:
            key: Cle de cache de la requete.
            request: Requete ayant produit la reponse.
            text: Contenu textuel renvoye par le modele.

        Raises:
            OpenRouterError: Si l'ecriture sur disque echoue.
        """
        path = self._path(key)
        payload = {
            "model": request.model,
            "prompt_version": request.prompt_version,
            "temperature": request.temperature,
            "system": request.system,
            "user": request.user,
            "text": text,
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            raise OpenRouterError(
                f"Ecriture du cache impossible : {path}"
            ) from error

    def _path(self, key: str) -> Path:
        """Donne le chemin de fichier d'une cle.

        Args:
            key: Cle de cache.

        Returns:
            Le chemin du fichier JSON correspondant.
        """
        return self.directory / f"{key}.json"


class OpenRouterClient:
    """Client OpenRouter, systematiquement adosse au cache.

    Attributes:
        cache: Cache disque consulte avant tout appel reseau.
        timeout: Delai maximal d'un appel, en secondes.
    """

    def __init__(
        self,
        api_key: str | None = None,
        cache: ResponseCache | None = None,
        timeout: float = 60.0,
    ) -> None:
        """Initialise le client.

        Args:
            api_key: Cle OpenRouter. Lue dans la variable
                d'environnement `OPENROUTER_API_KEY` si omise.
            cache: Cache a utiliser. Un cache par defaut est cree si
                l'argument est omis.
            timeout: Delai maximal d'un appel, en secondes.

        Raises:
            OpenRouterError: Si aucune cle n'est disponible.
        """
        key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise OpenRouterError(
                "Cle absente : renseigner OPENROUTER_API_KEY dans "
                "le fichier .env a la racine du depot."
            )
        self._api_key = key
        self.cache = cache if cache is not None else ResponseCache()
        self.timeout = timeout

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Soumet une requete, en passant par le cache.

        Args:
            request: Requete a soumettre.

        Returns:
            La reponse du modele, issue du cache ou du reseau.

        Raises:
            OpenRouterError: Si l'appel echoue, si le modele renvoie
                un statut d'erreur, ou si la reponse ne contient pas
                de contenu exploitable.
        """
        key = request.cache_key()
        cached = self.cache.get(key)
        if cached is not None:
            return ModelResponse(
                text=cached, model=request.model, from_cache=True
            )

        text = self._call(request)
        self.cache.put(key, request, text)
        return ModelResponse(text=text, model=request.model, from_cache=False)

    def _call(self, request: ModelRequest) -> str:
        """Effectue l'appel reseau.

        Args:
            request: Requete a soumettre.

        Returns:
            Le contenu textuel du premier choix renvoye.

        Raises:
            OpenRouterError: Si le reseau echoue, si le statut n'est
                pas 200, ou si la charge utile est inattendue.
        """
        payload = {
            "model": request.model,
            "temperature": request.temperature,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(
                OPENROUTER_URL,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        except httpx.HTTPError as error:
            raise OpenRouterError(
                f"Appel a {request.model} impossible : {error}"
            ) from error

        if response.status_code != httpx.codes.OK:
            raise OpenRouterError(
                f"{request.model} a renvoye le statut "
                f"{response.status_code} : {response.text[:200]}"
            )

        return self._extract_content(response.json(), request.model)

    @staticmethod
    def _extract_content(payload: object, model: str) -> str:
        """Extrait le contenu textuel d'une reponse OpenRouter.

        Args:
            payload: Charge utile JSON decodee.
            model: Modele interroge, pour le message d'erreur.

        Returns:
            Le contenu du premier choix. Une chaine vide est une
            reponse valide : certains modeles repondent ainsi quand
            un filtre interne s'est declenche.

        Raises:
            OpenRouterError: Si la structure attendue est absente.
        """
        if not isinstance(payload, dict):
            raise OpenRouterError(
                f"Reponse de {model} inattendue : objet JSON attendu"
            )
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            error = payload.get("error")
            raise OpenRouterError(
                f"Reponse de {model} sans choix exploitable : {error}"
            )
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise OpenRouterError(
                f"Reponse de {model} sans message exploitable"
            )
        content = message.get("content")
        if content is None:
            return ""
        if not isinstance(content, str):
            raise OpenRouterError(
                f"Contenu de {model} inattendu : chaine attendue"
            )
        return content
