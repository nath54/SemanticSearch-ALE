"""
Algorithme de découpe des conversations pour Rainbow

Auteur: Nathan Cerisara
"""


from dataclasses import dataclass
from typing import Optional, Any, cast

import os
import json
from torch import Tensor

from message import Message, MessagePart
from search_engine import SearchEngine
from config import Config
from lib import ConfigError, Date, avg, median

from profiling import profiling_task_start, profiling_last_task_ends





@dataclass
class ResultConversationCut:

    # Résultats
    conversations_msgs: list[list[str | MessagePart]]

    # Id du message -> couleur du message
    msgs_colors: dict[str, int]

    # Nombres de conversations
    nb_conversations: int

    # For all algorithms that uses a distance between messages matrix. (Dimension [n, n] )
    distances_matrix: Optional[Tensor] = None


#
class ConversationsAlgorithm:
    """
    Algorithme de découpe des conversations. Classe abstraite.
    """

    def __init__(self, algo_config: dict, config: Config) -> None:
        self.algo_config: dict = algo_config
        self.config: Config = config
        #

    #
    def cut(self, msgs: dict[str, Message]) -> ResultConversationCut:
        """
        Schéma Abstrait de la fonction de découpage des conversations.

        Args:
            msgs (dict[str, Message]): Liste des messages à regrouper en conversations, format {id_msg -> Message}.

        Returns:
            list[list[str | MessagePart]]: Liste des conversations, chaque conversation contenant soit des id de messages, soit des parties de messages.
        """
        return ResultConversationCut(list(msgs.keys()))


#
class SimpleTimeDifferences_ConversationAlgorithm(ConversationsAlgorithm):

    def __init__(self, algo_config: dict, config: Config) -> None:
        super().__init__(algo_config, config)

        # On vérifie que l'on a bien les attributs essentiels
        # TODO: utiliser le dictionnaire qui est au-dessus mtn avec les clés, et même la vérification de types
        for k in ["treshold_value", "treshold_type"]:
            if not k in algo_config:
                raise ConfigError(f"No key {k} in conversation algorithm config : {algo_config} !")
        #
        self.treshold_value: float = float(algo_config["treshold_value"])
        self.treshold_type: str = algo_config["treshold_type"]

    #
    def cut(self, msgs: dict[str, Message]) -> list[list[str | MessagePart]]:
        """
        Découpage des conversations avec la date. Si la différence de temps entre deux messages est plus grand qu'un certain treshold, on change de conversation.

        Args:
            msgs (dict[str, Message]): Liste des messages à regrouper en conversations, format {id_msg -> Message}.

        Returns:
            list[list[str | MessagePart]]: Liste des conversations, chaque conversation contenant soit des id de messages, soit des parties de messages.
        """

        conversations: list[list[str | MessagePart]] = []
        msgs_colors: dict[str, int] = {}
        nb_conversations: int = 0
        current_conversation: int = -1

        #
        id_msg: str
        for id_msg in msgs:
            #
            if current_conversation == -1:
                current_conversation = len(conversations)
                conversations.append([])
                nb_conversations += 1
            #
            separate: bool = False
            #
            if len(conversations[current_conversation]) > 0:
                #
                id_last: int = cast(int, conversations[current_conversation][-1])
                #
                if self.treshold_type == "seconds":
                    if abs(Date(from_txt_date=msgs[id_last].date).to_seconds() - Date(from_txt_date=msgs[id_msg].date).to_seconds()) >= self.treshold_value:
                        separate = True
                elif self.treshold_type == "minutes":
                    if abs(Date(from_txt_date=msgs[id_last].date).to_minutes() - Date(from_txt_date=msgs[id_msg].date).to_minutes()) >= self.treshold_value:
                        separate = True
                elif self.treshold_type == "hours":
                    if abs(Date(from_txt_date=msgs[id_last].date).to_hours() - Date(from_txt_date=msgs[id_msg].date).to_hours()) >= self.treshold_value:
                        separate = True
                elif self.treshold_type == "days":
                    if abs(Date(from_txt_date=msgs[id_last].date).to_days() - Date(from_txt_date=msgs[id_msg].date).to_days()) >= self.treshold_value:
                        separate = True
            #
            if separate:
                current_conversation = len(conversations)
                conversations.append([])
                nb_conversations += 1
            #
            conversations[current_conversation].append(id_msg)
            msgs_colors[id_msg] = current_conversation

        return ResultConversationCut(conversations, msgs_colors, nb_conversations)


