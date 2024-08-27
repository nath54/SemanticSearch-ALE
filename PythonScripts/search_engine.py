"""
Moteur de recherche pour effectuer de la recherche dans Rainbow

Auteur: Nathan Cerisara
"""

from dataclasses import dataclass
from typing import Optional, Any, cast

import threading
from multiprocessing.dummy import Pool as ThreadPool

from user import User
from bubble import Bubble
from message import Message, MessagePart, MessageSearch
from rainbow_instance import RainbowInstance
from search_algorithm import SearchAlgorithm
import search_algorithm as SA

from torch import Tensor, float32, zeros, mul as torch_mul

from config import Config
from lib import ConfigError

from profiling import profiling_task_start, profiling_last_task_ends


#
# Liste de tous les algorithmes de recherche disponibles
ALGORITHMS: dict[str, type[SearchAlgorithm]] = {
    "SimpleEmbedding_SearchAlgorithm": SA.SimpleEmbedding_SearchAlgorithm,
    "SimpleSyntaxic_SearchAlgorithm": SA.SimpleSyntaxic_SearchAlgorithm,
    "SyntaxicFullSentenceLevenshtein_SearchAlgorithm": SA.SyntaxicFullSentenceLevenshtein_SearchAlgorithm,
    "SyntaxicWordsLevenshtein_SearchAlgorithm": SA.SyntaxicWordsLevenshtein_SearchAlgorithm,
    "SimpleDictJaccard_NER_SearchAlgorithm": SA.SimpleDictJaccard_NER_SearchAlgorithm,
    "SimpleSearchByTime_SearchAlgorithm": SA.SimpleSearchByTime_SearchAlgorithm,
    "SearchByUsers_SearchAlgorithm": SA.SearchByUsers_SearchAlgorithm,
    "SearchWith_NER_Engine_SearchAlgorithm": SA.SearchWith_NER_Engine_SearchAlgorithm
}


#
@dataclass
class SearchSettings():
    """
    Paramètres d'une recherche
    """

    # On ne va faire la recherche que dans ces bulles là
    #   les int ici font références aux ids des bulles à inclure
    filter_bubbles: Optional[set[int]] = None

    # On ne va pas regarder ces bulles
    #   les int ici font références aux ids des bulles à exclure
    exclude_bubbles: Optional[set[int]] = None

    # On ne va regarder que dans ces intervalles précis de dates
    #   tuple[str, str] correspond à (Date début intervalle, Date fin intervalle)
    filter_date_precisely: Optional[list[tuple[str, str]]] = None

    # Si jamais l'utilisateur a précisé de façon un peu floue une date, on va pouvoir coefficienter le poids d'un message d'une recherche avec une distribution Gaussienne, centrée sur la date demandée, et une variance précisée
    #   tuple[str, float] correspond à (Date centrée, Variance de la distribution)
    # Note: Pas encore pris en compte dans la recherche
    gaussian_date_filter: Optional[tuple[str, float]] = None

    # Ne regarder que des messages de ces utilisateurs, sinon, par défaut, on regardera tous les messages de tous les utilisateurs
    from_users: Optional[set[int]] = None

    # Complètement ignorer les messages de ces utilisateurs
    exclude_users: Optional[set[int]] = None


