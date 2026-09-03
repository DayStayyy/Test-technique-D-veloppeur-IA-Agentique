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

La modération se limite à cinq motifs, en liste fermée : provocation
à la haine, à la discrimination ou à la violence ; injure visant une
personne ou un groupe à raison d'une caractéristique protégée ;
contestation ou apologie de crimes contre l'humanité ; apologie du
terrorisme ; contenu pédopornographique.

Le deuxième motif a été ajouté à la fin de la phase 3, en annotant.
La taxonomie ne comportait d'abord que la provocation, article 24 de
la loi de 1881. Or l'injure visant un groupe à raison de son origine
ou de sa religion est un délit distinct, article 33, et le corpus en
contenait un exemple manifeste. Le classer acceptable aurait été
absurde ; le ranger sous la provocation aurait été juridiquement
faux, l'insulte ne comportant aucun appel. Le trou venait de la
conception, pas des données.

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

La diffamation envers une personne identifiée est volontairement
exclue : elle suppose une appréciation du contexte, de la vérité des
faits et de la bonne foi, et n'est donc pas manifestement illicite.
L'injure envers une personne prise pour elle-même l'est également —
traiter un élu d'incompétent ou de voleur reste licite. Seule
l'injure rattachée à une caractéristique protégée est retenue.

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

### Le contexte conversationnel manque, surtout côté Facebook

Une part importante des commentaires ne répond pas à l'article ou au
post, mais **à un autre commentaire**. Sur Facebook, la convention
veut qu'on ouvre son message par le nom de la personne à qui l'on
s'adresse. En comptant les commentaires qui commencent par un nom
propre, on obtient un ordre de grandeur :

| | commence par un nom propre |
|---|---|
| commentaires d'articles | 264 / 10 000 — 2,6 % |
| commentaires de posts | **3 834 / 10 000 — 38,3 %** |

Le repérage est approximatif : il attrape aussi des commentaires qui
s'ouvrent sur un nom de lieu ou de personnalité. Mais l'écart entre
les deux canaux, quinze fois, ne doit rien à cette imprécision.

Or le message auquel ces commentaires répondent **ne figure pas dans
le jeu de données**. Le champ de contexte contient le post d'origine,
jamais le fil de discussion. Pour près de quatre commentaires
Facebook sur dix, il manque donc l'énoncé qui leur donne leur sens.

Les conséquences sont concrètes et se sont vérifiées à l'annotation.
Les pronoms et les démonstratifs n'ont plus de référent : « ces
gens-là » désigne qui ? L'ironie devient indécidable, puisqu'on ne
sait pas ce qui est moqué. Et certains commentaires sont
littéralement inqualifiables : le jeu de référence en contient un
comparant un groupe à « un corps étranger » qu'un organisme
éliminerait, sans qu'on puisse savoir qui est désigné, faute du
message auquel il répond.

Cette limite pèse identiquement sur l'annotation humaine et sur le
modèle, elle ne fausse donc aucune comparaison entre les deux. Mais
elle plafonne ce que l'un comme l'autre peuvent atteindre, et elle
pousse mécaniquement vers « acceptable » : un commentaire dont on ne
peut pas établir le sens ne peut pas être *manifestement* illicite.

Un système en production disposerait du fil complet. C'est la
première chose à corriger si ce prototype devait servir.

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

### Le jeu de référence

Les données fournies ne sont pas annotées, et on ne peut pas les
faire annoter par un modèle : il serait juge et partie, on
mesurerait sa cohérence avec lui-même, pas sa justesse. L'annotation
est donc manuelle.

Un tirage purement aléatoire ne conviendrait pas non plus : ces
espaces de commentaires sont déjà modérés en amont, et cent
commentaires tirés au sort ne contiendraient quasiment aucun contenu
illicite. Aucun rappel ne serait mesurable. D'où trois strates de
cent commentaires au total.

**Aléatoire (40)** — mesure le taux de faux positifs en conditions
réelles et la distribution des décisions.

**Présélectionnée par mots sensibles (40)** — enrichit en cas
limites. C'est la strate décisive : c'est là que vivent les
commentaires choquants mais légaux, et donc là que le comportement
par défaut d'un modèle se trompe.

**Adverse, écrite à la main (20)** — dix cas illicites, seule source
fiable pour mesurer le rappel, et **dix leurres** licites construits
pour ressembler à de l'illicite. Sans ces leurres, un modèle qui
rejette tout obtiendrait un score parfait sur cette strate.

