"""
Algorithme de recherche pour effectuer de la recherche dans Rainbow, plusieurs algorithmes différents peuvent être utilisés pour effectuer une même recherche.

Auteur: Nathan Cerisara
"""

from typing import cast, Optional, Any
from dataclasses import dataclass

from torch import Tensor, float32, eye, zeros
import math
import os
import json

from Levenshtein import distance as levenshtein_distance

from message import MessageSearch, MessagePart, Message
from embedding_calculator import EmbeddingCalculator
from language_translation import LanguageTranslation
from ner_engine import NER_Engine
from config import Config
from lib import ConfigError, escapeCharacters, Date
from lib_embedding import MessageEmbedding, DISTANCES_FUNCTIONS
from embeddings_cache import EmbeddingCache

from global_variables import GlobalVariables, init_global_variables, get_global_variables
from profiling import profiling_task_start, profiling_last_task_ends


#
def find_common_words(txt1: str, txt2: str) -> int:
    """
    Compte le nombre de mots en communs entre 2 chaînes de caractère, avec quelques améliorations (non sensible à la casse)

    Args:
        txt1 (str): La première chaîne
        txt2 (str): La seconde chaîne

    Returns:
        int: Le nombre de mots en communs
    """

    t1: str = txt1.strip().lower()
    t2: str = txt2.strip().lower()

    # On va convertir toute la chaîne en minuscule pour éviter des problèmes liés à la casse
    # Puis on va convertir la liste de mots en un Ensemble de mot, pour calculer l'intersection très rapidement.
    words1 = set(t1.split())

    # Taille de l'intersection
    res: int = 0

    for w in words1:
        if w in t2:
            res += 1

    if t1 in t2:
        res += 1

    return res

#
def full_sentence_levenshtein_distance(txt1: str, txt2: str) -> int:
    """
    Calcule la distance de Levenshtein directement sur les deux chaînes de caractères.

    Args:
        txt1 (str): premier texte à comparer
        txt2 (str): second texte à comparer

    Returns:
        int: distance de Levenshtein
    """

    return levenshtein_distance(txt1, txt2)

#
def words_levenshtein_distances(txt1: str, txt2: str, close_words_factor: float) -> float:
    """
    Recherche syntaxique qui consiste à calculer la distance de Levenshtein sur les couples de mots entre la recherche et chacun des messages à rechercher
    Deux mots sont considérés comme "proches" s'ils ont une distance de Levenshtein inférieure à un certain pourcentage de la somme de leurs tailles.

    Args:
        txt1 (str): premier texte à comparer
        txt2 (str): second texte à comparer
        close_words_factor (float): taux qui permet de calculer si deux mots sont proches ou non selon la distance de Levenshtein

    Returns:
        float: distance retournée
    """

    # Va contenir les index des mots "plus utilisables" du deuxième texte
    words_used: set[int] = set()

    # On coupe les textes en mots
    words_1 = txt1.strip().split(" ")
    words_2 = txt2.strip().split(" ")

    # On va enlever tous les mots vides
    while "" in words_1:
        words_1.remove("")
    while "" in words_2:
        words_2.remove("")

    # TODO: Piste d'amélioration? Enlever d'autres choses?

    # Liste
    words_distances: list[float] = []

    # On parcourt tous les couples de mots (w1, w2) possibles
    w1: str
    for w1 in words_1:

        word_distances: list[int] = []

        for id_word2 in range(len(words_2)):

            # On teste si un mot est encore utilisable ou pas
            if id_word2 in words_used:
                word_distances.append(-1)
                continue

            w2: str = words_2[id_word2]

            # Calcul de la distance de Levenshtein
            ld: int = levenshtein_distance(w1, w2)

            word_distances.append(ld)

            # On teste si ces deux mots sont considérés comme "proches" ou non
            tot_lenght: float = float(len(w1) + len(w2))
            ratio: float = float(ld) / tot_lenght

            if ratio <= close_words_factor:
                words_used.add(id_word2)

        # Pour l'instant, on ne va prendre que le minimum
        # TODO: Piste d'amélioration?

        d: Optional[float] = None
        cdw: float
        for cdw in words_distances:
            if cdw >= 0:
                if d is None or cdw < d:
                    d = cdw

        if d is not None:
            words_distances.append(d)

    # Pour l'instant, on ne va prendre que la somme des distances
    # TODO: Piste d'amélioration?

    return sum(word_distances)

#
def get_ner_jaccard_vec_base(ner_dicts: list[str]) -> list[str]:
    """
    Calcule la base pour l'espace vectoriel qui sera utilisée pour calculer la distance de jaccard pour les ner

    Args:
        ner_dicts (list[str]): Liste des dictionnaires qui contient les noms des dictionnaires de NER utilisés.

    Returns:
        list[str]: La liste du nom de toutes les entités nommées des dictionnaires.
    """

    # On va récupérer le set de tous les éléments des ner
    ner_keys_set: set[str] = set()

    for ner_dict_name in ner_dicts:
        list_of_ner_keys: list[str] = get_global_variables().get_NER_dict_keys(ner_dict_name)
        ner_keys_set = ner_keys_set.union(set(list_of_ner_keys))

    #
    ner_base: list[str] = list(ner_keys_set)

    # Pour s'assurer de toujours avoir le même ordre
    ner_base.sort()

    return ner_base

#
def calculate_NER_vector_from_txt_and_dicts(txt: str, ner_base: list[str]) -> set[int]:
    """
    Calcule un vecteur bag of entity de NER pour le texte demandé et la base demandée.

    Args:
        txt (str): Texte avec lequel calculer le vecteur bag of entity de NER
        ner_base (list[str]): _description_

    Returns:
        set[int]: Vecteur bag of entity de NER pour le texte
    """

    #
    vec: set[int] = set()
    for i in range(len(ner_base)):
        if ner_base[i] in txt:
            vec.add(i)

    #
    return vec

#
# https://fr.wikipedia.org/wiki/Indice_et_distance_de_Jaccard#:~:text=Similarit%C3%A9%20entre%20des%20ensembles%20binaires%5Bmodifier%20%7C%20modifier%20le%20code%5D
def jaccard_distance(vec1: set[int], vec2: set[int], ner_base_length: int) -> float:
    """
    Calcule la distance de Jaccard entre deux vecteurs selon une certaine base.

    Args:
        vec1 (set[int]): Premier vecteur bag of entity de NER.
        vec2 (set[int]): Second vecteur bag of entity de NER.
        ner_base_length (int): Dimension de la base de NER dans laquel sont les deux vecteurs.

    Returns:
        float: La distance de Jaccard entre ces deux vecteurs.
    """

    #
    full_ner: set[int] = set(range(ner_base_length))

    #
    vec1_inv: set[int] = full_ner.difference(vec1)
    vec2_inv: set[int] = full_ner.difference(vec2)

    #
    m11: int = len(vec1.intersection(vec2))
    m00: int = len(vec1_inv.intersection(vec2_inv))

    jaccard_indice: float = 0.0

    if m00 == ner_base_length:
        jaccard_indice = 1.0
    else:
        jaccard_indice = float(m11) / (float(ner_base_length) - float(m00))

    return 1.0 - jaccard_indice

