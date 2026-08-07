# SOS Amitié extract data

Les données d'activité du call center de l'association sont accessible à travers un dashboard connecté à une bdd SQL. Seules les données des 13 derniers mois sont disponibles (suppression du jour le plus ancien chaque soir)

Je n'ai pas accès à la base sql.

Le dashboard permet d'exporter les données, je me sers donc de cela pour les récupérer.

## Motivation

Je cherche à approximer la Demande réelle pour le service d'SOS Amitié.

La variable "**Appels par heure de la journée**" donne une nombre d'appels reçus.

Appels reçus = Appels pris + appels non pris


## Extraction

Librarie :
- Playwright

Le dashbord est simple et efficace, il y a un input pour la variable d'intérêt et 2 input de date (début et fin). 3 inputs en tout.

A l'aide de Playwright et des names HTML des éléments :
1. le code input les valeurs dans les 3 inputs
2. Exporte les données à l'aide du bouton "exporter"
3. attends une 20aine de seconde
4. recommence pour le jour suivant.