La présélection repose sur trois listes de termes, jamais sur une
seule. Un mot isolé ne veut rien dire : « dehors » dans « en dehors
d'une journée pluvieuse » n'a aucun intérêt. Les termes d'action —
expulser, virer, brûler — ne retiennent donc un commentaire que
s'ils accompagnent une cible protégée. La strate est ensuite tirée à
parts égales entre commentaires avec appel, qui mesurent le rappel,
et commentaires hostiles sans appel, qui mesurent les faux positifs.

Ce tirage a produit un résultat qui oriente tout le reste :
**sur 20 000 commentaires, 10 seulement associent une cible protégée
à un appel à agir**, et la lecture montre que la plupart sont de
simples coïncidences de vocabulaire — « éliminer un corps étranger »
dans une métaphore médicale. À l'inverse, 544 commentaires visent une
cible sans le moindre appel.

Autrement dit, le corpus fourni ne contient quasiment aucun contenu
manifestement illicite. Deux conséquences. La strate adverse est la
seule source possible de mesure du rappel. Et les deux autres strates
mesureront presque exclusivement les faux positifs — c'est-à-dire
exactement ce que la consigne demande de ne pas produire.

Le jeu est coupé en deux moitiés de composition proche. La première
sert au cadrage du prompt, la seconde est gelée et n'est regardée
qu'une fois, à la fin. Une seule itération de prompt entre les deux,
faute de quoi on s'ajusterait au jeu de test et les chiffres finaux
ne vaudraient rien.

### Une entorse assumée à la répartition

La répartition a été tirée à la construction, avant toute annotation
et avant tout appel au modèle. L'annotation terminée, il s'est avéré
qu'elle plaçait **les trois commentaires illicites issus du corpus du
même côté**, dans la moitié gelée. La moitié de cadrage n'aurait donc
contenu aucun contenu illicite réel, seulement des cas écrits à la
main.

Une ligne a été déplacée vers la moitié de cadrage, en connaissance
des étiquettes. Le choix s'est porté sur le plus net des trois : des
deux autres, l'un porte un doute d'annotation et ferait un mauvais
point d'ancrage, l'autre est le seul exemple d'injure raciale de tout
le jeu et devait rester du côté gelé pour que ce motif reste
mesurable.

Répartition finale : 51 lignes de cadrage contre 49 gelées, la strate
présélectionnée passant de 20/20 à 21/19. La moitié gelée conserve 8
contenus illicites dont 2 issus du corpus.

C'est une entorse au principe, et elle est écrite ici plutôt que
tue. Sa portée est limitée, mais elle signifie que la répartition
finale n'est pas entièrement aveugle aux étiquettes. Un lecteur doit
le savoir pour juger les chiffres.

### L'annotateur n'est pas juriste, et le protocole en tient compte

L'annotation reflète la lecture du droit d'une seule personne, non
juriste, appuyée sur les sources citées plus haut. Prétendre le
contraire fausserait tout ce qui suit. Le protocole intègre donc
cette fragilité au lieu de la masquer.

Chaque annotation porte **deux informations distinctes** : la
décision — illicite ou non — et un **indicateur de doute**. Quatre
réponses sont donc possibles à l'annotation : illicite, illicite mais
incertain, licite, licite mais incertain.

Le modèle produit de son côté son propre indicateur d'incertitude,
qui n'influence jamais sa décision. Croiser les deux donne trois
choses.

D'abord une **mesure de calibration** : le modèle hésite-t-il là où
un humain hésite ? Sans ce croisement, son champ d'incertitude ne
servirait à rien.

Ensuite une **lecture honnête des métriques**. Elles sont publiées
deux fois : sur l'ensemble du jeu, et sur le seul sous-ensemble où
l'annotateur était sûr de lui. Un système qui réussit là où la
vérité terrain est solide est démontré ; s'il échoue surtout sur les
cas douteux, c'est attendu et dit comme tel.

Enfin une **frontière documentable** : les cas où l'humain et le
modèle hésitent tous les deux sont les vrais cas limites du droit, et
alimentent la section des limites.

Une précaution rend l'ensemble valide. L'annotation est **figée avant
tout appel au modèle**. Sans cela, on ajusterait la vérité terrain
sur les réponses obtenues et plus aucun chiffre n'aurait de sens. Si
une relecture juridique conduit ensuite à corriger une annotation,
elle est faite contre le texte de loi et jamais contre l'avis du
modèle, la correction est consignée, et les métriques sont publiées
avant et après.

Sur une centaine de cas dont une quinzaine de douteux, cette
corrélation reste descriptive. Elle n'est pas présentée comme un
résultat statistique.

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