#
def real_minutes_time_distances(msg1: Message, msg2: Message) -> float:

    # On récupère les dates
    d1: Date = Date(from_txt_date=msg1.date)
    d2: Date = Date(from_txt_date=msg2.date)

    # On récupère la distance en minutes
    dm: float = abs(d1.to_minutes() - d2.to_minutes())

    # On renvoie le résultat
    return dm

#
def time_distance(msg1: Message, msg2: Message) -> float:

    # On récupère la distance en minute
    dm: float = real_minutes_time_distances(msg1, msg2)

    # On applique une formule mathématique de la main de Nathan Cerisara
    return math.exp( math.atan( (dm / 10.0) - 5.0 ) ) - math.exp( math.atan( -5.0 ) )

#
BAD_ENTITIES: set[str] = set(["", " ", "\n"])
def calc_common_entities(ents_1: list[ tuple[ int, str, str] ], ents_2: list[ tuple[ int, str, str ] ]) -> float:
    """Calcule le score de similarité entre deux listes d'entités

    Args:
        ents_1 (list[tuple[int, str, str]]): Première liste d'entités (idx_start, valeur, type)
        ents_2 (list[tuple[int, str, str]]): Deuxième liste d'entités (idx_start, valeur, type)

    Returns:
        float: Score de similarité entre les deux listes d'entités.
    """

    #
    score: float = 0.0

    #
    ent_1: tuple[int, str, str]
    ent_2: tuple[int, str, str]
    for ent_1 in ents_1:
        #
        if ent_1 in BAD_ENTITIES:
            continue
        #
        for ent_2 in ents_2:
            #
            if ent_2 in BAD_ENTITIES:
                continue
            #
            if ent_1[1] == ent_2[1]:
                score += 0.1
            elif ent_1[1] in ent_2[1] or ent_2[1] in ent_1[1]:
                score += 0.08

    #
    # if score > 0:
    #     print(f"\nScore common entities:\n - lst 1: {', '.join([e[1] for e in ents_1])}\n - lst 2: {', '.join([e[1] for e in ents_2])}\n - score : {score}\n")

    #
    return score


#
class SearchAlgorithm():
    """
    Classe Principale Générique pour un algorithme de recherche
    """

    def __init__(self, config_algo: dict, conf: Config) -> None:

        # Profiling 1
        # profiling_task_start(f"algo_init_[{escapeCharacters(config_algo["type"])}]")

        # Indique s'il y a besoin de cuda pour cet algorithme
        self.use_cuda: bool = False
        if "use_cuda" in config_algo and int(config_algo["use_cuda"]) > 0:
            self.use_cuda = True

        # Indique s'il y a besoin de traduire dans une certaine langue avant de traiter ce message
        self.translate_before: Optional[str] = None
        self.translation_method: str = "easyNMT"
        if "translate_before" in config_algo:
            self.translate_before = config_algo["translate_before"]
            #
            if "translate_method" in config_algo:
                self.translation_method = config_algo["translate_method"]

        # NER text replacement
        self.NER_text_replacement: bool = False
        if "NER_text_replacement" in config_algo and int(config_algo["NER_text_replacement"]) > 0:
            self.NER_text_replacement = True

        # Profiling 1
        # profiling_last_task_ends()

    #
    def pre_process_search_messages(self, search_input: str, lst_msgs: list[MessageSearch], ner_dicts: list[str]) -> tuple[str, list[MessageSearch]]:
        """
        Couche de pré-traitement nécessaire avant d'effectuer la recherche avec l'algorithme de recherche.

        Args:
            search_input (str): Texte de la recherche
            lst_msgs (list[MessageSearch]): Liste des messages à comparer avec la recherche

        Returns:
            tuple[str, list[MessageSearch]]: Le texte de la recherche pré-traité et la liste des messages pré-traités.
        """

        # Profiling 1 - start
        # profiling_task_start(f"pre_process_search_msgs_|_{search_input}_|_{len(lst_msgs)}")

        # Préparation au pré-processing
        pre_processed_search_input: str = search_input
        pre_processed_lst_msgs: list[MessageSearch] = lst_msgs

        # définition d'une variable qui sera utilisée pleins de fois
        id_msg: int

        # On s'occupe du NER text replacement
        # TODO: pour l'instant, on remplace systématiquement, faire une détection de si on remplace ou pas
        if self.NER_text_replacement:

            # Profiling 2 - start
            # profiling_task_start(f"ner_replacements_|_{search_input}_|_{len(lst_msgs)}")

            # On parcours chaque dictionnaire de NER | ordre de grandeur : 1 ~ 5
            for ner_dict_name in ner_dicts:

                # On récupère le dico
                ner_dict: dict[str, str] = get_global_variables().get_NER_dict(ner_dict_name)

                # On parcours chaque message des messages à traiter | ordre de grandeur : 10~100000 (max du max, bien moins en moyenne)
                for id_msg in range(len(pre_processed_lst_msgs)):

                    # On parcours chaque clé dans le dictionnaire de NER | ordre de grandeur : 1~100
                    nk: str
                    for nk in ner_dict:

                        # On remplace s'il y a une ou plus occurences dedans
                        if nk in pre_processed_lst_msgs[id_msg].content:
                            pre_processed_lst_msgs[id_msg].content = pre_processed_lst_msgs[id_msg].content.replace(nk, ner_dict[nk])

            # Profiling 2 - end
            # profiling_last_task_ends()

        # Traduction avant de traduire les messages
        if self.translate_before is not None:

            # Profiling 2 - start
            # profiling_task_start(f"translation_|_{search_input}_|_{len(lst_msgs)}")

            # On s'occupe de la recherche
            pre_processed_search_input = get_global_variables().translate(search_input)

            # On s'occupe des messages à traiter
            msg: MessageSearch
            for id_msg in range(len(lst_msgs)):
                msg = lst_msgs[id_msg]
                pre_processed_lst_msgs[id_msg].content = get_global_variables().translate(msg.content)

            # Profiling 2 - end
            # profiling_last_task_ends()

        # Profiling 1 - end
        # profiling_last_task_ends(f"search_input = {search_input}, len(lst_msgs)={len(lst_msgs)}")

        #
        return pre_processed_search_input, pre_processed_lst_msgs

    #
    def pre_process_base_messages(self, lst_msgs: list[Message], ner_dicts: list[str]) -> list[Message]:
        """
        Couche de pré-traitement pour les messages.

        Args:
            lst_msgs (list[Message]): Liste des messages à pré-traiter.

        Returns:
            list[Message]: Liste des messages pré-traités.
        """

        # Cas de la liste vide, comme ça, par la suite, on sait que la liste n'est pas vide.
        if len(lst_msgs) == 0:
            return []

        # Profiling 1 - start
        # profiling_task_start(f"pre_process_msgs_|_{escapeCharacters(lst_msgs[0].content)}_|_{len(lst_msgs)}")

        # Préparation au pré-processing
        pre_processed_lst_msgs: list[Message] = [m.new_msg_copy() for m in lst_msgs]

        # définition d'une variable qui sera utilisée pleins de fois
        id_msg: int

        # On s'occupe du NER text replacement
        # TODO: pour l'instant, on remplace systématiquement, faire une détection de si on remplace ou pas
        if self.NER_text_replacement:

            # Profiling 2 - start
            # profiling_task_start(f"ner_replacements_|_{escapeCharacters(lst_msgs[0].content)}_|_{len(lst_msgs)}")

            # On parcours chaque dictionnaire de NER | ordre de grandeur : 1 ~ 10
            for ner_dict_name in ner_dicts:

                # On récupère le dico
                ner_dict: dict[str, str] = get_global_variables().get_NER_dict(ner_dict_name)

                # On parcours chaque message des messages à traiter | ordre de grandeur : 10~100000 (100000=max du max, bien bien moins en moyenne)
                for id_msg in range(len(pre_processed_lst_msgs)):

                    # On parcours chaque clé dans le dictionnaire de NER | ordre de grandeur : 1~1000
                    nk: str
                    for nk in ner_dict:

                        # On remplace s'il y a une ou plus occurences dedans
                        if nk in pre_processed_lst_msgs[id_msg].content:
                            pre_processed_lst_msgs[id_msg].content = pre_processed_lst_msgs[id_msg].content.replace(nk, ner_dict[nk])

            # Profiling 2 - end
            # profiling_last_task_ends()

        # Traduction avant de traduire les messages
        if self.translate_before is not None:

            # Profiling 2 - start
            # profiling_task_start(f"translation_|_{escapeCharacters(lst_msgs[0].content)}_|_{len(lst_msgs)}")

            # On s'occupe des messages à traiter
            msg: Message
            for id_msg in range(len(lst_msgs)):
                msg = lst_msgs[id_msg]
                pre_processed_lst_msgs[id_msg].content = get_global_variables().translate(msg.content)

            # Profiling 2 - end
            # profiling_last_task_ends()

        # Profiling 1 - end
        # profiling_last_task_ends(f"slen(lst_msgs)={len(lst_msgs)}")

        #
        return pre_processed_lst_msgs

    #
    def get_matrix_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> Tensor:
        """
        Calcule la matrice des distances entre chaque messages avec cet algorithme.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            Tensor: La matrice des distances entre chaque messages. De dimensions (n, n).
        """

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(lst_msgs)

        # On initialise la matrice
        matrix_distances: Tensor = zeros((n, n), dtype=float32)

        return matrix_distances

    #
    def get_linear_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> list[float]:
        """
        Calcule la liste des distances entre le message précédent et le message actuel.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            list[float]: La liste des distances entre chaques messages séquentiellement.
        """

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(lst_msgs)

        # Résultat neutre car ce n'est qu'une fonction abstraite d'une classe abstraite.
        return [0.0] * n

    #
    def search(self, search_input: str, lst_msgs: list[MessageSearch], ner_dicts: list[str]) -> list[float]:
        """Abstraction de la fonction principale d'un algorithme de recherche: la recherche

        Args:
            search_input (str): Texte de la recherche
            lst_msgs (list[MessageSearch]): Liste de messages à comparer avec la recherche

        Returns:
            list[float]: Liste des scores correspondant à cette liste initiale de messages, dans l'ordre
        """

        # Ici, vu que ce n'est qu'une fonction abstraite, on renvoie un score neutre
        return [0] * len(lst_msgs)


