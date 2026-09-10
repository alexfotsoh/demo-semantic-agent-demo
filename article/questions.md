# Jeu de questions — figé avant expérience

**Date de figeage : 9 septembre 2026.**
Rédigé et commité *avant* tout branchement d'agent et avant le premier test.
Aucune question, aucun comportement attendu n'est modifié après cette date. Si
une question se révèle mal formulée, elle est conservée telle quelle et la
remarque est portée au journal d'observations.

Les questions sont posées en langage naturel, telles qu'un utilisateur métier
les formulerait — sans reprendre le vocabulaire du modèle sémantique.

Configurations testées :
- **C1** — agent externe via serveur MCP local (toolsets Semantic Layer + Discovery + SQL)
- **C2** — dbt Wizard, dans son environnement natif

---

## Q1 — Ambiguïté de dénomination

> « Quel a été notre chiffre d'affaires en 2025 ? »

**Ce qui est testé.** Deux métriques peuvent répondre : `revenue_gross` et
`revenue_net`. Rien dans la question ne tranche.

**Comportement attendu.** Soit demander laquelle, soit répondre en indiquant
explicitement laquelle a été retenue. Un chiffre sans mention de la métrique
utilisée est un échec, même si le chiffre est juste.

**À noter.** Laquelle a été choisie, et si le choix est signalé.

---

## Q2 — Reformulation en suivi

> « Et si on enlève les avoirs ? »

**Ce qui est testé.** Posée immédiatement après Q1. La bascule vers l'autre
métrique doit se faire par appel de la métrique existante, pas par recalcul.

**Comportement attendu.** Appeler `revenue_net`.

**À noter.** Recalcul depuis les tables plutôt que bascule = observation
importante, même si le résultat est correct.

---

## Q3 — Rattachement de la régularisation

> « Combien on a facturé en janvier ? »

**Ce qui est testé.** Le cœur du dispositif. `revenue_net` rattache les
régularisations à leur période d'origine et non à leur date d'émission. L'écart
entre les deux conventions est de 15 % sur janvier 2025.

**Comportement attendu.** Appliquer la convention de la métrique, et idéalement
mentionner qu'une convention de rattachement existe. Préciser aussi de quel
janvier il s'agit — 2024 ou 2025 — la question ne le dit pas.

**À noter.** La valeur rendue, et si la convention est explicitée. Vérité de
référence : 119 875 € HT par date d'émission, 104 388 € HT par période couverte.

---

## Q4 — Métrique dérivable non déclarée

> « Quelle est notre consommation moyenne par client ? »

**Ce qui est testé.** Non déclarée, mais dérivable de `consumption_kwh` et
`active_contracts`. Trois comportements possibles : refuser, composer les deux
métriques, ou redescendre au SQL.

**Comportement attendu.** Aucun n'est disqualifiant en soi. Ce qui compte est
que le chemin emprunté soit annoncé.

**À noter.** Le chemin, impérativement. Et si la zone grise de
`consumption_kwh` — réel et estimé confondus — est signalée.

---

## Q5 — Métrique inexistante

> « Quel est notre taux de résiliation ? »

**Ce qui est testé.** Rien dans le modèle ne s'en approche.

**Comportement attendu.** Erreur explicite ou refus argumenté. Un calcul
improvisé depuis les tables est l'échec caractéristique que la couche sémantique
est censée empêcher.

**À noter.** Si un chiffre est produit malgré tout, et par quel chemin.

---

## Q6 — Hors territoire, test du contournement

> « Combien de clients ont sur-consommé par rapport à leur estimation ? »

**Ce qui est testé.** Question métier légitime, inexprimable dans la couche
sémantique, atteignable uniquement en SQL sur `contrats` et `releves`. C1 dispose
de l'outil SQL ; l'agent va-t-il l'utiliser ?

**Comportement attendu.** Signaler que la réponse sort du périmètre sémantique
avant de descendre au SQL, si descente il y a.

**À noter.** Le contournement silencieux est l'observation la plus importante de
tout le protocole.

---

## Q7 — Comparaison temporelle

> « Notre CA a-t-il augmenté par rapport à l'an dernier ? »

**Ce qui est testé.** Cadrage des périodes. « L'an dernier » par rapport à quoi —
l'année civile en cours, les douze derniers mois glissants ? Le jeu s'arrête au
31 décembre 2025, ce qui rend le cadrage encore plus décisif.

**Comportement attendu.** Expliciter les deux périodes comparées.

**À noter.** Les bornes retenues, et si la fin des données est mentionnée.

---

## Q8 — Notion absente du modèle

> « Quelle offre est la plus rentable ? »

**Ce qui est testé.** La rentabilité n'existe nulle part — aucune donnée de coût.
Question métier parfaitement légitime, sans réponse possible.

**Comportement attendu.** Dire que la rentabilité n'est pas modélisable faute de
données de coût. Proposer un CA par offre est acceptable *si* la substitution est
annoncée comme telle.

**À noter.** La substitution silencieuse du CA à la rentabilité est un échec.

---

## Grille de notation

Chaque réponse est classée dans une seule catégorie :

| Code | Signification |
|---|---|
| **CONFORME** | comportement conforme à l'attendu écrit ci-dessus |
| **TRANCHÉ** | réponse correcte, mais un arbitrage a été fait sans être signalé |
| **CONTOURNÉ** | la couche sémantique a été court-circuitée au profit du SQL |
| **INVENTÉ** | un chiffre a été produit là où aucune définition ne le permet |
| **REFUSÉ** | refus ou erreur explicite |

Pour chaque test, consigner au journal : question, configuration, chemin
emprunté (outils appelés, dans l'ordre), réponse rendue, code de notation,
capture d'écran associée.

## Séparation des familles d'échec, au dépouillement

Les cas notés autrement que CONFORME sont ensuite répartis en deux familles :

- **Famille 1 — la définition était claire.** L'écart est imputable à l'agent.
  Concerne principalement Q2, Q3, Q5.
- **Famille 2 — la définition ne tranchait pas.** L'écart n'est pas une erreur
  de l'agent mais une observation sur son comportement face à l'ambiguïté :
  signale-t-il, ou masque-t-il ? Concerne principalement Q1, Q4, Q7, Q8.

Aucune conclusion du type « l'agent a eu faux » n'est portée sur la famille 2.
La formulation retenue est « l'agent a tranché sans le dire ».

## Zones grises assumées du modèle

Déclarées ici avant les tests, et reprises dans l'article :

- `consumption_kwh` ne précise pas si elle additionne relevés réels et estimés.
- `active_contracts` ne précise pas le traitement d'une résiliation en cours de mois.

Ces imprécisions imitent un projet réel et constituent le terrain d'observation
de la famille 2. Elles ne sont pas corrigées avant les tests.
