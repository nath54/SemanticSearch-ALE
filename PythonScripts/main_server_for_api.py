"""
Serveur python avec Sockets qui va servir pour la démo pour la recherche sémantique, il va être relié à un autre serveur en C# qui va intéragir avec le Rainbow SDK.

Auteur: Nathan Cerisara
"""


from typing import Optional, Callable
import socket
from socket import socket as Sock
import json
import threading
import asyncio
import os
import sys
import time
import signal
from dataclasses import dataclass
from threading import Thread, Lock
from config_socket_api import Config
from global_variables import init_global_variables, save_global_variables, free_global_variables
from lib_main_server import MainServer

from threads_tasks_server import ThreadsTasksServer, AddMessagesToBubbleRequest, SearchRequest
from search_engine import SearchSettings
from rainbow_instance import RainbowInstance
from message import Message
from user import User
from bubble import Bubble
from random import randint
# from profiling import profiling_init, profiling_save_and_stop, profiling_task_start, profiling_last_task_ends


# Constante qui indique la taille maximale des messages à accepter depuis le socket
MAX_SOCKET_MSG_SIZE: int = 16384


#
class TCPSocketServer(MainServer):
    """
    _summary_
    """

    def __init__(self, conf: Config) -> None:
        """
        _summary_

        Args:
            conf (Config): _description_
        """
        super().__init__(conf)
        self.send_to_client_is_coroutine = False

        # Configuration
        self.config: Config = conf
        # Port du socket
        self.port: int = conf.socket_port
        # Clients qui sont actuellement connectés au socket
        self.connected_clients: dict[str, dict[str, Optional[socket.socket] | Thread]] = {}
        # Fonctions pour traiter les différents types de messages
        self.messages_types_fcts: dict[str, Callable] = {
            "ping": self.handle_ping,
            "init_rbi": self.handle_init_rbi,
            "update_bubble": self.handle_update_rbi_bubble,
            "new_msg": self.handle_new_msg
        }
        # Liste des RBI actuellement chargées
        self.loaded_rbis: dict[str, RainbowInstance] = {}
        # Mutex pour protéger le chargement d'une RBI
        self.mutex_loading_rbi: Lock = Lock()
        # Outil de toutes les tâches
        self.threads_tasks_server: ThreadsTasksServer = ThreadsTasksServer(conf, self)
        # Mutex pour protéger
        self.mutex_socket_send: Lock = Lock()
        # Mutex pour protéger
        self.mutex_read_write_config_files: Lock = Lock()

        # à récupérer, id des bots, on va ignorer tous leurs messages pour la recherche
        self.bots_ids: set[str] = set()

    #
    def exit_gracefully(self, sig, frame) -> None:
        """
        _summary_

        Args:
            sig (_type_): _description_
            frame (_type_): _description_
        """

        # On sauvegarde les caches de traduction
        save_global_variables()

        # On affiche un message dans la console pour suivre ce qu'il se passe
        if sig is not None or frame is not None:
            print("\nSignal SIGINT reçu.\n")
        else:
            print("\nEnd of the program.\n")

        # On termine tous les threads
        self.threads_tasks_server.exit_threads()
        # On libère les variables globales
        free_global_variables()
        # On quitte tout
        sys.exit(0)

    #
    def handle_client(self, client_id: str) -> None:
        """
        _summary_

        Args:
            client_socket (socket.socket): _description_
            client_address (tuple): _description_
        """

        # On récupère les valeurs
        client_socket: socket.socket = self.connected_clients[client_id]["socket"]
        client_address: tuple = self.connected_clients[client_id]["adress"]

        # Affichage d'un message dans la console pour suivre ce qu'il se passe
        print(f"{client_id} connected.")

        # Indication au client qu'il est bien connecté
        self.send_to_client(client_socket, {"type": "connected"})

        #
        long_msgs_buffer: str = ""

        #
        try:
            # Tant que le client est connecté
            while True:
                # On essaie de lire sur le socket
                msgs: str
                msgs = client_socket.recv(MAX_SOCKET_MSG_SIZE).decode('utf-8')
                # Si il y a un problème, on quitte
                if not msgs:
                    break

                msg: str
                for msg in msgs.split(self.config.socket_messages_delimiter):

                    # Si message vide et/ou qui ne contient pas de dictionnaire json, on ignore
                    if not "{" in msg:
                        continue

                    # On affiche un message dans la console pour suivre ce qu'il se passe
                    print(f"{client_id} sent: {msg}")

                    if long_msgs_buffer != "":
                        #
                        try:
                            # On essaie de lire le message en json concaténé au buffer
                            msg_data: dict = json.loads(long_msgs_buffer+msg)
                            # Si Le message est malformé, on l'ignore
                            msg_type: str = msg_data.get("type", "")
                            # Sinon, on récupère la fonction qui va traiter le message reçu
                            handler = self.messages_types_fcts.get(msg_type, None)
                            #
                            print(f"\n\033[34;1mDEBUG :  type = {msg_type} | handler = {handler}\033[m\n")
                            # Si on en a bien trouvé une
                            if handler is not None:
                                # On l'éxecute
                                handler(client_id, client_socket, msg_data)

                            # On reset le buffer
                            long_msgs_buffer = ""
                            # C'est tout bon ici, on ne fait plus rien pour ce message
                            continue

                        # Si le message n'est pas sous format json, on l'ignore
                        except json.decoder.JSONDecodeError:
                            # La concaténation de message ne fonctionne pas, on essaie avec le message tout seul sans buffer
                            pass

                    #
                    try:
                        # On essaie de lire le message en json
                        msg_data: dict = json.loads(msg)
                        # Si Le message est malformé, on l'ignore
                        msg_type: str = msg_data.get("type", "")
                        # Sinon, on récupère la fonction qui va traiter le message reçu
                        handler = self.messages_types_fcts.get(msg_type, None)
                        #
                        print(f"\n\033[34;1mDEBUG :  type = {msg_type} | handler = {handler}\033[m\n")
                        # Si on en a bien trouvé une
                        if handler is not None:
                            # On l'éxecute
                            handler(client_id, client_socket, msg_data)

                    # Si le message n'est pas sous format json, on l'ignore
                    except json.decoder.JSONDecodeError:
                        # On a de grandes chances que ce message fasse partie d'un plus grand message
                        long_msgs_buffer += msg

        # Si il y a une une grosse erreur, ou que le client s'est bien déconnecté
        finally:
            # On ferme le socket
            client_socket.close()
            # On supprime le client
            del self.connected_clients[client_id]
            # On affiche un message dans la console pour suivre ce qu'il se passe
            print(f"{client_id} disconnected")

    #
    def send_to_client(self, client_socket: socket.socket, message: dict) -> None:
        """
        _summary_

        Args:
            client_socket (socket.socket): _description_
            message (dict): _description_
        """

        # On convertit le dictionnaire en format texte
        msg = json.dumps(message) + self.config.socket_messages_delimiter

        print(f"Try to send a message to a client : {msg}")

        # On s'assure d'être le seul qui va accéder au socket
        self.mutex_socket_send.acquire()

        # On essaie d'envoyer le message au socket
        try:
            client_socket.send(msg.encode('utf-8'))

        # S'il y a une erreur, on l'affiche
        except Exception as e:
            print(f"Error while trying to send {msg} to client {client_socket}")
            print(e)

        # Si tout c'est bien passé, ou s'il y a une une erreur
        finally:
            # On libère le mutex
            self.mutex_socket_send.release()

    #
    def handle_ping(self, client_id: str, client_socket: socket.socket, message: dict) -> None:
        """
        _summary_

        Args:
            client_id (str): _description_
            client_socket (socket.socket): _description_
            message (dict): _description_
        """

        # On envoie au socket un message
        self.send_to_client(client_socket, {"type": "pong"})

    #
    def handle_init_rbi(self, client_id: str, client_socket: socket.socket, message: dict) -> None:
        """
        _summary_

        Args:
            client_id (str): _description_
            client_socket (socket.socket): _description_
            message (dict): _description_
        """

        # On vérifie que le message est sous le bon format
        required_keys = ["rbi_name", "bot_id"]
        if not all(key in message for key in required_keys):
            return  # Si le message n'est pas sous le bon format, on l'ignore

        # On récupère les paramètres du messages
        rbi_name: str = message["rbi_name"]
        bot_id: str = message["bot_id"]

        self.bots_ids.add(bot_id)

        # On s'assure d'être le seul à toucher aux rbis
        self.mutex_loading_rbi.acquire()

        # On essaie de charger la RBI si elle n'est pas chargée
        try:
            if rbi_name not in self.loaded_rbis:
                # Si la RBI n'est pas chargée, on la charge
                self.loaded_rbis[rbi_name] = RainbowInstance(rbi_name, self.config)

        # Dans tous les cas, on libère le mutex
        finally:
            self.mutex_loading_rbi.release()

        # On va récupérer le dernier message pour chaque bulle
        bubbles_last_msgs_ids: dict[str, str] = {}

        # On parcourt chaque bulle dont on a actuellement les données
        bubble: Bubble
        for bubble in self.loaded_rbis[rbi_name].bubbles.values():
            # On récupère l'id du dernier message de la bulle actuelle
            last_msg_id: str = ""
            if len(bubble.messages_ids) > 0:
                last_msg_id = str(list(bubble.messages_ids)[-1])
            # On l'ajoute au dictionnaire que l'on va envoyer
            bubbles_last_msgs_ids[bubble.id] = last_msg_id

        # On envoie un message au client pour dire l'état de la RBI ici
        self.send_to_client(client_socket, {
            "type": "rbi_state",
            "rbi_name": rbi_name,
            "bubbles_last_msgs_ids": bubbles_last_msgs_ids
        })

    #
    def handle_update_rbi_bubble(self, client_id: str, client_socket: socket.socket, message: dict) -> None:
        """
        _summary_

        Args:
            client_id (str): _description_
            client_socket (socket.socket): _description_
            message (dict): _description_
        """

        # On vérifie que le message est sous le bon format
        required_keys: list[str] = ["rbi_name", "bubble_id", "bubble_name", "msgs"]
        all_keys_in: list[bool] = [key in message for key in required_keys]
        if not all(all_keys_in):
            print(f"DEBUG | handle_update_rbi_bubble | Missing keys : {[required_keys[i] for i in range(len(all_keys_in)) if not all_keys_in[i]]}\n")
            return

        # On récupère les paramètres du messages
        rbi_name: str = message["rbi_name"]
        bubble_id: str = message["bubble_id"]
        bubble_name: str = message["bubble_name"]
        msgs: list[dict] = message["msgs"]

        print(f"DEBUG | handle_update_rbi_bubble | Messages parameters : \n - rbi_name = {rbi_name}\n - bubble_id = {bubble_id}\n - bubble_name = {bubble_name}\n - msgs = {msgs}\n")

        # On s'assure d'être le seul à toucher aux rbis
        self.mutex_loading_rbi.acquire()

        # On essaie de charger la RBI si elle n'est pas chargée
        try:
            if rbi_name not in self.loaded_rbis:
                # Si la RBI n'est pas chargée, on la charge
                self.loaded_rbis[rbi_name] = RainbowInstance(rbi_name, self.config)

        # Dans tous les cas, on libère le mutex
        finally:
            self.mutex_loading_rbi.release()

        # On va préparer la requête
        request: AddMessagesToBubbleRequest = AddMessagesToBubbleRequest(
            task_type="add_msgs_to_bubble",
            client_id=client_id,
            client=client_socket,
            rbi_name=rbi_name,
            bubble_id=bubble_id,
            msgs_lst=msgs
        )

        print(f"DEBUG | handle_update_rbi_bubble | Request added : {request}\n")

        # On ajoute la requête dans la liste des requêtes à exécuter et on réveilles les threads qui peuvent s'en occuper
        self.threads_tasks_server.add_task_request_to_queues("add_msgs_to_bubble", request)

    #
    def handle_new_msg(self, client_id: str, client_socket: socket.socket, message: dict) -> None:
        """
        _summary_

        Args:
            client_id (str): _description_
            client_socket (socket.socket): _description_
            message (dict): _description_
        """

        # On vérifie que le message est sous le bon format
        required_keys: list[str] = ["rbi_name", "bubble_id", "msg"]
        if not all(key in message for key in required_keys):
            return

        # On récupère les paramètres du messages
        rbi_name: str = message["rbi_name"]
        bubble_id: str = message["bubble_id"]
        msg: dict = message["msg"]

        # On vérifie que le msg est sous le bon format
        required_msg_keys: list[str] = ["id", "content", "bubble_id", "bubble_name", "author_id", "author_name", "date", "answered_message_id"]
        if not all(key in msg for key in required_msg_keys):
            return

        # On s'assure d'être le seul à toucher aux rbis
        self.mutex_loading_rbi.acquire()

        # On essaie de charger la RBI si elle n'est pas chargée
        try:
            if rbi_name not in self.loaded_rbis:
                # Si la RBI n'est pas chargée, on la charge
                self.loaded_rbis[rbi_name] = RainbowInstance(rbi_name, self.config)

        # Dans tous les cas, on libère le mutex
        finally:
            self.mutex_loading_rbi.release()

        # On récupère le contenu du message
        msg_content: str = msg["content"]

        # Si c'est une commande de recherche
        if msg_content.startswith("/search "):

            # On récupère le contenu de la recherche
            search_input: str = msg_content[8:].strip()

            # On crée les paramètres de la recherche, vides (pour l'instant)
            search_settings_dict: dict = {
                "exclude_users": self.bots_ids
            }
            search_settings: SearchSettings = SearchSettings(**search_settings_dict)

            # On va préparer la requête
            request: SearchRequest = SearchRequest(
                task_type="search",
                client_id=client_id,
                client=client_socket,
                search_input=search_input,
                user_id=msg["author_id"],
                search_settings=search_settings,
                engine_config=self.config.main_default_engine_config_name,
                rbi_name=rbi_name,
                search_msg_id=msg["id"],
                search_msg_bubble_id=bubble_id
            )

            # On ajoute la requête dans la liste des requêtes à exécuter et on réveilles les threads qui peuvent s'en occuper
            self.threads_tasks_server.add_task_request_to_queues("search", request)

        # Sinon, on ajoute juste tout simplement le message à sa bulle
        else:
            # On va préparer la requête
            request: AddMessagesToBubbleRequest = AddMessagesToBubbleRequest(
                task_type="add_msgs_to_bubble",
                client_id=client_id,
                client=client_socket,
                rbi_name=rbi_name,
                bubble_id=bubble_id,
                msgs_lst=[msg]
            )

            # On ajoute la requête dans la liste des requêtes à exécuter et on réveilles les threads qui peuvent s'en occuper
            self.threads_tasks_server.add_task_request_to_queues("add_msgs_to_bubble", request)

    #
    async def run(self) -> None:
        """
        Démarre le serveur socket et commence à écouter les connections entrantes.
        """

        # On prépare le fait que lorsque l'on interromp le programme avec un Ctrl+C
        signal.signal(signal.SIGINT, self.exit_gracefully)

        #
        # On va lancer les threads
        await self.threads_tasks_server.run()

        # On crée le socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # On indique le port sur lequel le socket va écouter
        server_socket.bind(("", self.port))
        # On donne un timeout pour l'acceptation de clients (pour pouvoir écouter les signaux après)
        server_socket.settimeout(1.0)
        # On écoute les clients qui vont se connecter
        server_socket.listen(self.config.socket_max_clients_connected)

        # On affiche un message dans la console pour suivre ce qu'il se passe
        print(f"Server running on port {self.port}...")

        #
        try:
            while True:
                try:
                    # On accepte le client
                    client_socket, client_address = server_socket.accept()
                    # Création de l'id du client
                    client_id = f"Client_n{len(self.connected_clients) + 1}_{randint(0, 10000)}"
                    #
                    client_thread = threading.Thread(target=self.handle_client, args=(client_id,))
                    # Ajout du client connecté dans la liste des clients connectés
                    self.connected_clients[client_id] = {
                        "id": client_id,
                        "socket": client_socket,
                        "thread": client_thread,
                        "socket": client_socket,
                        "adress": client_address
                    }
                    #
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    raise e

        # Bonne façon de quitter le programme: déclencher un événement KeyboardInterrupt (Ctrl+C)
        except KeyboardInterrupt:
            print("\nServer shutting down...")

        # Dans tous les cas
        finally:
            # On s'assure de tout bien quitter
            self.exit_gracefully(None, None)
            # On ferme le socket
            server_socket.close()


if __name__ == "__main__":
    # On affiche un message dans la console pour suivre ce qu'il se passe
    print("Démarrage de l'application...")

    # On charge la config globale du programme
    conf = Config("config_socket_api.json")

    # On initialise les variables globales (**important**)
    init_global_variables(conf)

    # Profiling
    # profiling_init("TCP Python Server")

    # On crée le serveur socket python
    server = TCPSocketServer(conf)

    # On lance le serveur
    asyncio.run(server.run())