#
class SimpleEmbedding_SearchAlgorithm(SearchAlgorithm):
    """
    Algorithme de recherche qui va utiliser un embedding pour calculer ensuite les distances.
    Le `Simple` ici signifie qu'il ne va pas y avoir d'optimisations particulières sur l'utilisation du modèle (on ne va pas essayer de skipper des couches pour gagner en rapidité par exemple).
    """

    def __init__(self, algo_config: dict, conf: Config) -> None:
        #
        super().__init__(algo_config, conf)

        #
        self.algo_dict = algo_config

        # Embedding calculator est un couche d'abstraction, qui va gérer les modèles d'embeddings
        for key in ["batch_size", "model_name", "use_cuda"]:
            if not key in algo_config:
                raise ConfigError(f"La configuration de l'algorithme de recherche n'a pas d'attributs `{key}`.")

        # Taille des batchs
        self.batch_size: int = int(algo_config["batch_size"])

        #
        self.embedding_calculator: EmbeddingCalculator = EmbeddingCalculator(algo_config, conf)

        #
        self.distance_function: str = "euclidian"
        if "distance_function" in algo_config:
            self.distance_function = algo_config["distance_function"]

    #
    def calculate_embeddings_of_msgs_list(self, lst_msgs_to_process: list[str]) -> list[MessageEmbedding]:

        # On récupère la taille de la liste à calculer
        tot_length: int = len(lst_msgs_to_process)

        # Liste qui contiendra les embeddings calculés
        # 0 = search input, else it is the lst_msgs in order
        embeddings: list[Optional[MessageEmbedding]] = [None] * tot_length

        # pré-définition d'une variable qui sera utilisée des deux côtés de la condition
        embedding_cached: Optional[MessageEmbedding]

        # Dans le cas où il n'y a pas de batchs
        if self.batch_size == 1:

            for i in range(tot_length):

                # Profiling 1 - start
                # profiling_task_start(f"testing_cache_[{self.algo_dict['model_name']}]_nb_|_{lst_msgs_to_process[i]}")

                embedding_cached = get_global_variables().get_embedding_cache(self.algo_dict["model_name"], lst_msgs_to_process[i])

                # Profiling 1 - end
                # profiling_last_task_ends()

                if embedding_cached is not None:
                    embeddings[i] = embedding_cached

                else:

                    # Profiling 1 - start
                    # profiling_task_start(f"calculate_embedding_[{self.algo_dict['model_name']}]_nb_|_{lst_msgs_to_process[i]}")

                    embeddings[i] = self.embedding_calculator.get_embeddings([lst_msgs_to_process[i]])[0]
                    #
                    if embeddings[i] is None:
                        raise UserWarning("Error, embeddings is None")
                    #
                    get_global_variables().set_embedding_cache(self.algo_dict["model_name"],lst_msgs_to_process[i], cast(MessageEmbedding, embeddings[i]))

                    # Profiling 1 - end
                    # profiling_last_task_ends()

        else:
            # On va devoir découper par batchs

            # Batch
            batch: list[str] = []
            # Index du résultat à placer dans le tableau embeddings
            batch_embeddings_ids: list[int] = []

            #
            batch_embeddings: list[MessageEmbedding]

            # Index pour savoir où est-ce qu'on en est
            id_msg_batch: int = -1

            while id_msg_batch+1 < tot_length:
                id_msg_batch += 1

                # Profiling 1 - start
                # profiling_task_start(f"testing_cache_[{self.algo_dict['model_name']}]_b_{id_msg_batch}_|_{lst_msgs_to_process[id_msg_batch]}")

                # Si l'embedding est directement dans le cache, on le récupère directement
                embedding_cached = get_global_variables().get_embedding_cache(self.algo_dict["model_name"], lst_msgs_to_process[id_msg_batch])

                # Profiling 1 - end
                # profiling_last_task_ends()

                if embedding_cached is not None:
                    embeddings[id_msg_batch] = embedding_cached
                    continue

                # Sinon, on le rajoute dans le batch
                batch.append(lst_msgs_to_process[id_msg_batch])
                batch_embeddings_ids.append(id_msg_batch)

                # On teste s'il faut calculer le batch
                if len(batch) >= self.batch_size:

                    # Profiling 1 - start
                    # profiling_task_start(f"calculate_embeddings_batch_[{self.algo_dict['model_name']}]_|_{len(batch)}_|_{batch[0]}")

                    # On calcule le batch
                    batch_embeddings = self.embedding_calculator.get_embeddings(batch)

                    # Profiling 1 - end
                    # profiling_last_task_ends()

                    # Profiling 1 - start
                    # profiling_task_start(f"saving_batch_embeddings_[{self.algo_dict['model_name']}]_|_{len(batch)}_|_{batch[0]}")

                    # On restitue les résultats
                    id_bes: int
                    for id_bes in range(len(batch_embeddings_ids)):

                        # Profiling 2 - start
                        # profiling_task_start(f"saving_1_embedding_[{self.algo_dict['model_name']}]_|_{lst_msgs_to_process[batch_embeddings_ids[id_bes]]}")

                        #
                        embeddings[batch_embeddings_ids[id_bes]] = batch_embeddings[id_bes]
                        # On rajoute aussi le résultat au cache
                        get_global_variables().set_embedding_cache(self.algo_dict["model_name"],lst_msgs_to_process[batch_embeddings_ids[id_bes]], batch_embeddings[id_bes])

                        # Profiling 2 - end
                        # profiling_last_task_ends()

                    # Profiling 1 - end
                    # profiling_last_task_ends()

            # Si le batch n'est pas vide
            if len(batch) > 0:

                # Profiling 1 - start
                # profiling_task_start(f"calculate_embedding_batch_[{self.algo_dict['model_name']}]_|_{len(batch)}_|_{batch[0]}")

                # On calcule le batch
                batch_embeddings = self.embedding_calculator.get_embeddings(batch)

                # Profiling 1 - end
                # profiling_last_task_ends()

                # Profiling 1 - start
                # profiling_task_start(f"saving_batch_embeddings_[{self.algo_dict['model_name']}]_|_{len(batch)}_|_{batch[0]}")

                # On restitue les résultats
                for id_bes in range(len(batch_embeddings_ids)):

                    # Profiling 2 - start
                    # profiling_task_start(f"saving_1_embedding_[{self.algo_dict['model_name']}]_|_{lst_msgs_to_process[batch_embeddings_ids[id_bes]]}")

                    embeddings[batch_embeddings_ids[id_bes]] = batch_embeddings[id_bes]
                    get_global_variables().set_embedding_cache(self.algo_dict["model_name"],lst_msgs_to_process[batch_embeddings_ids[id_bes]], batch_embeddings[id_bes])

                    # Profiling 2 - end
                    # profiling_last_task_ends()

                # Profiling 1 - end
                # profiling_last_task_ends()

        # Profiling 1
        # profiling_task_start(f"saving_embeding_cache_|_{lst_msgs_to_process[0]}_|_{len(lst_msgs_to_process)}")

        # Profiling 1 - end
        # profiling_last_task_ends()

        # On renvoie le résultat
        return embeddings

    #
    def get_matrix_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> Tensor:
        """
        Calcule la matrice des distances entre chaque messages avec cet algorithme.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            Tensor: La matrice des distances entre chaque messages. De dimensions (n, n).
        """

        # On pré-traite les messages
        pre_processed_lst_msgs: list[Message] = self.pre_process_base_messages(lst_msgs, ner_dicts)

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(lst_msgs)

        # On va calculer une liste des embeddings des messages
        embeddings: list[Optional[MessageEmbedding]] = self.calculate_embeddings_of_msgs_list([m.content for m in pre_processed_lst_msgs])

        # On initialise la matrice
        matrix_distances: Tensor = zeros((n, n), dtype=float32)

        # On calcule les distances pour chaque couple de messages
        for id_msg1 in range(n):
            for id_msg2 in range(n):
                matrix_distances[id_msg1, id_msg2] = DISTANCES_FUNCTIONS[self.distance_function](cast(MessageEmbedding, embeddings[id_msg1]), cast(MessageEmbedding, embeddings[id_msg2]), self.algo_dict)

        # On renvoie le résultat
        return matrix_distances

    #
    def get_linear_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> list[float]:
        """
        Calcule la liste des distances entre le message précédent et le message actuel.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            list[float]: La liste des distances entre chaques messages séquentiellement.
        """

        # On pré-traite les messages
        pre_processed_lst_msgs: list[Message] = self.pre_process_base_messages(lst_msgs, ner_dicts)

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(lst_msgs)

        # On va calculer une liste des embeddings des messages
        embeddings: list[Optional[MessageEmbedding]] = self.calculate_embeddings_of_msgs_list([m.content for m in pre_processed_lst_msgs])

        # On calcule les résultats
        res: list[float] = [0] + [
            DISTANCES_FUNCTIONS[self.distance_function](cast(MessageEmbedding, embeddings[i-1]), cast(MessageEmbedding, embeddings[i]), self.algo_dict)

            for i in range(1, len(pre_processed_lst_msgs))
        ]

        # On renvoie les résultats
        return res

    #
    def search(self, search_input: str, lst_msgs: list[MessageSearch], ner_dicts: list[str]) -> list[float]:
        """
        Recherche embedding simple: calcule des embeddings par batchs, puis compare les embeddings de chaque message à celui de la recherche

        Args:
            search_input (str): Texte de la recherche
            lst_msgs (list[MessageSearch]): Liste de messages à comparer avec la recherche

        Returns:
            list[float]: Liste des scores de distance correspondant à cette liste initiale de messages, dans l'ordre
        """

        # Profiling 0 - start
        # profiling_task_start(f"simple_embedding_algorithm_search_[{self.algo_dict['model_name']}]_|_{search_input}_|_{len(lst_msgs)}")

        # Préparation au pré-processing
        pre_processed_search_input: str
        pre_processed_lst_msgs: list[MessageSearch]
        pre_processed_search_input, pre_processed_lst_msgs = self.pre_process_search_messages(search_input, lst_msgs, ner_dicts)

        #
        lst_msgs_to_process: list[str] = [pre_processed_search_input] + [m.content for m in pre_processed_lst_msgs]

        embeddings: list[MessageEmbedding] = self.calculate_embeddings_of_msgs_list(lst_msgs_to_process)

        # Profiling 1 - start
        # profiling_task_start(f"calculating_distances_of_embeddings_[{self.distance_function}]_|_{search_input}_|_{len(lst_msgs)}_|_{lst_msgs[0]}")

        # On renvoie ensuite la distance de l'embedding de recherche avec tous les autres
        res: list[float] = [
            DISTANCES_FUNCTIONS[self.distance_function](cast(MessageEmbedding, embeddings[0]), cast(MessageEmbedding, embeddings[i]), self.algo_dict)

            for i in range(1, len(pre_processed_lst_msgs)+1)
        ]

        # Profiling 1 - end
        # profiling_last_task_ends()

        # Profiling 0 - end
        # profiling_last_task_ends()

        return res


