"""
Classe Bubble représentant une bulle de Rainbow

Auteur: Nathan Cerisara
"""

from typing import Optional

import os
import json

from lib import FunctionResult, ResultError, ResultSuccess


#
class Bubble():
    """
    Représente une bulle de Rainbow
    """

    def __init__(self) -> None:
        # Identifiant unique de la bulle
        self.id: str = ""

        # Nom de la bulle
        self.name: str = ""

        # Liste des ids des membres de la bulle
        # (référence à un objet de la classe User)
        self.members_ids: set[str] = set()

        # Liste des ids des messages de la bulle
        # (référence à un objet de la classe Message)
        self.messages_ids: set[str] = set()

    #
    def __str__(self) -> str:
        """
        Renvoie un texte qui décrit cette bulle lorsqu'on essaie de l'afficher avec print par exemple.

        Returns:
            str: Le texte à afficher qui décrit cette bulle
        """

        return f"Bubble(id={self.id}, name={self.name}, members_id={self.members_ids}, messages_ids={self.messages_ids})"

    #
    def save(self, base_path: str) -> FunctionResult:
        """
        Sauvegarde une Bulle

        Args:
            base_path (str): Chemin du dossier racine où est sauvegardée l'instance Rainbow

        Returns:
            FunctionResult: ResultSuccess si la bulle a bien été sauvegardée, ResultError sinon
        """

        # On crée le sous-dossier pour sauvegarder les bulles s'il n'existe pas déjà
        if not os.path.exists(f"{base_path}bubbles/"):
            os.makedirs(f"{base_path}bubbles/")

        # Chemin du fichier pour sauvegarder la bulle
        path: str = f"{base_path}bubbles/bubble_{self.id}.json"

        # Sauvegarde de la bulle sous le format json
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "id": self.id,
                "name": self.name,
                "members_ids": list(self.members_ids),
                "messages_ids": list(self.messages_ids)
            }, f)

        # Tout c'est bien passé jusqu'ici, on a bien sauvegardé la bulle
        return ResultSuccess()

    #
    def load(self, path: str) -> FunctionResult:
        """
        Charge une bulle sauvegardée

        Args:
            path (str): Chemin vers la bulle sauvegardée

        Returns:
            FunctionResult: ResultSuccess si la bulle a été correctement chargée, ResultError sinon
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

            # On récupère la liste des membres
            members_ids: Optional[list[str | int]] = d.get("members_ids")
            if members_ids is not None:
                self.members_ids = set([str(mid) for mid in members_ids])
            else:
                return ResultError(f"Le fichier {path} ne contient pas de champs `members_id`.")

            # On récupère la liste des messages
            messages_ids: Optional[list[str | int]] = d.get("messages_ids")
            if messages_ids is not None:
                self.messages_ids = set([str(mid) for mid in messages_ids])
            else:
                return ResultError(f"Le fichier {path} ne contient pas de champs `messages_ids`.")

        # Tout c'est bien passé jusqu'ici, on a bien chargé la bulle
        return ResultSuccess()

    #
    def export_to_dict(self) -> dict:
        """
        Exporte une bulle dans un dictionnaire

        Returns:
            dict: La bulle sous le format dictionnaire
        """
        return {
            "id": self.id,
            "name": self.name,
            "members_ids": list(self.members_ids),
            "messages_ids": list(self.messages_ids)
        }

