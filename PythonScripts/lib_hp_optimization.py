"""
Fichier qui va contenir des outils et classes pour l'optimisation des hyper paramètres.

Auteur: Nathan Cerisara
"""

from typing import cast, Optional, Any, Callable, Awaitable
from copy import deepcopy
from random import uniform as rd_uniform
import numpy as np

from lib import ConfigError


#
def get_value_from_config(config_dict: dict, keys_of_the_value: list[str, int]) -> str | float | int:
    #
    current_dict_or_value: dict = config_dict
    for k in keys_of_the_value:
        if isinstance(k, list):
            current_dict_or_value = current_dict_or_value[k[0]]
        else:
            current_dict_or_value = current_dict_or_value[k]
    #
    return current_dict_or_value

#
def set_value_to_config(config_dict: dict, keys_of_the_value: list[str, int], value: str | float | int) -> dict:
    #
    current_dict_or_value: dict = config_dict
    for k in keys_of_the_value[:-1]:
        if isinstance(k, list):
            current_dict_or_value = current_dict_or_value[k[0]]
        else:
            current_dict_or_value = current_dict_or_value[k]
    #
    if isinstance(keys_of_the_value[-1], list):
        current_dict_or_value[keys_of_the_value[-1][0]] = value
    else:
        current_dict_or_value[keys_of_the_value[-1]] = value
    #
    return config_dict

# Renvoie un nouveau dictionnaire copié sans modifier le dictionnaire initial !
def set_all_values_to_config(config_dict: dict, keys_and_values: list[dict]) -> dict:
    #
    new_config_dict = deepcopy(config_dict)

    #
    for kv in keys_and_values:
        set_value_to_config(new_config_dict, kv["keys"], kv["value"])

    #
    return new_config_dict


#
"""
    Structure abstraite d'un algorithme d'optimisation des Hyper-Paramètres des différentes configurations des différents moteurs des différentes tâches à optimiser.

    Parameters:

        - task: str
            -=> une valeur de ["search", "NER", "conversation_cut"]
        - evaluation_function: Callable[[str, dict, dict], float]
            -=> evaluation_function(task, test_engine_config_with_modified_hp_values, benchmarks_to_optimize) -> score
        - base_engine_config: dict = Configuration de base
        - hyper_parameters_to_optimize: list[dict]
            -=> liste de
                    {
                        "keys": liste de clés ["key 1", 2, "key 3"],
                        "value_min": 0,
                        "value_max": 1
                    }
        - benchmarks_to_optimize: dict[str, float]
            -=> Couples benchmark_name -> benchmark_score_coefficient

        - algorithm_parameters: dict
            -=> Dictionnaire des paramètres spécifiques des différents algorithmes

        - send_results_update_to_ws: Optional[Callable[[dict], None]]
            -=> Fonction pour envoyer des mises à jour de la progression de l'optimisation algorithmique, messages sous le format :
                {
                    "iter": Entier unique et progressif (1, 2, 3, ...)
                    "color": Entier qui permet de différencier entre différents états de l'optimisation algorithmique en affichant les points d'une autre couleur
                    "score": Valeur flottante représentant le score de cet itération
                }

    Optimize Returns:

        - optimized_hyper_parameters: dict
            -=> Meilleure configuration du moteur trouvée à partir de la requête initiale
"""
class HPOptimisationAlgorithm:

    #
    def __init__(self, task: str, evaluation_function: Callable[[str, dict, dict], float], base_engine_config: dict, hyper_parameters_to_optimize: list[dict], benchmarks_to_optimize: dict[str, float], algorithm_parameters: dict = {}, send_results_update_to_ws: Optional[Callable[[dict], Awaitable[None]]] = None) -> None:
        self.task: str = task
        self.evaluation_function: Callable[[str, dict, dict], float] = evaluation_function
        self.base_engine_config: dict = base_engine_config
        self.hyper_parameters_to_optimize: list[dict] = hyper_parameters_to_optimize
        self.benchmarks_to_optimize: dict[str, float] = benchmarks_to_optimize
        self.algorithm_parameters: dict = algorithm_parameters
        self.send_results_update_to_ws: Optional[Callable[[dict], Awaitable[None]]] = send_results_update_to_ws

    #
    async def optimise(self) -> tuple[dict, float]:
        """
        Fonction de la classe abstraite, donc renvoie juste les valeurs pas défauts.

        Returns:
            list[dict]: Valeurs optimisées des hyper-paramètres de la config.
        """

        #
        optimized_hyper_parameters: list[dict] = [
            {
                "keys": p["keys"],
                "value": get_value_from_config(self.base_engine_config, p["keys"])
            }
            for p in self.hyper_parameters_to_optimize
        ]

        #
        return optimized_hyper_parameters, 0