#
class SimpleSyntaxic_SearchAlgorithm(SearchAlgorithm):
    """
    Algorithme de recherche très simple qui va juste compter le nombre de mots(=bouts de textes séparés par des espaces) en commun entre la recherche et les messages.
    """

    def __init__(self, algo_config: dict, conf: Config) -> None:
        #
        super().__init__(algo_config, conf)
        #
        self.config: Config = conf
        self.algo_config: dict = algo_config

    #
    def get_matrix_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> Tensor:
        """
        Calcule la matrice des distances entre chaque messages avec cet algorithme.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            Tensor: La matrice des distances entre chaque messages. De dimensions (n, n).
        """

        # On pré-traite les messages
        pre_processed_lst_msgs: list[Message] = self.pre_process_base_messages(lst_msgs, ner_dicts)

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(lst_msgs)

        # On initialise la matrice
        matrix_distances: Tensor = zeros((n, n), dtype=float32)

        # On calcule les distances pour chaque couple de messages
        for id_msg1 in range(n):
            for id_msg2 in range(n):
                matrix_distances[id_msg1, id_msg2] = -find_common_words(pre_processed_lst_msgs[id_msg1], pre_processed_lst_msgs[id_msg2])

        # On renvoie le résultat
        return matrix_distances

    #
    def get_linear_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> list[float]:
        """
        Calcule la liste des distances entre le message précédent et le message actuel.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            list[float]: La liste des distances entre chaques messages séquentiellement.
        """

        # On pré-traite les messages
        pre_processed_lst_msgs: list[Message] = self.pre_process_base_messages(lst_msgs, ner_dicts)

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(lst_msgs)

        # On calcule les résultats
        res: list[float] = [0] + [
            -find_common_words(pre_processed_lst_msgs[i-1], pre_processed_lst_msgs[i])

            for i in range(1, len(pre_processed_lst_msgs))
        ]

        # On renvoie les résultats
        return res

    #
    def search(self, search_input: str, lst_msgs: list[MessageSearch], ner_dicts: list[str]) -> list[float]:
        """
        Recherche syntaxique simple: compte le nombre de mots en communs

        Args:
            search_input (str): Texte de la recherche
            lst_msgs (list[MessageSearch]): Liste de messages à comparer avec la recherche

        Returns:
            list[float]: Liste des scores correspondant à cette liste initiale de messages, dans l'ordre
        """

        # Préparation au pré-processing
        pre_processed_search_input: str
        pre_processed_lst_msgs: list[MessageSearch]
        pre_processed_search_input, pre_processed_lst_msgs = self.pre_process_search_messages(search_input, lst_msgs, ner_dicts)

        # On renvoie les résultats
        return [-find_common_words(pre_processed_search_input, msg.content) for msg in pre_processed_lst_msgs]


