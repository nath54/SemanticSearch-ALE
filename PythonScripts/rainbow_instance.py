"""
Classe RainbowInstance représentant un example de serveur Rainbow, avec ses utilisateurs, ses entreprises, ses bulles avec ses conversations...

Auteur: Nathan Cerisara
"""

from typing import Optional

import os

from user import User
from bubble import Bubble
from message import Message

from config import Config
from lib import FunctionResult, ResultError, ResultSuccess


#
class RainbowInstance():
    """
    Summary: Classe RainbowInstance représentant un example de serveur Rainbow.
    """

    def __init__(self, server_name: str, config: Config) -> None:

        # Configuration du projet
        self.config: Config = config

        # Nom du serveur/instance Rainbow
        self.server_name: str = server_name

        # Liste des Utilisateurs, indexés par leur id
        self.users: dict[str, User] = {}
        # On va aussi faire une indexation sur leurs noms pour que ce soit plus simple pour la conversion dans `convert_fake_data_to_FakeRainbow_Instance.py`
        # Dictionnaire[nom -> index dans le dict self.users]
        self.users_names: dict[str, str] = {}

        # Liste des bulles, indexées par leur id
        self.bubbles: dict[str, Bubble] = {}

        # Liste des messages, indexés par leur id
        self.messages: dict[str, Message] = {}

        #
        self.loaded: bool = False

        # On charge s'il y a quelque chose à charger
        if self.have_something_to_load():
            self.load()

    #
    def save(self) -> FunctionResult:
        """
        Sauvegarde l'instance Rainbow.

        Args:

        Returns:
            success (FunctionResult): Renvoie ResultSuccess si la sauvegarde s'est bien passée, sinon ResultError
        """

        # Chemin de base pour sauvegarder
        base_path: str = f"{self.config.base_path_rbi_converted_saved}{self.server_name}/"

        # Si le chemin de base n'existe pas, alors on le crée
        if not os.path.exists(base_path):
            os.makedirs(base_path)

        # Identifiant des éléments à sauvegarder
        id:str

        # Retour des fonctions
        res: FunctionResult

        # On sauvegarde les utilisateurs
        for id in self.users:
            res = self.users[id].save(base_path)
            if isinstance(res, ResultError):
                return res

        # On sauvegarde les bulles
        for id in self.bubbles:
            res = self.bubbles[id].save(base_path)
            if isinstance(res, ResultError):
                return res

        # On sauvegarde les messages
        for id in self.messages:
            res = self.messages[id].save(base_path)
            if isinstance(res, ResultError):
                return res

        # Si on est arrivé jusqu'ici, c'est que tout a bien été sauvegardé
        return ResultSuccess()

    #
    def have_something_to_load(self) -> bool:
        """
        Indique s'il y a quelque chose à charger pour cette rbi.

        Returns:
            bool: s'il y a quelque chose à charger pour cette rbi.
        """

        #
        base_path = f"{self.config.base_path_rbi_converted_saved}{self.server_name}/"

        # On renvoie si le chemin de base existe
        return os.path.exists(base_path)

    #
    def load(self) -> FunctionResult:
        """
        Charge l'instance Rainbow demandée.

        Returns:
            success (bool): Renvoie Vrai si le chargement s'est bien passée, sinon Faux
        """

        # # On ne charge pas plusieurs fois
        # if self.loaded:
        #     return ResultError("Déjà chargé!")

        self.loaded = True

        #
        base_path = f"{self.config.base_path_rbi_converted_saved}{self.server_name}/"

        # Si le chemin de base n'existe pas, alors on le crée
        if not os.path.exists(base_path):
            return ResultError("Le chemin n'existe pas.")

        # Retour des fonctions
        res: FunctionResult

        # On va charger tous les utilisateurs
        if os.path.exists(f"{base_path}users/"):
            for e in os.listdir(f"{base_path}users/"):
                user: User = User()
                res = user.load(f"{base_path}users/{e}")
                if isinstance(res, ResultError):
                    return res
                self.users[user.id] = user
                self.users_names[user.name] = user.id

        # On va charger toutes les bulles
        if os.path.exists(f"{base_path}bubbles/"):
            for e in os.listdir(f"{base_path}bubbles/"):
                bubble: Bubble = Bubble()
                res = bubble.load(f"{base_path}bubbles/{e}")
                if isinstance(res, ResultError):
                    return res
                self.bubbles[bubble.id] = bubble

        # On va charger tous les messages
        if os.path.exists(f"{base_path}messages/"):
            for e in os.listdir(f"{base_path}messages/"):
                message: Message = Message()
                res = message.load(f"{base_path}messages/{e}")
                if isinstance(res, ResultError):
                    return res
                self.messages[message.id] = message

        # Si on est arrivé jusqu'ici, c'est que tout a bien été chargé
        return ResultSuccess()

    #
    def get_first_user_new_usable_id(self) -> str:
        """Renvoie le premier id non utilisé pour créer un nouvel utilisateur

        Returns:
            str: Premier id non utilisé
        """

        #
        id: int = len(self.users)
        while str(id) in self.users:
            id += 1

        return str(id)

    #
    def get_first_bubble_new_usable_id(self) -> str:
        """Renvoie le premier id non utilisé pour créer une nouvelle bulle

        Returns:
            str: Premier id non utilisé
        """

        #
        id: int = len(self.bubbles)
        while str(id) in self.bubbles:
            id += 1

        return str(id)

    #
    def get_first_message_new_usable_id(self) -> str:
        """Renvoie le premier id non utilisé pour créer une nouvelle bulle

        Returns:
            str: Premier id non utilisé
        """

        #
        id: int = len(self.messages)
        while str(id) in self.messages:
            id += 1

        return str(id)

    #
    def create_new_bubble(self, bubble_name: Optional[str] = None, bubble_id: Optional[str] = None, force_if_already_exists: bool = False) -> str:
        """
        Crée et ajoute une nouvelle bulle à cette instance Rainbow.

        Args:
            bubble_id (Optional[str], optional): Id de la nouvelle bulle à créer. Defaults to None.

        Returns:
            str: Renvoie l'id de la bulle qui vient d'être créée.
        """

        if bubble_id is not None and bubble_id in self.bubbles and not force_if_already_exists:
            return

        #
        if bubble_id is None:
            bubble_id = self.get_first_bubble_new_usable_id()

        self.bubbles[bubble_id] = Bubble()
        self.bubbles[bubble_id].id = bubble_id
        self.bubbles[bubble_id].name = bubble_id if bubble_name is None else bubble_name

    #
    def create_new_user(self, user_name: str, user_id: Optional[str] = None, force_if_already_exists: bool = False) -> str:
        """
        Crée et ajoute un nouvel utilisateur à cette instance Rainbow.

        Args:
            user_name (str): _description_
            user_id (Optional[str], optional): _description_. Defaults to None.

        Returns:
            str: _description_
        """

        if user_id is not None and user_id in self.users and not force_if_already_exists:
            return

        #
        if user_id is None:
            user_id = self.get_first_user_new_usable_id()

        self.users[user_id] = User()
        self.users[user_id].id = user_id
        self.users[user_id].name = user_id if user_name is None else user_name

    #
    def add_new_message_to_bubble(self, msg_dict: dict, bubble_id: str = None) -> bool:
        """
        Crée et ajoute un nouveau message à cette instance Rainbow.
        Retourne s'il y a eu un problème ou non.

        Args:
            msg_dict (dict): Les infos sur le message à créer/ajouter
        """

        # On vérifie que tout est bon
        for k in ["id", "content", "bubble_id", "bubble_name", "author_id", "author_name", "date", "answered_message_id"]:
            if not k in msg_dict:
                return False  # On renvoie que la création du message ne s'est pas bien passée

        # On vérifie qu'il n'y a pas d'incohérence sur la bulle à laquelle ajouter le message
        if bubble_id is not None and msg_dict["bubble_id"] != bubble_id:
            return False

        # On récupère les valeurs
        msg_id: str = msg_dict["id"]
        msg_content: str = msg_dict["content"]
        msg_date: str = msg_dict["date"]
        bubble_id: str = msg_dict["bubble_id"]
        bubble_name: str = msg_dict["bubble_name"]
        author_id: str = msg_dict["author_id"]
        author_name: str = msg_dict["author_name"]
        answered_message_id: str = msg_dict["answered_message_id"]

        # Si la bulle n'existe pas, on la crée
        if not bubble_id in self.bubbles:
            self.create_new_bubble(bubble_name=bubble_name, bubble_id=bubble_id)

        # Si l'auteur n'existe pas, on le crée
        if not author_id in self.users:
            self.create_new_user(user_name=author_name, user_id=author_id)

        # Si la bulle n'est pas dans les bulles de l'auteur, on l'y rajoute
        if not bubble_id in self.users[author_id].bubbles_ids:
            self.users[author_id].bubbles_ids.add(bubble_id)
            self.bubbles[bubble_id].members_ids.add(author_id)

        # On crée le message et on lui ajoute les valeurs
        self.messages[msg_id] = Message()
        self.messages[msg_id].id = msg_id
        self.messages[msg_id].content = msg_content
        self.messages[msg_id].date = msg_date
        self.messages[msg_id].author_id = author_id
        self.messages[msg_id].author_name = author_name
        self.messages[msg_id].bubble_id = bubble_id
        self.messages[msg_id].answered_message_id = answered_message_id

        # On ajoute ce message à sa bulle et à son utilisateur
        self.bubbles[bubble_id].messages_ids.add(msg_id)
        self.users[author_id].messages_ids.add(msg_id)

        # On renvoie que la création du message s'est bien passée
        return True

