# SOS Amitié extract data

Ce repo contient des des codes pour extraire automatiquement les données d'SOS Amitié de leur 2 sources : Sosatel et Stats module.


### Motivation

Les données ne sont pas accessible directement sous la forme d'une base de donnée ou d'un fichier unique. Elles sont accessible depuis des sites internets qui disposent de menu pour sélectionner des données ou créer un requête, et d'un bouton pour  télécharger un fichier de données.

Ce système impose une énorme contrainte sur la taille du fichier de données téléchargeable, qui d'après mes tests ne peut pas être supérieur à 110mb, soit ~2 mois de données pour stats module. En d'autres termes, c'est plus de 100 fichiers de données à récupérer et aggréger pour reconstruire les données brutes.

Pour m'épargner cela, j'ai écrit ces scripts qui récupèrent les données automatiquement, s'occupent des convertions de format, fixe les types de variables et retourne un unique fichier parquet des données récupérées.

Il y a 2 modules différents, pour extraire les données de sosatel et de statsmodule.

### Stats module

Stats module contient le plus gros volume de données.

Les données sont téléchargées depuis le site par le biais du navigateur, sous forme de ficher XML, téléchargés au format .xls (pas concrètement un format excel mais excel sait le lire).

Le pipeline comprends 3 scripts :

- **1_extract_statsmodule.py** se connecte à la plateforme, navigue les menus, sélectionne la query, inpute les filtres de dates et enfin télécharge le fichier.

- **2_convert_fake_xls_to_parquet.py** convertis les fichier XLM en fichiers parquet

- **3_prep_stats_module_data.py** prépare les données en appliquant les types de données, répare des erreurs de dates et d'heures et enfin anonymise les écoutants du dataset. Retourne la version finale.

### Sosatel

Sosatel contient les données du centre d'appel.

Les données brutes ne sont pas accessibles, seul des aggrégations de l'activité sont disponibles.

Ces données sont récupérée suivant la même logique que stats module. Le volume de données de Sosatel est bien inférieur donc l'extraction est moins longue et complexe.

## Stack

### Extraction :
- Playwright
- dotenv

L'extraction se fait avec Playwright et des names HTML des éléments pour inputer les valeurs de dates, sélectionner les champs pour l'identifiant et le mot de passe.

>[!WARNING] 
> L'accès aux plateformes nescessite un indentifiant et un mot de passe personnel. Le projet utilise dotenv pour gérer cela.

### Conertion :

- Pandas
- Polars
- lxml
- pyarrow

Polars dans sa version actuelle ne permet pas de lire des fichier HTML ou XML. J'utilise donc Pandas à l'aide de l'engine lxml. 

Polars peut convertir directement un DataFrame Pandas. Ainsi voici le cycle de vie des données :

1. fichier XLM (sur disque)
2. Pandas Dataframes (en mémoire)
3. Polars Dataframe (en mémoire)
4. fichier Parquet (sur disque)

Le script 2 inclue une fonction pour traiter les fichiers qui n'ont pas pu être convertis par Pandas. Pour cela il faut manuellement ouvrir le fichier .xls avec excel et le sauvegarder au format CSV sur le disque. A partir de là la fonction convertis de CSV à Parquet avec polars.

### Préparation

*A ce stade, les données sont regroupées dans un unique fichier parquet.*

La préparation se fait entièrement avec Polars et l'API lazy.