#
class SyntaxicFullSentenceLevenshtein_SearchAlgorithm(SearchAlgorithm):
    """
    Algorithme de recherche qui va juste calculer une distance de Levenshtein entre le texte de recherche et les messages
    """

    def __init__(self, algo_config: dict, conf: Config) -> None:
        #
        super().__init__(algo_config, conf)
        #
        self.config: Config = conf
        self.algo_config: dict = algo_config

    #
    def get_matrix_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> Tensor:
        """
        Calcule la matrice des distances entre chaque messages avec cet algorithme.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            Tensor: La matrice des distances entre chaque messages. De dimensions (n, n).
        """

        # On pré-traite les messages
        pre_processed_lst_msgs: list[Message] = self.pre_process_base_messages(lst_msgs, ner_dicts)

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(lst_msgs)

        # On initialise la matrice
        matrix_distances: Tensor = zeros((n, n), dtype=float32)

        # On calcule les distances pour chaque couple de messages
        for id_msg1 in range(n):
            for id_msg2 in range(n):
                matrix_distances[id_msg1, id_msg2] = full_sentence_levenshtein_distance(pre_processed_lst_msgs[id_msg1], pre_processed_lst_msgs[id_msg2])

        # On renvoie le résultat
        return matrix_distances

    #
    def get_linear_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> list[float]:
        """
        Calcule la liste des distances entre le message précédent et le message actuel.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            list[float]: La liste des distances entre chaques messages séquentiellement.
        """

        # On pré-traite les messages
        pre_processed_lst_msgs: list[Message] = self.pre_process_base_messages(lst_msgs, ner_dicts)

        # On calcule les résultats
        res: list[float] = [0] + [
            full_sentence_levenshtein_distance(pre_processed_lst_msgs[i-1], pre_processed_lst_msgs[i])

            for i in range(1, len(pre_processed_lst_msgs))
        ]

        # On renvoie les résultats
        return res

    #
    def search(self, search_input: str, lst_msgs: list[MessageSearch], ner_dicts: list[str]) -> list[float]:
        """
        Recherche syntaxique qui constiste à calculer la distance de Levenshtein sur les textes complets de recherche et de messages

        Args:
            search_input (str): Texte de la recherche
            lst_msgs (list[MessageSearch]): Liste de messages à comparer avec la recherche

        Returns:
            list[float]: Liste des scores correspondant à cette liste initiale de messages, dans l'ordre
        """

        # Préparation au pré-processing
        pre_processed_search_input: str
        pre_processed_lst_msgs: list[MessageSearch]
        pre_processed_search_input, pre_processed_lst_msgs = self.pre_process_search_messages(search_input, lst_msgs, ner_dicts)


        # On renvoie les résultats
        return [full_sentence_levenshtein_distance(pre_processed_search_input, msg.content) for msg in pre_processed_lst_msgs]


