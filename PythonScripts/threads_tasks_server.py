"""
Serveur python avec websockets qui va servir pour la démo pour la recherche sémantique.

Auteur: Nathan Cerisara
"""

# Affichage d'un message pour dire à l'utilisateur ce qu'il se passe
print("Importation des librairies python...")

# Importation des librairies pyhon...
from typing import Optional, Callable, Any
from dataclasses import dataclass

from threading import Thread, Lock, Condition
import signal
import asyncio
import websockets
from websockets import WebSocketServerProtocol as Wsp
from socket import socket as Sock
import json
import os
import sys
import time
import inspect

from torch.cuda import is_available as cuda_available

from rainbow_instance import RainbowInstance
from message import Message, MessageSearch
from user import User
from bubble import Bubble
from search_engine import SearchEngine, SearchSettings
from conversations_engine import ConversationsEngine, ResultConversationCut
from ner_engine import NER_Engine
from embedding_calculator import EmbeddingCalculator, MessageEmbedding
from config import Config
from lib import FunctionResult, ResultError, ResultSuccess, Date, escapeCharacters
from lib_types import TYPES, GENERAL_CLASSES
from main_tests_benchmarks import TestBenchmarks
from lib_hp_optimization import HPOptimisationAlgorithm, HPO_ALGORITHMS, HPO_ALGORITHMS_TO_SEND
from lib_main_server import MainServer

from main_convert_data_to_rbi import bubble_parser

from global_variables import GlobalVariables, init_global_variables, get_global_variables, save_global_variables, free_global_variables
from profiling import profiling_init, profiling_save_and_stop, profiling_task_start, profiling_last_task_ends


#
# Classe Abstraite représentant une requête à faire pour un thread
@dataclass
class TaskRequest:
    task_type: str
    client_id: str
    client: Wsp | Sock

#
# Classe pour gérer les demande de recherche
@dataclass
class SearchRequest(TaskRequest):
    search_input: str
    user_id: str
    search_settings: SearchSettings
    engine_config: str
    rbi_name: str
    search_msg_id: Optional[str] = None
    search_msg_bubble_id: Optional[str] = None

#
# Classe pour gérer les demandes de découpes des conversations
@dataclass
class ConversationCutRequest(TaskRequest):
    rbi_name: str
    bubble_id: str

#
# Classe pour gérer les demandes d'importation de bulles
@dataclass
class ImportRequest(TaskRequest):
    rbi_name: str
    bubble_name: str
    bubble_text_to_import: str

#
# Classe pour gérer les demandes de tests de benchmarks avec une config
@dataclass
class TestBenchmarkWithConfigRequest(TaskRequest):
    task: str
    engine_config_dict: dict
    test_benchmark_type: str
    param_values: Optional[dict[int, float]] = None
    param_pts_ids: Optional[dict[int, int]] = None

#
# Classe pour gérer les demandes d'optimisation algorithmique des hyper-paramètres
@dataclass
class HPOAlgorithmRequest(TaskRequest):
    task: str
    id_request: int
    base_engine_config: dict
    hyper_parameters_to_optimize: list[dict]
    benchmarks_to_optimize: dict[str, float]
    algorithm_parameters: dict[str, str | int | float]
    algo_name: str

#
# Classe pour gérer les demandes d'ajouts de messages dans les bulles
@dataclass
class AddMessagesToBubbleRequest(TaskRequest):
    rbi_name: str
    bubble_id: str
    msgs_lst: list[dict]


