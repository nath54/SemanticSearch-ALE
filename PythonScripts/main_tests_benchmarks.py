"""
Ceci est un script à éxécuter pour lancer les évaluations de tests/benchmarks pour évaluer la vitesse et la précision des différentes configuration de moteur de recherche
Les modalités de sauvegarde des résultats seront encore à définir.

Auteur: Nathan Cerisara
"""

from typing import Optional, cast

import sys
import os
import json
import time
from torch import cuda

import cpuinfo
import GPUtil

from rainbow_instance import RainbowInstance
from message import MessageSearch, MessagePart, Message
from user import User
from search_engine import SearchEngine, SearchSettings, SearchAlgorithm
from conversations_engine import ConversationsEngine, ConversationsAlgorithm, ResultConversationCut
from ner_engine import NER_Engine, NER_Algorithm
from config import Config
from lib import avg, ConfigError, FunctionResult, ResultError, escapeCharacters
from lib import set_edit_distance, get_sequence_separations, get_tp_fp_fn_from_two_sets, get_f1_score_from_tp_fp_fn, hash_string_to_int

from global_variables import GlobalVariables, init_global_variables, get_global_variables, free_global_variables
from profiling import profiling_init, profiling_save_and_stop, profiling_task_start, profiling_last_task_ends


#
class TestBenchmarks:
    """
    Classe principale qui va gérer les tests de benchmarks
    """

    def __init__(self, skip_search: bool = False, skip_ner: bool = False, skip_conversation: bool = False) -> None:

        #
        self.skip_search: bool = skip_search
        self.skip_ner: bool = skip_ner
        self.skip_conversation: bool = skip_conversation

        # On va charger la configuration de ce projet
        self.conf: Config = Config("config.json")

        # On va gérer ici les RBI, que l'on chargera à la volée quand on en aura besoin
        self.loaded_rbis: dict[str, RainbowInstance] = {}

        # On va stocker ici le moteur de recherche que l'on est actuellement en train d'utiliser
        self.current_search_engine: Optional[SearchEngine] = None

        # On va stocker ici le moteur de NER que l'on est actuellement en train d'utiliser
        self.current_ner_engine: Optional[NER_Engine] = None

        # On va stocker ici le moteur de découpe des conversatoins que l'on est actuellement en train d'utiliser
        self.current_conversation_engine: Optional[ConversationsEngine] = None

        # On va stocker ici le dict de config pour le moteur de recherche actuel
        self.current_search_engine_dict: dict = {}

        # On va stocker ici le dict de config pour le moteur de NER actuel
        self.current_ner_engine_dict: dict = {}

        # On va stocker ici le dict de config pour le moteur de découpe de conversations actuel
        self.current_conversation_engine_dict: dict = {}

        # On va stocker ici les données de tests
        self.loaded_benchmarks: dict[str, dict] = {}

        # Résultats du benchmark
        self.benchmarks_results: dict[str, dict] = {}

        # Autres données supplémentaires sur les benchmarks
        self.benchmark_data: dict = {}

        # On prépare pour récupérer le nom de la machine support
        gpus = GPUtil.getGPUs()
        gpu_names: str = ""
        for gpu in gpus:
            # get the GPU id
            gpu_id = gpu.id
            # name of GPU
            gpu_name = gpu.name
            #
            if gpu_names != "":
                gpu_names += " - "
            gpu_names += f"{gpu_name}({gpu_id})"

        cpu_name: str = cpuinfo.get_cpu_info()["brand_raw"]

        # Nom de la machine support
        self.platform_name: str = f"CPU: {cpu_name} - GPU: {gpu_names}"

        # On charge ici tous les fichiers de benchmarks pour les benchmarks de recherche
        self.all_search_benchmarks_files: list[str] = []

        # On charge ici tous les fichiers de benchmarks pour les benchmarks de NER
        self.all_ner_benchmarks_files: list[str] = []

        # On charge ici tous les fichiers de benchmarks pour les benchmarks de découpe de conversation
        self.all_conversations_benchmarks_files: list[str] = []

        #
        for fn in os.listdir(self.conf.tests_benchmarks_paths):
            if fn.startswith("semantic_search"):
                self.all_search_benchmarks_files.append(fn)
            elif fn.startswith("NER"):
                self.all_ner_benchmarks_files.append(fn)
            elif fn.startswith("conversation"):
                self.all_conversations_benchmarks_files.append(fn)
            else:
                continue

            # On va charger le fichier de benchmark

            # Profiling 3 - start
            # profiling_task_start(f"loading_benchmark_file_[{escapeCharacters(fn)}]")

            with open(f"{self.conf.tests_benchmarks_paths}{fn}", encoding="utf-8") as f:
                self.loaded_benchmarks[fn] = json.load(f)

            # Profiling 3 - end
            # profiling_last_task_ends()

    #
    def save_benchmarks_results(self) -> None:
        """
        Enregistre les résultats des benchmarks dans un fichier de sauvegarde json et dans un script js (pour y avoir accès facilement depuis un script js de la webapp à la page des benchmarks)
        """

        # On convertit en json les résultats
        txt_dict_benchmark_results: str = json.dumps(self.benchmarks_results)

        # On enregistre dans le fichier json
        with open(self.conf.benchmark_results_path_json, "w", encoding="utf-8") as f:
            f.write(txt_dict_benchmark_results)

        # On va aussi enregistrer des données supplémentaires aux benchmarks

        # On convertit en json les données supplémentaires
        txt_dict_benchmark_data: str = json.dumps(self.benchmark_data)

        # On enregistre dans le fichier json
        with open(self.conf.benchmark_data_json, "w", encoding="utf-8") as f:
            f.write(txt_dict_benchmark_data)

        # On va exporter dans un script js pour que ce soit plus pratique
        txt_js: str = f"var benchmark_results = {txt_dict_benchmark_results};"

        txt_json: str

        #
        if "platforms_engines_config" in self.benchmark_data:
            txt_json= json.dumps(self.benchmark_data["platforms_engines_config"])
            txt_js += f"\n\nvar platforms_engines_config = {txt_json};"
        else:
            txt_js += "\n\nvar platforms_engines_config = { };"

        #
        if "benchmarks" in self.benchmark_data:
            txt_json = json.dumps(self.benchmark_data["benchmarks"])
            txt_js += f"\n\nvar benchmarks = {txt_json};"
        else:
            txt_js += "\n\nvar benchmarks = { };"

        # On enregistre dans le fichier js
        with open(self.conf.benchmark_results_path_js, "w", encoding="utf-8") as f:
            f.write(txt_js)

    #
    def load_benchmarks_results(self) -> None:
        """
        Charge le fichier de sauvegarde des résultats des benchmarks
        """

        # Si le fichier n'existe pas, pas besoin de le charger
        if os.path.exists(self.conf.benchmark_results_path_json):

            # On ouvre le fichier, et charge le dictionnaire à l'intérieur
            with open(self.conf.benchmark_results_path_json, "r", encoding="utf-8") as f:
                self.benchmarks_results = json.load(f)

        # Va aussi charger des données enregistrées supplémentaires pour les benchmarks

        # Test si le fichier existe
        if os.path.exists(self.conf.benchmark_data_json):

            # On ouvre le fichier, et charge le dictionnaire à l'intérieur
            with open(self.conf.benchmark_data_json, "r", encoding="utf-8") as f:
                self.benchmark_data = json.load(f)

    #
    def run_search_benchmark(self, benchmark_engine_name: str, benchmark_dict: dict, search_engine: SearchEngine) -> dict:
        """
        Effectue un benchmark donné avec un moteur de recherche donné.

        Args:
            benchmark_engine_name (str): Nom d'affichage du benchmark associé au nom du moteur de recherche
            benchmark_dict (dict): données du benchmark à tester
            search_engine (SearchEngine): moteur de recherche avec lequel on va faire les tests du benchmark

        Returns:
            dict: un dictionnaire contenant pleins d'infos sur les résultats du benchmarks
        """

        # On affiche ce que l'on fait dans la console
        print(f"\nRunning Benchmark : {benchmark_engine_name}...")

        # On va charger le rbi si pas déjà chargé
        if not benchmark_dict["rbi_path"] in self.loaded_rbis:

            # Profiling 0 - start
            # profiling_task_start(f"loading_rbi_[{escapeCharacters(benchmark_dict["rbi_path"])}]")

            # On va skipper les benchmarks dont on n'a pas les RBI nécessaires
            if not os.path.exists(f"{self.conf.base_path_rbi_converted_saved}{benchmark_dict['rbi_path']}"):
                print("RBI path doesn't exists, skipping benchmark...")
                raise FileNotFoundError(f"File doesn't exists : {self.conf.base_path_rbi_converted_saved}{benchmark_dict['rbi_path']}")

            # On charge la rbi
            rbi: RainbowInstance = RainbowInstance(benchmark_dict["rbi_path"], self.conf)
            res: FunctionResult = rbi.load()
            if isinstance(res, ResultError):
                raise UserWarning(res.error_message)
            self.loaded_rbis[benchmark_dict["rbi_path"]] = rbi

            # Profiling 0 - end
            # profiling_last_task_ends()


        # On récupère ici la RBI
        rbi: RainbowInstance = self.loaded_rbis[benchmark_dict["rbi_path"]]

        # On enregistrera ici tous les scores de précision pour chaque recherche
        search_scores: list[float] = []

        # On enregistrera ici la précision absolue de chaque recherche
        search_absolute_scores: list[float] = []

        # On enregistrera ici tous les temps de chacune des recherche
        time_searchs: list[float] = []

        # Liste des ids des messages résultats pour la recherche (on enregistre ca pour l'affichage du résultat du benchmark)
        list_results_ids: list[ list[tuple[float, int | tuple[int, int, int]]] ] = []

        # Liste des données des messages résultats pour la recherche (on enregistre ca pour l'affichage du résultat du benchmark)
        result_msgs: dict[str, dict] = {}

        # La liste des dictionnaires de ner à utiliser pour cette recherche
        ner_dicts: list[str] = []
        if "ner_dicts" in benchmark_dict:
            ner_dicts = benchmark_dict["ner_dicts"]

        # Pour chaque recherche dans le test
        for search in benchmark_dict["searchs"]:

            # Pour simplifier et rendre le code plus propre, on récupère les champs de la recherche à tester

            # On récupère le texte de la recherche
            if "search_input" not in search:
                raise ConfigError(f"Erreur dans le fichier de test/benchmark {benchmark_dict['title']}, la recherche {search} n'a pas d'attributs `search_input`")
            search_input: str = search["search_input"]

            # On récupère l'id de l'utilisateur avec lequel on va faire la recherche
            if "user_id" not in search:
                raise ConfigError(f"Erreur dans le fichier de test/benchmark {benchmark_dict['title']}, la recherche {search} n'a pas d'attributs `user_id`")
            user_id: str = str(search["user_id"])

            # On récupère le résultat voulu/attendu de la recherche
            if "awaited_result_message" not in search:
                raise ConfigError(f"Erreur dans le fichier de test/benchmark {benchmark_dict['title']}, la recherche {search} n'a pas d'attributs `awaited_result_message`")
            awaited_result_message: str | int | list[str | int] = search["awaited_result_message"]

            # On vérifie si l'utilisateur demandé est bel et bien dans la rbi du benchmark
            if not user_id in rbi.users:
                raise ValueError(f"Erreur Mauvaise Valeur dans le benchmark {benchmark_dict['title']}, la RBI ne possède pas d'utilisateurs avec l'id {user_id}.\nTest de recherche problématique : {search}")
            user: User = rbi.users[user_id]

            # On effectue la recherche, tout en évaluant le temps total pris par la recherche
            t1: float = time.time()
            search_results: list[tuple[float, MessageSearch]] = search_engine.search_main(rbi, search_input, user, SearchSettings(), ner_dicts=ner_dicts)
            tt: float = time.time() - t1

            # On récupère la liste des id des messages résultats
            d: float
            ms: MessageSearch
            results_ids: list[tuple[float, str | tuple[str, int, int]]] = []
            for (d, ms) in search_results:
                #
                if len(ms.msg_pointing) == 0:
                    continue
                #
                if ms.msg_pointing[0].part is None:
                    results_ids.append( (d, ms.msg_pointing[0].msg_id) )
                else:
                    results_ids.append( (d, (ms.msg_pointing[0].msg_id, ms.msg_pointing[0].part[0], ms.msg_pointing[0].part[1]) ) )

            # On récupère les données des messages pour pouvoir les afficher dans la page d'affichage des benchmarks, car pas d'accès aux rbis là-bas.
            for rid in results_ids:
                # Cas où c'est une id qui pointe directement sur un message en entier
                if isinstance(rid[1], int) or isinstance(rid[1], str):
                    #
                    if not rid[1] in result_msgs:
                        result_msgs[rid[1]] = rbi.messages[rid[1]].export_to_dict()
                # Cas où c'est une id qui pointe vers une partie d'un message
                elif isinstance(rid[1], tuple):
                    #
                    if not rid[1][0] in result_msgs:
                        result_msgs[rid[1][0]] = rbi.messages[rid[1][0]].export_to_dict()

            # On ajoute ces données dans les bonnes listes correspondantes
            list_results_ids.append(results_ids)

            # On enregistre le temps pris par la recherche
            time_searchs.append(tt)

            # definition de certaines variables que l'on va utiliser de chaque côté de la condition
            corresponding_message: bool = False
            position_result: int
            result: tuple[float, MessageSearch]

            # définition de cette variable qui va être utilisée des deux côtés de la condition
            msg_part: MessagePart

            # On va maintenant calculer le score de précision de ce résultat de recherche

            # Si on attends qu'un seul message
            if isinstance(awaited_result_message, int | str):
                # Pour cela, on va chercher la position du message voulu dans le résultat de recherche
                position_wanted_message: int = -1

                # On parcours les résultats avec leurs positions
                for (position_result, result) in enumerate(search_results):

                    # Sert à savoir si c'était le message que l'on voulait ou pas
                    corresponding_message: bool = False

                    # On parcourt chaque potentielle partie de réponse
                    for msg_part in result[1].msg_pointing:
                        # Selon le type de la variable awaited_result_message, on teste si l'id du résultat correspond à l'id du message voulu
                        if isinstance(awaited_result_message, int):
                            if int(msg_part.msg_id) == awaited_result_message:
                                corresponding_message = True
                                break
                        elif isinstance(awaited_result_message, str):
                            if msg_part.msg_id == awaited_result_message:
                                corresponding_message = True
                                break

                    # Si le message correspond, on indique la position d'où on l'a trouvé
                    if corresponding_message:
                        position_wanted_message = position_result
                        break

                # Si le résultat de recherche n'a pas été trouvé, on met le score le plus bas possible
                if position_wanted_message < 0:
                    search_scores.append(0)
                    search_absolute_scores.append(-1)
                # Sinon, on met un score plus ou moins grand selon le temps que l'on a mit pour trouver le message voulu
                else:
                    search_scores.append( 1.0/(position_wanted_message+1.0) )
                    search_absolute_scores.append(position_wanted_message)

            # Si on attends plusieurs messages
            elif isinstance(awaited_result_message, list):

                awaited_msgs: list[int | str] = awaited_result_message

                is_continuous_list: bool = True
                try:
                    awaited_min_msg_id: int = min(awaited_msgs)
                    awaited_max_msg_id: int = max(awaited_msgs)
                    if awaited_max_msg_id != awaited_min_msg_id + 1:
                        awaited_msg_ids: set[int] = set(awaited_msgs)
                        for i in range(awaited_min_msg_id+1, awaited_max_msg_id):
                            if not i in awaited_msg_ids:
                                is_continuous_list = False
                                break
                except:
                    is_continuous_list = False

                position_all_wanted_msgs: list[int] = [-1] * len(awaited_msgs)

                nb_msgs_intermediate: float = 0
                result_nb_msgs_intermediate_importance: float = 1.0

                # Pour chaque résultat
                for (position_result, result) in enumerate(search_results):

                    # On indique d'abord qu'il ne correspond pas
                    corresponding_message = False

                    # On parcourt tout les messages pointés par ce résultat
                    for msg_part in result[1].msg_pointing:

                        # Si le résultat pointe vers un des messages que l'on attendait
                        if int(msg_part.msg_id) in awaited_msgs or msg_part.msg_id in awaited_msgs:

                            # On indique que ce message correspond bien
                            corresponding_message = True

                            # On récupère l'index du résultat
                            idx: int = awaited_msgs.index(int(msg_part.msg_id))
                            if idx == -1:
                                idx = awaited_msgs.index(msg_part.msg_id)

                            # Pour indiquer que ce résultat a été trouvé
                            if position_all_wanted_msgs[idx] == -1:
                                position_all_wanted_msgs[idx] = position_result

                                # On réduit aussi l'importance de l'attente des prochains résultats vu que l'on a déjà trouvé un des résultats
                                result_nb_msgs_intermediate_importance /= 5.0

                    # Si le message ne correspond pas
                    if not corresponding_message:
                        nb_msgs_intermediate += 1.0 * result_nb_msgs_intermediate_importance

                    # Si le message correspond
                    else:

                        # Si la liste est continue
                        if is_continuous_list:
                            # On indique que tout a été trouvé à la position actuelle
                            for i in range(len(position_all_wanted_msgs)):
                                position_all_wanted_msgs[i] = position_result
                            # On arrête
                            break

                        # Si tout a été trouvé
                        if all([p != -1 for p in position_all_wanted_msgs]):
                            # On arrête
                            break

                #
                nb_awaited: float = float(len(awaited_msgs))

                # Si tous les résultats de recherche n'a pas été trouvé, on met le score le plus bas possible
                if any([p == -1 for p in position_all_wanted_msgs]):
                    search_scores.append( nb_awaited / (nb_msgs_intermediate+nb_awaited) )
                    search_absolute_scores.append(nb_msgs_intermediate)

                # Sinon, on met le score
                else:
                    search_scores.append( nb_awaited / (nb_msgs_intermediate+nb_awaited) )
                    search_absolute_scores.append(nb_msgs_intermediate)

            # Le benchmark est erroné, corrompu, ou bien ce code n'est pas à jour
            else:
                search_scores.append(0)
                search_absolute_scores.append(-1)

        # On calcule le score moyen
        avg_score: float = avg(search_scores)

        # On calcule le temps total du benchmark
        tot_time: float = sum(time_searchs)

        #
        print(f"Benchmark done : {tot_time} sec - average score : {avg_score}")

        # On renvoie les résultats
        return {
            "platform_name": self.platform_name,
            "benchmark_name": benchmark_dict['title'],
            "search_engine_name": search_engine.config_name,
            "avg_score": avg_score,
            "absolute_scores": search_absolute_scores,
            "search_times": time_searchs,
            "total_benchmark_time": tot_time,
            "result_ids": list_results_ids,
            "result_msgs": result_msgs
        }

    #
    def benchmark_current_search_engine_and_test(self, tests_benchmarks_file: str, can_skip: bool = True) -> None:
        """
        On va faire tourner le benchmark demandé sur le moteur de recherche actuel

        Args:
            tests_benchmarks_file (str): Fichier du benchmark à faire

        Raises:
            ConfigError: Erreur de configuration, manque de clé
            ConfigError: Erreur de configuration, manque de clé
            ValueError: Erreur de valeur de user id dans la rbi
        """

        #
        if self.current_search_engine is None:
            print("Error search engine is None, skipping...")
            return

        # benchmark&engine name
        benchmark_engine_name: str = "search_benchmark - " + self.loaded_benchmarks[tests_benchmarks_file]["title"] + " - search engine - " + self.current_search_engine.config_name + " | " + self.platform_name

        # On ne va pas faire un benchmark que l'on a déjà fait
        if benchmark_engine_name in self.benchmarks_results:

            # On ne va skipper que si le benchmark est différent quand même
            if can_skip and "benchmarks" in self.benchmark_data and benchmark_engine_name in self.benchmark_data["benchmarks"] and self.loaded_benchmarks[tests_benchmarks_file] == self.benchmark_data["benchmarks"][benchmark_engine_name]:

                # On affiche ce que l'on fait dans la console
                print(f"\nSkipping Benchmark : {benchmark_engine_name}")

                return

        # On ajoute le résultat du benchmark aux résultats
        self.benchmarks_results[benchmark_engine_name] = self.run_search_benchmark(benchmark_engine_name, self.loaded_benchmarks[tests_benchmarks_file], self.current_search_engine)

        # On va aussi ajouter des données supplémentaires au données de benchmarks

        # On enregistre le benchmark testé
        if not "benchmarks" in self.benchmark_data:
            self.benchmark_data["benchmarks"] = {}

        # On enregistre si le benchmark n'a jamais été enregistré, ou si le benchmark a été mis à jour depuis la dernière fois
        if not benchmark_engine_name in self.benchmark_data["benchmarks"] or self.benchmark_data["benchmarks"][benchmark_engine_name] != self.loaded_benchmarks[tests_benchmarks_file]:
            self.benchmark_data["benchmarks"][benchmark_engine_name] = self.loaded_benchmarks[tests_benchmarks_file]
            self.benchmark_data["benchmarks"][self.loaded_benchmarks[tests_benchmarks_file]["title"]] = self.loaded_benchmarks[tests_benchmarks_file]

    #
    def run_search_tests(self) -> None:
        """
        Point d'entrée pour lancer tous les benchmarks sur tous les moteurs de recherches

        Raises:
            UserWarning: Erreur de chargement d'une RBI
        """

        print("\n\nSearch Tests.\n\n")

        # Profiling 1 - start
        # profiling_task_start("loading_previous_results")

        # On va charger les résultats précédents de benchmarks
        self.load_benchmarks_results()

        # Profiling 1 - end
        # profiling_last_task_ends()

        # Profiling 1 - start
        # profiling_task_start("run_for_all_engine_configs")

        # On va parcourir chaque fichier de configuration
        engine_config_file: str
        for engine_config_file in os.listdir(self.conf.search_engine_configs_paths):

            # On ne traite pas les fichiers de configurations cachés, où les autres fichiers qui peuvent ne pas être de la config, et dont on ne sait pas pourquoi ils sont là
            if engine_config_file.startswith(".") or not engine_config_file.endswith(".json"):
                continue

            # Profiling 2 - start
            # profiling_task_start(f"loading_engine_config_file_[{engine_config_file}]")

            # On va charger le fichier de configuration du moteur de recherche
            self.current_search_engine_dict = {}
            with open(f"{self.conf.search_engine_configs_paths}{engine_config_file}", encoding="utf-8") as f:
                self.current_search_engine_dict = json.load(f)

            # Pour cette configuration de moteur de recherche, on regarde s'il y a besoin d'avoir cuda ou pas
            cuda_needed: bool = False
            algo: dict
            for algo in self.current_search_engine_dict["algorithms"]:
                if "use_cuda" in algo and int(algo["use_cuda"]) == 1:
                    cuda_needed = True
                    break

            # S'il y a besoin de cuda, on teste si cuda est disponible
            if cuda_needed:
                if not cuda.is_available():
                    print(f"\nSkipping tests on engine config {self.current_search_engine_dict['config_name']} because cuda is needed but not available")

                    # Profiling 2 - end
                    # profiling_last_task_ends()

                    continue

            # Profiling 2 - end
            # profiling_last_task_ends()

            # Profiling 2 - start
            # profiling_task_start(f"create_search_engine_[{escapeCharacters(engine_config_file)}]")

            # On va créer le moteur de recherche associé à cette configuration
            self.current_search_engine = SearchEngine(self.current_search_engine_dict, self.conf)

            # Profiling 2 - end
            # profiling_last_task_ends()

            # Sert à empêcher de skipper un benchmark si une config de moteur de recherche n'a pas déjà été enregistrée, ou est différente de ce qui avait été enregistré
            can_skip: bool = True

            # On enregistre la configuration du moteur de recherche pour la machine support actuelle
            if not "platforms_engines_config" in self.benchmark_data:
                self.benchmark_data["platforms_engines_config"] = {}
                can_skip = False

            if not self.platform_name in self.benchmark_data["platforms_engines_config"]:
                self.benchmark_data["platforms_engines_config"][self.platform_name] = {}
                can_skip = False

            if not self.current_search_engine.config_name in self.benchmark_data["platforms_engines_config"][self.platform_name] or self.benchmark_data["platforms_engines_config"][self.platform_name][self.current_search_engine.config_name] != self.current_search_engine_dict:
                self.benchmark_data["platforms_engines_config"][self.platform_name][self.current_search_engine.config_name] = self.current_search_engine_dict
                can_skip = False

            # Profiling 2 - start
            # profiling_task_start(f"run_for_all_benchmarks_files_[{escapeCharacters(engine_config_file)}]")

            # On va parcourir chaque fichier de tests
            tests_benchmarks_file: str
            for tests_benchmarks_file in self.all_search_benchmarks_files:

                # On va charger le fichier de test
                if not tests_benchmarks_file in self.loaded_benchmarks:

                    # Profiling 3 - start
                    # profiling_task_start(f"loading_benchmark_file_[{escapeCharacters(tests_benchmarks_file)}]")

                    with open(f"{self.conf.tests_benchmarks_paths}{tests_benchmarks_file}", encoding="utf-8") as f:
                        self.loaded_benchmarks[tests_benchmarks_file] = json.load(f)

                    # Profiling 3 - end
                    # profiling_last_task_ends()

                # On va charger le rbi si pas déjà chargé
                if not self.loaded_benchmarks[tests_benchmarks_file]["rbi_path"] in self.loaded_rbis:

                    # Profiling 3 - start
                    # profiling_task_start(f"loading_rbi_[{escapeCharacters(self.loaded_benchmarks[tests_benchmarks_file]["rbi_path"])}]")

                    # On va skipper les benchmarks dont on n'a pas les RBI nécessaires
                    if not os.path.exists(f"{self.conf.base_path_rbi_converted_saved}{self.loaded_benchmarks[tests_benchmarks_file]['rbi_path']}"):
                        print("RBI path doesn't exists, skipping benchmark...")
                        continue

                    #
                    rbi: RainbowInstance = RainbowInstance(self.loaded_benchmarks[tests_benchmarks_file]["rbi_path"], self.conf)
                    res: FunctionResult = rbi.load()
                    if isinstance(res, ResultError):
                        raise UserWarning(res.error_message)
                    self.loaded_rbis[self.loaded_benchmarks[tests_benchmarks_file]["rbi_path"]] = rbi

                    # Profiling 3 - end
                    # profiling_last_task_ends()

                # Profiling 3 - start
                # profiling_task_start(f"run_benchmark_[{escapeCharacters(tests_benchmarks_file)}]_[{engine_config_file}]")

                # On va lancer le test
                self.benchmark_current_search_engine_and_test(tests_benchmarks_file, can_skip)

                # Profiling 3 - end
                # profiling_last_task_ends(f"benchmark : {tests_benchmarks_file} by engine : {engine_config_file}")

            # Profiling 2 - end
            # profiling_last_task_ends()

            # Nettoyage
            self.current_search_engine = None
            self.current_search_engine_dict = {}

        # Profiling 1 - end
        # profiling_last_task_ends()

    #
    def evaluate_ner(self,
                     message: str,
                     correct_ners: list[tuple[int, str, str]],
                     algo_ners: list[tuple[int, str, str]]) -> dict[str, float]:
        """
        Evaluate NER algorithm performance against a benchmark.

        Args:
            message (str): input message.
            correct_ners (list[tuple[int, str, str]]): List of correct NER results.
            algo_ners (list[tuple[int, str, str]]): List of algorithm NER results.

        Returns:
            dict[str, float]: message scores
        """

        true_positives: float = 0.0
        # Calcul des vrais positifs
        for rn in algo_ners:
            bon: bool = False
            for cn in correct_ners:
                if rn[0] == cn[0] and rn[1] == cn[1] and (rn[2] == "" or rn[2] == cn[2]):
                    bon = True
                    break
            #
            if bon:
                true_positives += 1
        #
        false_positives: float = 0.0 + len(algo_ners) - true_positives
        false_negatives: float = 0.0 + len(correct_ners) - true_positives

        precision: float = true_positives / (true_positives + false_positives) if true_positives + false_positives > 0.0 else 0.0
        recall: float = true_positives / (true_positives + false_negatives) if true_positives + false_negatives > 0.0 else 0.0
        f1_score: float = 2 * (precision * recall) / (precision + recall) if precision + recall > 0.0 else 0.0

        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score
        }

    #
    def run_ner_benchmark(self, benchmark_engine_name: str, benchmark_dict: dict, ner_engine: NER_Engine) -> dict:
        """_summary_

        Args:
            benchmark_engine_name (str): _description_
            benchmark_dict (dict): _description_
            ner_engine (NER_Engine): _description_

        Returns:
            dict: _description_
        """

        # On affiche ce que l'on fait dans la console
        print(f"\nRunning Benchmark : {benchmark_engine_name}...")

        # Pour calculer le temps total du benchmark
        deb_time: float = time.time()

        #
        f1_scores: list[float] = []
        per_msg_scores: list[dict[str, float]] = []
        msg_ner_results: list[list[tuple[int, str, str]]] = []

        #
        for test in benchmark_dict["tests"]:
            text: str = test["text"]
            correct_ner: list[tuple[int, str, str]] = [cast(tuple[int, str, str], tuple(t)) for t in test["entities"]]
            #
            algo_ner: list[tuple[int, str, str]] = ner_engine.main_recognize(text)
            msg_ner_results.append(algo_ner)
            #
            msg_score: dict[str, float] = self.evaluate_ner(text, correct_ner, algo_ner)
            #
            per_msg_scores.append(msg_score)
            #
            f1_scores.append(msg_score["f1_score"])

        #
        macro_avg_f1: float = float(sum(f1_scores)) / float(len(f1_scores)) if len(f1_scores) > 0 else 0.0

        # On calcule le temps total du benchmark
        tot_time: float = time.time() - deb_time

        print(f"Benchmark done : {tot_time} sec - average score : {macro_avg_f1}")

        # On renvoie les résultats
        return {
            "platform_name": self.platform_name,
            "benchmark_name": benchmark_dict['title'],
            "ner_engine_name": ner_engine.config_name,
            "time": tot_time,
            "macro_avg_f1": macro_avg_f1,
            "per_msg_scores": per_msg_scores,
            "msg_ner_results": msg_ner_results
        }

    #
    def benchmark_current_ner_engine_and_test(self, tests_benchmarks_file: str, can_skip: bool = True) -> None:
        """
        On va faire tourner le benchmark demandé sur le moteur de NER actuel

        Args:
            tests_benchmarks_file (str): Fichier du benchmark à faire
        """

        if self.current_ner_engine is None:
            return

        # benchmark&engine name
        benchmark_engine_name: str = "ner_benchmark - " + self.loaded_benchmarks[tests_benchmarks_file]["title"] + " - ner engine - " + self.current_ner_engine.config_name + " | " + self.platform_name

        # On ne va pas faire un benchmark que l'on a déjà fait
        if benchmark_engine_name in self.benchmarks_results:

            # On ne va skipper que si le benchmark est différent quand même
            if can_skip and "benchmarks" in self.benchmark_data and benchmark_engine_name in self.benchmark_data["benchmarks"] and self.loaded_benchmarks[tests_benchmarks_file] == self.benchmark_data["benchmarks"][benchmark_engine_name]:

                # On affiche ce que l'on fait dans la console
                print(f"\nSkipping Benchmark : {benchmark_engine_name}")
                return

        # On ajoute le résultat du benchmark aux résultats
        self.benchmarks_results[benchmark_engine_name] = self.run_ner_benchmark(benchmark_engine_name, self.loaded_benchmarks[tests_benchmarks_file], self.current_ner_engine)

        # On enregistre le benchmark testé
        if not "benchmarks" in self.benchmark_data:
            self.benchmark_data["benchmarks"] = {}

        # On enregistre si le benchmark n'a jamais été enregistré, ou si le benchmark a été mis à jour depuis la dernière fois
        if not benchmark_engine_name in self.benchmark_data["benchmarks"] or self.benchmark_data["benchmarks"][benchmark_engine_name] != self.loaded_benchmarks[tests_benchmarks_file]:
            self.benchmark_data["benchmarks"][benchmark_engine_name] = self.loaded_benchmarks[tests_benchmarks_file]
            self.benchmark_data["benchmarks"][self.loaded_benchmarks[tests_benchmarks_file]["title"]] = self.loaded_benchmarks[tests_benchmarks_file]

    #
    def run_NER_tests(self) -> None:
        """
        Point d'entrée pour lancer tous les benchmarks sur tous les moteurs de NER
        """

        print("\n\nNER Tests.\n\n")

        # On va parcourir chaque fichier de configuration
        engine_config_file: str
        for engine_config_file in os.listdir(self.conf.ner_engine_configs_paths):

            # On va charger le fichier de configuration du moteur de NER
            self.current_ner_engine_dict = {}
            with open(f"{self.conf.ner_engine_configs_paths}{engine_config_file}", encoding="utf-8") as f:
                self.current_ner_engine_dict = json.load(f)

            # On va créer le moteur de NER associé à cette configuration
            self.current_ner_engine = NER_Engine(self.current_ner_engine_dict, self.conf)

            # Indique si l'on peut skipper ou pas des benchmarks avec ce moteur
            can_skip: bool = True

            # On enregistre la configuration du moteur de recherche pour la machine support actuelle
            if not "platforms_engines_config" in self.benchmark_data:
                self.benchmark_data["platforms_engines_config"] = {}
                can_skip = False

            if not self.platform_name in self.benchmark_data["platforms_engines_config"]:
                self.benchmark_data["platforms_engines_config"][self.platform_name] = {}
                can_skip = False

            if not self.current_ner_engine.config_name in self.benchmark_data["platforms_engines_config"][self.platform_name] or self.benchmark_data["platforms_engines_config"][self.platform_name][self.current_ner_engine.config_name] != self.current_ner_engine_dict:
                self.benchmark_data["platforms_engines_config"][self.platform_name][self.current_ner_engine.config_name] = self.current_ner_engine_dict
                can_skip = False

            # On va parcourir chaque fichier de tests
            tests_benchmarks_file: str
            for tests_benchmarks_file in self.all_ner_benchmarks_files:

                # On va charger le fichier de test
                if not tests_benchmarks_file in self.loaded_benchmarks:

                    with open(f"{self.conf.tests_benchmarks_paths}{tests_benchmarks_file}", encoding="utf-8") as f:
                        self.loaded_benchmarks[tests_benchmarks_file] = json.load(f)

                # On va lancer les tests
                self.benchmark_current_ner_engine_and_test(tests_benchmarks_file, can_skip)

            # Nettoyage
            self.current_ner_engine = None
            self.current_ner_engine_dict = {}

    #
    def run_conversation_cut_benchmark(self, benchmark_engine_name: str, benchmark_dict: dict, conversation_engine: ConversationsEngine) -> dict:
        """
        _summary_

        Args:
            benchmark_engine_name (str): _description_
            benchmark_dict (dict): _description_
            conversation_engine (ConversationsEngine): _description_

        Returns:
            dict: _description_
        """

        # On affiche ce que l'on fait dans la console
        print(f"\nRunning Benchmark : {benchmark_engine_name}...")

        # Pour calculer le temps total du benchmark
        deb_time: float = time.time()

        # TODO: implémenter la découpe de messages en plusieurs morceaux pour des longs messages dont plusieurs parties peuvent appartenir à plusieurs discussions différentes

        # On va récupérer la liste des messages à donner à l'algo
        msgs_dict: dict[str, Message] = {}
        for m in benchmark_dict["messages"]:
            msgs_dict[m["id"]] = Message()
            msgs_dict[m["id"]].id = m["id"]
            msgs_dict[m["id"]].date = m["date"]
            msgs_dict[m["id"]].content = m["content"]
            msgs_dict[m["id"]].author_id = hash_string_to_int(m["author"])
            msgs_dict[m["id"]].author_name = m["author"]
            msgs_dict[m["id"]].answered_message_id = m["answer_message"]

        # On va récupérer tous les messages en une seule liste
        msgs: list[str] = [m["content"] for m in benchmark_dict["messages"]]

        # Définition pour les deux boucles
        id_msg: str | list[str]

        # On va récupérer la "coloration" de chaque message
        correct_msgs_cl: dict[str, int] = {}
        for cl in range(len(benchmark_dict["conversation_results"])):

            for id_msg in benchmark_dict["conversation_results"][cl]:
                # TODO: découpe de messages
                if isinstance(id_msg, list):
                    id_msg = id_msg[0]

                correct_msgs_cl[str(id_msg)] = cl

        if conversation_engine is None:
            return

        # On va calculer la "coloration" par le moteur de découpe actuellement testé
        algo_results: ResultConversationCut = conversation_engine.main_cut(msgs_dict)

        # On va récupérer la "coloration" de chaque message de l'algorithme
        algo_msgs_cl: dict[str, int] = {}
        for cl in range(len(algo_results.conversations_msgs)):
            #
            id_message: str | MessagePart
            for id_message in algo_results.conversations_msgs[cl]:
                # TODO: découpe de messages
                if isinstance(id_message, MessagePart):
                    id_message = id_message.msg_id

                algo_msgs_cl[str(id_message)] = cl

        #
        values_correct_msgs_cl: list[int] = [correct_msgs_cl[str(k)] for k in sorted([int(kk) for kk in correct_msgs_cl.keys()])]
        values_algo_msgs_cl: list[int] = [algo_msgs_cl[str(k)] for k in sorted([int(kk) for kk in algo_msgs_cl.keys()])]

        # On va calculer le score de séparation
        sep_correct: set[int] = get_sequence_separations(values_correct_msgs_cl)
        sep_algo: set[int] = get_sequence_separations(values_algo_msgs_cl)

        tp: int # True Positives
        fp: int # False Positives
        fn: int # False Negatives
        tp, fp, fn = get_tp_fp_fn_from_two_sets(sep_correct, sep_algo)
        f1_score_separations: float = get_f1_score_from_tp_fp_fn(tp, fp, fn)

        # TODO: gérer les messages découpés
        # On va calculer la distance d'édition des sous-ensembles de conversations
        edit_distance_conversations: float = set_edit_distance(benchmark_dict["conversation_results"], [[r.msg_id if isinstance(r, MessagePart) else r for r in res] for res in algo_results.conversations_msgs])

        edit_distance_conversations = (float(len(msgs))) / (float(len(msgs)) + edit_distance_conversations)

        #
        final_score: float = (f1_score_separations + edit_distance_conversations) / 2.0

        # On calcule le temps total du benchmark
        tot_time: float = time.time() - deb_time

        #
        print(f"Benchmark done : {tot_time} sec - average score : {final_score}")

        # On renvoie les résultats
        results: dict = {
            "platform_name": self.platform_name,
            "benchmark_name": benchmark_dict['title'],
            "conversation_engine_name": conversation_engine.config_name,
            "correct_msgs_cl": correct_msgs_cl,
            "algo_msgs_cl": algo_msgs_cl,
            "time": tot_time,
            "score": final_score,
            "f1_score_separations": f1_score_separations,
            "edit_distance_conversations": edit_distance_conversations
        }

        if algo_results.distances_matrix is not None:
            results["distances_matrix"] = algo_results.distances_matrix.tolist()

        #
        return results

    #
    def benchmark_current_conversation_engine_and_test(self, tests_benchmarks_file: str, can_skip: bool = True) -> None:
        """
        On va faire tourner le benchmark demandé sur le moteur de découpe des conversations actuel

        Args:
            tests_benchmarks_file (str): Fichier du benchmark à faire
        """

        if self.current_conversation_engine is None:
            return

        # benchmark&engine name
        benchmark_engine_name: str = "conversation_benchmark - " + self.loaded_benchmarks[tests_benchmarks_file]["title"] + " - conversation engine - " + self.current_conversation_engine.config_name + " | " + self.platform_name

        # On ne va pas faire un benchmark que l'on a déjà fait
        if benchmark_engine_name in self.benchmarks_results:

            # On ne va skipper que si le benchmark est différent quand même
            if can_skip and "benchmarks" in self.benchmark_data and benchmark_engine_name in self.benchmark_data["benchmarks"] and self.loaded_benchmarks[tests_benchmarks_file] == self.benchmark_data["benchmarks"][benchmark_engine_name]:

                # On affiche ce que l'on fait dans la console
                print(f"\nSkipping Benchmark : {benchmark_engine_name}")

                return

        # On ajoute le résultat du benchmark aux résultats
        self.benchmarks_results[benchmark_engine_name] = self.run_conversation_cut_benchmark(benchmark_engine_name, self.loaded_benchmarks[tests_benchmarks_file], self.current_conversation_engine)

        # On va aussi ajouter des données supplémentaires au données de benchmarks

        # On enregistre le benchmark testé
        if not "benchmarks" in self.benchmark_data:
            self.benchmark_data["benchmarks"] = {}

        # On enregistre si le benchmark n'a jamais été enregistré, ou si le benchmark a été mis à jour depuis la dernière fois
        if not benchmark_engine_name in self.benchmark_data["benchmarks"] or self.benchmark_data["benchmarks"][benchmark_engine_name] != self.loaded_benchmarks[tests_benchmarks_file]:
            self.benchmark_data["benchmarks"][benchmark_engine_name] = self.loaded_benchmarks[tests_benchmarks_file]
            self.benchmark_data["benchmarks"][self.loaded_benchmarks[tests_benchmarks_file]["title"]] = self.loaded_benchmarks[tests_benchmarks_file]

    #
    def run_conversations_tests(self) -> None:
        """
        Point d'entrée pour lancer tous les benchmarks sur tous les moteurs de découpe de conversations.
        """

        print("\n\nConversations Tests.\n\n")

        # On va parcourir chaque fichier de configuration
        engine_config_file: str
        for engine_config_file in os.listdir(self.conf.conversations_engine_configs_paths):

            # On va charger le fichier de configuration du moteur de NER
            self.current_conversation_engine_dict = {}
            with open(f"{self.conf.conversations_engine_configs_paths}{engine_config_file}", encoding="utf-8") as f:
                self.current_conversation_engine_dict = json.load(f)

            # On va créer le moteur de NER associé à cette configuration
            self.current_conversation_engine = ConversationsEngine(self.current_conversation_engine_dict, self.conf)

            # Indique si l'on peut skipper un benchmark ou non
            can_skip: bool = True

            # On enregistre la configuration du moteur de recherche pour la machine support actuelle
            if not "platforms_engines_config" in self.benchmark_data:
                self.benchmark_data["platforms_engines_config"] = {}
                can_skip = False

            if not self.platform_name in self.benchmark_data["platforms_engines_config"]:
                self.benchmark_data["platforms_engines_config"][self.platform_name] = {}
                can_skip = False

            if not self.current_conversation_engine.config_name in self.benchmark_data["platforms_engines_config"][self.platform_name] or self.benchmark_data["platforms_engines_config"][self.platform_name][self.current_conversation_engine.config_name] != self.current_conversation_engine_dict:
                self.benchmark_data["platforms_engines_config"][self.platform_name][self.current_conversation_engine.config_name] = self.current_conversation_engine_dict
                can_skip = False

            # On va parcourir chaque fichier de tests
            tests_benchmarks_file: str
            for tests_benchmarks_file in self.all_conversations_benchmarks_files:

                # On va charger le fichier de test
                if not tests_benchmarks_file in self.loaded_benchmarks:

                    with open(f"{self.conf.tests_benchmarks_paths}{tests_benchmarks_file}", encoding="utf-8") as f:
                        self.loaded_benchmarks[tests_benchmarks_file] = json.load(f)

                # On va lancer les tests
                self.benchmark_current_conversation_engine_and_test(tests_benchmarks_file)

            # Nettoyage
            self.current_conversation_engine = None
            self.current_conversation_engine_dict = {}

    #
    def run_all_tests(self) -> None:

        #
        if not self.skip_search:

            # Profiling 1 - start
            # profiling_task_start("run search tests benchmarks")

            self.run_search_tests()

            # Profiling 1 - end
            # profiling_last_task_ends()

        #
        if not self.skip_ner:

            # Profiling 1 - start
            # profiling_task_start("run NER tests benchmarks")

            self.run_NER_tests()

            # Profiling 1 - end
            # profiling_last_task_ends()

        #
        if not self.skip_conversation:

            # Profiling 1 - start
            # profiling_task_start("run Conversations tests benchmarks")

            self.run_conversations_tests()

            # Profiling 1 - end
            # profiling_last_task_ends()

        # Profiling 1 - start
        # profiling_task_start("saving_results")

        # On va enregistrer les résultats des benchmarks
        self.save_benchmarks_results()

        # Profiling 1 - end
        # profiling_last_task_ends()


if __name__ == "__main__":

    # On charge la configuration
    conf: Config = Config("config.json")

    # On initialise les variables globales
    init_global_variables(conf)

    # On regarde les arguments
    skip_search: bool = False
    skip_ner: bool = False
    skip_conversation: bool = False

    #
    if "skip_search" in sys.argv or "skip_searchs" in sys.argv:
        skip_search = True
    if "skip_ner" in sys.argv or "skip_ners" in sys.argv:
        skip_ner = True
    if "skip_conversation" in sys.argv or "skip_conversations" in sys.argv:
        skip_conversation = True

    # Profiling - init
    # profiling_init("Benchmarks Tests")

    # Profiling 1 - start
    # profiling_task_start("init_test_benchmarks")

    test_benchmarks: TestBenchmarks = TestBenchmarks(
        skip_search=skip_search,
        skip_ner=skip_ner,
        skip_conversation=skip_conversation
    )

    # Profiling 1 - end
    # profiling_last_task_ends()

    # Profiling 1 - start
    # profiling_task_start("run_all_benchmarks")

    #
    test_benchmarks.run_all_tests()

    # Profiling 1 - end
    # profiling_last_task_ends()

    # Profiling - save and stop
    # profiling_save_and_stop()

    #
    free_global_variables()