#
class SyntaxicWordsLevenshtein_SearchAlgorithm(SearchAlgorithm):
    """
    Algorithme de recherche qui va juste calculer une distance de Levenshtein entre le texte de recherche et les messages
    """

    def __init__(self, algo_config: dict, conf: Config) -> None:
        #
        super().__init__(algo_config, conf)
        #
        self.config: Config = conf
        self.algo_config: dict = algo_config

        #
        for key in ["close_words_factor"]:
            if not key in algo_config:
                raise ConfigError(f"La configuration de l'algorithme de recherche n'a pas d'attributs `{key}`.")

        # Deux mots sont considérés comme "proches" s'ils ont une distance de Levenshtein inférieure à un certain pourcentage de la somme de leurs tailles.
        self.close_words_factor: float = float(algo_config["close_words_factor"])

    #
    def get_matrix_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> Tensor:
        """
        Calcule la matrice des distances entre chaque messages avec cet algorithme.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            Tensor: La matrice des distances entre chaque messages. De dimensions (n, n).
        """

        # On pré-traite les messages
        pre_processed_lst_msgs: list[Message] = self.pre_process_base_messages(lst_msgs, ner_dicts)

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(lst_msgs)

        # On initialise la matrice
        matrix_distances: Tensor = zeros((n, n), dtype=float32)

        # On calcule les distances pour chaque couple de messages
        for id_msg1 in range(n):
            for id_msg2 in range(n):
                matrix_distances[id_msg1, id_msg2] = words_levenshtein_distances(pre_processed_lst_msgs[id_msg1], pre_processed_lst_msgs[id_msg2])

        # On renvoie le résultat
        return matrix_distances

    #
    def get_linear_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> list[float]:
        """
        Calcule la liste des distances entre le message précédent et le message actuel.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            list[float]: La liste des distances entre chaques messages séquentiellement.
        """

        # On pré-traite les messages
        pre_processed_lst_msgs: list[Message] = self.pre_process_base_messages(lst_msgs, ner_dicts)

        # On calcule les résultats
        res: list[float] = [0] + [
            words_levenshtein_distances(pre_processed_lst_msgs[i-1], pre_processed_lst_msgs[i])

            for i in range(1, len(pre_processed_lst_msgs))
        ]

        # On renvoie les résultats
        return res

    #
    def search(self, search_input: str, lst_msgs: list[MessageSearch], ner_dicts: list[str]) -> list[float]:
        """
        Recherche syntaxique qui consiste à calculer la distance de Levenshtein sur les couples de mots entre la recherche et chacun des messages à rechercher
        Deux mots sont considérés comme "proches" s'ils ont une distance de Levenshtein inférieure à un certain pourcentage de la somme de leurs tailles.

        Args:
            search_input (str): Texte de la recherche
            lst_msgs (list[MessageSearch]): Liste de messages à comparer avec la recherche

        Returns:
            list[float]: Liste des scores correspondant à cette liste initiale de messages, dans l'ordre
        """

        # Préparation au pré-processing
        pre_processed_search_input: str
        pre_processed_lst_msgs: list[MessageSearch]
        pre_processed_search_input, pre_processed_lst_msgs = self.pre_process_search_messages(search_input, lst_msgs, ner_dicts)

        # On renvoie les résultats
        return [words_levenshtein_distances(pre_processed_search_input, msg.content, self.close_words_factor) for msg in pre_processed_lst_msgs]


#
class SimpleDictJaccard_NER_SearchAlgorithm(SearchAlgorithm):
    """
    Algorithme de recherche qui va juste faire un petit NER simple qui va détecter tous les éléments de NER depuis les dictionnaires de NER, puis va calculer une distance de Jaccard sur les résultats
    """

    def __init__(self, algo_config: dict, conf: Config) -> None:
        #
        super().__init__(algo_config, conf)
        #
        self.config: Config = conf
        self.algo_config: dict = algo_config

    #
    def get_matrix_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> Tensor:
        """
        Calcule la matrice des distances entre chaque messages avec cet algorithme.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            Tensor: La matrice des distances entre chaque messages. De dimensions (n, n).
        """

        # On pré-traite les messages
        pre_processed_lst_msgs: list[Message] = self.pre_process_base_messages(lst_msgs, ner_dicts)

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(lst_msgs)

        # On initialise la matrice
        matrix_distances: Tensor = zeros((n, n), dtype=float32)

        # On calcule la base de Jaccard
        ner_base: list[str] = get_ner_jaccard_vec_base(ner_dicts)
        ner_base_length: int = len(ner_base)

        if ner_base_length == 0:
            return matrix_distances

        # On calcule les distances pour chaque couple de messages
        for id_msg1 in range(n):
            for id_msg2 in range(n):
                matrix_distances[id_msg1, id_msg2] = -jaccard_distance(
                    calculate_NER_vector_from_txt_and_dicts(pre_processed_lst_msgs[id_msg1], ner_base),
                    calculate_NER_vector_from_txt_and_dicts(pre_processed_lst_msgs[id_msg2], ner_base),
                    ner_base_length
                )

        # On renvoie le résultat
        return matrix_distances

    #
    def get_linear_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> list[float]:
        """
        Calcule la liste des distances entre le message précédent et le message actuel.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            list[float]: La liste des distances entre chaques messages séquentiellement.
        """

        # On calcule la base de Jaccard
        ner_base: list[str] = get_ner_jaccard_vec_base(ner_dicts)
        ner_base_length: int = len(ner_base)

        if ner_base_length == 0:
            return [0.0] * len(lst_msgs)

        # On pré-traite les messages
        pre_processed_lst_msgs: list[Message] = self.pre_process_base_messages(lst_msgs, ner_dicts)

        # On calcule les résultats
        res: list[float] = [0] + [
                -jaccard_distance(
                    calculate_NER_vector_from_txt_and_dicts(pre_processed_lst_msgs[i-1], ner_base),
                    calculate_NER_vector_from_txt_and_dicts(pre_processed_lst_msgs[i], ner_base),
                    ner_base_length
                )
            for i in range(1, len(pre_processed_lst_msgs))
        ]

        # On renvoie les résultats
        return res

    #
    def search(self, search_input: str, lst_msgs: list[MessageSearch], ner_dicts: list[str]) -> list[float]:
        """
        Recherche qui va juste faire un petit NER simple qui va détecter tous les éléments de NER depuis les dictionnaires de NER, puis va calculer une distance de Jaccard sur les résultats

        Args:
            search_input (str): Texte de la recherche
            lst_msgs (list[MessageSearch]): Liste de messages à comparer avec la recherche

        Returns:
            list[float]: Liste des scores correspondant à cette liste initiale de messages, dans l'ordre
        """

        # Préparation au pré-processing
        pre_processed_search_input: str
        pre_processed_lst_msgs: list[MessageSearch]
        pre_processed_search_input, pre_processed_lst_msgs = self.pre_process_search_messages(search_input, lst_msgs, ner_dicts)

        # On calcule la base de Jaccard
        ner_base: list[str] = get_ner_jaccard_vec_base(ner_dicts)
        ner_base_length: int = len(ner_base)

        if ner_base_length == 0:
            return [0.0] * len(lst_msgs)

        #
        vec_input: set[int] = calculate_NER_vector_from_txt_and_dicts(pre_processed_search_input, ner_base)

        # On renvoie les résultats
        return [
            -jaccard_distance(vec_input, calculate_NER_vector_from_txt_and_dicts(msg.content, ner_base), ner_base_length)
            for msg in pre_processed_lst_msgs
        ]