#
class ClusteringFusion_ConversationAlgorithm(ConversationsAlgorithm):

    def __init__(self, algo_config: dict, config: Config) -> None:
        super().__init__(algo_config, config)

        # On vérifie que l'on a bien les attributs essentiels
        # TODO: utiliser le dictionnaire qui est au-dessus mtn avec les clés, et même la vérification de types
        for k in ["search_engine_config_dict", "treshold_conversation_distance"]:
            if not k in algo_config:
                raise ConfigError(f"No key {k} in conversation algorithm config : {algo_config} !")

        # On récupère les attributs
        self.search_engine_config_dict: str = algo_config["search_engine_config_dict"]
        self.treshold_conversation_distance: float = float(algo_config["treshold_conversation_distance"])

        # On va charger le moteur de recherche
        self.search_engine: SearchEngine = SearchEngine(self.search_engine_config_dict, self.config)

        # Nombre d'itérations maximal
        self.max_iterations: int = 20

    #
    def cut(self, msgs: dict[str, Message], ner_dicts: list[str] = []) -> ResultConversationCut:
        """
        Découpage des conversations avec un moteur de distance entre messages et un algorithme de clustering de type Fusion. Ce moteur utilise des embeddings de texte pour de la recherche sémantique, mais aussi de la distance temporelle et autre.

        Args:
            msgs (dict[str, Message]): Liste des messages à regrouper en conversations, format {id_msg -> Message}.

        Returns:
            ResultConversationCut: Liste des conversations, chaque conversation contenant soit des id de messages, soit des parties de messages.
        """

        # Contient les conversations finales
        conversations: list[list[str | MessagePart]] = []

        # Contient la liste des messages que l'on va clusteriser
        lst_messages: list[Message] = []
        # Permet de passer entre l'index de la liste lst_messages à id_msg
        conv_lst_msgs_id: list[str] = []
        # Va contenir le numéro de conversation associé à chaque message à tout moment de l'algorithme
        msgs_conversations: list[int] = []
        # Va contenir la liste des messages pour chacunes des conversations
        conversations_msgs: dict[int, list[int]] = {}
        #

        # On va remplir les deux listes de ci-dessus
        id_msg: str
        msg: Message
        for (id_msg, msg) in msgs.items():
            conversations_msgs[len(msgs_conversations)] = [len(msgs_conversations)]
            msgs_conversations.append(len(msgs_conversations))
            lst_messages.append(msg)
            conv_lst_msgs_id.append(id_msg)

        # On va calculer la matrice des distances
        distances_matrix: Tensor = self.search_engine.get_distances_matrix_from_messages_main(lst_messages, ner_dicts)

        # On va appliquer l'algorithme de clustering suivant:
        # à chaque itération:
        # on va calculer les distance moyenne, médiane, minimales et maximales de chaque messages aux messages des autres conversation,
        # ainsi que la sienne s'il est dans une conversation avec au moins X messages.
        #   -> On va bouger le message vers la conversation de distance moyenne minimale
        id_conv: int
        msg_idx: int
        id_iteration: int = 0
        changes: bool = True

        while changes and id_iteration < self.max_iterations:

            # On incrémente le compteur d'itérations
            id_iteration += 1

            #
            changes = False

            # On parcours donc tous les messages à chaque itération
            for msg_idx in range(len(lst_messages))[::-1]:

                #
                id_min_conv: int = -1
                conversations_dists: dict[int, dict[str, float]] = {}

                # On va donc parcourir toutes les conversations
                for id_conv in conversations_msgs.keys():

                    # On évite les situations bloquantes, car si un message est tout seul dans une conversation, il ne voudra jamais en sortir car la distance moyenne à la conversation sera toujours 0
                    if id_conv == msgs_conversations[msg_idx] and len(conversations_msgs[id_conv]) == 1:
                        continue

                    # On évite les listes vides aussi, ca pose problème
                    if len(conversations_msgs[id_conv]) == 0:
                        continue

                    # On initialise la distance
                    dists: list[float] = []

                    # On va donc parcourir les messages de la conversation et ajouter leurs distance à la liste temporaire des distances
                    for msg2_idx in conversations_msgs[id_conv]:
                        dists.append(distances_matrix[msg_idx, msg2_idx])

                    # On récupère ces valeurs
                    conversations_dists[id_conv] = {
                        "avg": avg(dists),
                        "min": min(dists),
                        "max": max(dists),
                        "median": median(dists)
                    }

                    conversations_dists[id_conv]["modif_avg"] = float(conversations_dists[id_conv]["avg"] + conversations_dists[id_conv]["min"] + conversations_dists[id_conv]["max"]) / 3.0

                    # On va traquer la conversation avec la moyenne minimale
                    if (id_min_conv == -1 or conversations_dists[id_min_conv]["modif_avg"] > conversations_dists[id_conv]["modif_avg"]) and conversations_dists[id_conv]["modif_avg"] <= self.treshold_conversation_distance:
                    # if (id_min_conv == -1 or conversations_dists[id_min_conv]["avg"] > conversations_dists[id_conv]["avg"]) and conversations_dists[id_conv]["avg"] <= self.treshold_conversation_distance:
                    # if (id_min_conv == -1 or conversations_dists[id_min_conv]["min"] > conversations_dists[id_conv]["min"]) and conversations_dists[id_conv]["min"] <= self.treshold_conversation_distance:
                        id_min_conv = id_conv

                # On regarde s'il y a un changement de conversation
                if id_min_conv != -1 and id_min_conv != msgs_conversations[msg_idx]:

                    # Changement !
                    changes = True
                    id_conv_src: int = msgs_conversations[msg_idx]
                    id_conv_dst: int = id_min_conv

                    msgs_conversations[msg_idx] = id_conv_dst
                    conversations_msgs[id_conv_src].remove(msg_idx)
                    conversations_msgs[id_conv_dst].append(msg_idx)
                    #
                    if len(conversations_msgs[id_conv_src]) == 0:
                        del conversations_msgs[id_conv_src]

        # On va récupérer la liste des conversations finales
        #
        msgs_colors: dict[str, int] = {}
        nb_conversations: int = 0
        #
        for id_conv in conversations_msgs:
            conversations.append(conversations_msgs[id_conv])
            #
            nb_conversations += 1
            #
            for id_msg in conversations[-1]:
                msgs_colors[ conv_lst_msgs_id[id_msg] ] = id_conv

        # On renvoie le résultat
        return ResultConversationCut(conversations, msgs_colors, nb_conversations, distances_matrix)


