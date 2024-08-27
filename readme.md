# ALE - Découpage des conversations Rainbow et recherche sémantique

## Description générale

Ceci est le dépôt github de mon projet de découpage des conversations Rainbow et de recherche sémantique pour mon stage de 3 mois à Alcatel-Lucent-Enterprise.

S'inspire de premiers travaux initiaux ici : https://github.com/nath54/SemanticSearch-DiscordBot.

## Comment ca marche ?

Je complèterais cette partie plus tard, mais pour l'instant, je souhaite juste notifier que tous les scripts à exécuter pour les différentes tâches sont tous des fichiers python dont le nom commence par `main_`, tous les autres fichiers sont des modules/librairies.

Un rapport technique complet est disponible ici: [lien](documents/Rapport%20Technique%20Stage%20ALE%202024%20Nathan%20Cerisara.pdf).

## Comment faire tourner les scripts sur sa machine?

*<u>Note:</u> ces explications sont destinées à un public un minimum averti de l'utilisation de python et d'une console de commandes.*


**• étape 0 : Cloner ou télécharger le répertoire github**

*◽ Cloner depuis la ligne de commande*

```shell
git clone https://github.com/nath54/SemanticSearch-ALE/
```


*◽ télécharger directement*

https://github.com/nath54/SemanticSearch-ALE/archive/refs/heads/main.zip


**• étape 0.1 : installer une version récente de python >= 3.10 (à vérifier la version minimale, 3.12 fonctionne bien)**

Chercher sur internet si vous ne savez pas faire : https://www.python.org/downloads/


**• étape 0.2 (Optionnel, mais recommandé si plusieurs projets python) : Utiliser un environnement virtuel python**

*◽ Créer un environnement si aucun n'est créé*

```shell
python -m venv semantic_search
```


*◽ Utiliser l'environnement virtuel python*

```shell
source semantic_search/bin/activate
```


*◽ à la fin, si on veut sortir de l'environnement*

```shell
deactivate
```


**• étape 1 : installer les librairies python nécessaires**

```shell
python -m pip install --upgrade --upgrade-strategy eager -r ./requirements.txt
```


**• étape 2 : modifier les configurations par défaut si besoins spécifiques**

Le fichier de configuration général se situe à l'endroit : `PythonScripts/config.json`.

Voici ma configuration par défaut :

```json
{
    "base_rainbow_instance_save_path": "../SavedImported_RBI/",
    "base_path_data_to_convert": "../DataToImport/",
    "models_paths" : "../models/",
    "search_engine_configs_paths": "../Configs_SearchEngines/",
    "conversations_engine_configs_paths": "../Configs_ConversationEngines/",
    "ner_engine_configs_paths": "../Configs_NER_Engines/",
    "tests_benchmarks_paths": "../TestsBenchmarks/",
    "webapp_port": 42042,
    "main_default_engine_config_name": "Embeddings all-MiniLM-L6-v2 with NER Engine and translation",
    "main_server_nb_threads": 5,
    "main_server_nb_threads_specifics_for_tasks": {
        "search": 1,
        "conversation_cut": 1,
        "bubble_import": 1,
        "test_benchmark_with_config": 1
    },
    "benchmarks_results_json": "../WebApp/data_benchmarks/benchmark_results.json",
    "benchmarks_results_js": "../WebApp/data_benchmarks/benchmark_results.js",
    "benchmark_data_json": "../WebApp/data_benchmarks/data_benchmarks.json",
    "translation_cache_json": "../cache/translations",
    "embedding_cache_dir": "../cache/embeddings/",
    "NER_dicts_dir": "../Dicts_NER/"
}
```

Il se peut qu'il y ait des modifications supplémentaires pour certaines configurations, par exemple, si le port de la web-app est modifié, il faudra aussi le modifier dans le script javascript de la webapp, parce que la webapp est juste une page web statique sans serveur http, et à causes de certaines sécurités, il n'est pas possible d'ouvrir un fichier json depuis un script javascript d'une page web statique sans serveur http.


**• étape 3 : ajouter les données de bulles supplémentaires qui sont confidentielles ou personnelles**

L'environnement de test/benchmarks fonctionne avec des Fausses Instances Rainbow, qui sont construites chacune à partir d'un sous-dossier `/DataToImport/`. Pour que ce soit clair, chaque sous dossier de `/DataToImport/` définit une instance Rainbow différente.


**• étape 4 : Construire ces Instances Rainbow**

Il suffit de lancer le script python :

```shell
# Si vous n'êtes pas ou plus dans le dossier PythonScripts depuis votre console
cd PythonScripts/
```

```shell
# Lancer le script python
python main_convert_data_to_rbi.py
```

Attention! Il est impératif de lancer les scripts python depuis le sous-dossier `/PythonScripts/`. Sinon, les scripts ne pourront pas trouver le fichier de config pour récupérer toutes les autres configurations.


**• étape 5 : utiliser les 2 scripts possibles**

Maintenant, tout est prêt pour soit lancer le seveur pour la démo, soit effectuer des benchmarks!


*◽ Lancer le serveur*

```shell
# Si vous n'êtes pas ou plus dans le dossier PythonScripts depuis votre console
cd PythonScripts/
```

```shell
# Lancer le script python
python main_server_for_webapp.py
```

Et voilà, le serveur est lancé.

Et vous allez pouvoir utiliser la démo sur la page web locale : `/WebApp/demo.html`.

***Rappel:***  Pour ouvrir une page web statique locale sur votre ordinateur, il faut ouvrir la page `file://le_chemin_absolu_ou_est_le_repertoire_du_projet/WebApp/demo.html` sur votre navigateur web préféré.


*◽ Lancer les benchmarks*

Pour les benchmarks il est important de comprendre comment cela fonctionne.

Le script va récupérer toutes les configurations de moteur de recherche `/ConfigsSearchEngines/`

Il va ensuite les charger une par une. Pour chaque configuration de recherche, on ne va exécuter que celles qui sont possibles d'éxécuter sur la machine actuelle. Par exemple, celles qui ont besoin de cuda ne vont pas s'éxécuter s'il n'y a pas de cartes graphiques NVIDIA sur la machine.

Ensuite, toujours pour chaque configuration de moteur de recherche, le script va tester chaque benchmark situé dans le dossier `/TestsBenchmarks/`.

Les benchmarks peuvent prendre un peu de temps à s'éxécuter, surtout la première fois, où il n'y a pas encore de cache d'embeddings et de traduction (les traductions peuvent prendre beaucoup de temps à s'éxécuter pour la première fois quand il faudra en faire plusieurs milliers).

***Utile:*** Il est possible de désactiver une configuration de moteur de recherche en renommant le fichier en rajoutant un `.` au début du nom du fichier de configuration à désactiver.

Le script pour lancer les benchmarks se lance donc avec la commande suivante :

```shell
# Si vous n'êtes pas ou plus dans le dossier PythonScripts depuis votre console
cd PythonScripts/
```

```shell
# Lancer le script python
python main_tests_benchmarks.py
```

Et vous allez pouvoir voir les résultats directement sur la page web locale : `/WebApp/benchmarks.html` (bien sur sans à avoir à lancer de serveur car page web statique!).

***Rappel:***  Pour ouvrir une page web statique locale sur votre ordinateur, il faut ouvrir la page `file://le_chemin_absolu_ou_est_le_repertoire_du_projet/WebApp/benchmarks.html` sur votre navigateur web préféré.


## Accronymes redondants dans ce projet

- ALE: Alcatel-Lucent-Enterprise
- RBI: RainBow Instance
