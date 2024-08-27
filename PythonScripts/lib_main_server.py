"""
Classe MainServer qui présente une classe abstraite pour main_server_webapp et main_server_api.

Auteur: Nathan Cerisara
"""

from typing import Optional
from config import Config
from threading import Lock
from rainbow_instance import RainbowInstance
from websockets import WebSocketServerProtocol as Wsp
from socket import socket as Sock


class MainServer:
    """
    Classe qui représente un serveur.
    """

    def __init__(self, conf: Config) -> None:
        """
        Initialisation du serveur.

        Args:
            conf (Config): fichier de configuration générale de l'app.
        """

        # Il n'y a ici que le minimum qu'une classe de ce type doit avoir car on est ici dans un modèle de classe abstraite.

        # Configuration
        self.config: Config = conf

        # Liste des RBI actuellement chargées
        self.loaded_rbis: dict[str, RainbowInstance] = {}
        # Mutex pour protéger le chargement d'une RBI
        self.mutex_loading_rbi: Lock = Lock()

        #
        self.send_to_client_is_coroutine: bool = True

    #
    async def send_to_client(self, client: Wsp | Sock, message: dict) -> None:
        """
        Envoie un message au client demandé.

        Args:
            client (Wsp | Sock): client auquel envoyer le message
            message (dict): message à envoyer.
        """
        # On ne fait rien, on est dans une classe abstraite, on donne juste l'interface minimale de la classe.
        return

    #
    async def handle_rbi_ask_infos(self, client_id: str, client: Wsp | Sock, message: dict) -> None:
        """
        Fonction qui va renvoyer au client les infos sur une rbi demandée

        Args:
            client_id (str): Id du client qui a envoyé le message
            client (Wsp | Sock): Socket du client qui a envoyé le message
            message (dict): Message reçu par le client
        """
        # On ne fait rien, on est dans une classe abstraite, on donne juste l'interface minimale de la classe.
        return