#
class ClusteringSeq_ConversationAlgorithm(ConversationsAlgorithm):

    def __init__(self, algo_config: dict, config: Config) -> None:
        super().__init__(algo_config, config)

        # On vérifie que l'on a bien les attributs essentiels
        # TODO: utiliser le dictionnaire qui est au-dessus mtn avec les clés, et même la vérification de types
        for k in ["search_engine_config_dict", "treshold_conversation_distance"]:
            if not k in algo_config:
                raise ConfigError(f"No key {k} in conversation algorithm config : {algo_config} !")

        # On récupère les attributs
        self.search_engine_config_dict: str = algo_config["search_engine_config_dict"]
        self.treshold_conversation_distance: float = float(algo_config["treshold_conversation_distance"])

        # On va charger le moteur de recherche
        self.search_engine: SearchEngine = SearchEngine(self.search_engine_config_dict, self.config)

    #
    def cut(self, msgs: dict[str, Message], ner_dicts: list[str] = []) -> ResultConversationCut:
        """
        Découpage des conversations avec un moteur de distance entre messages et un algorithme de clustering qui va progressivement ajouter séquentiellement les messages dans les conversations. Ce moteur utilise des embeddings de texte pour de la recherche sémantique, mais aussi de la distance temporelle et autre.

        Args:
            msgs (dict[str, Message]): Liste des messages à regrouper en conversations, format {id_msg -> Message}.

        Returns:
            list[list[str | MessagePart]]: Liste des conversations, chaque conversation contenant soit des id de messages, soit des parties de messages.
        """

        # Contient les conversations finales
        conversations: list[list[str | MessagePart]] = []

        # Contient la liste des messages que l'on va clusteriser
        lst_messages: list[Message] = []
        # Permet de passer entre l'index de la liste lst_messages à id_msg
        conv_lst_msgs_id: list[str] = []
        # Va contenir le numéro de conversation associé à chaque message à tout moment de l'algorithme
        msgs_conversations: list[int] = [-1] * len(msgs)
        # Va contenir la liste des messages pour chacunes des conversations
        conversations_msgs: dict[int, list[int]] = {}
        #

        # On va remplir les deux listes de ci-dessus
        id_msg: str
        msg: Message
        for (id_msg, msg) in msgs.items():
            lst_messages.append(msg)
            conv_lst_msgs_id.append(id_msg)

        # On va calculer la matrice des distances
        distances_matrix: Tensor = self.search_engine.get_distances_matrix_from_messages_main(lst_messages, ner_dicts)

        # On va appliquer l'algorithme de clustering suivant:
        # à chaque itération:
        # on va calculer les distance moyenne, médiane, minimales et maximales de chaque messages aux messages des autres conversation,
        # ainsi que la sienne s'il est dans une conversation avec au moins X messages.
        #   -> On va bouger le message vers la conversation de distance moyenne minimale
        id_conv: int
        msg_idx: int

        # On parcours donc une seule fois tous les messages
        for msg_idx in range(len(lst_messages)):

            # On va chercher la conversation déjà existante qui se rapproche le plus de ce message
            id_min_conv: int = -1
            conversations_dists: dict[int, dict[str, float]] = {}

            # On va donc parcourir toutes les conversations
            for id_conv in conversations_msgs.keys():

                # On évite les listes vides aussi, ca pose problème
                if len(conversations_msgs[id_conv]) == 0:
                    continue

                # On initialise la distance
                dists: list[float] = []

                # On va donc parcourir les messages de la conversation et ajouter leurs distance à la liste temporaire des distances
                for msg2_idx in conversations_msgs[id_conv]:
                    dists.append(distances_matrix[msg_idx, msg2_idx])

                # On récupère ces valeurs
                conversations_dists[id_conv] = {
                    "avg": avg(dists),
                    "min": min(dists),
                    "max": max(dists),
                    "median": median(dists)
                }

                # On va traquer la conversation avec la moyenne minimale
                if (id_min_conv == -1 or conversations_dists[id_min_conv]["avg"] > conversations_dists[id_conv]["avg"]) and conversations_dists[id_conv]["avg"] <= self.treshold_conversation_distance:
                # if (id_min_conv == -1 or conversations_dists[id_min_conv]["min"] > conversations_dists[id_conv]["min"]) and conversations_dists[id_conv]["min"] <= self.treshold_conversation_distance:
                    id_min_conv = id_conv

            # On regarde si l'on doit créer une nouvelle conversation
            id_conv_dst: int = id_min_conv
            if id_min_conv == -1:
                # On crée une conversation
                id_conv_dst = len(conversations_msgs)
                conversations_msgs[id_conv_dst] = []

            # On rajoute le message à la conversation
            msgs_conversations[msg_idx] = id_conv_dst
            conversations_msgs[id_conv_dst].append(msg_idx)

        # On va récupérer la liste des conversations finales
        #
        msgs_colors: dict[str, int] = {}
        nb_conversations: int = 0
        #
        for id_conv in conversations_msgs:
            conversations.append(conversations_msgs[id_conv])
            #
            nb_conversations += 1
            #
            for id_msg in conversations[-1]:
                msgs_colors[ conv_lst_msgs_id[id_msg] ] = id_conv

        # On renvoie le résultat
        return ResultConversationCut(conversations, msgs_colors, nb_conversations, distances_matrix)