#
class SearchEngine():
    """
    Classe Mère d'un moteur de recherche, à initialiser au démarrage d'une session uilisateur, et qui va être utilisé pour chaque recherche, une objet SearchEngine contiendra tous ses hyper paramètres.
    """

    def __init__(self, engine_config: dict, config: Config) -> None:
        #
        self.engine_config: dict = engine_config
        self.config: Config = config
        #
        for k in ["config_name", "algorithms"]:
            if not k in engine_config:
                raise ConfigError(f"No key {k} in conversation engine config : {engine_config} !")

        # Nom de la configuration du search engine, sera affiché lors du résultat des tests
        self.config_name: str = engine_config["config_name"]

        # Algorithmes de recherche
        self.algorithms: list[SearchAlgorithm] = []
        self.coef_algorithms: list[float] = []
        #
        for algo_config in engine_config["algorithms"]:
            #
            for k in ["type", "coef"]:
                if not k in algo_config:
                    raise ConfigError(f"No key {k} in search algorithm config : {algo_config} (from engine_config : {self.config_name}) !")
            #
            algo_type: str = algo_config["type"]
            #
            if not algo_type in ALGORITHMS:
                raise UserWarning(f"Unknown conversation algorithm: {algo_type}")
            #
            algo: SearchAlgorithm = ALGORITHMS[algo_type](algo_config, config)
            self.algorithms.append(algo)
            self.coef_algorithms.append(float(algo_config["coef"]))

        # Nombres de threads utilisés pour paralléliser les calculs
        self.nb_threads: int = 1
        if "nb_threads" in engine_config:
            self.nb_threads = int(engine_config["nb_threads"])

        # Nombres de threads utilisés pour paralléliser les calculs
        if not "max_message_length" in engine_config:
            raise ConfigError("La configuration d'un des algorithmes de recherche n'a pas d'attribut `max_message_length`")
        self.max_message_length: int = int(engine_config["max_message_length"])

        # Nombres de messages à renvoyer pour le résultat de la recherche
        if not "nb_search_results" in engine_config:
            raise ConfigError("La configuration d'un des algorithmes de recherche n'a pas d'attribut `nb_search_results`")
        self.nb_search_results: int = int(engine_config["nb_search_results"])

        # On n'envoie pas les messages qui ont une distance plus grande que cette limite si elle est fixée
        self.distance_limit: Optional[float] = None
        if "distance_limit" in engine_config:
            self.distance_limit = float(engine_config["distance_limit"])

        # On sauvegardera ici les attributs d'une recherche pour faciliter l'implémentation du multi-threading

        # Utilisateur qui a fait la recherche
        self.current_search_user: Optional[User] = None

        # Texte de la recherche
        self.current_search_input: Optional[str] = None

        # Parametres de la recherche
        self.current_search_settings: Optional[SearchSettings] = None

        # NER dicts de la recherche
        self.current_search_ner_dicts: list[str] = []

    #
    def get_distances_matrix_from_messages_main(self, msgs_lsts: list[Message], ner_dicts: list[str] = []) -> Tensor:
        """
        Calcule la matrice des distances entre chaque messages en combinants les distances de chaque algorithmes de ce moteur de recherche.

        Args:
            msgs_lsts (list[Message]): La liste des messages.

        Returns:
            Tensor: La matrice des distances entre chaque messages. De dimensions (n, n).
        """

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(msgs_lsts)

        # On initialise la matrice
        matrix_distances: Tensor = zeros((n, n), dtype=float32)

        # Pour chaque algorithme
        for (algo_id, algo) in enumerate(self.algorithms):

            matrix_distances_algo: Tensor = algo.get_matrix_distances_from_messages_main(msgs_lsts, ner_dicts)

            matrix_distances += torch_mul(self.coef_algorithms[algo_id], matrix_distances_algo)

        return matrix_distances

    #
    def get_distances_linear_from_messages_main(self, msgs_lsts: list[Message], ner_dicts: list[str] = []) -> list[float]:
        """
        Calcule la matrice des distances entre chaque messages en combinants les distances de chaque algorithmes de ce moteur de recherche.

        Args:
            msgs_lsts (list[Message]): La liste des messages.

        Returns:
            Tensor: La matrice des distances entre chaque messages. De dimensions (n, n).
        """

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(msgs_lsts)

        # On initialise la liste
        lst_distances: list[float] = [0.0] * n

        # Pour chaque algorithme
        for (algo_id, algo) in enumerate(self.algorithms):

            lda: list[float] = algo.get_linear_distances_from_messages_main(msgs_lsts, ner_dicts)

            for i in range(n):
                lst_distances[i] += lda[i]

        #
        return lst_distances

    #
    def search_part_of_msg_list(self, msg_lst: list[MessageSearch] | MessageSearch) -> list[tuple[float, MessageSearch]]:
        """
        On va lancer la recherche sur les différents algorithmes, et combiner les résultats

        Args:
            msg_lst (list[MessageSearch]): Liste des messages à traiter

        Returns:
            list[tuple[float, MessageSearch]]: Le résultat, sous la forme: liste de (score du message, message)
        """

        if isinstance(msg_lst, MessageSearch):
            msg_lst = [msg_lst]

        # Tests de bonnes valeurs
        if self.current_search_input is None:
            raise SystemError("Erreur, current_search_input est vide.")

        if self.current_search_user is None:
            raise SystemError("Erreur, current_search_user est vide.")

        if self.current_search_settings is None:
            raise SystemError("Erreur, current_search_settings est vide.")

        # Id du thread actuel
        id_crt_thread: int = threading.get_native_id()

        # Profiling 1 - start
        # profiling_task_start(f"search_part_of_msg_list_[{self.config_name}]_|_{len(msg_lst)}_|_{msg_lst[0]}")

        # On prépare la liste de résultat
        final_results: list[list[Any]] = [[.0, m] for m in msg_lst]

        # Pour chaque algorithme
        for (algo_id, algo) in enumerate(self.algorithms):

            # Profiling 2 - start
            # profiling_task_start(f"search_algo_{algo_id}_[{self.config_name}]_|_{len(msg_lst)}_|_{msg_lst[0]}")

            # On applique l'algorithme
            msgs_scores: list[float] = algo.search(self.current_search_input, msg_lst, self.current_search_ner_dicts)

            # On combine le résultat
            for i in range(len(msg_lst)):
                final_results[i][0] += msgs_scores[i] * self.coef_algorithms[algo_id]

            # Profiling 2 - end
            # profiling_last_task_ends()

        # On convertit, car final_results utilise des listes car on veut modifier les valeurs, mais après, on ne veut plus, donc on convertit en tuple
        final_results_converted: list[tuple[float, MessageSearch]] = [cast(tuple[float, MessageSearch], tuple(r)) for r in final_results]

        # Profiling 1 - end
        # profiling_last_task_ends()

        # On renvoie le résultat final
        return final_results_converted

    #
    def search_main(self, rbi: RainbowInstance, search_input: str, user: User, search_settings: SearchSettings, ner_dicts: list[str] = []) -> list[tuple[float, MessageSearch]]:
        """
        Fonction qui est appelée à chaque recherche.

        Args:
            search_input (str): Contenu de la recherche
            user (User): Référence à l'utilisateur qui a fait la recherche
            search_settings (SearchSettings): Paramètres de la recherche (filtres, etc...)
        """

        # Profiling 1 - start
        # profiling_task_start(f"search_main_[{self.config_name}]_|_{search_input}_|_{user.id}_|_{rbi.server_name}")

        # Liste de tous les messages sur lesquels on va effectuer la recherche
        msgs_to_search: list[MessageSearch] = []

        # Profiling 2 - start
        # profiling_task_start(f"get_all_messages_to_process_[{self.config_name}]_|_{search_input}_|_{user.id}_|_{rbi.server_name}")

        # On parcourt toutes les bulles d'un utilisateur selon les filtres
        for bubble_id in user.bubbles_ids:

            # On teste les filtres pour les bulles

            # Filtre d'exclusion
            if search_settings.exclude_bubbles is not None and bubble_id in search_settings.exclude_bubbles:
                continue

            # Filtre d'inclusion
            if search_settings.filter_bubbles is not None and bubble_id not in search_settings.filter_bubbles:
                continue

            # On va donc pour l'instant, juste récupérer simplement tous les messages sans découpage

            # Pour cela, on va parcourir tous les messages de la bulle
            for message_id in rbi.bubbles[bubble_id].messages_ids:

                # On récupère le message
                msg: Message = rbi.messages[message_id]

                # On filtre les messages trop courts
                if len(msg.content) <= 2:
                    continue

                # On filtre les messages qui commencent par "/search"
                if msg.content.startswith("/search"):
                    continue

                # On applique les filtres positifs sur les utilisateurs
                if search_settings.from_users is not None and msg.author_id not in search_settings.from_users:
                    continue

                # On applique les filtres négatifs sur les utilisateurs
                if search_settings.exclude_users is not None and msg.author_id in search_settings.exclude_users:
                    continue

                # On applique les filtres sur les dates
                if search_settings.filter_date_precisely is not None:
                    inside: bool = False

                    # On va donc vérifier si la date du message est dans l'un des intervalles du filtre
                    for date_intervalle in search_settings.filter_date_precisely:
                        if msg.date >= date_intervalle[0] and msg.date <= date_intervalle[1]:
                            inside = True
                            break

                    # S'elle n'y est pas, on ne traite pas le message
                    if not inside:
                        continue

                # Si on est arrivé ici, c'est que l'on va traiter ce message

                # Pour l'instant, on l'ajoute donc simplement à la liste des messages à traiter, sans plus de découpage intelligent des conversations
                if self.max_message_length <= 0 or len(msg.content) <= self.max_message_length:
                    msgs_to_search.append(MessageSearch(
                                                content=msg.content,
                                                date=msg.date,
                                                author_id=set([msg.author_id]),
                                                author_name=set([msg.author_name]) if isinstance(msg.author_name, str) else msg.author_name,
                                                msg_pointing=[MessagePart(message_id)]
                                        ))

                # Mais quand même, si le message est trop long, on va découper le message en plusieurs parties, et faire une recherche indépendamment des parties
                else:

                    END_SENTENCES_CHARS: list[str] = ".;?!\n\r"

                    # Pour tracer la progression du curseur sur le message
                    i: int = 0
                    while len(msg.content) - i >= self.max_message_length + 1:
                        # On va chercher le dernier signe de fin de phrase
                        j: int = i+self.max_message_length
                        while j > i and msg.content[j] not in END_SENTENCES_CHARS:
                            j -= 1
                        # S'il n'y a pas de fin de phrase, on va alors aller chercher le dernier espace
                        if j == i:
                            j = i+self.max_message_length
                            while j > i and msg.content[j] != ' ':
                                j -= 1
                        # S'il n'y a pas d'espaces, on va couper comme des bourrins.
                        if j == i:
                            msgs_to_search.append(MessageSearch(
                                                        content=msg.content[i: i+self.max_message_length],
                                                        date=msg.date,
                                                        author_id=set([msg.author_id]),
                                                        author_name=set([msg.author_name]) if isinstance(msg.author_name, str) else msg.author_name,
                                                        msg_pointing=[MessagePart(message_id, (i, i+self.max_message_length))]
                                                ))
                            i += self.max_message_length
                        else:
                            msgs_to_search.append(MessageSearch(
                                                        content=msg.content[i: j+1],
                                                        date=msg.date,
                                                        author_id=set([msg.author_id]),
                                                        author_name=set([msg.author_name]) if isinstance(msg.author_name, str) else msg.author_name,
                                                        msg_pointing=[MessagePart(message_id, (i, i+self.max_message_length))]
                                                ))
                            i = j + 1

                    # S'il reste encore des choses à la fin
                    if len(msg.content) - i > 0:
                        msgs_to_search.append(MessageSearch(
                                                    content=msg.content[i:],
                                                    date=msg.date,
                                                    author_id=set([msg.author_id]),
                                                    author_name=set([msg.author_name]) if isinstance(msg.author_name, str) else msg.author_name,
                                                    msg_pointing=[MessagePart(message_id, (i, len(msg.content)))]
                                            ))

        # Arrivé ici, on a donc la liste de tous les messages bien découpés avec lesquels on va faire la recherche

        # Profiling 2 - end
        # profiling_last_task_ends()

        # Score/Distance des messages selon la recherche, (plus petit veut dire meilleur)
        msgs_scores: list[tuple[float, MessageSearch]] = []

        # On sauvegarde les paramètres actuels de la recherche
        self.current_search_input = search_input
        self.current_search_settings = search_settings
        self.current_search_user = user
        self.current_search_ner_dicts = ner_dicts

        # Profiling 2 - start
        # profiling_task_start(f"searching_[{self.config_name}]_|_{search_input}_|_{user.id}_|_{rbi.server_name}")

        assert isinstance(msgs_to_search, list)

        # Cas où l'on ne va pas faire de multi-threading
        if True or self.nb_threads <= 1:

            # On fait donc simplement la recherche sur toute la liste entière de messages à traiter, en un seul coup
            msgs_scores = self.search_part_of_msg_list(msgs_to_search)

        # Cas où l'on va faire du multi-threading
        else:

            # On prépare l'outil de multi-threading
            pool = ThreadPool(self.nb_threads)

            # On lance le calcul parallélisé
            msgs_scores = pool.map(self.search_part_of_msg_list, msgs_to_search)

            # On ferme le Pool, et on attends que tous les threads ont fini leur travail
            pool.close()
            pool.join()

        # Profiling 2 - end
        # profiling_last_task_ends()

        # Profiling 2 - start
        # profiling_task_start(f"sorting_results_|_{search_input}_|_{user.id}_|_{rbi.server_name}")

        msgs_ids: set[str] = set()
        # On va filtrer les messages qui sont en double
        for res_msg in msgs_scores:
            is_duplicate: bool = False
            for msg_pointing in res_msg[1].msg_pointing:
                if msg_pointing.msg_id in msgs_ids:
                    is_duplicate = True
                    break
                msgs_ids.add(msg_pointing.msg_id)
            if is_duplicate:
                msgs_scores.remove(res_msg)

        # Ici, les calculs de distance sont donc finis, il faut donc maintent trier dans l'ordre de score croissant les résultats de recherche
        msgs_scores.sort(key=lambda r: r[0])

        # Pour l'instant, on va simplement directement renvoyer les N messages les plus proches
        search_result: list[tuple[float, MessageSearch]] = []

        # Dans le cas où l'on veut tous les résultas ou que l'on a moins de résultats que demandés, on renvoie tous les résultats de la recherche
        if self.nb_search_results <= 0 or len(msgs_scores) <= self.nb_search_results:
            search_result = msgs_scores

        # Dans le cas où l'on a plus de résultats que demandé, on ne renvoie que le nombre demandé
        else:
            search_result = msgs_scores[:self.nb_search_results]

        # Si l'attribut "distance_limit" est activé
        if self.distance_limit is not None:
            #
            msgs_to_skip: Optional[int] = None
            for i in range(len(search_result)):
                if search_result[i][0] >= self.distance_limit:
                    msgs_to_skip = i
                    break
            #
            if msgs_to_skip is not None:
                search_result = search_result[:msgs_to_skip]

        # Fin de la recherche, phase de nettoyage

        # On nettoie les paramètres actuels de la recherche
        self.current_search_input = None
        self.current_search_settings = None
        self.current_search_user = None

        # Profiling 2 - end
        # profiling_last_task_ends()

        # Profiling 1 - end
        # profiling_last_task_ends(f"searching \"{search_input}\" on rbi {rbi.server_name} with engine {self.config_name}")

        # On renvoie le résultat de la recherche
        return search_result

