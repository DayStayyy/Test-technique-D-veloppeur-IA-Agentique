# Test technique — Développeur IA Agentique

**Durée de travail effectif attendue : 4h** (réalisable dans ce délai si vous exploitez correctement des outils comme Claude ou Cursor — c'est même l'un des points évalués).
**Délai de rendu :** 5 jours calendaires à partir de la réception du sujet.

---

## Contexte

Pour ce test, vous allez construire une **fonction de modération de commentaires** : à partir d'un commentaire (et éventuellement de son contexte), le système doit décider s'il est acceptable ou non.

Le sujet est **volontairement ouvert** : on ne vous impose pas la décomposition exacte (un seul agent ou plusieurs), ni les critères de modération, ni le LLM à utiliser. On veut voir comment vous structurez le problème vous-même.

## Mission

1. Concevoir et implémenter une fonction de modération de commentaires en Python, capable de juger un commentaire selon un ou plusieurs critères de votre choix (toxicité, spam, hors-sujet, etc.).
2. **Documenter la stratégie adoptée** : pourquoi cette décomposition (une fonction unique qui juge tout, ou plusieurs modules spécialisés par critère), comment les critères sont évalués puis agrégés en une décision finale, et quels prompts ont été utilisés et pourquoi.
3. **Valider le fonctionnement** du système sur un dataset contenant de nombreux commentaires, et présenter une analyse des résultats (métriques si pertinent, ou analyse qualitative des cas limites, faux positifs/négatifs).

**Règle minimum non négociable** : quels que soient les critères additionnels que vous choisissez, la fonction doit a minima détecter et rejeter les contenus manifestement illégaux au regard de la loi française (incitation à la haine, apologie de crimes contre l'humanité, contenus pédopornographiques, etc.), tout en respectant la liberté d'expression — la modération ne doit pas être plus restrictive que ce qu'impose la loi.

Points volontairement laissés ouverts, à vous de trancher et de documenter votre choix :
- Le nombre et la nature des critères de modération.
- L'architecture : une fonction unique, ou plusieurs modules spécialisés orchestrés en série ou en parallèle.
- Le dataset de validation : deux datasets vous seront fournis, `article_comments.csv` (commentaires sur des articles) et `post_comments.csv` (commentaires sur des posts Facebook) — à vous de choisir comment les exploiter (l'un, l'autre, les deux, avec ou sans distinction de traitement selon le canal).
- Le format de la décision retournée (booléen, score, catégorie + justification...).

## Contraintes techniques

- **Python** (gestion d'environnement libre : uv, venv, poetry...).
- Une clé API OpenRouter peut vous être fournie si nécessaire, vous laissant le choix du ou des modèles utilisés. Une approche hybride règles + LLM est possible si vous la justifiez.
- Le code doit être exécutable localement avec des instructions claires (README).

## Livrables attendus

1. **Code source** (repo Git zippé ou lien).
2. **README** expliquant :
   - la stratégie de modération retenue et sa justification,
   - l'architecture (un schéma simple suffit),
   - le dataset utilisé pour la validation et les résultats obtenus,
   - comment lancer le programme et le tester.
3. **Note "usage de l'IA"** (10–15 lignes) : comment vous avez utilisé Claude/Cursor pendant le test — ce qui a été généré directement, ce que vous avez corrigé ou rejeté, et pourquoi. On ne pénalise pas l'usage massif de l'IA, on évalue votre esprit critique dessus.

## Notes

- Aucune pénalité si tout n'est pas fini : on préfère une stratégie claire et partiellement implémentée à un système complet mais bricolé.
- N'hésitez pas à signaler dans le README ce que vous auriez fait avec plus de temps.