class Random_Search_HPO_Algorithm(HPOptimisationAlgorithm):
    """
    Implémentation d'un algorithme de recherche hyperparamétrique utilisant une stratégie de recherche aléatoire.

    Cet algorithme optimise les hyperparamètres en les choisissant aléatoirement dans une plage définie, 
    puis évalue les configurations obtenues en fonction d'une fonction de coût ou d'évaluation spécifique.

    Args:
        HPOptimisationAlgorithm (class): Classe de base pour les algorithmes d'optimisation d'hyperparamètres.
        task (str): La tâche spécifique à laquelle les hyperparamètres seront appliqués.
        evaluation_function (Callable[[str, dict, dict], float]): Fonction qui évalue une configuration d'hyperparamètres et retourne un score de performance.
        base_engine_config (dict): Configuration de base du moteur sur laquelle les hyperparamètres optimisés seront appliqués.
        hyper_parameters_to_optimize (list[dict]): Liste des hyperparamètres à optimiser avec leurs plages de valeurs.
        benchmarks_to_optimize (dict[str, float]): Objectifs de benchmarks à atteindre pour l'optimisation.
        algorithm_parameters (dict, optional): Paramètres spécifiques à l'algorithme, comme le nombre d'itérations ("nb_iter").
        send_results_update_to_ws (Optional[Callable[[dict], Awaitable[None]]], optional): Fonction de callback pour envoyer les résultats intermédiaires via WebSocket.

    Raises:
        ConfigError: Erreur soulevée si un paramètre requis pour l'algorithme n'est pas présent dans `algorithm_parameters`.

    Returns:
        tuple: Une paire composée de la meilleure configuration d'hyperparamètres trouvée et du score correspondant.
    """

    #
    def __init__(self, task: str, evaluation_function: Callable[[str, dict, dict], float], base_engine_config: dict, hyper_parameters_to_optimize: list[dict], benchmarks_to_optimize: dict[str, float], algorithm_parameters: dict = {}, send_results_update_to_ws: Optional[Callable[[dict], Awaitable[None]]] = None) -> None:
        super().__init__(task, evaluation_function, base_engine_config, hyper_parameters_to_optimize, benchmarks_to_optimize, send_results_update_to_ws=send_results_update_to_ws)

        #
        for k in ["nb_iter"]:
            if not k in algorithm_parameters:
                raise ConfigError(f"No key {k} in conversation algorithm parameters : {algorithm_parameters} !")

        #
        self.nb_iter: int = int(algorithm_parameters["nb_iter"])

    #
    async def optimise(self) -> tuple[dict, float]:
        """
        Fonction principale d'optimisation utilisant la recherche aléatoire.

        Exécute un nombre défini d'itérations, où chaque itération génère une nouvelle configuration
        d'hyperparamètres aléatoirement dans les plages spécifiées, évalue cette configuration, et
        garde en mémoire celle qui offre le meilleur score.

        Returns:
            tuple[dict, float]: Un tuple contenant la meilleure configuration d'hyperparamètres et le score associé.
        """

        best_optimized_hp: Optional[list[dict]] = None
        best_optimized_hp_score: Optional[float] = None

        for i in range(self.nb_iter):

            #
            optimized_hyper_parameters: list[dict] = [
                {
                    "keys": p["keys"],
                    "value": rd_uniform(float(p["value_min"]), float(p["value_max"]))
                }
                for p in self.hyper_parameters_to_optimize
            ]

            #
            optimized_hyper_parameters_config = set_all_values_to_config(self.base_engine_config, optimized_hyper_parameters)

            #
            score: float = self.evaluation_function(
                self.task,
                optimized_hyper_parameters_config,
                self.benchmarks_to_optimize
            )

            #
            if best_optimized_hp_score is None or score > best_optimized_hp_score:
                best_optimized_hp_score = score
                best_optimized_hp = optimized_hyper_parameters_config

            #
            if self.send_results_update_to_ws is not None:
                await self.send_results_update_to_ws({
                    "iter": i,
                    "color": 0,
                    "score": score,
                    "config": optimized_hyper_parameters_config
                })

        #
        return best_optimized_hp, best_optimized_hp_score


#
def grid_exploration(grid_points: list[list[float]], hyper_params_values: list[float], current_dim: int, hyper_params: list[dict], nb_grid_cuts: int = 5, current_grid_deep_process: int = 0, best_hyper_params_score: list[float] = None) -> None:
    #
    if current_dim >= len(hyper_params):
        grid_points.append(hyper_params_values)
        return
    #
    param_value_interval_min: float = hyper_params[current_dim]["value_min"]
    param_value_interval_max: float = hyper_params[current_dim]["value_max"]
    #
    if best_hyper_params_score is not None and len(best_hyper_params_score) >= current_dim:
        interval_size: float = (param_value_interval_max - param_value_interval_min) / float(nb_grid_cuts ** current_grid_deep_process)
        #
        param_value_interval_min = best_hyper_params_score[current_dim] - interval_size / 2.0
        param_value_interval_max = best_hyper_params_score[current_dim] + interval_size / 2.0
    #
    # Clamping values
    if param_value_interval_min < hyper_params[current_dim]["value_min"]:
        param_value_interval_min = hyper_params[current_dim]["value_min"]
    if param_value_interval_max > hyper_params[current_dim]["value_max"]:
        param_value_interval_max = hyper_params[current_dim]["value_max"]
    #
    interval_steps: float = (param_value_interval_max - param_value_interval_min) / float(nb_grid_cuts - 1.0)
    j: int = 0
    for j in range(nb_grid_cuts):
        param_value: float = param_value_interval_min + interval_steps * float(j)
        #
        new_hp_values: list[float] = deepcopy(hyper_params_values)
        new_hp_values.append(param_value)
        #
        grid_exploration(
            grid_points=grid_points,
            hyper_params_values=new_hp_values,
            current_dim=current_dim+1,
            hyper_params=hyper_params,
            nb_grid_cuts=nb_grid_cuts,
            current_grid_deep_process=current_grid_deep_process,
            best_hyper_params_score=best_hyper_params_score
        )