#
# Classe ThreadsTasksServer
class ThreadsTasksServer():
    """
    Ceci est la classe qui va gérer les threads qui vont effectuer les différentes tâches disponibles.
    """

    def __init__(self, conf: Config, main_server: MainServer) -> None:
        """
        Initialisation de du serveur WebSocket.

        Args:
            conf (Config): Fichier de configuration du projet
        """

        # On enregistre la configuration
        self.config: Config = conf

        # Main server (rbis + send_to_client)
        self.main_server: MainServer = main_server

        # Toutes les fonctions et classes pour gérer les différentes types de tâches à faire pour les threads
        self.tasks_types_fcts: dict[str, Callable] = {
            "search": self.search_handler_search,
            "conversation_cut": self.conversation_cut_handler_cut,
            "bubble_import": self.bubble_import_handler_import,
            "test_benchmark_with_config": self.test_benchmarks_handler_test,
            "hpo_algorithmic_optimization": self.hpo_algorithmic_optimization_handler_optimize,
            "add_msgs_to_bubble": self.add_new_messages_to_bubble_handler_add
        }

        # Toutes les configurations de moteurs de recherche ici, chargement à la volée quand on en a besoin
        # Piste d'amélioration: indiquer la "lourdeur" de chaque moteur de recherche et imposer une limite quand au nombre de moteurs "lourds" chargés en même temps.
        self.loaded_search_engines: dict[str, SearchEngine] = {}

        self.load_search_engine_mutex: Lock = Lock()

        # Toutes les configurations de moteurs de recherche ici
        self.configs_search_engines: dict[str, dict] = {}

        # On va enregistrer le nom fichier de chaque configuration
        self.configs_search_engines_file_paths: dict[str, str] = {}

        # On va les charger
        config_file: str
        for config_file in os.listdir(self.config.search_engine_configs_paths):

            # On ne traite pas ceux qui commencent par un "."
            if config_file.startswith("."):
                continue

            #
            with open(f"{self.config.search_engine_configs_paths}{config_file}", "r", encoding="utf-8") as f:
                try:
                    config_dict: dict = json.load(f)
                    self.configs_search_engines[config_dict["config_name"]] = config_dict
                    #
                    self.configs_search_engines_file_paths[config_dict["config_name"]] = f"{self.config.search_engine_configs_paths}{config_file}"
                except Exception as e:
                    pass

        # Toutes les configurations de moteurs de NER ici
        self.configs_NER_engines: dict[str, dict] = {}

        # On va enregistrer le nom fichier de chaque configuration
        self.configs_NER_engines_file_paths: dict[str, str] = {}

        # On va les charger
        for config_file in os.listdir(self.config.ner_engine_configs_paths):

            # On ne traite pas ceux qui commencent par un "."
            if config_file.startswith("."):
                continue

            #
            with open(f"{self.config.ner_engine_configs_paths}{config_file}", "r", encoding="utf-8") as f:
                try:
                    config_dict: dict = json.load(f)
                    self.configs_NER_engines[config_dict["config_name"]] = config_dict
                    #
                    self.configs_NER_engines_file_paths[config_dict["config_name"]] = f"{self.config.ner_engine_configs_paths}{config_file}"
                except Exception as e:
                    pass

        # Toutes les configurations de moteurs de découpe de conversations ici
        self.configs_conversations_engines: dict[str, dict] = {}

        # On va enregistrer le nom fichier de chaque configuration
        self.configs_conversation_engines_file_paths: dict[str, str] = {}

        # On va les charger
        for config_file in os.listdir(self.config.conversations_engine_configs_paths):

            # On ne traite pas ceux qui commencent par un "."
            if config_file.startswith("."):
                continue

            #
            with open(f"{self.config.conversations_engine_configs_paths}{config_file}", "r", encoding="utf-8") as f:
                try:
                    config_dict: dict = json.load(f)
                    self.configs_conversations_engines[config_dict["config_name"]] = config_dict
                    #
                    self.configs_conversation_engines_file_paths[config_dict["config_name"]] = f"{self.config.conversations_engine_configs_paths}{config_file}"
                except Exception as e:
                    pass

        # On charge la classe qui s'occupe des benchmarks
        self.tests_benchmarks: TestBenchmarks = TestBenchmarks()

        ##### CONVERSATION CUT THREADS #####

        # Config pour le moteur de découpe des conversations
        self.conversation_cut_engine_dict: dict = {}
        default_conversation_engine_config_file: str = "config_clustering_seq.json"
        with open(f"{self.config.conversations_engine_configs_paths}{default_conversation_engine_config_file}", "r", encoding="utf-8") as f:
            self.conversation_cut_engine_dict = json.load(f)

        # Moteurs de découpe des conversations, indexés par le nom de la configuration chargée
        self.conversation_cut_engines: dict[str, ConversationsEngine] = {
            "default": ConversationsEngine(self.conversation_cut_engine_dict, self.config)
        }

        ##### BUBBLE IMPORT THREADS #####

        # Config pour le moteur de calcul d'embeddings
        self.embedding_model_name: str = "optimum/all-MiniLM-L6-v2"
        self.embedding_model_type: str = "sentence-transformers"

        # Moteurs de calcul d'embeddings
        self.bubble_import_embedding_calculator: EmbeddingCalculator = EmbeddingCalculator({
                                                                            "model_name": self.embedding_model_name,
                                                                            "model_type": self.embedding_model_type,
                                                                            "model_optimisations": "optimum",
                                                                            "use_cuda": 1 if cuda_available() else 0
                                                                        }, self.config)

        ##### GLOBAL MULTI-TASKS THREADS #####

        # Dictionnaire de toutes les queues de requêtes en attente
        self.tasks_requests_queue: dict[str, list[TaskRequest]] = {}

        # Mutex pour protéger le dictionnare de toutes les queues de requêtes en attente
        self.tasks_requests_queue_mutex: Lock = Lock()

        # Liste de tous les threads multi-tâches génériques
        self.threads: list[Thread] = []

        # Liste des contraintes de tâches (si éléments dans la liste => Ne réalise que ces tâches là)
        self.threads_tasks_constraints: list[set[str]] = []

        # Condition pour réveiller le thread
        self.threads_new_request_conditions: list[Condition] = []

        #####  #####

        # Variable pour indiquer à tous les threads que le programme se termine.
        self.close_threads: bool = False

        # Mutex pour protéger l'écriture et la lecture de fichiers de configurations
        self.mutex_read_write_config_files: Lock = Lock()

    #
    def exit_threads(self) -> None:
        """
        Fonction à appeler lors de l'interception d'un signal SIGINT pour fermer correctement tous les threads.
        """

        # On va couper tous les threads
        self.close_threads = True

        # On va réveiller tous les threads et les joindre
        for id_thread in range(len(self.threads_new_request_conditions)):
            self.threads_new_request_conditions[id_thread].acquire()
            try:
                self.threads_new_request_conditions[id_thread].notify_all()
            finally:
                self.threads_new_request_conditions[id_thread].release()
            self.threads[id_thread].join()
            print(f"Thread {id_thread} Joined")

    #
    async def send_to_client(self, client: Wsp | Sock, msg_dict: dict) -> None:
        #
        if self.main_server.send_to_client_is_coroutine:
            await self.main_server.send_to_client(client, msg_dict)
        else:
            self.main_server.send_to_client(client, msg_dict)

    #
    async def search_handler_search(self, id_thread: int, search_request: SearchRequest) -> None:
        """
        Effectue une recherche depuis un thread

        Args:
            id_thread (int): id du thread
            search_request (SearchRequest): recherche à effectuer
        """

        print(f"On va faire la recherche `{search_request.search_input}`...")

        # On va charger la rbi si elle n'est pas chargée
        self.main_server.mutex_loading_rbi.acquire()
        try:
            rbi: RainbowInstance
            if search_request.rbi_name not in self.main_server.loaded_rbis:
                rbi = RainbowInstance(search_request.rbi_name, self.config)
                if not rbi.load():

                    #
                    print(f"Erreur RBI, search canceled : {search_request.rbi_name}")

                    # On va notifier le client que l'on ne va pas faire la recherche
                    await self.send_to_client(search_request.client, {
                        "type": "search_canceled",
                        "search_input": search_request.search_input
                    })

                    # Problème, on annule la requête
                    return
                #
                self.main_server.loaded_rbis[search_request.rbi_name] = rbi
            else:
                rbi = self.main_server.loaded_rbis[search_request.rbi_name]
        finally:
            self.main_server.mutex_loading_rbi.release()

        # On réucupère l'objet utilisateur
        user: User = rbi.users[search_request.user_id]

        # On va charger le moteur de recherche s'il n'est pas chargé
        print(f"Asking for {search_request.engine_config} with thread {id_thread}")
        #
        print(f"Current loaded searchs engines : {self.loaded_search_engines}")
        search_engine: SearchEngine
        self.load_search_engine_mutex.acquire()
        try:
            if search_request.engine_config not in self.loaded_search_engines:
                print("Search engine is not loaded, loading it...")
                search_engine = SearchEngine(self.configs_search_engines[search_request.engine_config], self.config)
                self.loaded_search_engines[search_request.engine_config] = search_engine
            else:
                print("Search engine already loaded.")
                search_engine = self.loaded_search_engines[search_request.engine_config]
        finally:
            self.load_search_engine_mutex.release()

        # On va notifier le client que l'on va faire la recherche
        await self.send_to_client(search_request.client, {
            "type": "search_will_be_done",
            "search_input": search_request.search_input
        })

        print("Searching...")

        t_: float = time.time()

        # On va faire la requête
        search_results: list[tuple[float, MessageSearch]] = search_engine.search_main(rbi, search_request.search_input, user, search_request.search_settings)

        search_time: float = time.time() - t_

        print(f"Search done. {len(search_results)} results.")

        # On va envoyer une préparation aux résultats de la requête
        await self.send_to_client(search_request.client, {
            "type": "prepare_search_results",
            "search_input": search_request.search_input,
            "nb_results": len(search_results),
            "search_msg_id": search_request.search_msg_id,
            "search_msg_bubble_id": search_request.search_msg_bubble_id,
            "search_time": search_time
        })

        time.sleep(0.01)

        # On va envoyer tous les résultats de la requête
        for (id_res, res) in enumerate(search_results):

            res_msg_id: str = res[1].msg_pointing[0].msg_id
            res_msg_content: str = "[ERROR]"
            res_msg_author_id: str = ""
            res_msg_bubble_id: str = ""
            res_msg_author_name: str = "[ERROR]"
            res_msg_bubble_name: str = "[ERROR]"
            if res_msg_id in rbi.messages:
                res_msg_content = rbi.messages[res_msg_id].content
                res_msg_author_id = rbi.messages[res_msg_id].author_id
                res_msg_bubble_id = rbi.messages[res_msg_id].bubble_id
            if res_msg_author_id in rbi.users:
                res_msg_author_name = rbi.users[res_msg_author_id].name
            if res_msg_bubble_id in rbi.bubbles:
                res_msg_bubble_name = rbi.bubbles[res_msg_bubble_id].name

            await self.send_to_client(search_request.client, {
                "type": "search_result",
                "search_input": search_request.search_input,
                "index_result": id_res,
                "msg_id": res_msg_id,
                "distance": res[0],
                "msg_content": res_msg_content,
                "msg_author_name": res_msg_author_name,
                "msg_bubble_name": res_msg_bubble_name
            })

            time.sleep(0.001)

        print("Results sent to client.")

    #
    async def conversation_cut_handler_cut(self, id_thread: int, conversation_cut_request: ConversationCutRequest) -> None:
        """
        Effectue une découpe des conversations depuis un thread

        Args:
            id_thread (int): id du thread
            conversation_cut_request (ConversationCutRequest): recherche à effectuer
        """

        print(f"On va faire la découpe des conversations `{conversation_cut_request.rbi_name} - {conversation_cut_request.bubble_id}`...")

        # On va charger la rbi si elle n'est pas chargée
        self.main_server.mutex_loading_rbi.acquire()
        try:
            rbi: RainbowInstance
            if conversation_cut_request.rbi_name not in self.main_server.loaded_rbis:
                rbi = RainbowInstance(conversation_cut_request.rbi_name, self.config)
                if not rbi.load():

                    #
                    print(f"Erreur RBI, conversation cut canceled : {conversation_cut_request.rbi_name}")

                    # On va notifier le client que l'on ne va pas faire la recherche
                    await self.send_to_client(conversation_cut_request.client, {
                        "type": "conversation_cut_canceled",
                        "rbi_name": conversation_cut_request.rbi_name,
                        "bubble_id": conversation_cut_request.bubble_id
                    })

                    # Problème, on annule la requête
                    return
                #
                self.main_server.loaded_rbis[conversation_cut_request.rbi_name] = rbi
            else:
                rbi = self.main_server.loaded_rbis[conversation_cut_request.rbi_name]
        finally:
            self.main_server.mutex_loading_rbi.release()

        # On récupère l'objet bulle
        bubble: Bubble = rbi.bubbles[conversation_cut_request.bubble_id]

        #
        print("Conversation cut...")

        # On va préparer la requête

        #
        msgs_dict: dict[int, Message] = {}
        for msg_id in bubble.messages_ids:
            msgs_dict[msg_id] = rbi.messages[msg_id]

        # On va faire la requête
        conv_cut_result: ResultConversationCut = self.conversation_cut_engines["default"].main_cut(msgs_dict)

        print(f"Conversation cut done.")

        # On va envoyer une préparation aux résultats de la requête
        await self.send_to_client(conversation_cut_request.client, {
            "type": "conversation_cut_results",
            "current_rbi": conversation_cut_request.rbi_name,
            "current_bubble": conversation_cut_request.bubble_id,
            "nb_conversations": conv_cut_result.nb_conversations,
            "msgs_colors": conv_cut_result.msgs_colors
        })

        print("Results sent to client.")

    #
    async def bubble_import_handler_import(self, id_thread: int, bubble_import_request: ImportRequest) -> None:
        """
        Effectue une découpe des conversations depuis un thread

        Args:
            id_thread (int): id du thread
            conversation_cut_request (ConversationCutRequest): recherche à effectuer
        """

        print(f"On va faire l'importation d'une bulle: `{bubble_import_request.rbi_name} - {bubble_import_request.bubble_name}`...")

        # On va charger la rbi si elle n'est pas chargée
        rbi: RainbowInstance
        self.main_server.mutex_loading_rbi.acquire()
        try:
            if bubble_import_request.rbi_name not in self.main_server.loaded_rbis:
                rbi = RainbowInstance(bubble_import_request.rbi_name, self.config)
                if not rbi.load():

                    #
                    print(f"Erreur RBI, import canceled : {bubble_import_request.rbi_name}")

                    # On va notifier le client que l'on ne va pas faire la recherche
                    await self.send_to_client(bubble_import_request.client, {
                        "type": "bubble_import_error",
                        "rbi_name": bubble_import_request.rbi_name,
                        "bubble_name": bubble_import_request.bubble_name,
                        "error": "Error with RBI loading"
                    })
                    #
                    print("Bubble import error.")

                    # Problème, on annule la requête
                    return
                #
                self.main_server.loaded_rbis[bubble_import_request.rbi_name] = rbi
            else:
                rbi = self.main_server.loaded_rbis[bubble_import_request.rbi_name]
        finally:
            self.main_server.mutex_loading_rbi.release()

        #
        print(f"Import bubble \"{bubble_import_request.bubble_name}\" ...")

        # On va parser la bulle
        res: FunctionResult = bubble_parser(f"{self.config.base_data_to_convert_path}{bubble_import_request.rbi_name}", bubble_import_request.bubble_name, rbi, import_from_txt = bubble_import_request.bubble_text_to_import)
        if isinstance(res, ResultError):
            # On va notifier le client qu'il y a eu une erreur
            await self.send_to_client(bubble_import_request.client, {
                "type": "bubble_import_error",
                "rbi_name": bubble_import_request.rbi_name,
                "bubble_name": bubble_import_request.bubble_name,
                "error": res.error_message
            })
            #
            print("Bubble import error.")
            #
            return

        print(f"Bubble \"{bubble_import_request.bubble_name}\" converted.\nEmbedding Calculation...")

        # On va maintenant calculer les embeddings et la traduction de tous les messages pour les mettres dans le cache
        bubble: Bubble = rbi.bubbles[res.return_values[1]]

        #
        str_estimated_time: str = Date(seconds=(len(bubble.messages_ids) * 1.0)).display()
        #
        await self.send_to_client(bubble_import_request.client, {
            "type": "bubble_import_started",
            "rbi_name": bubble_import_request.rbi_name,
            "bubble_name": bubble_import_request.bubble_name,
            "nb_msgs": len(bubble.messages_ids),
            "estimated_time": str_estimated_time
        })

        #
        tot_nb_messages: int = len(bubble.messages_ids)
        msgs_processed: int = 0
        tot_time: float = 0
        last_update: float = time.time()
        #
        for msg_id in bubble.messages_ids:
            #
            msg: Message = rbi.messages[msg_id]
            # Traduction
            translated_content: str = get_global_variables().translate(msg.content)
            # Calcul de l'embedding sans traduction
            emb: MessageEmbedding
            if get_global_variables().get_embedding_cache(self.embedding_model_name, msg.content) is None:
                emb = self.bubble_import_embedding_calculator.get_embeddings([msg.content])[0]
                get_global_variables().set_embedding_cache(self.embedding_model_name, msg.content, emb)
            # Calcul de l'embedding avec traduction
            if get_global_variables().get_embedding_cache(self.embedding_model_name, translated_content) is None:
                emb = self.bubble_import_embedding_calculator.get_embeddings([translated_content])[0]
                get_global_variables().set_embedding_cache(self.embedding_model_name, translated_content, emb)
            #
            msgs_processed += 1
            #
            time_took:float = time.time() - last_update
            last_update = time.time()
            tot_time += time_took
            #
            time_per_message: float = tot_time / float(msgs_processed)
            print(f"\nEstimated time_per_message : {time_per_message} \n")
            estimated_time: float = time_per_message * float(tot_nb_messages - msgs_processed)
            #
            str_estimated_time: str = Date(seconds=estimated_time).display()
            #
            await self.send_to_client(bubble_import_request.client, {
                "type": "bubble_import_progress_update",
                "rbi_name": bubble_import_request.rbi_name,
                "bubble_name": bubble_import_request.bubble_name,
                "msgs_processed": msgs_processed,
                "estimated_time": str_estimated_time
            })
        #
        get_global_variables().save()
        #
        rbi.save()
        #
        await self.send_to_client(bubble_import_request.client, {
            "type": "bubble_import_finished",
            "rbi_name": bubble_import_request.rbi_name,
            "bubble_name": bubble_import_request.bubble_name,
            "bubble_id": bubble.id
        })

        #
        await self.main_server.handle_rbi_ask_infos(bubble_import_request.client_id, bubble_import_request.client, {"rbi_name": bubble_import_request.rbi_name})

        #
        print(f"Bubble \"{bubble_import_request.bubble_name}\" has been imported.")

    #
    async def add_new_messages_to_bubble_handler_add(self, id_thread: int, add_request: AddMessagesToBubbleRequest) -> None:
        """
        Ajoute de nouveaux messages à une bulle (crée les utilisateurs s'ils n'existent pas, et crée les bulles si elles n'existent pas non plus).

        Args:
            id_thread (int): id du thread
            conversation_cut_request (ConversationCutRequest): recherche à effectuer
        """

        #
        print(f"On ajouter {len(add_request.msgs_lst)} messages à la bulle d'id {add_request.bubble_id}...")

        # On va charger la rbi si elle n'est pas chargée
        rbi: RainbowInstance
        self.main_server.mutex_loading_rbi.acquire()
        try:
            if add_request.rbi_name not in self.main_server.loaded_rbis:
                rbi = RainbowInstance(add_request.rbi_name, self.config)
                if not rbi.load():

                    #
                    print(f"Erreur RBI, import canceled : {add_request.rbi_name}")

                    # On va notifier le client que l'on ne va pas faire la recherche
                    await self.send_to_client(add_request.client, {
                        "type": "bubble_import_error",
                        "rbi_name": add_request.rbi_name,
                        "bubble_name": add_request.bubble_name,
                        "error": "Error with RBI loading"
                    })
                    #
                    print("Bubble import error.")

                    # Problème, on annule la requête
                    return
                #
                self.main_server.loaded_rbis[add_request.rbi_name] = rbi
            else:
                # Si la rbi est déjà chargée, on la récupère juste tout simplement
                rbi = self.main_server.loaded_rbis[add_request.rbi_name]
        # Dans tous les cas, on libère le mutex
        finally:
            self.main_server.mutex_loading_rbi.release()

        # On va ajouter chaque message
        for msg_to_add in add_request.msgs_lst:

            # On vérifie que tout est bon
            for k in ["id", "content", "bubble_id", "bubble_name", "author_id", "author_name", "date", "answered_message_id"]:
                if not k in msg_to_add:
                    continue  # On ignore ce message malformé

            rbi.add_new_message_to_bubble(msg_dict=msg_to_add, bubble_id=add_request.bubble_id)

            # On va calculer les différents éléments pour qu'ils soient dans le cache

            msg_content = msg_to_add["content"]

            # Traduction
            translated_content: str = get_global_variables().translate(msg_content)
            # Calcul de l'embedding sans traduction
            emb: MessageEmbedding
            if get_global_variables().get_embedding_cache(self.embedding_model_name, msg_content) is None:
                emb = self.bubble_import_embedding_calculator.get_embeddings([msg_content])[0]
                get_global_variables().set_embedding_cache(self.embedding_model_name, msg_content, emb)
            # Calcul de l'embedding avec traduction
            if get_global_variables().get_embedding_cache(self.embedding_model_name, translated_content) is None:
                emb = self.bubble_import_embedding_calculator.get_embeddings([translated_content])[0]
                get_global_variables().set_embedding_cache(self.embedding_model_name, translated_content, emb)

        # On sauvegarde la rbi
        rbi.save()

        # On sauvegarde le cache de traduction
        save_global_variables()

        #
        print(f"Les {len(add_request.msgs_lst)} messages ont été ajoutés à la bulle d'id {add_request.bubble_id}.")

    #
    async def test_benchmarks_handler_test(self, id_thread: int, test_benchmark_request: TestBenchmarkWithConfigRequest) -> None:
        """
        Effectue un test de tous les benchmarks d'une certaine tâche (NER, conversation_cut, search) avec une configuration très spécifique depuis un thread.

        Args:
            id_thread (int): id du thread
            test_benchmark_request (TestBenchmarkWithConfigRequest): requête à effectuer
        """

        print(f"On va faire le test de benchmarks avec la tâche: `{test_benchmark_request.task}`...")

        benchmark_results: dict[str, float] = {}
        engine: NER_Engine | ConversationsEngine | SearchEngine

        if test_benchmark_request.task == "NER":
            #
            engine = NER_Engine(test_benchmark_request.engine_config_dict, self.config)
            #
            for benchmark_name in self.tests_benchmarks.all_ner_benchmarks_files:
                #
                res: dict = self.tests_benchmarks.run_ner_benchmark(engine.config_name, self.tests_benchmarks.loaded_benchmarks[benchmark_name], engine)
                #
                benchmark_results[benchmark_name] = res["macro_avg_f1"]
            #
        elif test_benchmark_request.task == "conversation_cut":
            #
            engine = ConversationsEngine(test_benchmark_request.engine_config_dict, self.config)
            #
            for benchmark_name in self.tests_benchmarks.all_conversations_benchmarks_files:
                #
                res: dict = self.tests_benchmarks.run_conversation_cut_benchmark(engine.config_name, self.tests_benchmarks.loaded_benchmarks[benchmark_name], engine)
                #
                benchmark_results[benchmark_name] = res["score"]
            #
        elif test_benchmark_request.task == "search":
            #
            engine = SearchEngine(test_benchmark_request.engine_config_dict, self.config)
            #
            for benchmark_name in self.tests_benchmarks.all_search_benchmarks_files:
                #
                res: dict = self.tests_benchmarks.run_search_benchmark(engine.config_name, self.tests_benchmarks.loaded_benchmarks[benchmark_name], engine)
                #
                benchmark_results[benchmark_name] = res["avg_score"]

        # Calcul score moyen du benchmark
        avg: float = 0.0
        for val in benchmark_results.values():
            avg += val
        #
        if len(benchmark_results) > 0:
            avg /= float(len(benchmark_results))
        #
        benchmark_results["avg"] = avg

        #
        if test_benchmark_request.test_benchmark_type == "single_test":
            #
            await self.send_to_client(test_benchmark_request.client, {
                "type": "hpo_single_test_benchmark_results",
                "task": test_benchmark_request.task,
                "config": test_benchmark_request.engine_config_dict,
                "benchmark_results": benchmark_results,
                "test_benchmark_type": test_benchmark_request.test_benchmark_type
            })
        elif test_benchmark_request.test_benchmark_type == "curve_test":
            #
            await self.send_to_client(test_benchmark_request.client, {
                "type": "hpo_curve_test_benchmark_results",
                "task": test_benchmark_request.task,
                "config": test_benchmark_request.engine_config_dict,
                "benchmark_results": benchmark_results,
                "test_benchmark_type": test_benchmark_request.test_benchmark_type,
                "param_values": test_benchmark_request.param_values,
                "param_pts_ids": test_benchmark_request.param_pts_ids,
            })

    #
    async def hpo_algorithmic_optimization_handler_optimize(self, id_thread: int, hpo_algorithmic_request: HPOAlgorithmRequest) -> None:
        """
        Effectue une optimisation algorithmique des hyper-paramètres d'une configuration d'une tâche.

        Args:
            id_thread (int): id du thread
            hpo_algorithmic_request (HPOAlgorithmRequest): requête à effectuer
        """

        #
        print(f"On va lancer une optimisation des hyper paramètres de la configuration {hpo_algorithmic_request.base_engine_config['config_name']} (de la tâche {hpo_algorithmic_request.task} ) ...")

        #
        def evaluation_function(task: str, test_engine_config_with_modified_hp_values: dict, benchmarks_to_optimize: dict) -> float:
            #
            score: float = 0.0
            sum_coefs: float = 0.0
            #
            for benchmark_name in benchmarks_to_optimize:
                #
                if task == "NER":
                    engine: NER_Engine = NER_Engine(test_engine_config_with_modified_hp_values, self.config)
                    res: dict = self.tests_benchmarks.run_ner_benchmark(test_engine_config_with_modified_hp_values['config_name'], self.tests_benchmarks.loaded_benchmarks[benchmark_name], engine)
                    score += benchmarks_to_optimize[benchmark_name] * res["macro_avg_f1"]
                elif task == "conversation_cut":
                    engine: ConversationsEngine = ConversationsEngine(test_engine_config_with_modified_hp_values, self.config)
                    res: dict = self.tests_benchmarks.run_conversation_cut_benchmark(test_engine_config_with_modified_hp_values['config_name'], self.tests_benchmarks.loaded_benchmarks[benchmark_name], engine)
                    score += benchmarks_to_optimize[benchmark_name] * res["score"]
                elif task == "search":
                    engine: SearchEngine = SearchEngine(test_engine_config_with_modified_hp_values, self.config)
                    res: dict = self.tests_benchmarks.run_search_benchmark(test_engine_config_with_modified_hp_values['config_name'], self.tests_benchmarks.loaded_benchmarks[benchmark_name], engine)
                    score += benchmarks_to_optimize[benchmark_name] * res["avg_score"]
                else:
                    break
                #
                sum_coefs += benchmarks_to_optimize[benchmark_name]
            #
            if sum_coefs == 0.0:
                return 0.0
            #
            score /= sum_coefs
            #
            return score

        #
        async def send_results_update_to_ws(dict_msg) -> None:
            #
            await self.send_to_client(hpo_algorithmic_request.client, {
                    "type": "hpo_algo_opti_update",
                    "id_request": hpo_algorithmic_request.id_request,
                    "update_config_score": dict_msg
                })

        #
        hpo_opti_algo: HPOptimisationAlgorithm = HPO_ALGORITHMS[hpo_algorithmic_request.algo_name][0](
                                                    hpo_algorithmic_request.task,
                                                    evaluation_function,
                                                    hpo_algorithmic_request.base_engine_config,
                                                    hpo_algorithmic_request.hyper_parameters_to_optimize,
                                                    hpo_algorithmic_request.benchmarks_to_optimize,
                                                    hpo_algorithmic_request.algorithm_parameters,
                                                    send_results_update_to_ws
                                                )

        #
        config_optimized_hp: dict
        config_optimized_score: float
        config_optimized_hp, config_optimized_score = await hpo_opti_algo.optimise()

        #
        await self.send_to_client(hpo_algorithmic_request.client, {
                "type": "hpo_algo_opti_result",
                "id_request": hpo_algorithmic_request.id_request,
                "config_optimized_hp": config_optimized_hp,
                "config_optimized_score": config_optimized_score
            })

    #
    def main_thread_handler(self, id_thread: int, tasks_constraints: set[str] = set()) -> None:
        """
        Thread qui va s'occuper des importations de bulles.
        Architecture utile pour scaler.

        Args:
            id_thread (int): id du thread actuel
        """

        # On affiche un message dans la console
        if len(tasks_constraints) == 0:
            print(f"Le thread n°{id_thread} pour tout gérer est prêt")
        else:
            print(f"Le thread n°{id_thread} pour gérer les tâches {tasks_constraints} est prêt")

        # Requête en cours
        current_request: Optional[TaskRequest] = None
        current_request_task: str = ""

        #
        next_request_available: bool = False

        # On attends
        self.threads_new_request_conditions[id_thread].acquire()
        while self.threads_new_request_conditions[id_thread] or next_request_available:
            #
            if not next_request_available:
                self.threads_new_request_conditions[id_thread].wait()
            #
            self.threads_new_request_conditions[id_thread].release()

            #
            next_request_available = False

            #
            if self.close_threads:
                print(f"Thread tasks handler ({tasks_constraints}) closed : {id_thread}")
                return

            # Message dans la console pour indiquer qu'il se passe qqchose
            print(f"Thread tasks handler ({tasks_constraints}) awaken : {id_thread}")

            # On bloque le mutex
            self.tasks_requests_queue_mutex.acquire()

            try:

                # Pour toutes les tâches à faire
                for task in self.tasks_types_fcts.keys():

                    # S'il y a une contrainte de tâches à ne pas faire
                    if len(tasks_constraints) > 0 and not task in tasks_constraints:
                        continue

                    # S'il n'y a pas/plus de requêtes pour cette tâche
                    if len(self.tasks_requests_queue[task]) == 0:
                        continue

                    # S'il en reste une on la prend
                    current_request = self.tasks_requests_queue[task].pop(0)
                    current_request_task = task
                    break

            finally:
                # On débloque le mutex
                self.tasks_requests_queue_mutex.release()

            # S'il y a une tâche à faire trouvée
            if current_request is not None:

                # On gère la requête
                asyncio.run(self.tasks_types_fcts[current_request_task](id_thread, current_request))

                # On nettoie les variables
                current_request = None
                current_request_task = ""

                # Test de s'il y a directement une prochaine tâche à faire:

                # Pour toutes les tâches à faire
                for task in self.tasks_types_fcts.keys():

                    # S'il y a une contrainte de tâches à ne pas faire
                    if len(tasks_constraints) > 0 and not task in tasks_constraints:
                        continue

                    # On teste s'il reste encore une recherche à traiter, s'il n'y en a pas, on attends la prochaine notification
                    if len(self.tasks_requests_queue[task]) > 0:
                        next_request_available = True
                        break

            # on attends la prochaine notification
            self.threads_new_request_conditions[id_thread].acquire()

    #
    def wake_up_threads_for_task(self, wake_up_task: str) -> None:
        """
        Va réveiller tous les threads qui peuvent s'occuper d'une certaine tâche.

        Args:
            wake_up_task (str): tâche que doit faire un thread pour être réveillé
        """

        for id_thread in range(len(self.threads)):

            if len(self.threads_tasks_constraints[id_thread]) == 0 or wake_up_task in self.threads_tasks_constraints[id_thread]:

                # On va notifier à tous les threads qu'il y a eu une requête
                self.threads_new_request_conditions[id_thread].acquire()
                try:
                    self.threads_new_request_conditions[id_thread].notify_all()
                finally:
                    self.threads_new_request_conditions[id_thread].release()

    #
    def add_task_request_to_queues(self, task: str, request: TaskRequest) -> None:

        #
        if not task in self.tasks_requests_queue:
            return

        # On va ajouter la recherche dans la liste des requêtes en attente
        self.tasks_requests_queue_mutex.acquire()
        try:
            self.tasks_requests_queue[task].append( request )
        finally:
            self.tasks_requests_queue_mutex.release()

        # On va notifier à tous les threads qu'il y a eu une requête
        self.wake_up_threads_for_task(task)

    #
    async def run(self) -> None:
        """
        Fonction qui va lancer les threads
        """

        # On va initialiser les files d'attentes pour les requêtes pour toutes les tâches
        for task_name in self.tasks_types_fcts.keys():
            self.tasks_requests_queue[task_name] = []

        #
        nb_threads_created: int = 0

        #
        for task_name in self.config.main_server_nb_threads_specifics_for_tasks.keys():
            #
            for _ in range(self.config.main_server_nb_threads_specifics_for_tasks[task_name]):

                #
                tasks_constraints: set = set([task_name])

                # On crée le thread
                thread: Thread = Thread(target = self.main_thread_handler, args = (nb_threads_created, tasks_constraints))
                nb_threads_created += 1

                # On lance le thread
                thread.start()

                # On ajoute le thread à la liste des threads
                self.threads.append(thread)

                #
                self.threads_new_request_conditions.append(Condition())

                #
                self.threads_tasks_constraints.append(tasks_constraints)


        # On va lancer tous les autres threads restants
        for _ in range(self.config.main_server_nb_threads - nb_threads_created):

            #
            tasks_constraints: set = set()

            # On crée le thread
            thread: Thread = Thread(target = self.main_thread_handler, args = (nb_threads_created, tasks_constraints))
            nb_threads_created += 1

            # On lance le thread
            thread.start()

            # On ajoute le thread à la liste des threads
            self.threads.append(thread)

            #
            self.threads_new_request_conditions.append(Condition())

            #
            self.threads_tasks_constraints.append(tasks_constraints)
