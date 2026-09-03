# Modération de commentaires

Fonction de modération de commentaires en Python. Elle reçoit un
commentaire et éventuellement son contexte (post Facebook ou titre
d'article) et retourne une décision : acceptable ou rejeté.

Contrainte centrale : rejeter les contenus manifestement illégaux au
regard de la loi française, **sans être plus restrictif que la loi**.

---

## Stratégie

La consigne impose une seule chose : rejeter ce qui est
manifestement illégal au regard de la loi française, sans être plus
restrictif que la loi. Ces deux exigences ne sont pas symétriques.
La première est facile — un LLM rejette volontiers. La seconde est
tout le travail.

Le comportement par défaut d'un modèle se situe très au-dessus de la
ligne légale : il rejette la vulgarité, l'insulte, la critique
politique ou religieuse, l'ironie. Or les corpus fournis sont
remplis de commentaires exactement de ce type. Le premier
commentaire du fichier articles traite le niqab de « déguisement » :
c'est méprisant, et c'est parfaitement légal. Tout le prompt consiste
donc à **ramener le modèle à la ligne légale, pas à le brider**.

### Le fondement juridique

La modération se limite à quatre motifs, en liste fermée :
provocation à la haine, à la discrimination ou à la violence ;
contestation ou apologie de crimes contre l'humanité ; apologie du
terrorisme ; contenu pédopornographique.

Trois distinctions font le travail, et ce sont elles qui figurent
dans le prompt.

**Provoquer n'est pas détester.** La loi punit la *provocation*,
c'est-à-dire un appel ou une exhortation. La Cour de cassation admet
que cet appel soit implicite, mais exige qu'il existe : un propos
même outrageant qui ne contient aucun appel, fût-il voilé, n'est pas
une provocation. Le critère retenu n'est donc pas « explicite contre
implicite » mais **« appel contre absence d'appel »**.

**Un groupe de personnes n'est pas une idée.** La loi protège les
personnes visées pour leur origine, leur religion, leur sexe, leur
orientation ou leur handicap. Elle ne protège ni les religions, ni
les idéologies, ni les partis, ni les gouvernements. Il n'existe pas
de délit de blasphème en France.

**Faire l'apologie n'est pas expliquer.** Présenter un crime comme
légitime est une apologie ; le contextualiser ou le dire prévisible
n'en est pas une, même dit de façon indécente.

À cela s'ajoute une règle de décision issue du mot « manifestement »
lui-même : **en cas de doute, la décision est « acceptable »**. Le
modèle signale son hésitation dans un champ dédié, qui ne modifie
jamais la décision.

La diffamation et l'injure envers une personne identifiée sont
volontairement exclues : elles supposent une appréciation du
contexte, de la vérité des faits et de la bonne foi, et ne sont donc
pas manifestement illicites.

### Périmètre

Le système ne juge que le légal. Les critères éditoriaux — spam,
hors-sujet, toxicité — sont hors périmètre tant que la partie légale
n'est pas validée sur l'ensemble des phases, l'objectif du test
portant sur elle. Le champ « motifs éditoriaux » existe dans l'objet
de décision et reste toujours vide ; il n'est pas demandé au modèle.

Sources juridiques :
[curseur de la provocation fixé par la Cour de cassation](https://www.europedeslibertes.eu/article/provocation-a-la-haine-a-la-discrimination-ou-a-la-violence-a-legard-dun-groupe-de-personnes-a-raison-de-leur-religion-le-curseur-fixe-par-la-cour-de-cassation-pour-qualifier-l/),
[les nouveaux contours de la provocation à la haine](https://droit.cairn.info/revue-legipresse-2019-HS1-page-33?lang=fr),
[limites admissibles de la liberté d'expression](https://www.legipresse.com/011-46207-Le-delit-de-provocation-a-la-discrimination-la-violence-ou-la-haine-raciale-et-les-limites-admissibles-de-la-liberte-d-expression.html).

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

### Test de perception des emojis

Le profil a montré 132 commentaires réduits à des emojis, et
beaucoup d'autres en contiennent. Un emoji n'est pas un ornement :
il peut porter à lui seul le sens d'un commentaire, y compris un
sens illicite — un emoji singe adressé à une personne, par exemple.
Encore faut-il que le modèle le perçoive correctement.

Sept cas ont été envoyés à chaque modèle, choisis pour leurs
difficultés d'encodage, avec une seule question : nomme ce que tu as
reçu, sans interpréter.

| cas | envoyé | Haiku | Luna | Ministral |
|---|---|---|---|---|
| simple | 🍆 | aubergine | aubergine | **poivron rouge** |
| répétition | 😅😅😅 | correct | correct | **rire aux éclats** |
| drapeau | 🇫🇷 | correct | correct | correct |
| séquence jointe | 👨‍👩‍👧 | correct | correct | **compté deux fois** |
| teinte de peau | 👍🏿 | correct | correct | **dédoublé** |
| chargé | 🐒 | singe | singe | singe |
| mélange texte | Bravo 👏 honte 🤮 | correct | correct | **grimace au lieu de vomit** |

Haiku et Luna : 7 sur 7. **Ministral : trois erreurs d'identification
et deux erreurs de comptage** sur les séquences multi-caractères.

Contrairement au test de refus, ce test départage. À nuancer sur deux
points : Ministral se trompe sur des emojis anodins et identifie
correctement le seul du lot pouvant porter une charge raciste, et les
commentaires purement emoji ne pèsent que 0,66 % du corpus. Le risque
reste néanmoins réel pour un emoji mal perçu au milieu d'un texte.

### Modèle utilisé pendant le développement

Le test de refus n'élimine personne, le test emoji écarte Ministral.
Le développement se poursuit donc avec **GPT-5.6 Luna**
(`openai/gpt-5.6-luna`) : 7 sur 7 en perception, et le moins cher des
deux modèles restants.

C'est un choix de travail, pas le choix final. La comparaison des
trois candidats est reportée aux tests finaux, sur le jeu de
référence gelé. C'est le seul moment où elle a du sens.

## Lancement et tests

*(à compléter — phase 6)*

## Usage de l'IA

*(à compléter — phase 6)*

## Limites et pistes

*(à compléter — phase 6)*