#
class Grid_Search_HPO_Algorithm(HPOptimisationAlgorithm):
    """
    Implémente un algorithme de recherche hyperparamétrique basé sur la méthode de la recherche en grille.

    Args:
        HPOptimisationAlgorithm (class): Classe de base pour les algorithmes d'optimisation des hyperparamètres.
        task (str): La tâche à optimiser.
        evaluation_function (Callable[[str, dict, dict], float]): Fonction d'évaluation prenant la tâche, la configuration de l'algorithme, et les benchmarks en entrée, et renvoyant un score de performance.
        base_engine_config (dict): Configuration de base du moteur sur laquelle les hyperparamètres seront appliqués.
        hyper_parameters_to_optimize (list[dict]): Liste des dictionnaires définissant les hyperparamètres à optimiser.
        benchmarks_to_optimize (dict[str, float]): Dictionnaire des benchmarks avec les valeurs cibles que l'algorithme doit atteindre ou surpasser.
        algorithm_parameters (dict, optional): Paramètres spécifiques à l'algorithme de recherche en grille, tels que le nombre de divisions de la grille (`nb_grid_cuts`) et les profondeurs d'exploration (`deep_steps`). Par défaut {}.
        send_results_update_to_ws (Optional[Callable[[dict], Awaitable[None]]], optional): Fonction asynchrone facultative permettant d'envoyer des mises à jour des résultats, par exemple à une interface WebSocket. Par défaut None.

    Raises:
        ConfigError: Erreur levée si des paramètres requis de l'algorithme ne sont pas présents dans `algorithm_parameters`.

    Returns:
        Tuple[dict, float]: Une paire contenant la configuration des hyperparamètres optimisés et le score de performance associé.
    """

    #
    def __init__(self, task: str, evaluation_function: Callable[[str, dict, dict], float], base_engine_config: dict, hyper_parameters_to_optimize: list[dict], benchmarks_to_optimize: dict[str, float], algorithm_parameters: dict = {}, send_results_update_to_ws: Optional[Callable[[dict], Awaitable[None]]] = None) -> None:
        super().__init__(task, evaluation_function, base_engine_config, hyper_parameters_to_optimize, benchmarks_to_optimize, send_results_update_to_ws=send_results_update_to_ws)

        #
        for k in ["nb_grid_cuts"]:
            if not k in algorithm_parameters:
                raise ConfigError(f"No key {k} in conversation algorithm parameters : {algorithm_parameters} !")

        #
        self.nb_grid_cuts: int = int(algorithm_parameters["nb_grid_cuts"])
        self.deeps_to_go: int = 1
        if "deep_steps" in algorithm_parameters:
            self.deeps_to_go = int(algorithm_parameters["deep_steps"])

    #
    async def optimise(self) -> tuple[dict, float]:
        """
        Exécute l'algorithme de recherche en grille pour optimiser les hyperparamètres.

        Returns:
            tuple[dict, float]: La meilleure configuration d'hyperparamètres trouvée ainsi que le score de performance associé.
        """

        # Initialisation des variables pour stocker les meilleurs hyperparamètres trouvés et leur score
        best_optimized_hp: Optional[list[dict]] = None
        best_optimized_hp_values: Optional[list[float]] = None
        best_optimized_hp_score: Optional[float] = None

        # Compteur pour suivre le nombre d'itérations
        nb_iter: int = 0

        # Boucle sur les profondeurs de la grille à explorer
        for current_deep in range(self.deeps_to_go):
            # Liste des points à tester pour la configuration actuelle de la grille
            points_to_tests: list[list[float]] = []

            # Fonction de génération des points de grille à explorer
            grid_exploration(
                grid_points=points_to_tests,
                hyper_params_values=[],
                current_dim=0,
                hyper_params=self.hyper_parameters_to_optimize,
                nb_grid_cuts=self.nb_grid_cuts,
                current_grid_deep_process=current_deep,
                best_hyper_params_score=best_optimized_hp_values
            )

            # Boucle sur chaque point de grille généré
            for pts in points_to_tests:

                # Création de la configuration des hyperparamètres pour le point actuel
                optimized_hyper_parameters: list[dict] = [
                    {
                        "keys": self.hyper_parameters_to_optimize[i]["keys"],
                        "value": pts[i]
                    }
                    for i in range(len(self.hyper_parameters_to_optimize))
                ]

                # Mise à jour de la configuration de base avec les valeurs des hyperparamètres optimisés
                optimized_hyper_parameters_config = set_all_values_to_config(self.base_engine_config, optimized_hyper_parameters)

                # Évaluation du score pour la configuration courante
                score: float = self.evaluation_function(
                    self.task,
                    optimized_hyper_parameters_config,
                    self.benchmarks_to_optimize
                )

                # Mise à jour des meilleures valeurs trouvées si le score actuel est meilleur
                if best_optimized_hp_score is None or score > best_optimized_hp_score:
                    best_optimized_hp_score = score
                    best_optimized_hp_values = pts
                    best_optimized_hp = optimized_hyper_parameters_config

                # Envoi des résultats mis à jour via WebSocket si une fonction est fournie
                if self.send_results_update_to_ws is not None:
                    await self.send_results_update_to_ws({
                        "iter": nb_iter,
                        "color": current_deep,
                        "score": score,
                        "config": optimized_hyper_parameters_config
                    })

                # Incrément du compteur d'itérations
                nb_iter += 1

        # Retourne la meilleure configuration d'hyperparamètres trouvée et son score
        return best_optimized_hp, best_optimized_hp_score


#
def linear_exploration(idx_param: int, best_hp_values: list[float], hyper_params: list[dict], nb_pts: int, current_deep: int = 0) -> list[np.ndarray]:
    """
    Génère une liste de points échantillonnés de manière linéaire dans l'espace des hyperparamètres pour l'optimisation.

    Args:
        idx_param (int): L'indice du paramètre hyperparamétrique à explorer dans `hyper_params`.
        best_hp_values (list[float]): Liste des meilleures valeurs actuelles des hyperparamètres, utilisée comme point de départ pour l'exploration.
        hyper_params (list[dict]): Liste des dictionnaires définissant les hyperparamètres, avec leurs intervalles de valeurs minimum et maximum.
        nb_pts (int): Nombre de points à échantillonner dans l'intervalle spécifié.
        current_deep (int, optional): Profondeur actuelle de l'exploration, utilisée pour affiner les intervalles à chaque itération. Par défaut 0.

    Returns:
        list[np.ndarray]: Liste de tableaux numpy représentant les points explorés dans l'espace des hyperparamètres.
    """

    # Liste pour stocker les points explorés
    pts_list: list[np.ndarray] = []

    # Détermine les valeurs minimale et maximale pour l'intervalle du paramètre à explorer
    param_value_interval_min: float = float(hyper_params[idx_param]["value_min"])
    param_value_interval_max: float = float(hyper_params[idx_param]["value_max"])

    # Si une exploration en profondeur est en cours, ajuste l'intervalle autour des meilleures valeurs trouvées
    if current_deep > 0:
        interval_size: float = (param_value_interval_max - param_value_interval_min) / float(nb_pts ** current_deep)

        # Ajuste les bornes de l'intervalle autour de la meilleure valeur actuelle du paramètre
        param_value_interval_min = float(best_hp_values[idx_param]) - interval_size / 2.0
        param_value_interval_max = float(best_hp_values[idx_param]) + interval_size / 2.0

    # S'assure que les valeurs de l'intervalle ne dépassent pas les limites définies dans `hyper_params`
    if param_value_interval_min < float(hyper_params[idx_param]["value_min"]):
        param_value_interval_min = float(hyper_params[idx_param]["value_min"])
    if param_value_interval_max > float(hyper_params[idx_param]["value_max"]):
        param_value_interval_max = float(hyper_params[idx_param]["value_max"])

    # Calcule la distance entre chaque point dans l'intervalle
    interval_steps: float = (param_value_interval_max - param_value_interval_min) / float(nb_pts - 1.0)

    # Génère les points en échantillonnant linéairement l'intervalle
    j: int = 0
    for j in range(nb_pts):

        # Valeur actuelle de l'hyper paramètre
        param_value: float = param_value_interval_min + interval_steps * float(j)

        # Crée une copie des meilleures valeurs et modifie le paramètre actuel avec la nouvelle valeur
        point = deepcopy(best_hp_values)
        point[idx_param] = param_value

        # Ajoute le nouveau point à la liste des points explorés
        pts_list.append(np.array(point))

    # Retourne la liste des points à explorer
    return pts_list


