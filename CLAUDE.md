# CLAUDE.md — modération de commentaires

Ce fichier est la référence de travail du dépôt. Il prime sur les
habitudes par défaut. En cas de contradiction avec `consigne.md`,
c'est `consigne.md` qui prime, et la contradiction doit être
signalée.

## 1. Le projet

On construit une fonction de modération de commentaires en Python.
Elle reçoit un commentaire et éventuellement son contexte (un post
Facebook ou un titre d'article) et retourne une décision :
acceptable ou rejeté.

**La contrainte centrale**, tirée de `consigne.md` : détecter et
rejeter les contenus manifestement illégaux au regard de la loi
française, **sans être plus restrictif que la loi**. Le comportement
par défaut d'un LLM est très au-dessus de ce plafond : il rejette la
vulgarité, l'insulte, la critique politique ou religieuse, l'ironie.
Le travail de prompting consiste donc à ramener le modèle à la ligne
légale, pas à le brider. C'est le fil conducteur du projet.

Budget : **4 h de travail effectif**. On préfère un système partiel
avec une stratégie claire à un système complet mais bricolé.
L'historique de commits doit raconter la progression de la réflexion.

## 2. Mode de travail — règles non négociables

- **Aucune décision structurante sans l'accord explicite d'Adrien.**
- **Aucun code écrit sans son accord explicite**, y compris code de
  configuration, de test ou d'exploration.
- En cas d'hésitation entre plusieurs options : les présenter avec
  leur coût et une recommandation, puis **attendre la réponse**.
- En cas de doute sur une demande : **poser la question avant
  d'agir**.
- **Périmètre strict** : ne rien implémenter qui n'a pas été demandé.

La démarche est rendue lisible par **deux moyens, et deux
seulement** : les messages de commit et la section « Arbitrages » du
README. Pas de dossier de réflexion séparé — l'évaluateur lit le
README et l'historique Git, tout doit être là.

## 3. Messages de commit

Chaque commit porte dans son message **la décision qu'il
matérialise**, pas seulement le fichier touché. Quand une piste est
abandonnée, le commit qui la retire dit pourquoi.

**Claude ne commite jamais.** C'est Adrien qui commite, lui seul.
Claude fournit uniquement le texte du message. Quand plusieurs
commits sont pertinents, Claude indique en plus quels fichiers vont
dans quel commit.

## 4. Section « Arbitrages » du README

Créée dès le premier commit, complétée au fil des phases. Elle ne
contient que les décisions structurantes, **quatre ou cinq au
total** :

1. format de la décision ;
2. architecture et agrégation ;
3. protocole d'évaluation ;
4. choix du modèle ;
5. ce qu'on a sacrifié faute de temps.

Chaque arbitrage tient en une dizaine de lignes, au format :

> **Problème :** comment construire un dataset de test alors que les
> données ne sont pas annotées.
>
> **Options envisagées :**
> - Faire annoter par un modèle. Rejeté : le modèle serait juge et
>   partie, on mesurerait sa cohérence, pas sa justesse.
> - Construire un jeu de référence annoté à la main d'une centaine
>   d'exemples, en trois strates : aléatoire, présélectionné par
>   heuristique, adverse écrit à la main. Retenu.
>
> **Décision :** jeu de référence de N exemples, split dev/test.

Au moment où un arbitrage est tranché, Claude propose un **brouillon**
de ce bloc. **Adrien le réécrit dans ses mots** avant qu'il entre dans
le README. Le README doit rester autonome et lisible en cinq minutes.

## 5. Journal d'usage de l'IA

Un fichier `journal_ia.md` à la racine, **purement factuel** : à la
fin de chaque phase, une ligne sur ce que Claude a généré et une
ligne sur ce qu'Adrien a corrigé ou rejeté.

Claude **ne rédige pas** la note « usage de l'IA » demandée par la
consigne (10–15 lignes). Adrien l'écrit lui-même à partir de ce
journal.

## 6. Décisions déjà prises

Ces choix ont été arrêtés en amont. Ne pas les remettre en cause,
sauf problème concret identifié — auquel cas le signaler avant de
continuer.

### Format de la décision

Un objet à cinq champs :

- décision binaire : `acceptable` / `rejeté` ;
- motif légal, issu d'une **liste fermée**, ou vide ;
- motifs éditoriaux : liste, **toujours vide tant que le périmètre
  est réduit au légal**. Le champ est conservé pour marquer la
  frontière de ce qu'on a choisi de ne pas faire, mais il n'est pas
  demandé au modèle ;
- justification en une phrase ;
- indicateur d'incertitude, **en métadonnée**, qui n'influence pas la
  décision.

### Taxonomie légale fermée

Fondée sur le standard « manifestement illicite » :

- provocation à la haine, à la discrimination ou à la violence ;
- apologie ou contestation de crimes contre l'humanité ;
- apologie du terrorisme ;
- contenu pédopornographique.

La **diffamation** et l'**injure** envers une personne identifiée ne
sont pas manifestement illicites et ne sont donc **pas rejetées**.

### Architecture

**Périmètre réduit au légal, décidé en phase 2.** Un seul étage :
une question au modèle, avec la liste fermée.

L'étage éditorial initialement prévu (spam) est **reporté**. On
valide d'abord tout le légal sur l'ensemble des phases, c'est
l'objectif du test. L'éditorial ne sera ajouté que s'il reste du
temps. Deux raisons : la consigne n'impose que le légal et laisse
les critères additionnels libres ; et le spam est mal détectable sur
un commentaire isolé, sans historique d'auteur ni fréquence de
publication.

La question de l'agrégation disparaît donc avec le second étage. Ce
n'est pas un agent outillé, c'est un **pipeline à étapes fixes**, et
on l'assume dans la documentation.

### Règles et LLM

Les règles déterministes servent **uniquement** au pré-filtre
mécanique (commentaire vide, lien seul, doublon exact) et à la
présélection de candidats pour l'annotation. **Jamais comme verdict
légal.**

### Modèles

Via **OpenRouter**, avec une clé que possède Adrien. Un modèle
propriétaire et un modèle ouvert, comparés sur le jeu de référence.

Le choix du modèle principal se fait après un **test de refus** :
cinq commentaires illégaux écrits à la main, envoyés bruts à chaque
candidat, pour vérifier qu'il **classifie au lieu de refuser**. Un
modèle qui refuse est disqualifié pour l'étage légal.

Température fixée quand le modèle l'accepte, mais la reproductibilité
repose sur **le cache et sur un taux d'accord mesuré**, pas sur la
température.

**Shortlist soumise au test de refus** — trois profils distincts :

| Modèle | id OpenRouter | $/M in | $/M out | Profil |
|---|---|---|---|---|
| Claude Haiku 4.5 | `anthropic/claude-haiku-4.5` | 1,00 | 5,00 | propriétaire, alignement lourd |
| GPT-5.6 Luna | `openai/gpt-5.6-luna` | 0,20 | 1,20 | propriétaire, économique |
| Ministral 3 14B | `mistralai/ministral-14b-2512` | 0,20 | 0,20 | poids ouverts, FR/UE |

Les critères sont **le taux de refus** et **le taux de
faux positifs sur les cas « choquant mais légal »**.

**Modèle de travail : `openai/gpt-5.6-luna`.** Le test de refus n'a
disqualifié aucun candidat, mais le test de perception des emojis
écarte Ministral : trois erreurs d'identification et deux erreurs de
comptage sur sept cas, quand Haiku et Luna font 7 sur 7. Luna est le
moins cher des deux restants.

C'est un choix de travail, pas le choix final. La comparaison des
trois candidats est reportée aux tests finaux, sur le jeu de
référence gelé.

À confirmer en phase 1, au premier appel réel : l'id exact du modèle
Mistral (le préfixe `mistralai/` reste à vérifier), et la capacité de
chaque candidat à rendre du JSON strict sur la taxonomie fermée —
observable gratuitement pendant le test de refus, et disqualifiant au
même titre que le refus.

### Cache

Toute réponse de modèle est mise en cache **sur disque**, indexée par
modèle, version de prompt et texte d'entrée. Relancer sans rien
changer doit être **gratuit**.

### Tests, trois niveaux

1. **Sans modèle** : parsing des quatre états de sortie (réponse
   valide, mal formée, refus, erreur), règles du pré-filtre,
   agrégation, et test de trajectoire vérifiant que l'étage spam
   n'est pas appelé quand le légal rejette — le tout avec des
   réponses simulées.
2. **Quelques vrais appels en cache**, pour vérifier le format.
3. **L'évaluation sur le jeu de référence.**

### Évaluation

Jeu de référence d'une **centaine de commentaires annotés à la main**
en trois strates : aléatoire, présélectionné par liste de mots
sensibles, adverse écrit à la main. Coupé en une moitié de
développement et une moitié gelée. **Une seule itération de prompt**
entre les deux.

Mesures : précision et rappel par catégorie légale, taux de faux
positifs sur les cas « choquant mais légal », taux de refus,
stabilité sur exécutions répétées, distribution des décisions sur un
échantillon aléatoire de quelques centaines de lignes.

## 7. Conventions de code

- **Python**, environnement géré avec **uv**.
- **PEP 8 strict**, lignes de **79 caractères** (72 pour docstrings
  et commentaires).
- **Docstrings Google obligatoires** sur chaque fonction :
  description, `Args`, `Returns`, `Raises` si applicable.
- **Type hints** sur toutes les signatures.
- **Orienté objet** quand c'est pertinent.
- **Gestion d'erreurs explicite et documentée**, messages clairs pour
  le débogage.
- Pas d'emojis, pas de langage informel, pas de commentaires
  redondants, pas de fonctionnalité non demandée.

## 8. Plan en six phases

1. **Cadrage** — environnement, chargement des deux CSV, profil
   rapide, test de refus des modèles candidats.
2. **Conception** — taxonomie, format de décision, prompt légal v1,
   prompt spam v1. **Aucun code.**
3. **Jeu de référence** — présélection, cas adverses, annotation
   manuelle par Adrien, split dev/test.
4. **Pipeline**, dans cet ordre : client avec cache et parsing, tests
   niveau un, étage légal, exécution en lot, pré-filtre, étage spam
   et agrégation. Si le temps manque, on sacrifie d'abord le
   pré-filtre, puis l'étage spam.
5. **Évaluation** — dev, analyse des erreurs, prompt v2, held-out sur
   les deux modèles, stabilité, distribution.
6. **Documentation** — README, note usage de l'IA, limites et pistes.

Chaque phase correspond à un ou plusieurs commits dont le message
nomme **la décision prise**, pas seulement le fichier touché.

## 9. Questions encore ouvertes

À poser avant la phase où elles deviennent bloquantes, pas avant.

- Le spam entraîne-t-il un rejet, ou seulement un marquage sans
  rejet ? *Bloquant à la phase 4, étape agrégation.*

La question « quels modèles soumettre au test de refus » est tranchée
— voir la shortlist en section 6.
