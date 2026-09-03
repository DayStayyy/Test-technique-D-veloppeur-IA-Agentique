# Journal d'usage de l'IA

Relevé factuel, une entrée par phase : ce que l'IA a généré, ce qui a
été corrigé ou rejeté. Sert de matière première à la note « usage de
l'IA » du README, rédigée à la main.

## Phase 0 — mise en place

- Généré : Le prompt utilisé pour la création du plan et de la mise en place du projet via une discution avec sur claude desktop.
- Corrigé / rejeté : premier message de commit rejeté, trop verbeux et empilant les termes techniques, réécrit en phrases simples ; consigne donnée à Claude de trancher lui-même au lieu de faire valider chaque point.

## Phase 1 — cadrage

- Généré : environnement uv et configuration ruff ; module de chargement des deux CSV vers un format commun ; module de profil descriptif ; client OpenRouter avec cache disque ; test de refus et ses deux scripts de lancement ; cinq exemples de commentaires illicites ; vérification des identifiants de modèles auprès d'OpenRouter; test de perception des emojis sur les trois modèles.
- Corrigé / rejeté : les cinq commentaires du test de refus sont réécrits à la main, les exemples générés ne servant que de gabarit ; modèle de travail imposé pour la suite, Ministral, au lieu de laisser le choix ouvert jusqu'aux tests finaux.

## Phase 2 — conception

- Généré : recherche et vérification de la jurisprudence sur la provocation implicite ; prompt légal v1, ses trois tests de démarcation et sa liste de ce qui n'est jamais rejeté ; sections « Stratégie » et résultats du README.
- Corrigé / rejeté : ma recommandation de ne retenir que la provocation explicite a été rejetée, à raison : la Cour de cassation admet l'appel implicite dès lors qu'il ne fait pas de doute, le critère retenu devient « appel contre absence d'appel ». Périmètre réduit au légal seul sur toutes les phases, l'étage spam et les motifs éditoriaux étant reportés faute d'être détectables sur un commentaire isolé et non exigés par la consigne. Test emoji demandé, que je n'avais pas prévu : il écarte Ministral et fait basculer le modèle de travail sur Luna.

## Phase 3 — jeu de référence

- Généré : vingt cas adverses, dix illicites et dix leurres, avec la qualification proposée et son raisonnement ; listes de termes de présélection ; module d'échantillonnage à graine fixe ; module de lecture et écriture du jeu de référence avec validation des annotations ; script de construction du jeu ; script d'annotation manuelle à quatre réponses ; sections correspondantes du README.
- Corrigé / rejeté : textes de plusieurs cas adverses réécrits à la main, dont un reformulé autour d'un emoji plutôt que d'un mot explicite ; qualifications proposées conservées, y compris sur les quatre cas que je signalais comme discutables. Première version de la présélection rejetée après lecture des tirages : un mot isolé remontait des commentaires sans rapport, la règle a été refaite en trois listes avec les termes d'action conditionnés à la présence d'une cible. Taxonomie corrigée en fin de phase : l'annotation a révélé qu'une insulte visant un groupe à raison de son origine relève de l'article 33 et non de la provocation de l'article 24 ; un cinquième motif a été ajouté, la liste initiale que j'avais proposée était incomplète. Répartition dev/test corrigée à la main après annotation, les trois illicites du corpus étant tous tombés côté gelé : une ligne déplacée vers le cadrage, entorse assumée et documentée dans le README.

## Phase 4 — pipeline

- Généré : objet de décision et taxonomie en source unique (decision.py) ; parsing des quatre états de sortie ; fonction Moderator.moderate ; 26 tests sans réseau ; script d'exécution en lot ; sections correspondantes du README.
- Corrigé / rejeté : retry accepté sur réponse mal formée uniquement, jamais sur refus ni erreur réseau, décidé avant le code. Pré-filtre abandonné plutôt que codé : proposé par moi avec justification chiffrée, validé sans discussion. Proposition d'utiliser LangGraph pour un futur mini-agent expliquée avec ses coûts et écartée par moi pour la boucle principale, mais retenue comme piste pour la phase 6 à la demande d'Adrien, pour la valeur de démonstration plutôt que la nécessité technique.

## Phase 5 — évaluation

- Généré :
- Corrigé / rejeté :

## Phase 6 — documentation

- Généré :
- Corrigé / rejeté :