#
class Linear_Individual_Search_HPO_Algorithm(HPOptimisationAlgorithm):
    """
    Implémente un algorithme d'optimisation hyperparamétrique en utilisant une approche de recherche linéaire individuelle.

    Args:
        HPOptimisationAlgorithm (class): Classe de base pour les algorithmes d'optimisation des hyperparamètres.
        task (str): La tâche à optimiser.
        evaluation_function (Callable[[str, dict, dict], float]): Fonction d'évaluation prenant la tâche, la configuration de l'algorithme, et les benchmarks en entrée, et renvoyant un score de performance.
        base_engine_config (dict): Configuration de base du moteur sur laquelle les hyperparamètres seront appliqués.
        hyper_parameters_to_optimize (list[dict]): Liste des dictionnaires définissant les hyperparamètres à optimiser.
        benchmarks_to_optimize (dict[str, float]): Dictionnaire des benchmarks avec les valeurs cibles que l'algorithme doit atteindre ou surpasser.
        algorithm_parameters (dict, optional): Paramètres spécifiques à l'algorithme, tels que le nombre de pas par paramètre (`nb_steps_per_parameter`) et le nombre total de répétitions (`nb_overall_repetitions`). Par défaut {}.
        send_results_update_to_ws (Optional[Callable[[dict], Awaitable[None]]], optional): Fonction asynchrone facultative permettant d'envoyer des mises à jour des résultats, par exemple à une interface WebSocket. Par défaut None.

    Raises:
        ConfigError: Erreur levée si des paramètres requis de l'algorithme ne sont pas présents dans `algorithm_parameters`.

    Returns:
        Tuple[dict, float]: Une paire contenant la configuration des hyperparamètres optimisés et le score de performance associé.
    """

    #
    def __init__(self, task: str, evaluation_function: Callable[[str, dict, dict], float], base_engine_config: dict, hyper_parameters_to_optimize: list[dict], benchmarks_to_optimize: dict[str, float], algorithm_parameters: dict = {}, send_results_update_to_ws: Optional[Callable[[dict], Awaitable[None]]] = None) -> None:
        super().__init__(task, evaluation_function, base_engine_config, hyper_parameters_to_optimize, benchmarks_to_optimize, send_results_update_to_ws=send_results_update_to_ws)

        # Vérifie que les paramètres requis pour l'algorithme de recherche linéaire sont présents dans `algorithm_parameters`
        for k in ["nb_steps_per_parameter", "nb_overall_repetitions"]:
            if not k in algorithm_parameters:
                raise ConfigError(f"No key {k} in conversation algorithm parameters : {algorithm_parameters} !")

        # Initialisation des attributs de l'algorithme en fonction des paramètres fournis
        self.nb_steps_per_parameter: int = int(algorithm_parameters["nb_steps_per_parameter"])
        self.nb_overall_repetitions: int = int(algorithm_parameters["nb_overall_repetitions"])

        # Initialisation des variables pour stocker les meilleures configurations trouvées
        self.best_optimized_hp: Optional[list[dict]] = None
        self.best_optimized_hp_values: Optional[list[float]] = None
        self.best_optimized_hp_score: Optional[float] = None

        # Initialisation des meilleures valeurs et scores pour chaque hyperparamètre individuellement
        self.best_optimized_value_per_parameter: list[float] = []
        self.best_optimized_value_per_parameter_scores: list[float] = []

        # Remplit les valeurs initiales avec la configuration de base
        for hp in self.hyper_parameters_to_optimize:
            self.best_optimized_value_per_parameter.append( get_value_from_config(base_engine_config, hp["keys"]) )

        # Évalue le score de la configuration de base
        score_base_config: float = self.evaluation_function(
                self.task,
                base_engine_config,
                self.benchmarks_to_optimize
        )

        # Remplit les scores initiaux avec le score de la configuration de base
        for hp in self.hyper_parameters_to_optimize:
            self.best_optimized_value_per_parameter_scores.append(score_base_config)

        # Initialisation du compteur d'itérations
        self.nb_iter = 0

    #
    async def optimize_linear_one_parameter(self, idx_param: int, current_deep: int = 0):
        """
        Optimise un seul hyperparamètre à la fois en utilisant une exploration linéaire.

        Args:
            idx_param (int): L'indice du paramètre à optimiser dans `hyper_parameters_to_optimize`.
            current_deep (int, optional): Profondeur actuelle de l'exploration. Par défaut 0.
        """

        # Génère les points à tester pour l'hyperparamètre courant
        points_to_test: list[np.ndarray] = linear_exploration(idx_param, self.best_optimized_value_per_parameter, self.hyper_parameters_to_optimize, self.nb_steps_per_parameter, current_deep)

        # Boucle sur chaque point généré pour évaluer sa performance
        for p in points_to_test:
            # Crée une configuration optimisée en appliquant les valeurs courantes des hyperparamètres
            optimized_hyper_parameters: list[dict] = [
                {
                    "keys": self.hyper_parameters_to_optimize[i]["keys"],
                    "value": p[i]
                }
                for i in range(len(self.hyper_parameters_to_optimize))
            ]

            # Met à jour la configuration de base avec les valeurs optimisées
            optimized_hyper_parameters_config = set_all_values_to_config(self.base_engine_config, optimized_hyper_parameters)

            # Évalue le score de la configuration optimisée
            score: float = self.evaluation_function(
                self.task,
                optimized_hyper_parameters_config,
                self.benchmarks_to_optimize
            )

            # Met à jour les meilleures valeurs pour le paramètre actuel si le score est meilleur
            if score > self.best_optimized_value_per_parameter_scores[idx_param]:
                self.best_optimized_value_per_parameter_scores[idx_param] = score
                self.best_optimized_value_per_parameter[idx_param] = p[idx_param]

            # Met à jour les meilleures valeurs globales si le score est meilleur
            if self.best_optimized_hp_score is None or score > self.best_optimized_hp_score:
                best_optimized_hp_score = score
                self.best_optimized_hp_values = p
                self.best_optimized_hp = optimized_hyper_parameters_config

            # Envoie des mises à jour des résultats si une fonction est fournie
            if self.send_results_update_to_ws is not None:
                await self.send_results_update_to_ws({
                    "iter": self.nb_iter,
                    "color": idx_param + len(self.best_optimized_value_per_parameter) * current_deep,
                    "score": score,
                    "config": optimized_hyper_parameters_config
                })

            # Incrément du compteur d'itérations
            self.nb_iter += 1


    #
    async def optimise(self) -> tuple[dict, float]:
        """
        Exécute l'optimisation en parcourant tous les hyperparamètres de manière linéaire.

        Returns:
            tuple[dict, float]: Les meilleures valeurs optimisées des hyperparamètres de la configuration et le score associé.
        """

        # Réinitialisation du compteur d'itérations
        self.nb_iter: int = 0

        # Boucle sur le nombre de répétitions globales
        for current_deep in range(self.nb_overall_repetitions):
            # Boucle sur chaque hyperparamètre à optimiser
            for idx_param in range(len(self.best_optimized_value_per_parameter)):
                # Optimise l'hyperparamètre courant
                await self.optimize_linear_one_parameter(idx_param, current_deep)

        # Retourne la meilleure configuration d'hyperparamètres trouvée et son score
        return self.best_optimized_hp, self.best_optimized_hp_score