#
class SimpleSearchByTime_SearchAlgorithm(SearchAlgorithm):
    """
    Algorithme de recherche très simple qui va juste regarder la différence de temps entre deux messages.
    """

    def __init__(self, algo_config: dict, conf: Config) -> None:
        #
        super().__init__(algo_config, conf)
        #
        self.config: Config = conf
        self.algo_config: dict = algo_config

    #
    def get_matrix_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> Tensor:
        """
        Calcule la matrice des distances entre chaque messages avec cet algorithme.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            Tensor: La matrice des distances entre chaque messages. De dimensions (n, n).
        """

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(lst_msgs)

        # On initialise la matrice
        matrix_distances: Tensor = zeros((n, n), dtype=float32)

        # On calcule les distances pour chaque couple de messages
        for id_msg1 in range(n):
            for id_msg2 in range(n):
                matrix_distances[id_msg1, id_msg2] = time_distance(lst_msgs[id_msg1], lst_msgs[id_msg2])

        # On renvoie le résultat
        return matrix_distances

    #
    def get_linear_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> list[float]:
        """
        Calcule la liste des distances entre le message précédent et le message actuel.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            list[float]: La liste des distances entre chaques messages séquentiellement.
        """

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(lst_msgs)

        # On calcule les résultats
        res: list[float] = [0] + [
            time_distance(lst_msgs[i-1], lst_msgs[i])

            for i in range(1, len(lst_msgs))
        ]

        # On renvoie les résultats
        return res

    #
    def search(self, search_input: str, lst_msgs: list[MessageSearch], ner_dicts: list[str]) -> list[float]:
        """
        Recherche de temps simple: on n'a pas de temps avec le texte de recherche, on va donc renvoyer un score neutre.

        Args:
            search_input (str): Texte de la recherche
            lst_msgs (list[MessageSearch]): Liste de messages à comparer avec la recherche

        Returns:
            list[float]: Liste des scores correspondant à cette liste initiale de messages, dans l'ordre
        """

        # On n'a pas de dates sur le texte de recherche
        return [0.0] * len(lst_msgs)


#
class SearchByUsers_SearchAlgorithm(SearchAlgorithm):
    """
    Algorithme de recherche qui va analyser les utilisateurs qui discuttent souvent entre eux, et qui va ensuite peser les messages entre eux avec ces données.
    """

    def __init__(self, algo_config: dict, conf: Config) -> None:
        #
        super().__init__(algo_config, conf)
        #
        self.config: Config = conf
        self.algo_config: dict = algo_config

    #
    def analyse_users(self, lst_msgs: list[MessageSearch | Message], ner_dicts: list[str] = []) -> tuple[Tensor, Tensor, dict[int, int] ]:
        """
        Cette fonction analyse les utilisateurs et les messages d'une liste de messages de recherche (lst_msgs).

        Args:
            lst_msgs (list[MessageSearch]): Une liste d'objets MessageSearch contenant les informations sur les messages.
            ner_dicts (list[str], optional): Une liste optionnelle de dictionnaires d'entités nommées à utiliser pour l'analyse (par défaut, une liste vide).

        Returns:
            tuple[Tensor, Tensor]: Un tuple contenant deux tenseurs. Le premier est une matrice d'utilisateurs où la valeur à l'indice (i, j) représente la proximité entre les utilisateurs i et j
                                    basée sur leur participation aux mêmes conversations. Le second est une matrice de messages où la valeur à l'indice (i, j) représente la proximité entre les messages
                                    i et j basée sur leur appartenance à la même conversation.
        """

        #
        list_conversations: list[list[int]] = []
        list_authors_conversation: list[set[int]] = []
        author_ids_convert: dict[int, int] = {}

        # authors ids
        authors_ids: set[int] = set()

        # On regroupe les conversations par temps
        for i in range(len(lst_msgs)):
            #
            author: set[int] = lst_msgs[i].author_id if isinstance(lst_msgs[i].author_id, set) else set([lst_msgs[i].author_id])

            #
            for a in author:
                if a not in author_ids_convert:
                    author_ids_convert[a] = len(author_ids_convert)

            #
            authors_ids = authors_ids.union(author)

            #
            if len(list_conversations) == 0:
                list_conversations.append([i])
                list_authors_conversation.append(author)
            #
            else:
                #
                if real_minutes_time_distances(lst_msgs[i], lst_msgs[list_conversations[-1][-1]]) < 6:
                    list_conversations[-1].append(i)
                    list_authors_conversation[-1] = author.union(list_authors_conversation[-1])
                #
                else:
                    list_conversations.append([i])
                    list_authors_conversation.append(author)

        # On crée la matrice des utilisateurs
        nb_authors: int = len(authors_ids)
        users_matrix: Tensor = -eye(nb_authors, nb_authors, dtype=float32)

        #
        id_conv: int
        id_user_1: int
        id_user_2: int
        for id_conv in range(len(list_conversations)):
            #
            for id_user_1 in list_authors_conversation[id_conv]:
                for id_user_2 in list_authors_conversation[id_conv]:
                    users_matrix[author_ids_convert[id_user_1]][author_ids_convert[id_user_2]] -= 0.2

        # On crée la matrice des messages
        nb_msgs: int = len(lst_msgs)
        msgs_matrix: Tensor = -eye(nb_msgs, nb_msgs, dtype=float32)

        #
        id_msg_1: int
        id_msg_2: int
        for id_conv in range(len(list_conversations)):
            #
            for id_msg_1 in list_conversations[id_conv]:
                for id_msg_2 in list_conversations[id_conv]:
                    msgs_matrix[id_msg_1][id_msg_2] -= 0.2

        #
        return (users_matrix, msgs_matrix, author_ids_convert)

    #
    def get_matrix_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> Tensor:
        """
        Calcule la matrice des distances entre chaque messages avec cet algorithme.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            Tensor: La matrice des distances entre chaque messages. De dimensions (n, n).
        """

        # On récupère les analyse des messages
        users_matrix: Tensor
        msgs_matrix: Tensor
        author_ids_convert: dict[int, int]
        users_matrix, msgs_matrix, author_ids_convert = self.analyse_users(lst_msgs, ner_dicts)

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(lst_msgs)

        # On initialise la matrice
        matrix_distances: Tensor = zeros((n, n), dtype=float32)

        # On calcule les distances pour chaque couple de messages
        for id_msg1 in range(n):
            for id_msg2 in range(n):
                matrix_distances[id_msg1, id_msg2] = msgs_matrix[id_msg1][id_msg2] + users_matrix[author_ids_convert[lst_msgs[id_msg1].author_id]][author_ids_convert[lst_msgs[id_msg2].author_id]]

        # On renvoie le résultat
        return matrix_distances

    #
    def get_linear_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> list[float]:
        """
        Calcule la liste des distances entre le message précédent et le message actuel.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            list[float]: La liste des distances entre chaques messages séquentiellement.
        """

        # On récupère les analyse des messages
        users_matrix: Tensor
        msgs_matrix: Tensor
        users_matrix, msgs_matrix = self.analyse_users(lst_msgs, ner_dicts)

        # Nombre de messages pour les lignes et les colonnes de la matrice
        n: int = len(lst_msgs)

        # On calcule les résultats
        res: list[float] = [0]
        #
        for i in range(1, len(lst_msgs)):
            id_msg1: int = i - 1
            id_msg2: int = i
            #
            res.append( msgs_matrix[id_msg1][id_msg2] - users_matrix[lst_msgs[id_msg1].author_id][lst_msgs[id_msg2].author_id] )

        # On renvoie les résultats
        return res

    #
    def search(self, search_input: str, lst_msgs: list[MessageSearch], ner_dicts: list[str]) -> list[float]:
        """
        Recherche entre utilisateurs simple: on renvoie un score neutre, on n'a pas d'utilisateurs sur le texte de recherche.

        Args:
            search_input (str): Texte de la recherche
            lst_msgs (list[MessageSearch]): Liste de messages à comparer avec la recherche

        Returns:
            list[float]: Liste des scores correspondant à cette liste initiale de messages, dans l'ordre
        """

        # On n'a pas de dates sur le texte de recherche
        return [0.0] * len(lst_msgs)


