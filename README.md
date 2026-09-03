# Modération de commentaires

Fonction de modération de commentaires en Python. Elle reçoit un
commentaire et éventuellement son contexte (post Facebook ou titre
d'article) et retourne une décision : acceptable ou rejeté.

Contrainte centrale : rejeter les contenus manifestement illégaux au
regard de la loi française, **sans être plus restrictif que la loi**.

---

## Stratégie

*(à compléter — phase 2)*

## Arbitrages

*(à compléter au fil des phases — quatre ou cinq décisions
structurantes : format de la décision, architecture et agrégation,
protocole d'évaluation, choix du modèle, sacrifices assumés)*

## Architecture

*(à compléter — phase 4)*

### Cache des réponses

Chaque réponse de modèle est écrite sur le disque, dans `.cache/`,
sous une clé calculée à partir de trois éléments : le modèle
interrogé, la version du prompt et le texte envoyé. Avant tout appel,
on regarde si cette clé existe déjà. Si oui, la réponse est relue du
disque, sans appel réseau et sans coût.

Ce mécanisme sert trois objectifs à la fois.

Relancer une évaluation sans rien changer est gratuit et immédiat.
Sur le test de refus, la seconde exécution a servi les 15 réponses
depuis le disque, sans un seul appel réseau.

Les résultats publiés sont reproductibles à l'identique, quelle que
soit la température du modèle. C'est le cache qui garantit la
reproductibilité, pas le réglage de température.

Enfin, réécrire un prompt change sa version, donc la clé, donc
invalide automatiquement les réponses obtenues avec l'ancienne
version. Il n'y a jamais à vider le cache à la main, et aucun risque
de comparer des résultats issus de deux prompts différents.

## Dataset et résultats

### Les corpus fournis

Deux fichiers, **10 000 commentaires chacun**. Ce n'est pas le nombre
de lignes des fichiers, 12 455 et 15 619 : beaucoup de commentaires
contiennent des retours à la ligne.

| | articles | posts |
|---|---|---|
| commentaires | 10 000 | 10 000 |
| longueur médiane | 117 car. | 68 car. |
| doublons exacts | 232 (2,32 %) | 95 (0,95 %) |
| liens seuls | 8 (0,08 %) | 265 (2,65 %) |
| sans lettre ni chiffre | 7 (0,07 %) | 125 (1,25 %) |
| vides | 0 | 0 |
| contexte renseigné | 100 % | 99,97 % |

Les deux canaux ne se ressemblent pas. Les commentaires d'articles
sont deux fois plus longs et se répètent davantage. Les commentaires
de posts Facebook concentrent les liens seuls et les messages réduits
à des emojis.

Deux conséquences pour la suite. La règle de pré-filtre « commentaire
vide » ne servira à rien, il n'y en a aucun dans les deux corpus. Les
règles « lien seul » et « doublon exact » ont en revanche de la
matière, 273 et 339 cas. Restent 132 commentaires sans aucune lettre,
du type `😅😅😅`, qui ne sont ni illégaux ni du spam : il faudra
décider explicitement de ce que le système en fait.

### Test de refus des modèles candidats

Avant de choisir un modèle, il faut vérifier qu'il accepte de faire
le travail. Un modèle de modération peut très bien refuser de
répondre face à un contenu haineux, et aucun prompt ne rattrape un
modèle qui refuse de regarder le texte.

Cinq commentaires manifestement illicites, écrits à la main, ont donc
été soumis aux trois candidats avec une consigne minimale : la liste
des motifs et le format de sortie, rien de plus.

| modèle | classé | mal formé | refus | erreur |
|---|---|---|---|---|
| `anthropic/claude-haiku-4.5` | 5 | 0 | 0 | 0 |
| `openai/gpt-5.6-luna` | 5 | 0 | 0 | 0 |
| `mistralai/ministral-14b-2512` | 5 | 0 | 0 | 0 |

**15 appels sur 15 classés, aucun refus**, et les trois modèles
identifient le bon motif à chaque fois. Aucun candidat n'est
disqualifié.

C'est en soi le résultat à retenir : le test de refus ne départage
rien. Le choix du modèle principal se jouera donc entièrement sur le
critère inverse, le taux de faux positifs sur les commentaires
choquants mais légaux, qui ne sera mesuré qu'à l'évaluation finale.

Observation utile pour l'étage de parsing : deux modèles sur trois
entourent leur JSON de balises Markdown, le troisième renvoie du JSON
nu. Le parseur doit gérer les deux formes.

### Modèle utilisé pendant le développement

Puisque le test de refus n'élimine personne, le développement se
poursuit avec un seul modèle, **Ministral 3 14B**
(`mistralai/ministral-14b-2512`). C'est un choix de travail, pas le
choix final : il permet d'avancer sans multiplier les appels, et il
est à poids ouverts, donc le moins susceptible d'être remplacé ou
retiré sous nos pieds.

La comparaison des trois candidats est reportée aux tests finaux, sur
le jeu de référence gelé. C'est le seul moment où elle a du sens.

## Lancement et tests

*(à compléter — phase 6)*

## Usage de l'IA

*(à compléter — phase 6)*

## Limites et pistes

*(à compléter — phase 6)*
