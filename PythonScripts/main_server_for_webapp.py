"""
Serveur python avec websockets qui va servir pour la démo pour la recherche sémantique.

Auteur: Nathan Cerisara
"""

# Affichage d'un message pour dire à l'utilisateur ce qu'il se passe
print("Importation des librairies python...")

# Importation des librairies pyhon...
from typing import Optional, Callable
from dataclasses import dataclass

from threading import Thread, Lock, Condition
import signal
import asyncio
import websockets
from websockets import WebSocketServerProtocol as Wsp
import json
import os
import sys
import time

from torch.cuda import is_available as cuda_available

from rainbow_instance import RainbowInstance
from message import Message
from user import User
from bubble import Bubble
from search_engine import SearchSettings
from config import Config
from lib import escapeCharacters
from lib_types import TYPES, GENERAL_CLASSES
from lib_hp_optimization import HPO_ALGORITHMS_TO_SEND
from lib_main_server import MainServer

from main_convert_data_to_rbi import bubble_parser

from global_variables import init_global_variables, save_global_variables, free_global_variables
from profiling import profiling_init, profiling_save_and_stop, profiling_task_start, profiling_last_task_ends

from threads_tasks_server import ThreadsTasksServer, SearchRequest, ConversationCutRequest, ImportRequest, TestBenchmarkWithConfigRequest, HPOAlgorithmRequest, TaskRequest