#
def init_gaussian(I: tuple[list[float], list[float]], bell_center: np.ndarray, bell_center_function_value: float, average_value: float, minimal_value: float) -> float:
    """
    Initialise la valeur de sigma^2 pour avoir une gaussienne de valeur minimale min_v, de valeur moyenne avg_v, centrée en mu telle que G(mu) = mu_v.

    Args:
        I (tuple[list[float], list[float]]): domaine de définition
        mu (np.ndarray): vecteur dans I
        mu_v (float): valeur telle que G(mu) = mu_v
        avg_v (float): valeur moyenne souhaitée
        min_v (float): valeur minimale souhaitée

    Returns:
        float: La valeur déterminée de sigma^2 pour obtenir une telle fonction gaussienne.
    """

    n: int = len(I)
    # c_I: np.ndarray = np.array([float(I[i][1] - I[i][0])/2.0 for i in range(n)]) # Center of the space I
    # sigma_square: float = ( np.linalg.norm(c_I - bell_center) ** 2 ) / (2.0 * np.log( np.abs(bell_center_function_value - minimal_value) / np.abs(average_value - minimal_value)  ))

    #
    volume_I: float = 1.0
    for i in range(n):
        volume_I *= np.abs(I[i][1] - I[i][0])

    #
    numerator = volume_I * (average_value - minimal_value)
    denominator = bell_center_function_value - minimal_value
    sigma_square = (1 / (2 * np.pi)) * (numerator / denominator)**(2.0 / n)

    #
    def gaussian(x: np.ndarray) -> float:
        """
        Calcule la fonction min_v + mu_v * exp( - ( ||x - mu||² ) / (2.0 * sigma_square) )

        Args:
            x (np.ndarray): point à calculer
            mu (np.ndarray): centre de la gaussienne
            sigma_square (float): écart type au carré
            mu_v (float): valeur du centre de la gaussienne
            min_v (float): valeur minimale de la fonction

        Returns:
            float: résultat de la fonction
        """
        return minimal_value + (bell_center_function_value-minimal_value) * np.exp( - ( np.linalg.norm(x - bell_center) ** 2 ) / (2.0 * sigma_square) )

    return gaussian

