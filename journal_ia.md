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

- Généré :
- Corrigé / rejeté :

## Phase 4 — pipeline

- Généré :
- Corrigé / rejeté :

## Phase 5 — évaluation

- Généré :
- Corrigé / rejeté :

## Phase 6 — documentation

- Généré :
- Corrigé / rejeté :
