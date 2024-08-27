"""
La classe Config dans ce fichier contient les configs

Auteur: Nathan Cerisara
"""

from typing import cast

import os
import json

from lib import ConfigError, MissingFileError


# Clés pour les configurations, pour facilement pouvoir les changer si on le veut
KEY_BASE_SAVE_PATH: str = "base_rainbow_instance_save_path"
KEY_MODELS_PATH: str = "models_paths"
KEY_SEARCH_ENGINE_CONFIGS_PATHS: str = "search_engine_configs_paths"
KEY_CONVERSATIONS_ENGINE_CONFIGS_PATHS: str = "conversations_engine_configs_paths"
KEY_NER_ENGINE_CONFIGS_PATHS: str = "ner_engine_configs_paths"
KEY_SOCKET_PORT: str = "socket_port"
KEY_MAIN_DEFAULT_ENGINE_CONFIG_NAME: str = "main_default_engine_config_name"
KEY_MAIN_SERVER_NB_THREADS: str = "main_server_nb_threads"
KEY_MAIN_SERVER_NB_THREADS_SPECIFIC_FOR_TASKS: str = "main_server_nb_threads_specifics_for_tasks"
KEY_SOCKET_MAX_CLIENTS_CONNECTED: str = "socket_max_clients_connected"
KEY_CACHE_TRANSLATION_JSON: str = "translation_cache_json"
KEY_CACHE_DIR_EMBEDDINGS: str = "embedding_cache_dir"
KEY_NER_DICTS_DIR: str = "NER_dicts_dir"
KEY_SOCKET_MESSAGES_DELIMITER: str = "socket_messages_delimiter"


# Liste de toutes les clés pour la configuration
CONFIG_KEYS: list[str] = [
    KEY_BASE_SAVE_PATH,
    KEY_MODELS_PATH,
    KEY_SEARCH_ENGINE_CONFIGS_PATHS,
    KEY_CONVERSATIONS_ENGINE_CONFIGS_PATHS,
    KEY_NER_ENGINE_CONFIGS_PATHS,
    KEY_SOCKET_PORT,
    KEY_MAIN_DEFAULT_ENGINE_CONFIG_NAME,
    KEY_MAIN_SERVER_NB_THREADS,
    KEY_MAIN_SERVER_NB_THREADS_SPECIFIC_FOR_TASKS,
    KEY_SOCKET_MAX_CLIENTS_CONNECTED,
    KEY_CACHE_TRANSLATION_JSON,
    KEY_CACHE_DIR_EMBEDDINGS,
    KEY_NER_DICTS_DIR,
    KEY_SOCKET_MESSAGES_DELIMITER
]


#
class Config():
    """
    Configurations de ce projet
    """

    def __init__(self, config_path: str) -> None:
        """
        Initialise une configuration à partir d'un chemin vers un fichier de configuration json

        Args:
            config_path (str): Chemin vers le fichier de configuration

        Raises:
            MissingFileError: Le fichier demandé n'existe pas
            ConfigError: La clé ___ n'existe pas
        """

        # On vérifie si le fichier de configuration existe bien
        if not os.path.exists(config_path):
            raise MissingFileError(f"Le fichier `{config_path}` n'existe pas!")

        config_dict: dict[str, str | int] = {}

        # On charge le fichier
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = json.load(f)

        # On vérifie qu'il y a bien toutes les clés nécessaires à un bon fichier de configuration
        for key in CONFIG_KEYS:
            if not key in config_dict:
                raise ConfigError(f"La configuration ne possède pas la clé {key}!")

        # On charge les composantes de la configuration, on sait donc que toutes les clés existent bien

        # Chemin de base où les exemples d'instances de Rainbow sont sauvegardés.
        self.base_path_rbi_converted_saved: str = cast(str, config_dict[KEY_BASE_SAVE_PATH])

        # Chemin où sauvegarder les modèles à télécharger localement
        self.models_path: str = cast(str, config_dict[KEY_MODELS_PATH])

        # Chemin vers les configurations de moteur de recherche
        self.search_engine_configs_paths: str = cast(str, config_dict[KEY_SEARCH_ENGINE_CONFIGS_PATHS])

        # Chemin vers les configurations de moteurs de découpe de conversations
        self.conversations_engine_configs_paths: str = cast(str, config_dict[KEY_CONVERSATIONS_ENGINE_CONFIGS_PATHS])

        # Chemin vers les configurations de moteurs de NER
        self.ner_engine_configs_paths: str = cast(str, config_dict[KEY_NER_ENGINE_CONFIGS_PATHS])

        # Port pour la socket
        self.socket_port: int = cast(int, config_dict[KEY_SOCKET_PORT])

        # Configuration par défaut du moteur de recherche pour la socket
        self.main_default_engine_config_name: str = cast(str, config_dict[KEY_MAIN_DEFAULT_ENGINE_CONFIG_NAME])

        # Nombre de threads créés par le serveur qui vont pouvoir gérer des requêtes simultanément
        self.main_server_nb_threads: int = cast(int, config_dict[KEY_MAIN_SERVER_NB_THREADS])

        # Nombre minimum de threads créés par le serveur qui vont pouvoir gérer spécifiquement une seule tâche
        self.main_server_nb_threads_specifics_for_tasks: dict[str, int] = cast(int, config_dict[KEY_MAIN_SERVER_NB_THREADS_SPECIFIC_FOR_TASKS])

        # Nombre maximal de clients connectés au socket
        self.socket_max_clients_connected: int = cast(int, config_dict[KEY_SOCKET_MAX_CLIENTS_CONNECTED])

        # Chemin vers un fichier de cache de traductions
        self.cache_translations_json: str = cast(str, config_dict[KEY_CACHE_TRANSLATION_JSON])

        # Dossier vers les caches des embeddings pour chaque modèle
        self.cache_dir_embeddings: str = cast(str, config_dict[KEY_CACHE_DIR_EMBEDDINGS])

        # Dossier vers les dictionnaires de NER
        self.ner_dicts_dir: str = cast(str, config_dict[KEY_NER_DICTS_DIR])

        # Séparateur entre les messages envoyés au socket
        self.socket_messages_delimiter: str = cast(str, config_dict[KEY_SOCKET_MESSAGES_DELIMITER])