#
class Gaussian_Exploration_Search_HPO_Algorithm(HPOptimisationAlgorithm):
    """
    Implémente un algorithme de recherche d'optimisation d'hyperparamètres basé sur l'exploration gaussienne.

    Cet algorithme combine une phase d'exploration initiale aléatoire et une phase d'exploration guidée par des
    fonctions gaussiennes pour trouver les meilleures configurations d'hyperparamètres.

    Args:
        HPOptimisationAlgorithm (class): Classe parent représentant un algorithme d'optimisation d'hyperparamètres.
        task (str): La tâche ou le contexte dans lequel les hyperparamètres doivent être optimisés.
        evaluation_function (Callable[[str, dict, dict], float]): Fonction d'évaluation qui retourne un score basé sur les hyperparamètres donnés.
        base_engine_config (dict): Configuration de base de l'algorithme ou du moteur à optimiser.
        hyper_parameters_to_optimize (list[dict]): Liste des hyperparamètres à optimiser, avec leurs plages de valeurs.
        benchmarks_to_optimize (dict[str, float]): Benchmarks de référence à optimiser.
        algorithm_parameters (dict, optional): Paramètres spécifiques à l'algorithme. Par défaut vide.
        send_results_update_to_ws (Optional[Callable[[dict], Awaitable[None]]], optional): Fonction de mise à jour des résultats en temps réel. Par défaut None.

    Raises:
        ConfigError: Erreur soulevée si des paramètres nécessaires à l'algorithme ne sont pas fournis.

    Returns:
        None
    """

    #
    def __init__(self, task: str, evaluation_function: Callable[[str, dict, dict], float], base_engine_config: dict, hyper_parameters_to_optimize: list[dict], benchmarks_to_optimize: dict[str, float], algorithm_parameters: dict = {}, send_results_update_to_ws: Optional[Callable[[dict], Awaitable[None]]] = None) -> None:
        super().__init__(task, evaluation_function, base_engine_config, hyper_parameters_to_optimize, benchmarks_to_optimize, send_results_update_to_ws=send_results_update_to_ws)

        # Vérification que tous les paramètres algorithmiques nécessaires sont présents
        for k in ["nb_init_iter", "nb_tot_iter", "nb_search_exploration", "expl_coef_non_expl", "expl_coef_good_score"]:
            if not k in algorithm_parameters:
                raise ConfigError(f"No key {k} in conversation algorithm parameters : {algorithm_parameters} !")

        # Initialisation des paramètres spécifiques à l'algorithme
        self.nb_init_iter: int = int(algorithm_parameters["nb_init_iter"])
        self.nb_tot_iter: int = int(algorithm_parameters["nb_tot_iter"])
        self.nb_search_exploration: int = int(algorithm_parameters["nb_search_exploration"])
        self.expl_coef_non_expl: float = float(algorithm_parameters["expl_coef_non_expl"])
        self.expl_coef_good_score: float = float(algorithm_parameters["expl_coef_good_score"])

        # Définition des intervalles pour chaque hyperparamètre
        self.pts_intervals: list[tuple[float, float]] = []
        #
        for hp in self.hyper_parameters_to_optimize:
            self.pts_intervals.append( (float(hp["value_min"]), float(hp["value_max"])) )

        # Calcul de la distance maximale entre les points dans l'espace des hyperparamètres
        self.max_pts_dist: float = np.linalg.norm(
            np.array([pt[0] for pt in self.pts_intervals]) - np.array([pt[1] for pt in self.pts_intervals])
        )

        # Initialisation des listes pour les points calculés et les fonctions gaussiennes
        self.calculated_points: list[tuple[np.ndarray, float]] = []
        self.gaussian_functions: list[Callable[[np.ndarray], float]] = []

    #
    def update_gaussian_functions(self) -> None:
        """
        Met à jour les fonctions gaussiennes basées sur les points calculés.

        Cette méthode crée une fonction gaussienne pour chaque point calculé, utilisant la valeur moyenne
        et la valeur minimale des points calculés pour ajuster la courbe.
        """

        # Réinitialisation des fonctions gaussiennes
        self.gaussian_functions = []
        nb_pts: int = len(self.calculated_points)
        if nb_pts == 0:
            return

        # Calcul des valeurs minimales et moyennes pour ajuster les fonctions gaussiennes
        value_min: float = 1.0
        avg_value: float = 0.0
        #
        for pt in self.calculated_points:
            if pt[1] < value_min:
                value_min = pt[1]
            avg_value += pt[1]
        avg_value /= float(nb_pts)

        # Création des fonctions gaussiennes pour chaque point calculé
        for pt in self.calculated_points:
            self.gaussian_functions.append(
                init_gaussian(
                    I=self.pts_intervals,
                    bell_center=pt[0],
                    bell_center_function_value=pt[1],
                    average_value=avg_value,
                    minimal_value=value_min
                )
            )

    #
    def main_model_estimation_evaluation_function(self, x: np.ndarray) -> float:
        """
        Évalue la qualité d'un point donné dans l'espace des hyperparamètres en utilisant une combinaison de fonctions gaussiennes.

        Args:
            x (np.ndarray): Point à évaluer dans l'espace des hyperparamètres.

        Returns:
            float: Score moyen basé sur l'évaluation des fonctions gaussiennes.
        """

        #
        score: float = 0
        #
        nb_fns: int = len(self.gaussian_functions)
        #
        if nb_fns == 0:
            return score

        # Somme des évaluations gaussiennes pour le point donné
        for fn in self.gaussian_functions:
            score += fn(x)
        #
        return score / float(nb_fns)

    #
    def exploration_function(self, x: np.ndarray) -> float:
        """
        Calcule un score combinant l'exploration de nouvelles régions de l'espace des hyperparamètres et l'exploitation des connaissances actuelles.

        Args:
            x (np.ndarray): Point à évaluer dans l'espace des hyperparamètres.

        Returns:
            float: Score d'exploration pour le point donné.
        """

        # Score d'exploration basé sur la distance par rapport aux points déjà explorés
        score_non_exploration: float = (sum([np.linalg.norm(x - pt[0]) for pt in self.calculated_points])) / (self.max_pts_dist * float(len(self.calculated_points)))

        # Score basé sur l'estimation des fonctions gaussiennes
        score_eval: float = self.main_model_estimation_evaluation_function(x)

        #
        return self.expl_coef_non_expl * score_non_exploration + self.expl_coef_good_score * score_eval

    #
    def random_point_in_param_space(self) -> np.ndarray:
        """
        Génère un point aléatoire dans l'espace des hyperparamètres.

        Returns:
            np.ndarray: Point aléatoire généré.
        """
        return np.array([
                rd_uniform(float(p["value_min"]), float(p["value_max"]))
                for p in self.hyper_parameters_to_optimize
            ])

    #
    def find_where_to_explore(self) -> np.ndarray:
        """
        Trouve le meilleur point à explorer dans l'espace des hyperparamètres en utilisant la fonction d'exploration.

        Returns:
            np.ndarray: Le point le plus prometteur à explorer.
        """
        #
        best_pt: Optional[np.ndarray] = None
        best_pt_score: Optional[float] = None

        # Teste plusieurs points aléatoires et garde celui avec le meilleur score d'exploration
        for _ in range(self.nb_search_exploration):
            pt: np.ndarray = self.random_point_in_param_space()
            score: float = self.exploration_function(pt)
            #
            if best_pt_score is None or score > best_pt_score:
                best_pt_score = score
                best_pt = pt
        #
        return best_pt

    #
    async def optimise(self) -> tuple[dict, float]:
        """
        Optimise les hyperparamètres en combinant une exploration initiale et une recherche guidée par des fonctions gaussiennes.

        Returns:
            dict: Configuration des hyperparamètres optimisés.
            float: Meilleur score obtenu avec cette configuration.
        """

        #
        self.calculated_points = []
        self.gaussian_functions = []

        #
        best_optimized_hp: Optional[list[dict]] = None
        best_optimized_hp_score: Optional[float] = None

        #
        nb_iter: int = 0

        # PHASE D'EXPLORATION INITIALE POUR AVOIR UNE BONNE ESTIMATION DE L'ESPACE
        for _ in range(self.nb_init_iter):
            #
            optimized_hyper_parameters: list[dict] = [
                {
                    "keys": p["keys"],
                    "value": rd_uniform(float(p["value_min"]), float(p["value_max"]))
                }
                for p in self.hyper_parameters_to_optimize
            ]

            #
            pt: np.ndarray = np.array([p["value"] for p in optimized_hyper_parameters])

            #
            optimized_hyper_parameters_config = set_all_values_to_config(self.base_engine_config, optimized_hyper_parameters)

            #
            score: float = self.evaluation_function(
                self.task,
                optimized_hyper_parameters_config,
                self.benchmarks_to_optimize
            )

            #
            self.calculated_points.append((pt, score))

            #
            if best_optimized_hp_score is None or score > best_optimized_hp_score:
                best_optimized_hp_score = score
                best_optimized_hp = optimized_hyper_parameters_config

            #
            if self.send_results_update_to_ws is not None:
                await self.send_results_update_to_ws({
                    "iter": nb_iter,
                    "color": 0,
                    "score": score,
                    "config": optimized_hyper_parameters_config
                })

            #
            nb_iter += 1

        # PHASE D'EXPLORATION ET DE RECHERCHE
        for _ in range(self.nb_tot_iter - self.nb_init_iter):
            #
            self.update_gaussian_functions()
            #
            pt: np.ndarray = self.find_where_to_explore()
            #
            optimized_hyper_parameters: list[dict] = [
                {
                    "keys": self.hyper_parameters_to_optimize[i]["keys"],
                    "value": float(pt[i])
                }
                for i in range(len(self.hyper_parameters_to_optimize))
            ]

            #
            optimized_hyper_parameters_config = set_all_values_to_config(self.base_engine_config, optimized_hyper_parameters)

            #
            score: float = self.evaluation_function(
                self.task,
                optimized_hyper_parameters_config,
                self.benchmarks_to_optimize
            )

            #
            self.calculated_points.append((pt, score))

            #
            if best_optimized_hp_score is None or score > best_optimized_hp_score:
                best_optimized_hp_score = score
                best_optimized_hp = optimized_hyper_parameters_config

            #
            if self.send_results_update_to_ws is not None:
                await self.send_results_update_to_ws({
                    "iter": nb_iter,
                    "color": 1,
                    "score": score,
                    "config": optimized_hyper_parameters_config
                })

            #
            nb_iter += 1

        #
        return best_optimized_hp, best_optimized_hp_score


