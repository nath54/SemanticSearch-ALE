"""
Moteur de découpe des conversations pour Rainbow

Auteur: Nathan Cerisara
"""


from dataclasses import dataclass
from typing import Optional, Any, cast

from torch import Tensor

from message import Message, MessagePart
from config import Config
from lib import ConfigError, visualize_clusters
from conversations_algorithms import ConversationsAlgorithm, ResultConversationCut
import conversations_algorithms as CA

from profiling import profiling_task_start, profiling_last_task_ends


#
# Liste de tous les algorithmes de découpe de conversations disponibles
ALGORITHMS: dict[str, type[ConversationsAlgorithm]] = {
    "SimpleTimeDifferences_ConversationAlgorithm": CA.SimpleTimeDifferences_ConversationAlgorithm,
    "ClusteringFusion_ConversationAlgorithm": CA.ClusteringFusion_ConversationAlgorithm,
    "ClusteringSeq_ConversationAlgorithm": CA.ClusteringSeq_ConversationAlgorithm
}


#
class ConversationsEngine:
    """
    Moteur de découpe des conversations.
    """

    def __init__(self, conversation_config: dict, config: Config) -> None:
        self.conversation_config: dict = conversation_config
        self.config: Config = config
        #
        for k in ["config_name", "algorithms"]:
            if not k in conversation_config:
                raise ConfigError(f"No key {k} in conversation engine config : {conversation_config} !")
        #
        self.config_name: str = conversation_config["config_name"]
        self.algorithms: list[ConversationsAlgorithm] = []
        self.coefs_algorithms: list[float] = []
        #
        for algo_config in conversation_config["algorithms"]:
            #
            for k in ["type", "coef"]:
                if not k in algo_config:
                    raise ConfigError(f"No key {k} in conversation algorithm config : {algo_config} (from engine config : {self.config_name} !)")
            #
            algo_type: str = algo_config["type"]
            #
            if not algo_type in ALGORITHMS:
                raise UserWarning(f"Unknown conversation algorithm: {algo_type}")
            #
            algo: ConversationsAlgorithm = ALGORITHMS[algo_type](algo_config, config)
            self.algorithms.append(algo)
            self.coefs_algorithms.append(float(algo_config["coef"]))

    #
    def main_cut(self, msgs: dict[str, Message]) -> ResultConversationCut:
        """
        Point d'entrée principal pour faire de la découpe de conversations.
        Appelle un ou plusieurs algorithmes de découpe des conversations et regroupe les résultats.
        # TODO : Pour l'instant, pas de combinaisons des résultats, on va juste renvoyer les résultats du premier algorithme de découpage des conversations.

        Args:
            msgs (dict[str, Message]): Liste des messages à regrouper en conversations, format {id_msg -> Message}.

        Returns:
            list[list[str | MessagePart]]: Liste des conversations, chaque conversation contenant soit des id de messages, soit des parties de messages.
        """

        # S'il n'y a pas de sous-algorithmes
        if len(self.algorithms) == 0:
            # On ne renvoie qu'une seule conversation avec l'id de tous les messages de l'input
            return [list(msgs.keys())]

        # Sinon, pour l'instant, pas de combinaisons d'algorithmes, on ne renvoie les résultats que du premier algorithme.
        res: ResultConversationCut = self.algorithms[0].cut(msgs)

        # Pour visualiser en 2d les clusters de conversations
        # if res.distances_matrix is not None:
        #     print("DEBUG | affichage matrice de distances")
        #     visualize_clusters(res.distances_matrix.numpy())

        #
        # print(f"MAIN CUT ||| Input msgs: {msgs} | results : {res}")

        #
        return res

