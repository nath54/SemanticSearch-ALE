"""
Ce fichier contient une classe et des fonctions pour faire du cache d'embeddings, ce qui permet de calculer une seule fois un embedding, et d'ensuite l'enregistrer sur le disque, et ensuite, on le recharge au lieu de le recalculer.

Auteur: Nathan Cerisara
"""

from typing import Optional

import os
import json
import pickle

from config import Config
from lib_embedding import MessageEmbedding, load_message_embedding_from_dict
from lib import escapeCharacters

from profiling import profiling_task_start, profiling_last_task_ends


#
class EmbeddingCache:
    """
    Ce fichier contient une classe et des fonctions pour faire du cache d'embeddings, ce qui permet de calculer une seule fois un embedding, et d'ensuite l'enregistrer sur le disque, et ensuite, on le recharge au lieu de le recalculer.
    La méthode utilisée ici est de stocker chaque embedding dans un fichier à part dans un sous-dossier à part pour chaque modèle d'embedding différent.
    """

    def __init__(self, embedding_model_name: str, conf: Config) -> None:
        # La configuration globale du projet
        self.conf: Config = conf

        # Le nom du modèle d'embedding utilisé
        self.embedding_model_name: str = embedding_model_name

        # On prépare ici le chemin où seront enregistrés les embeddings
        self.base_dir_path: str = f"{self.conf.cache_dir_embeddings}/{self.embedding_model_name}/"

        # Pour savoir s'il y a des modifications que l'on n'a pas enregistrées
        self.unsaved_changes: bool = False

        # On crée le dossier où l'on va enregistrer les embeddings s'il n'existe pas encore
        if not os.path.exists(self.base_dir_path):
            os.makedirs(self.base_dir_path)

        # Un buffer pour ne pas lire/écrire sur le disque à chaque fois
        self.buffer: dict[str, MessageEmbedding] = {}
        self.max_buffer_size: int = 20
        #

    #
    def get_path_key(self, txt_key: str) -> str:
        """
        Fonction pour convertir le texte du message de l'embedding vers un chemin précis.

        Args:
            txt_key (str): le texte du message de l'embedding

        Returns:
            str: Le chemin pour l'embedding sauvegardé pour ce message de l'embedding
        """

        file_base_name: str = f"{self.base_dir_path}{txt_key}"
        #
        if len(file_base_name) > 260:
            file_base_name = file_base_name[:260]
        #
        return f"{file_base_name}.pk"

    #
    def save_txt_key_from_buffer(self, txt_key: str) -> None:
        """
        Enregistre sur le disque l'embedding d'un message qui est dans le buffer

        Args:
            txt_key (str): le texte du message de l'embedding

        Raises:
            SystemError: renvoie une erreur si le message à enregistrer n'est pas dans le buffer
        """

        #
        if not txt_key in self.buffer:
            raise SystemError(f"Error, key \"{txt_key}\" is not in buffer")
        #
        with open(self.get_path_key(txt_key), "wb") as f:
            pickle.dump(self.buffer[txt_key], f, protocol=pickle.HIGHEST_PROTOCOL)

    #
    def save_txt_key_directly(self, txt_key: str, msg_emb: MessageEmbedding) -> None:
        """
        Sauvegarde directement un message et son embedding sur le disque.

        Args:
            txt_key (str): le texte du message de l'embedding
            msg_emb (MessageEmbedding): l'embedding du message
        """

        #
        with open(self.get_path_key(txt_key), "wb") as f:
            pickle.dump(msg_emb, f, protocol=pickle.HIGHEST_PROTOCOL)
        #
        print(f"Cache set : {self.get_path_key(txt_key)}")
        #

    #
    def add_to_buffer(self, txt_key: str, msg_emb: MessageEmbedding) -> None:
        """
        Ajoute un message et son embedding dans le buffer.

        Args:
            txt_key (str): le texte du message de l'embedding
            msg_emb (MessageEmbedding): L'embedding du message
        """

        #
        if len(self.buffer) >= self.max_buffer_size:
            self.save()
        #
        self.buffer = {}
        #
        self.buffer[txt_key] = msg_emb
        #
        self.unsaved_changes = True

    #
    def save(self) -> None:
        """
        Sauvegarde toutes les modifications du caches qui n'ont pas encore été sauvegardées.
        """

        # On ne sauvegarde pas s'il n'y a rien à sauvegarder
        if not self.unsaved_changes:
            return

        #
        for txt_key in self.buffer:
            self.save_txt_key_from_buffer(txt_key)

        #
        self.unsaved_changes = False

    #
    def has(self, txt_key: str) -> bool:
        """
        Renvoie Vrai ou Faux s'il y a ou non un embedding pré-calculé dans le cache pour un message demandé.

        Args:
            txt_key (str): le texte du message de l'embedding

        Returns:
            bool: Vrai si il y a un embedding pré-calculé associé à ce message dans le cache, Faux sinon
        """

        #
        txt_key = escapeCharacters(txt_key)
        #
        return os.path.exists(self.get_path_key(txt_key))

    #
    def get(self, txt_key: str) -> Optional[MessageEmbedding]:
        """
        Récupère s'il existe l'embedding pré-calculé pour le message qui lui est associé.

        Args:
            txt_key (str): le texte du message de l'embedding

        Returns:
            Optional[MessageEmbedding]: L'embedding pré-calculé pour ce message
        """

        #
        txt_key = escapeCharacters(txt_key)
        #
        if not self.has(txt_key):
            return None
        #
        try:
            #
            with open(self.get_path_key(txt_key), "rb") as f:
                msg_embedding: MessageEmbedding = pickle.load(f)
            return msg_embedding
        #
        except Exception as e:
            #
            os.remove(self.get_path_key(txt_key))
            #
            print(f"Error JSON embedding loading: {txt_key}")
            return None

    #
    def set(self, txt_key: str, message_embedding: MessageEmbedding) -> None:
        """
        Ajoute dans le cache l'embedding calculé pour le message qui lui est associé.

        Args:
            txt_key (str): le texte du message de l'embedding
            message_embedding (MessageEmbedding): L'embedding calculé
        """

        #
        txt_key = escapeCharacters(txt_key)
        #
        self.save_txt_key_directly(txt_key, message_embedding)
        #
        # self.add_to_buffer(txt_key, message_embedding)
        #
        # self.unsaved_changes = True