#
class Gaussian_Exploration_Arround_Best_Found_Points_HPO_Algorithm(HPOptimisationAlgorithm):
    """
    Implémente un algorithme d'optimisation des hyperparamètres basé sur une exploration gaussienne autour des meilleurs points trouvés.

    Args:
        HPOptimisationAlgorithm (HPOptimisationAlgorithm): Classe mère dont hérite cette classe. 
        task (str): La tâche à optimiser.
        evaluation_function (Callable[[str, dict, dict], float]): Fonction d'évaluation utilisée pour estimer la performance des hyperparamètres.
        base_engine_config (dict): Configuration de base du moteur à optimiser.
        hyper_parameters_to_optimize (list[dict]): Liste des hyperparamètres à optimiser avec leurs valeurs minimales et maximales.
        benchmarks_to_optimize (dict[str, float]): Benchmarks ou objectifs à optimiser, sous forme de dictionnaire.
        algorithm_parameters (dict, optional): Paramètres spécifiques à l'algorithme, incluant le nombre d'itérations initiales, le nombre total d'itérations, etc.
        send_results_update_to_ws (Optional[Callable[[dict], Awaitable[None]]], optional): Fonction optionnelle pour envoyer les mises à jour des résultats en temps réel via WebSocket.

    Raises:
        ConfigError: Si un paramètre requis n'est pas présent dans `algorithm_parameters`.

    Returns:
        None: Cette classe ne retourne rien, mais produit les meilleurs hyperparamètres optimisés après l'exécution.
    """

    #
    def __init__(self, task: str, evaluation_function: Callable[[str, dict, dict], float], base_engine_config: dict, hyper_parameters_to_optimize: list[dict], benchmarks_to_optimize: dict[str, float], algorithm_parameters: dict = {}, send_results_update_to_ws: Optional[Callable[[dict], Awaitable[None]]] = None) -> None:
        super().__init__(task, evaluation_function, base_engine_config, hyper_parameters_to_optimize, benchmarks_to_optimize, send_results_update_to_ws=send_results_update_to_ws)

        # Vérifie que tous les paramètres nécessaires à l'algorithme sont fournis
        for k in ["nb_init_iter", "nb_tot_iter", "nb_search_exploration", "min_radius_exploration", "max_radius_exploration"]:
            if not k in algorithm_parameters:
                raise ConfigError(f"No key {k} in conversation algorithm parameters : {algorithm_parameters} !")

        # Initialise les paramètres spécifiques à l'algorithme
        self.nb_init_iter: int = int(algorithm_parameters["nb_init_iter"])
        self.nb_tot_iter: int = int(algorithm_parameters["nb_tot_iter"])
        self.nb_search_exploration: int = int(algorithm_parameters["nb_search_exploration"])
        self.min_radius_exploration: float = float(algorithm_parameters["min_radius_exploration"])
        self.max_radius_exploration: float = float(algorithm_parameters["max_radius_exploration"])

        # Initialisation des intervalles des points pour chaque hyperparamètre
        self.pts_intervals: list[tuple[float, float]] = []
        for hp in self.hyper_parameters_to_optimize:
            self.pts_intervals.append( (float(hp["value_min"]), float(hp["value_max"])) )

        # Calcul de la distance maximale entre les points dans l'espace des hyperparamètres
        self.max_pts_dist: float = np.linalg.norm(
            np.array([pt[0] for pt in self.pts_intervals]) - np.array([pt[1] for pt in self.pts_intervals])
        )

        # Initialisation des variables pour stocker les meilleurs points trouvés
        self.best_calculated_point: Optional[np.ndarray] = None
        self.best_calculated_point_score: Optional[float] = None
        self.calculated_points: list[tuple[np.ndarray, float]] = []
        self.gaussian_functions: list[Callable[[np.ndarray], float]] = []

    #
    def update_gaussian_functions(self) -> None:
        """
        Met à jour les fonctions gaussiennes basées sur les points calculés pour guider l'exploration.

        Cette méthode calcule une fonction gaussienne pour chaque point évalué, basée sur sa performance, 
        afin de favoriser l'exploration dans les zones prometteuses.
        """

        # Réinitialise la liste des fonctions gaussiennes
        self.gaussian_functions = []
        nb_pts: int = len(self.calculated_points)

        # Si aucun point n'a été calculé, on sort de la fonction
        if nb_pts == 0:
            return

        # Initialisation des variables pour calculer la valeur minimale et la valeur moyenne
        value_min: float = 1.0
        avg_value: float = 0.0

        # Calcul de la valeur minimale et de la moyenne des scores des points calculés
        for pt in self.calculated_points:
            if pt[1] < value_min:
                value_min = pt[1]
            avg_value += pt[1]
        avg_value /= float(nb_pts)

        # Création des fonctions gaussiennes pour chaque point calculé
        for pt in self.calculated_points:
            self.gaussian_functions.append(
                init_gaussian(
                    I=self.pts_intervals,
                    bell_center=pt[0],
                    bell_center_function_value=pt[1],
                    average_value=avg_value,
                    minimal_value=value_min
                )
            )

    #
    def main_model_estimation_evaluation_function(self, x: np.ndarray) -> float:
        """
        Évalue la performance estimée d'un point donné en utilisant la moyenne des fonctions gaussiennes.

        Args:
            x (np.ndarray): Point dans l'espace des hyperparamètres à évaluer.

        Returns:
            float: Score moyen de l'évaluation du point `x` par les fonctions gaussiennes.
        """

        #
        score: float = 0
        nb_fns: int = len(self.gaussian_functions)

        # Si aucune fonction gaussienne n'est définie, le score est nul
        if nb_fns == 0:
            return score

        # Somme les évaluations de toutes les fonctions gaussiennes
        for fn in self.gaussian_functions:
            score += fn(x)

        # Retourne la moyenne des scores
        return score / float(nb_fns)

    #
    def exploration_function(self, x: np.ndarray) -> float:
        """
        Fonction d'exploration pour évaluer un point dans l'espace des hyperparamètres.

        Args:
            x (np.ndarray): Point dans l'espace des hyperparamètres à explorer.

        Returns:
            float: Score estimé du point `x` basé sur la fonction d'évaluation principale.
        """

        #
        score_eval: float = self.main_model_estimation_evaluation_function(x)

        #
        return score_eval

    #
    def random_point_in_param_space(self) -> np.ndarray:
        """
        Génère un point aléatoire dans l'espace des hyperparamètres.

        Returns:
            np.ndarray: Point aléatoire généré dans l'espace des hyperparamètres.
        """
        return np.array([
                rd_uniform(float(p["value_min"]), float(p["value_max"]))
                for p in self.hyper_parameters_to_optimize
            ])

    #
    def random_point_around_p(self, p: np.ndarray, r: float) -> np.ndarray:
        """
        Génère un point aléatoire q autour du point p dans R^n
        à une distance r de p.

        Args:
        p (numpy.ndarray): Un point dans R^n.
        r (float): La distance entre p et le point aléatoire q.

        Returns:
        numpy.ndarray: Un point aléatoire q dans R^n à une distance r de p.
        """

        # La dimension
        n: int = p.shape[0]
        print(f"DEBUG | p = {p} | n = {n}")

        # Générer un vecteur gaussien aléatoire de dimension n
        v = np.random.normal(0, 1, n)

        # Normaliser le vecteur pour qu'il soit de norme 1
        u = v / np.linalg.norm(v)

        # Multiplier par le rayon r
        ru = r * u

        # Ajouter le point p pour obtenir q
        q = p + ru

        # On renvoie le résultat
        return q

    #
    def find_where_to_explore(self) -> np.ndarray:
        """
        Trouve le meilleur point à explorer dans l'espace des hyperparamètres en fonction des points déjà évalués.

        Returns:
            np.ndarray: Le prochain point à explorer dans l'espace des hyperparamètres.
        """
        #
        if self.best_calculated_point is None:
            return self.random_point_in_param_space()
        #
        best_pt: Optional[np.ndarray] = None
        best_pt_score: Optional[float] = None

        # Explore `nb_search_exploration` points autour du meilleur point calculé
        for _ in range(self.nb_search_exploration):
            r: float = rd_uniform(self.min_radius_exploration, self.max_radius_exploration)
            pt: np.ndarray = self.random_point_around_p(self.best_calculated_point, r)
            score: float = self.exploration_function(pt)
            # Met à jour le meilleur point trouvé lors de l'exploration
            if best_pt_score is None or score > best_pt_score:
                best_pt_score = score
                best_pt = pt
        #
        return best_pt

    #
    async def optimise(self) -> tuple[dict, float]:
        """
        Fonction principale de l'algorithme pour optimiser les hyperparamètres.

        Returns:
            tuple[dict, float]: Meilleure configuration des hyperparamètres et le score associé.
        """

        # Initialisation des points calculés et des fonctions gaussiennes
        self.calculated_points = []
        self.gaussian_functions = []

        #
        best_optimized_hp: Optional[list[dict]] = None
        best_optimized_hp_score: Optional[float] = None

        #
        nb_iter: int = 0

        # PHASE D'EXPLORATION INITIALE POUR AVOIR UNE BONNE ESTIMATION DE L'ESPACE
        for _ in range(self.nb_init_iter):
            #
            optimized_hyper_parameters: list[dict] = [
                {
                    "keys": p["keys"],
                    "value": rd_uniform(float(p["value_min"]), float(p["value_max"]))
                }
                for p in self.hyper_parameters_to_optimize
            ]

            #
            pt: np.ndarray = np.array([p["value"] for p in optimized_hyper_parameters])

            #
            optimized_hyper_parameters_config = set_all_values_to_config(self.base_engine_config, optimized_hyper_parameters)

            #
            score: float = self.evaluation_function(
                self.task,
                optimized_hyper_parameters_config,
                self.benchmarks_to_optimize
            )

            #
            self.calculated_points.append((pt, score))

            #
            if self.best_calculated_point_score is None or score > self.best_calculated_point_score:
                self.best_calculated_point_score = score
                self.best_calculated_point = pt

            #
            if best_optimized_hp_score is None or score > best_optimized_hp_score:
                best_optimized_hp_score = score
                best_optimized_hp = optimized_hyper_parameters_config

            #
            if self.send_results_update_to_ws is not None:
                await self.send_results_update_to_ws({
                    "iter": nb_iter,
                    "color": 0,
                    "score": score,
                    "config": optimized_hyper_parameters_config
                })

            #
            nb_iter += 1

        # PHASE D'EXPLORATION ET DE RECHERCHE
        for _ in range(self.nb_tot_iter - self.nb_init_iter):
            #
            self.update_gaussian_functions()
            #
            pt: np.ndarray = self.find_where_to_explore()
            #
            optimized_hyper_parameters: list[dict] = [
                {
                    "keys": self.hyper_parameters_to_optimize[i]["keys"],
                    "value": float(pt[i])
                }
                for i in range(len(self.hyper_parameters_to_optimize))
            ]

            #
            optimized_hyper_parameters_config = set_all_values_to_config(self.base_engine_config, optimized_hyper_parameters)

            #
            score: float = self.evaluation_function(
                self.task,
                optimized_hyper_parameters_config,
                self.benchmarks_to_optimize
            )

            #
            self.calculated_points.append((pt, score))

            #
            if self.best_calculated_point_score is None or score > self.best_calculated_point_score:
                self.best_calculated_point_score = score
                self.best_calculated_point = pt

            #
            if best_optimized_hp_score is None or score > best_optimized_hp_score:
                best_optimized_hp_score = score
                best_optimized_hp = optimized_hyper_parameters_config

            #
            if self.send_results_update_to_ws is not None:
                await self.send_results_update_to_ws({
                    "iter": nb_iter,
                    "color": 1,
                    "score": score,
                    "config": optimized_hyper_parameters_config
                })

            #
            nb_iter += 1

        #
        return best_optimized_hp, best_optimized_hp_score