#
class SearchWith_NER_Engine_SearchAlgorithm(SearchAlgorithm):
    """
    Algorithme de recherche qui va analyser et rapprocher les messages entre eux qui ont des entités en commun.
    """

    def __init__(self, algo_config: dict, config: Config) -> None:
        #
        super().__init__(algo_config, config)
        #
        self.config: Config = config
        self.algo_config: dict = algo_config

        #
        for key in ["ner_engine_config_dict"]:
            if not key in algo_config:
                raise ConfigError(f"La configuration de l'algorithme de recherche n'a pas d'attributs `{key}`.")

        # On récupère les attributs
        self.ner_engine_config_dict: dict = algo_config["ner_engine_config_dict"]

        # On va charger le moteur de recherche
        self.ner_engine: NER_Engine = NER_Engine(self.ner_engine_config_dict, self.config)

    #
    def analyse_entities(self, lst_msgs: list[MessageSearch | Message], ner_dicts: list[str] = []) -> tuple[Tensor, dict[int, int] ]:
        """
        Cette fonction analyse messages d'une liste de messages de recherche (lst_msgs).

        Args:
            lst_msgs (list[MessageSearch]): Une liste d'objets MessageSearch contenant les informations sur les messages.
            ner_dicts (list[str], optional): Une liste optionnelle de dictionnaires d'entités nommées à utiliser pour l'analyse (par défaut, une liste vide).

        Returns:
            Tensor: Un tensur qui est une matrice de messages où la valeur à l'indice (i, j) représente la proximité entre les messages
                                    i et j basée sur leurs nombres d'entités en commun.
        """

        #
        nb_msgs: int = len(lst_msgs)

        # On récupère la liste des entités par messages
        lst_msgs_entities: list[ list[ tuple[ int, str, str ] ] ] = []

        #
        id_msg: int
        for id_msg in range(nb_msgs):
            lst_msgs_entities.append( self.ner_engine.main_recognize(lst_msgs[id_msg].content) )
            if isinstance(lst_msgs[id_msg].author_name, set):
                lst_msgs_entities[-1] += [(0, name, "PERS") for name in lst_msgs[id_msg].author_name]
            elif isinstance(lst_msgs[id_msg].author_name, str):
                lst_msgs_entities[-1].append( (0, lst_msgs[id_msg].author_name, "PERS") )

        # On crée la matrice des messages
        msgs_matrix: Tensor = zeros(nb_msgs, nb_msgs, dtype=float32)

        #
        id_msg_1: int
        id_msg_2: int
        for id_msg_1 in range(nb_msgs):
            for id_msg_2 in range(nb_msgs):
                msgs_matrix[id_msg_1][id_msg_2] -= calc_common_entities(lst_msgs_entities[id_msg_1], lst_msgs_entities[id_msg_2])

        #
        return msgs_matrix

    #
    def get_matrix_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> Tensor:
        """
        Calcule la matrice des distances entre chaque messages avec cet algorithme.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            Tensor: La matrice des distances entre chaque messages. De dimensions (n, n).
        """

        # On récupère les analyse des messages
        matrix_distances: Tensor
        matrix_distances = self.analyse_entities(lst_msgs, ner_dicts)

        # On renvoie le résultat
        return matrix_distances

    #
    def get_linear_distances_from_messages_main(self, lst_msgs: list[Message], ner_dicts: list[str] = []) -> list[float]:
        """
        Calcule la liste des distances entre le message précédent et le message actuel.

        Args:
            lst_msgs (list[Message]): La liste des messages.

        Returns:
            list[float]: La liste des distances entre chaques messages séquentiellement.
        """

        # On récupère les analyse des messages
        matrix_distances: Tensor
        matrix_distances = self.analyse_entities(lst_msgs, ner_dicts)

        # On calcule les résultats
        res: list[float] = [0]
        #
        for i in range(1, len(lst_msgs)):
            id_msg1: int = i - 1
            id_msg2: int = i
            #
            res.append( matrix_distances[id_msg1][id_msg2] )

        # On renvoie les résultats
        return res

    #
    def search(self, search_input: str, lst_msgs: list[MessageSearch], ner_dicts: list[str]) -> list[float]:
        """
        _summary_

        Args:
            search_input (str): Texte de la recherche
            lst_msgs (list[MessageSearch]): Liste de messages à comparer avec la recherche

        Returns:
            list[float]: Liste des scores correspondant à cette liste initiale de messages, dans l'ordre
        """

        # Pas de pré-processing ici, ca va abîmer les données.

        #
        search_input_entitites: list[ tuple[int, str, str] ] = self.ner_engine.main_recognize(search_input)

        #
        lst_msgs_entities: list[ list[ tuple[ int, str, str ] ] ] = []
        for msg_srch in lst_msgs:
            #
            lst_msgs_entities.append( self.ner_engine.main_recognize(msg_srch.content) )
            #
            if isinstance(msg_srch.author_name, set):
                lst_msgs_entities[-1] += [ (0, name, "PERS") for name in msg_srch.author_name]
            elif isinstance(msg_srch.author_name, str):
                lst_msgs_entities[-1].append( (0, msg_srch.author_name, "PERS") )

        # On renvoie le résultats
        return [
            -calc_common_entities(search_input_entitites, lst_msgs_entities[i])
            for i in range(len(lst_msgs))
        ]