#
# Classe WebsocketHandler
class WebsocketServer(MainServer):
    """
    Ceci est la classe qui va gérer le serveur websocket pour la démo de l'application de découpe des conversations et de recherche sémantique.
    """

    def __init__(self, conf: Config) -> None:
        """
        Initialisation de du serveur WebSocket.

        Args:
            conf (Config): Fichier de configuration du projet
        """
        super().__init__(conf)

        # On enregistre la configuration
        self.config: Config = conf

        # Port actif du serveur qui va gérer la connexion
        self.port: int = conf.webapp_port

        # Liste des clients websockets connectés
        self.connected_clients: dict[str, dict[str, Optional[Wsp]]] = {}

        # Toutes les fonctions pour gérer les différents types de messages seront ici
        self.messages_types_fcts: dict[str, Callable] = {
            "ping": self.handle_ping,
            "ask_for_rbi_infos": self.handle_rbi_ask_infos,
            "search_request": self.handle_search_request,
            "conversation_cut_request": self.handle_conversation_cut_requests,
            "import_request": self.handle_import_request,
            "hpo_task_configs_and_benchmarks": self.handle_hpo_task_configs_and_benchmarks,
            "hpo_ask_types_and_classes": self.handle_hpo_ask_types_and_classes,
            "hpo_create_new_config_file": self.handle_hpo_create_new_config_file,
            "hpo_save_edited_config_file": self.handle_hpo_save_edited_config_file,
            "hpo_delete_config_file": self.handle_hpo_delete_config_file,
            "hpo_test_config_all_benchmarks": self.handle_hpo_test_config_all_benchmarks_request,
            "hpo_algorithmic_optimization": self.handle_hpo_algorithmic_optimization
        }

        # La liste du nom de toutes les instances Rainbow disponibles
        self.available_rbis: list[str] = []

        # On va la charger
        rbi_name: str
        for rbi_name in os.listdir(self.config.base_path_rbi_converted_saved):
            self.available_rbis.append(rbi_name)

        # Toutes les instances Rainbow ici, chargement à la volée quand on en a besoin
        self.loaded_rbis: dict[str, RainbowInstance] = {}

        #####  #####

        #
        self.mutex_loading_rbi: Lock = Lock()

        #
        self.threads_tasks_server: ThreadsTasksServer = ThreadsTasksServer(conf, self)

        # Mutex pour protéger les envois de message dans le socket
        self.mutex_socket_send: Lock = Lock()

        # Mutex pour protéger l'écriture et la lecture de fichiers de configurations
        self.mutex_read_write_config_files: Lock = Lock()

    #
    def exit_gracefully(self, sig, frame) -> None:
        """
        Fonction qui va intercepter un SIGINT pour fermer les éléments qui pourraient ne pas se fermer.
        """

        # On affiche un petit message dans la console
        print("\nSignal SIGINT reçu.\n")

        #
        save_global_variables()

        # On ferme les threads
        self.threads_tasks_server.exit_threads()

        #
        free_global_variables()

        # On ferme le programme
        sys.exit(0)

    #
    async def handle_client(self, client_ws: Wsp) -> None:
        """
        Fonction de base qui va gérer la connexion d'un client, la réception de ses messages, et sa déconnexion.

        Args:
            client_ws (Wsp): Le Socket du client
        """

        # On va créer un identifiant pour le client
        client_id: str = f"Client {len(self.connected_clients) + 1}"

        # On va ajouter le client aux clients connectés
        self.connected_clients[client_id] = {
            "socket": client_ws,
        }

        # On affiche que le client est connecté
        print(f"{client_id} connected.")

        # On envoie au client qu'il s'est bien connecté au serveur
        await self.send_to_client(client_ws, {
            "type": "connected"
        })

        # Quand un client se connecte, on lui envoie la liste de toutes les rbi disponnibles
        rbi_name: str
        for rbi_name in self.loaded_rbis:
            await self.send_to_client(
                client_ws,
                {
                    "type": "data_rbi_name",
                    "rbi_name": rbi_name,
                    "nb_bubbles": len(self.loaded_rbis[rbi_name].bubbles),
                    "nb_users": len(self.loaded_rbis[rbi_name].users),
                    "nb_messages": len(self.loaded_rbis[rbi_name].messages)
                }
            )
            time.sleep(0.001)

        # Quand un client se connecte, on lui envoie aussi la liste de tous les moteurs de recherche disponnibles
        engine_config_name: str
        for engine_config_name in self.threads_tasks_server.configs_search_engines:
            await self.send_to_client(
                client_ws,
                {
                    "type": "search_engine_configuration",
                    "config_name": engine_config_name,
                    "config_dict": self.threads_tasks_server.configs_search_engines[engine_config_name]
                }
            )
            time.sleep(0.001)

        # Et on lui envoie aussi la configuration par défaut
        if self.config.main_default_engine_config_name in self.threads_tasks_server.configs_search_engines:
            await self.send_to_client(
                client_ws,
                {
                    "type": "default_search_engine_config_name",
                    "config_name": self.config.main_default_engine_config_name,
                }
            )

        # Tant que l'on reçoit des messages du socket du client
        message: str
        async for msg in client_ws:

            if isinstance(msg, bytes):
                continue
            message = msg

            # On affiche message reçu
            print(f"{client_id} sent: {message}")

            # Le try except, c'est pour gérer les erreurs de décodage json
            try:

                # On essaie de décoder le message reçu par le client
                msg_data: dict = json.loads(message)

                # Si le message est malformé, on l'ignore, tous les messages biens formés possèdent un champs `type` qui indique de quel type de message il s'agit.
                if "type" not in msg_data:
                    continue

                # Sinon, on cherche la bonne fonction qui va pouvoir traiter le message reçu
                for msg_type in self.messages_types_fcts:
                    if msg_data["type"] == msg_type:
                        await self.messages_types_fcts[msg_type](client_id, client_ws, msg_data)
                        break

            # Si json n'a pas réussit à décoder le message reçu, on ignore, on ne fait rien
            except json.decoder.JSONDecodeError as e:
                continue

        # On déconnecte bien le client
        del self.connected_clients[client_id]
        print(f"{client_id} déconnecté")

    #
    async def send_to_client(self, client_ws: Wsp, message: dict) -> None:
        """
        Envoie un message au client dont le socket est donné.

        Args:
            client_ws (Wsp): Socket du client à qui envoyer le message
            message (dict): Message à envoyer au client
        """

        # On prépare le message
        msg: str = json.dumps(message)

        # On va faire attention à ne pas envoyer pleins de messages en même temps
        self.mutex_socket_send.acquire()

        # On envoie le message
        try:
            await client_ws.send(msg)
        except Exception as e:
            print(f"Error while trying to send {msg} to client {client_ws}")
            print(e)
        finally:
            # On sort de la zone critique
            self.mutex_socket_send.release()

    #
    async def send_to_client_id(self, client_id: str, message: dict) -> None:
        """
        Envoie un message à un client, avec seulement son identifiant.

        Args:
            client_id (str): Identifiant du client à qui on veut envoyer le message
            message (dict): Message à envoyer au client
        """

        # On vérifie que le client est bien connecté
        if client_id not in self.connected_clients:
            return

        # On récupère le socket du client
        socket_client: Optional[Wsp] = self.connected_clients[client_id]["socket"]
        if socket_client is None:
            return

        # On envoie le message
        await self.send_to_client(socket_client, message)

    #
    async def broadcast_to_clients(self, message: dict, excluding_clients: Optional[list[str]] = None) -> None:
        """
        Envoie un message à tous les clients connectés.

        Args:
            message (dict): Message à envoyer
            excluding_clients (Optional[list[str]], optional): Liste des clients à qui ne pas envoyer le message. Valeur par défaut: None.
        """

        # On convertit le message de la forme d'un dictionnaire sous la forme d'une chaine de caractères, bien plus simple à envoyer par le réseau
        msg: str = json.dumps(message)

        # On parcourt tous les clients connectés
        for client_id in self.connected_clients:

            # On vérifie que le client n'est exclus du broadcast
            if excluding_clients is not None and client_id in excluding_clients:
                continue

            # On récupère le socket du client
            socket_client: Optional[Wsp] = self.connected_clients[client_id]["socket"]

            # On envoie le message
            if socket_client is not None:
                await socket_client.send(msg)

    #
    async def send_error(self, client_ws: Wsp, error_msg: str) -> None:
        """
        Envoie un message d'erreur à un client.

        Args:
            client_ws (Wsp): Client à qui envoyer l'erreur
            error_msg (str): Le message d'erreur à envoyer
        """

        # On prépare le message
        msg: str = json.dumps({
            "type": "error",
            "error_message": "Error: " + error_msg
        })

        # On envoie le message d'erreur au client
        await client_ws.send(msg)

    #
    async def handle_ping(self, client_id: str, client_ws: Wsp, message: dict) -> None:
        """
        Fonction de base qui va juste gérer un test de connexion.

        Args:
            client_id (str): Id du client qui a envoyé le message
            client_ws (Wsp): Socket du client qui a envoyé le message
            message (dict): Message reçu par le client
        """

        # On renvoie la réponse au client
        await self.send_to_client(client_ws, {
            "type": "pong"
        })

    #
    async def handle_rbi_ask_infos(self, client_id: str, client_ws: Wsp, message: dict) -> None:
        """
        Fonction qui va renvoyer au client les infos sur une rbi demandée

        Args:
            client_id (str): Id du client qui a envoyé le message
            client_ws (Wsp): Socket du client qui a envoyé le message
            message (dict): Message reçu par le client
        """

        # On teste la requête
        for k in ["rbi_name"]:
            if k not in message:
                # S'il manque un attribut, on annule la requête
                return

        # On récupère les attributs de la requête
        rbi_name: str = message["rbi_name"]

        #
        self.mutex_loading_rbi.acquire()

        try:
            # On teste s'il faut charger la rbi
            if rbi_name not in self.loaded_rbis:
                # La rbi n'est pas chargée, donc il faut la charger
                rbi: RainbowInstance = RainbowInstance(rbi_name, self.config)
                if not rbi.load():
                    # Problème de chargement de la rbi, on annule la requête
                    return
                # Sinon, la rbi s'est bien chargée, on la rajoute dans le dictionnaire
                self.loaded_rbis[rbi.server_name] = rbi
        finally:
            #
            self.mutex_loading_rbi.release()

        # On envoie le message de préparation au transfert
        await self.send_to_client(client_ws, {
            "type": "rbi_prepare_transfer",
            "rbi_name": rbi_name,
            "nb_bubbles": len(self.loaded_rbis[rbi_name].bubbles),
            "nb_users": len(self.loaded_rbis[rbi_name].users),
            "nb_messages": len(self.loaded_rbis[rbi_name].messages)
        })

        # Ensuite, on va envoyer toutes les bulles
        bubble: Bubble
        for bubble in self.loaded_rbis[rbi_name].bubbles.values():
            await self.send_to_client(client_ws, {
                "type": "data_bubble",
                "rbi_name": rbi_name,
                "data_bubble": bubble.export_to_dict()
            })
            time.sleep(0.001)

        # Ensuite, on va envoyer tous les utilisateurs
        user: User
        for user in self.loaded_rbis[rbi_name].users.values():
            await self.send_to_client(client_ws, {
                "type": "data_user",
                "rbi_name": rbi_name,
                "data_user": user.export_to_dict()
            })
            time.sleep(0.001)

        # Ensuite, on va envoyer tous les messages
        msg: Message
        for msg in self.loaded_rbis[rbi_name].messages.values():
            await self.send_to_client(client_ws, {
                "type": "data_message",
                "rbi_name": rbi_name,
                "data_message": msg.export_to_dict()
            })
            time.sleep(0.001)

    #
    async def handle_search_request(self, client_id: str, client_ws: Wsp, message: dict) -> None:
        """
        Fonction qui va traiter la demande de recherche du client sur une rbi demandée

        Args:
            client_id (str): Id du client qui a envoyé le message
            client_ws (Wsp): Socket du client qui a envoyé le message
            message (dict): Message reçu par le client
        """

        # On teste la requête
        for k in ["rbi_name", "engine_config", "user_id", "search_input", "search_settings"]:
            if k not in message:
                # S'il manque un attribut, on annule la requête
                return

        # On récupère les arguments
        rbi_name: str = message["rbi_name"]
        engine_config: str = message["engine_config"]
        user_id: str = str(message["user_id"])
        search_input: str = message["search_input"]
        search_settings_dict: dict = message["search_settings"]

        # On prépare l'objet search_settings
        search_settings: SearchSettings = SearchSettings(**search_settings_dict)

        # On va préparer la demande de recherche
        search_request: SearchRequest = SearchRequest(
            task_type="search",
            client_id=client_id,
            client=client_ws,
            search_input=search_input,
            user_id=user_id,
            search_settings=search_settings,
            engine_config=engine_config,
            rbi_name=rbi_name
        )

        #
        self.threads_tasks_server.add_task_request_to_queues("search", search_request)

    #
    async def handle_import_request(self, client_id: str, client_ws: Wsp, message: dict) -> None:
        """
        Fonction qui va traiter la demande d'importation d'une requête

        Args:
            client_id (str): Id du client qui a envoyé le message
            client_ws (Wsp): Socket du client qui a envoyé le message
            message (dict): Message reçu par le client
        """

        # On teste la requête
        for k in ["rbi_name", "bubble_name", "bubble_text_to_import"]:
            if k not in message:
                # S'il manque un attribut, on annule la requête
                return

        # On récupère les arguments
        rbi_name: str = message["rbi_name"]
        bubble_name: str = message["bubble_name"]
        bubble_text_to_import: str = message["bubble_text_to_import"]

        # On va préparer la requête
        import_request: ImportRequest = ImportRequest(
            task_type="bubble_import",
            client_id=client_id,
            client=client_ws,
            rbi_name=rbi_name,
            bubble_name=bubble_name,
            bubble_text_to_import=bubble_text_to_import
        )

        # On ajoute la requête dans la liste des requêtes à exécuter et on réveilles les threads qui peuvent s'en occuper
        self.threads_tasks_server.add_task_request_to_queues("bubble_import", import_request)

    #
    async def handle_conversation_cut_requests(self, client_id: str, client_ws: Wsp, message: dict) -> None:
        """
        Fonction qui va traiter la demande de découpe de conversatoin du client sur une bulle d'une rbi demandée

        Args:
            client_id (str): Id du client qui a envoyé le message
            client_ws (Wsp): Socket du client qui a envoyé le message
            message (dict): Message reçu par le client
        """

        # On teste la requête
        for k in ["rbi_name", "bubble_id"]:
            if k not in message:
                # S'il manque un attribut, on annule la requête
                return

        # On récupère les arguments
        rbi_name: str = message["rbi_name"]
        bubble_id: str = str(message["bubble_id"])

        # On va préparer la demande de recherche
        conversation_cut_request: ConversationCutRequest = ConversationCutRequest(
            task_type="conversation_cut",
            client_id=client_id,
            client=client_ws,
            rbi_name=rbi_name,
            bubble_id=bubble_id
        )

        #
        self.threads_tasks_server.add_task_request_to_queues("conversation_cut", conversation_cut_request)

    #
    async def handle_hpo_task_configs_and_benchmarks(self, client_id: str, client_ws: Wsp, message: dict) -> None:
        """
        Fonction qui va renvoyer au client les fichiers de configurations de moteurs et benchmarks sur la tâche demandée.

        Args:
            client_id (str): Id du client qui a envoyé le message
            client_ws (Wsp): Socket du client qui a envoyé le message
            message (dict): Message reçu par le client
        """

        # On teste la requête
        for k in ["task"]:
            if k not in message:
                # S'il manque un attribut, on annule la requête
                return

        # On récupère les attributs de la requête
        task: str = message["task"]

        config_dicts_list: list[dict] = []
        benchmarks_names_list: list[str] = []
        default_config: str = ""

        if task == "NER":
            config_dicts_list = self.threads_tasks_server.configs_NER_engines.values()
            benchmarks_names_list = self.threads_tasks_server.tests_benchmarks.all_ner_benchmarks_files
            default_config = "SimpleSyntaxicNER"
        elif task == "conversation_cut":
            config_dicts_list = self.threads_tasks_server.configs_conversations_engines.values()
            benchmarks_names_list = self.threads_tasks_server.tests_benchmarks.all_conversations_benchmarks_files
            default_config = "Clustering Sequentiel"
        elif task == "search":
            config_dicts_list = self.threads_tasks_server.configs_search_engines.values()
            benchmarks_names_list = self.threads_tasks_server.tests_benchmarks.all_search_benchmarks_files
            default_config = "Embeddings all-MiniLM-L6-v2 with NER replacement and translation"

        #
        print(f"HPO client asked configs (-> {len(config_dicts_list)}) and benchmarks (-> {len(benchmarks_names_list)}) for task : {task}")

        # On envoie le message de préparation au transfert
        await self.send_to_client(client_ws, {
            "type": "hpo_prepare_transfer",
            "task": task,
            "nb_configs": len(config_dicts_list),
            "nb_benchmarks": len(benchmarks_names_list),
            "default_config": default_config,
            "hpo_algorithms": HPO_ALGORITHMS_TO_SEND
        })

        # Ensuite, on va envoyer toutes les configs
        config: dict
        for config in config_dicts_list:
            await self.send_to_client(client_ws, {
                "type": "hpo_data_config",
                "task": task,
                "config": config
            })
            time.sleep(0.001)

        # Ensuite, on va envoyer tous les benchmarks
        benchmark_name: str
        for benchmark_name in benchmarks_names_list:
            await self.send_to_client(client_ws, {
                "type": "hpo_data_benchmark",
                "task": task,
                "benchmark_name": benchmark_name
            })
            time.sleep(0.001)

    #
    async def handle_hpo_ask_types_and_classes(self, client_id: str, client_ws: Wsp, message: dict) -> None:
        """
        Fonction qui va renvoyer au client les classes / types des moteurs et des algorithmes.

        Args:
            client_id (str): Id du client qui a envoyé le message
            client_ws (Wsp): Socket du client qui a envoyé le message
            message (dict): Message reçu par le client
        """

        #
        print(f"HPO client asked types / classes")

        # On envoie le message de préparation au transfert
        await self.send_to_client(client_ws, {
            "type": "hpo_types_and_classes",
            "types": TYPES,
            "general_classes": GENERAL_CLASSES,
        })

    #
    async def handle_hpo_create_new_config_file(self, client_id: str, client_ws: Wsp, message: dict) -> None:
        """
        Fonction qui va créer un nouveau fichier de configurations de moteur sur la tâche demandée.

        Args:
            client_id (str): Id du client qui a envoyé le message
            client_ws (Wsp): Socket du client qui a envoyé le message
            message (dict): Message reçu par le client
        """

        # On teste la requête
        for k in ["task", "engine_config_name", "config"]:
            if k not in message:
                # S'il manque un attribut, on annule la requête
                return

        # On récupère les attributs de la requête
        task: str = message["task"]

        #
        file_name: str = "config_file_" + task + "_" + escapeCharacters(message["config"]["config_name"]) + ".json"

        #
        print(f"Received request create new config file for task {task} with name {file_name}")

        #
        self.mutex_read_write_config_files.acquire()

        try:
            #
            if task == "NER":
                with open(self.config.ner_engine_configs_paths + file_name, "w", encoding="utf-8") as f:
                    json.dump(message["config"], f)
                #
                self.threads_tasks_server.configs_NER_engines[message["engine_config_name"]] = message["config"]
                self.threads_tasks_server.configs_NER_engines_file_paths[message["engine_config_name"]] = self.config.ner_engine_configs_paths + file_name

            elif task == "conversation_cut":
                with open(self.config.conversations_engine_configs_paths + file_name, "w", encoding="utf-8") as f:
                    json.dump(message["config"], f)
                #
                self.threads_tasks_server.configs_conversations_engines[message["engine_config_name"]] = message["config"]
                self.threads_tasks_server.configs_conversation_engines_file_paths[message["engine_config_name"]] = self.config.conversations_engine_configs_paths + file_name

            elif task == "search":
                with open(self.config.search_engine_configs_paths + file_name, "w", encoding="utf-8") as f:
                    json.dump(message["config"], f)
                #
                self.threads_tasks_server.configs_search_engines[message["engine_config_name"]] = message["config"]
                self.threads_tasks_server.configs_search_engines_file_paths[message["engine_config_name"]] = self.config.search_engine_configs_paths + file_name
        finally:
            #
            self.mutex_read_write_config_files.release()

    #
    async def handle_hpo_save_edited_config_file(self, client_id: str, client_ws: Wsp, message: dict) -> None:
        """
        Fonction qui va créer un nouveau fichier de configurations de moteur sur la tâche demandée.

        Args:
            client_id (str): Id du client qui a envoyé le message
            client_ws (Wsp): Socket du client qui a envoyé le message
            message (dict): Message reçu par le client
        """

        # On teste la requête
        for k in ["task", "engine_config_name", "config"]:
            if k not in message:
                # S'il manque un attribut, on annule la requête
                return

        # On récupère les attributs de la requête
        task: str = message["task"]

        #
        file_path: str = ""
        #
        if task == "NER":
            file_path = self.threads_tasks_server.configs_NER_engines_file_paths[message["engine_config_name"]]
            if message["config"]["config_name"] != message["engine_config_name"]: # Renommage de nom de config
                del(self.threads_tasks_server.configs_NER_engines[message["engine_config_name"]])
                del(self.threads_tasks_server.configs_NER_engines_file_paths[message["engine_config_name"]])
                self.threads_tasks_server.configs_NER_engines[message["config"]["config_name"]] = message["config"]
                self.threads_tasks_server.configs_NER_engines_file_paths[message["config"]["config_name"]] = file_path
            else:
                self.threads_tasks_server.configs_NER_engines[message["engine_config_name"]] = message["config"]
        #
        elif task == "conversation_cut":
            file_path = self.threads_tasks_server.configs_conversation_engines_file_paths[message["engine_config_name"]]
            if message["config"]["config_name"] != message["engine_config_name"]: # Renommage de nom de config
                del(self.threads_tasks_server.configs_conversations_engines[message["engine_config_name"]])
                del(self.threads_tasks_server.configs_conversation_engines_file_paths[message["engine_config_name"]])
                self.threads_tasks_server.configs_conversations_engines[message["config"]["config_name"]] = message["config"]
                self.threads_tasks_server.configs_conversation_engines_file_paths[message["config"]["config_name"]] = file_path
            else:
                self.threads_tasks_server.configs_conversations_engines[message["engine_config_name"]] = message["config"]

        elif task == "search":
            file_path = self.threads_tasks_server.configs_search_engines_file_paths[message["engine_config_name"]]
            if message["config"]["config_name"] != message["engine_config_name"]: # Renommage de nom de config
                del(self.threads_tasks_server.configs_search_engines[message["engine_config_name"]])
                del(self.threads_tasks_server.configs_search_engines_file_paths[message["engine_config_name"]])
                self.threads_tasks_server.configs_search_engines[message["config"]["config_name"]] = message["config"]
                self.threads_tasks_server.configs_search_engines_file_paths[message["config"]["config_name"]] = file_path
            else:
                self.threads_tasks_server.configs_search_engines[message["engine_config_name"]] = message["config"]

        else:
            return

        #
        print(f"Received request edit config file for task {task} at {file_path}")

        #
        self.mutex_read_write_config_files.acquire()

        try:
            #
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(message["config"], f)
        finally:
            #
            self.mutex_read_write_config_files.release()

    #
    async def handle_hpo_delete_config_file(self, client_id: str, client_ws: Wsp, message: dict) -> None:
        """
        Fonction qui va créer un nouveau fichier de configurations de moteur sur la tâche demandée.

        Args:
            client_id (str): Id du client qui a envoyé le message
            client_ws (Wsp): Socket du client qui a envoyé le message
            message (dict): Message reçu par le client
        """

        # On teste la requête
        for k in ["task", "engine_config_name"]:
            if k not in message:
                print(f"Missing request attribute : {k}")
                # S'il manque un attribut, on annule la requête
                return

        # On récupère les attributs de la requête
        task: str = message["task"]

        #
        file_path: str = ""

        #
        if task == "NER":
            file_path = self.threads_tasks_server.configs_NER_engines_file_paths[message["engine_config_name"]]

        elif task == "conversation_cut":
            file_path = self.threads_tasks_server.configs_conversation_engines_file_paths[message["engine_config_name"]]

        elif task == "search":
            file_path = self.threads_tasks_server.configs_search_engines_file_paths[message["engine_config_name"]]

        else:
            return

        #
        print(f"Received request delete config file for task {task} at path {file_path}")

        #
        self.mutex_read_write_config_files.acquire()

        try:
            #
            if task == "NER":
                del self.threads_tasks_server.configs_NER_engines[message["engine_config_name"]]
                del self.threads_tasks_server.configs_NER_engines_file_paths[message["engine_config_name"]]

            elif task == "conversation_cut":
                del self.threads_tasks_server.configs_conversations_engines[message["engine_config_name"]]
                del self.threads_tasks_server.configs_conversation_engines_file_paths[message["engine_config_name"]]

            elif task == "search":
                del self.threads_tasks_server.configs_search_engines[message["engine_config_name"]]
                del self.threads_tasks_server.configs_search_engines_file_paths[message["engine_config_name"]]

            #
            os.remove(file_path)
        finally:
            #
            self.mutex_read_write_config_files.release()

    #
    async def handle_hpo_test_config_all_benchmarks_request(self, client_id: str, client_ws: Wsp, message: dict) -> None:
        """
        Fonction qui va traiter la demande d'une requête de test de benchmarks

        Args:
            client_id (str): Id du client qui a envoyé le message
            client_ws (Wsp): Socket du client qui a envoyé le message
            message (dict): Message reçu par le client
        """

        # On teste la requête
        for k in ["task", "config_dict", "test_benchmark_type"]:
            if k not in message:
                # S'il manque un attribut, on annule la requête
                return

        # On récupère les arguments
        task: str = message["task"]
        config_dict: dict = message["config_dict"]
        test_benchmark_type: str = message["test_benchmark_type"]

        # On va préparer la demande de recherche
        test_request: TestBenchmarkWithConfigRequest = TestBenchmarkWithConfigRequest(
            task_type="test_benchmark_with_config",
            client_id=client_id,
            client=client_ws,
            task=task,
            engine_config_dict=config_dict,
            test_benchmark_type=test_benchmark_type
        )

        #
        if test_benchmark_type == "curve_test":
            # On teste la requête
            for k in ["param_values", "param_pts_ids"]:
                if k not in message:
                    # S'il manque un attribut, on annule la requête
                    return

            # On ajoute les attributs à la requête
            test_request.param_values = message["param_values"]
            test_request.param_pts_ids = message["param_pts_ids"]

        #
        self.threads_tasks_server.add_task_request_to_queues("test_benchmark_with_config", test_request)

    #
    async def handle_hpo_algorithmic_optimization(self, client_id: str, client_ws: Wsp, message: dict) -> None:
        """
        Fonction qui va traiter la demande d'une requête d'optimisation algorithmique des hyper-paramètres

        Args:
            client_id (str): Id du client qui a envoyé le message
            client_ws (Wsp): Socket du client qui a envoyé le message
            message (dict): Message reçu par le client
        """

        # On teste la requête
        for k in ["id_request", "task", "base_engine_config", "hyper_parameters_to_optimize", "benchmarks_to_optimize", "algorithm_parameters", "algo_name"]:
            if k not in message:
                # S'il manque un attribut, on annule la requête
                return

        # On récupère les arguments
        id_request: int = message["id_request"]
        task: str = message["task"]
        base_engine_config: dict = message["base_engine_config"]
        hyper_parameters_to_optimize: dict = message["hyper_parameters_to_optimize"]
        benchmarks_to_optimize: dict[str, float] = message["benchmarks_to_optimize"]
        algorithm_parameters: dict[str, str | int | float] = message["algorithm_parameters"]
        algo_name: str = message["algo_name"]

        # On va préparer la requête
        request: HPOAlgorithmRequest = HPOAlgorithmRequest(
            task_type="hpo_algorithmic_optimization",
            client_id=client_id,
            client=client_ws,
            task=task,
            id_request=id_request,
            base_engine_config=base_engine_config,
            hyper_parameters_to_optimize=hyper_parameters_to_optimize,
            benchmarks_to_optimize=benchmarks_to_optimize,
            algorithm_parameters=algorithm_parameters,
            algo_name=algo_name
        )

        #
        self.threads_tasks_server.add_task_request_to_queues("hpo_algorithmic_optimization", request)

    #
    async def run(self) -> None:
        """
        Fonction qui va lancer le serveur websocket pour la webapp.
        """

        # On va charger toutes les RBIs disponibles
        for rbi_name in os.listdir(self.config.base_path_rbi_converted_saved):

            # La rbi n'est pas chargée, donc il faut la charger
            rbi: RainbowInstance = RainbowInstance(rbi_name, self.config)
            if not rbi.load():
                # Problème de chargement de la rbi, on arrête le serveur
                return
            # Sinon, la rbi s'est bien chargée, on la rajoute dans le dictionnaire
            self.loaded_rbis[rbi.server_name] = rbi

        # On va lancer les threads
        await self.threads_tasks_server.run()

        # On prépare le fait que lorsque l'on interromp le programme avec un Ctrl+C
        signal.signal(signal.SIGINT, self.exit_gracefully)

        # On affiche un message sur la console pour indiquer que le serveur va bien être lancé
        print(f"Server running on the port {self.port}...")

        # On lance le serveur
        async with websockets.serve(self.handle_client, "", self.port):
            await asyncio.Future()  # Execution infinie, ne s'arretera qu'avec un signal SIGINT, SIGTERM ou SIGKILL


#
if __name__ == "__main__":

    # Affichage d'un message pour dire à l'utilisateur ce qu'il se passe
    print("Démarrage de l'application...")

    # On charge la configuration
    conf: Config = Config("config.json")

    # On initialise les variables globales
    init_global_variables(conf)

    # Profiling - init
    # profiling_init("WebApp Python Server")

    # On crée le serveur WebSocket
    server: WebsocketServer = WebsocketServer(conf)

    # On lance le serveur de façon asynchrone
    asyncio.run(server.run())