#
"""
Format:

Dictionnaire des algorithmes d'optimisation{
    Nom de l'algorithme : (
        Classe de l'algorithme,
        Dictionnaire des paramètres de l'algorithme {
            nom_du_paramètre: (type_du_paramètre, valeur_par_défaut_du_paramètre)
        }
    )
}
"""
HPO_ALGORITHMS: dict[str, tuple[HPOptimisationAlgorithm, dict[str, tuple[str, str | int | float]]]] = {
    "Random_Search_HPO_Algorithm": (
        Random_Search_HPO_Algorithm, {
            "nb_iter": ("number", 10)
        }
    ),
    "Simple_Grid_Search_HPO_Algorithm": (
        Grid_Search_HPO_Algorithm, {
            "nb_grid_cuts": ("number", 5)
        }
    ),
    "Deep_Recursive_Grid_Search_HPO_Algorithm": (
        Grid_Search_HPO_Algorithm, {
            "nb_grid_cuts": ("number", 5),
            "deep_steps": ("number", 3)
        }
    ),
    "Linear_Individual_Search_HPO_Algorithm": (
        Linear_Individual_Search_HPO_Algorithm, {
            "nb_steps_per_parameter": ("number", 20),
            "nb_overall_repetitions": ("number", 2)
        }
    ),
    "Gaussian_Exploration_Search_HPO_Algorithm": (
        Gaussian_Exploration_Search_HPO_Algorithm, {
            "nb_init_iter": ("number", 20),
            "nb_tot_iter": ("number", 200),
            "nb_search_exploration": ("number", 1000),
            "expl_coef_non_expl": ("number", 1.0),
            "expl_coef_good_score": ("number", 2.0)
        }
    ),
    "Gaussian_Exploration_Arround_Best_Found_Points_HPO_Algorithm": (
        Gaussian_Exploration_Arround_Best_Found_Points_HPO_Algorithm,
        {
            "nb_init_iter": ("number", 20),
            "nb_tot_iter": ("number", 200),
            "nb_search_exploration": ("number", 1000),
            "min_radius_exploration": ("number", 0.01),
            "max_radius_exploration": ("number", 0.2)
        }
    )
}

HPO_ALGORITHMS_TO_SEND: dict[str, dict[str, tuple[str, str | int | float]]] = {}

for hk in HPO_ALGORITHMS:
    HPO_ALGORITHMS_TO_SEND[hk] = HPO_ALGORITHMS[hk][1]

