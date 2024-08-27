"""
Classe User représentant un Utilisateur de Rainbow

Auteur: Nathan Cerisara
"""

from typing import Optional

import os
import json

from lib import FunctionResult, ResultError, ResultSuccess


#
class User():
    """
    Summary: Représente un utilisateur de Rainbow
    """

    def __init__(self) -> None:

        # Identifiant unique de l'utilisateur
        self.id: str = ""

        # Nom de l'utilisateur
        self.name: str = ""

        # Liste des ids des bulles dont l'utilisateur est
        #  (référence vers objets de type Bubble)
        self.bubbles_ids: set[str] = set()

        # Liste des messages dont l'utilisateur a envoyé au total, toutes les bulles mélangées
        #  (référence vers objets de type Message)
        self.messages_ids: set[str] = set()

    #
    def __str__(self) -> str:
        """
        Renvoie un texte qui décrit cet utilisateur lorsqu'on essaie de l'afficher avec print par exemple.

        Returns:
            str: Le texte à afficher qui décrit cet utilisateur
        """

        return f"User(id={self.id}, name={self.name}, bubbles_ids={self.bubbles_ids}, messages_ids={self.messages_ids})"

    #
    def save(self, base_path: str) -> FunctionResult:
        """
        Sauvegarde un utilisateur

        Args:
            base_path (str): Chemin du dossier racine où est sauvegardée l'instance Rainbow

        Returns:
            FunctionResult: ResultSuccess si l'utilisateur a bien été sauvegardée, ResultError sinon
        """

        # On crée le sous-dossier pour sauvegarder les utilisateurs s'il n'existe pas déjà
        if not os.path.exists(f"{base_path}users/"):
            os.makedirs(f"{base_path}users/")

        # Chemin du fichier pour sauvegarder l'utilisateur
        path: str = f"{base_path}users/user_{self.id}.json"

        # Sauvegarde de l'utilisateur sous le format json
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "id": self.id,
                "name": self.name,
                "bubbles_ids": list(self.bubbles_ids),
                "messages_ids": list(self.messages_ids)
            }, f)

        # Tout c'est bien passé jusqu'ici, on a bien sauvegardé l'utilisateur
        return ResultSuccess()

    #
    def load(self, path: str) -> FunctionResult:
        """
        Charge une bulle sauvegardée

        Args:
            path (str): Chemin vers l'utilisateur sauvegardée

        Returns:
            FunctionResult: ResultSuccess si l'utilisateur a été correctement chargée, ResultError sinon
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

            # On récupère le nom
            name: Optional[str] = d.get("name")
            if name is not None:
                self.name = name
            else:
                return ResultError(f"Le fichier {path} ne contient pas de champs `name`.")

            # On récupère la liste des bulles
            bubbles_ids: Optional[list[int | str]] = d.get("bubbles_ids")
            if bubbles_ids is not None:
                self.bubbles_ids = set([str(bid) for bid in bubbles_ids])
            else:
                return ResultError(f"Le fichier {path} ne contient pas de champs `bubbles_ids`.")

            # On récupère la liste des messages
            messages_ids: Optional[list[int | str]] = d.get("messages_ids")
            if messages_ids is not None:
                self.messages_ids = set([str(mid) for mid in messages_ids])
            else:
                return ResultError(f"Le fichier {path} ne contient pas de champs `messages_ids`.")

        # Tout c'est bien passé jusqu'ici, on a bien chargé l'utilisateur
        return ResultSuccess()

    #
    def export_to_dict(self) -> dict:
        """
        Exporte un utilisateur dans un dictionnaire

        Returns:
            dict: L'utilisateur sous le format dictionnaire
        """
        return {
            "id": self.id,
            "name": self.name,
            "bubbles_ids": list(self.bubbles_ids),
            "messages_ids": list(self.messages_ids)
        }

