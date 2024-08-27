"""
Classe Message représentant un message d'une bulle de Rainbow

Auteur: Nathan Cerisara
"""

from dataclasses import dataclass
from typing import Optional, Self

import os
import json

from lib import FunctionResult, ResultError, ResultSuccess


#
class Message():
    """
    Summary: Représente un message d'une bulle de Rainbow
    """

    def __init__(self) -> None:
        # Identifiant unique de la bulle
        self.id: str = ""

        # Contenu textuel du message
        self.content: str = ""

        # Id de l'auteur du message
        # (référence à un objet de la classe User)
        self.author_id: str = ""
        #
        self.author_name: str | set[str] = set()

        # Date du message
        self.date: str = ""

        # Id de la bulle dans lequel ce message est
        # (référence à un objet de la classe Bubble)
        self.bubble_id: str = ""

        # Id d'un message auquel ce message-ci est une réponse,
        #   vaut "" ou "-1" si ce message n'est pas une réponse (dans la plupart des cas)
        # (référence à un objet de la classe Message)
        self.answered_message_id: str = ""

    #
    def __str__(self) -> str:
        """
        Renvoie un texte qui décrit ce message lorsqu'on essaie de l'afficher avec print par exemple.

        Returns:
            str: Le texte à afficher qui décrit ce message
        """

        return f"Message(id={self.id}, content={self.content}, author_id={self.author_id}, author_name=\"{self.author_name}\", date={self.date}, bubble_id={self.bubble_id})"

    #
    def save(self, base_path: str) -> FunctionResult:
        """
        Sauvegarde un Message

        Args:
            base_path (str): Chemin du dossier racine où est sauvegardée l'instance Rainbow

        Returns:
            FunctionResult: ResultSuccess si le message a bien été sauvegardée, ResultError sinon
        """

        # On crée le sous-dossier pour sauvegarder les messages s'il n'existe pas déjà
        if not os.path.exists(f"{base_path}messages/"):
            os.makedirs(f"{base_path}messages/")

        # Chemin du fichier pour sauvegarder le message
        path: str = f"{base_path}messages/message_{self.id}.json"

        # Sauvegarde du message sous le format json
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "id": self.id,
                "content": self.content,
                "author_id": self.author_id,
                "author_name": self.author_name if isinstance(self.author_name, str) else list(self.author_name),
                "date": self.date,
                "bubble_id": self.bubble_id,
                "answered_message_id": self.answered_message_id
            }, f)

        # Tout c'est bien passé jusqu'ici, on a bien sauvegardé le message
        return ResultSuccess()

    #
    def load(self, path: str) -> FunctionResult:
        """
        Charge un message sauvegardée

        Args:
            path (str): Chemin vers le message sauvegardée

        Returns:
            FunctionResult: ResultSuccess si le message a été correctement chargé, ResultError sinon
        """

        # On vérifie que le chemin existe bien
        if not os.path.exists(path):
            return ResultError(f"Le chemin {path} n'existe pas.")

        # On ouvre le fichier
        with open(path, "r", encoding="utf-8") as f:

            # On récupère les données sous le format json
            d: dict = json.load(f)

            # On récupère l'id
            id: Optional[str | int] = d.get("id")
            if id is not None:
                self.id = str(id)
            else:
                return ResultError(f"Le fichier {path} ne contient pas de champs `id`.")

            # On récupère le contenu du message
            content: Optional[str] = d.get("content")
            if content is not None:
                self.content = content
            else:
                return ResultError(f"Le fichier {path} ne contient pas de champs `content`.")

            # On récupère l'id de l'auteur du message
            author_id: Optional[str | int] = d.get("author_id")
            if author_id is not None:
                self.author_id = str(author_id)
            else:
                return ResultError(f"Le fichier {path} ne contient pas de champs `author_id`.")

            # On récupère le nom de l'auteur du message
            author_name: Optional[str | list[str]] = d.get("author_name")
            if author_name is not None:
                if isinstance(self.author_name, str):
                    self.author_name = author_name
                elif isinstance(self.author_name, list):
                    self.author_name = set(author_name)
                elif isinstance(self.author_name, set):
                    self.author_name = set(author_name)
                else:
                    self.author_name = set()
            else:
                return ResultError(f"Le fichier {path} ne contient pas de champs `author_name`.")

            # On récupère la date du message
            date: Optional[str] = d.get("date")
            if date is not None:
                self.date = date
            else:
                return ResultError(f"Le fichier {path} ne contient pas de champs `date`.")

            # On récupère l'id de la bulle dans laquelle ce message est
            bubble_id: Optional[str | int] = d.get("bubble_id")
            if bubble_id is not None:
                self.bubble_id = str(bubble_id)
            else:
                return ResultError(f"Le fichier {path} ne contient pas de champs `bubble_id`.")

            # On récupère l'id du message dont ce message est peut-être une réponse
            answered_message_id: Optional[str | int] = d.get("answered_message_id")
            if answered_message_id is not None:
                self.answered_message_id = str(answered_message_id)
                if self.answered_message_id == "-1": # Pour assurer la compatibilité entre le refactoring du code qui transforme les id de int à str
                    self.answered_message_id = ""
            else:
                return ResultError(f"Le fichier {path} ne contient pas de champs `answered_message_id`.")


        # Tout c'est bien passé jusqu'ici, on a bien chargé le message
        return ResultSuccess()

    #
    def export_to_dict(self) -> dict:
        """
        Exporte un message dans un dictionnaire

        Returns:
            dict: Le message sous le format dictionnaire
        """
        return {
            "id": self.id,
            "content": self.content,
            "author_id": self.author_id,
            "author_name": self.author_name if isinstance(self.author_name, str) else ", ".join(list(self.author_name)),
            "date": self.date,
            "bubble_id": self.bubble_id,
            "answered_message_id": self.answered_message_id
        }

    #
    def new_msg_copy(self) -> Self:
        """
        Fonction de copie de cet objet Message.

        Returns:
            Message: L'objet copié de ce message.
        """

        # On crée un nouveau objet message, et on copie les attributs de ce message vers le nouveau message
        new_msg: Message = Message()
        new_msg.content = self.content
        new_msg.author_id = self.author_id
        new_msg.bubble_id = self.bubble_id
        new_msg.date = self.date
        new_msg.answered_message_id = self.answered_message_id

        return new_msg

#
@dataclass
class MessagePart:

    # Id de la partie du message
    msg_id: str

    # Indication sur la partie du message (début, fin) (en charactères)
    #   Si cette valeur est à None, alors on considère le message en entier
    part: Optional[tuple[int, int]] = None

    def __str__(self) -> str:
        return f"MessagePart(msg_id={self.msg_id}, part={self.part})"


#
@dataclass
class MessageSearch:

    # Contenu textuel d'un message, d'une partie d'un message ou d'un block de messages
    content: str

    # Date du message ou de la partie d'un message, ou d'un block de message
    date: str

    # Auteur du message, ou liste d'auteurs du groupe de message
    author_id: set[str]
    author_name: set[str]

    # Message(s) pointé(s) par ce contenu textuel
    msg_pointing: list[MessagePart]

    #
    def __str__(self) -> str:
        return f"MessageSearch(content=\"{self.content}\", date=\"{self.date}\", author_id={self.author_id}, author_name={self.author_name}, msg_pointing={[mp.__str__() for mp in self.msg_pointing]})"

