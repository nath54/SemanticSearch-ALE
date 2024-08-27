"""
Moteur de NER pour améliorer la recherche dans Rainbow

Auteur: Nathan Cerisara
"""


from dataclasses import dataclass
from typing import Optional, Any, cast

from config import Config
from lib import ConfigError, linear_collision
from ner_algorithms import NER_Algorithm
import ner_algorithms as NA

from profiling import profiling_task_start, profiling_last_task_ends


#
# Liste de tous les algorithmes de NER disponibles
ALGORITHMS: dict[str, type[NER_Algorithm]] = {
    "SimpleSyntaxic_NER_Algorithm": NA.SimpleSyntaxic_NER_Algorithm,
    "SpaCy_SM_NER_Algorithm": NA.SpaCy_SM_NER_Algorithm,
    "SpaCy_LG_NER_Algorithm": NA.SpaCy_LG_NER_Algorithm,
}


#
class NER_Engine:
    """
    Moteur de NER.
    """

    def __init__(self, ner_config: dict, config: Config) -> None:
        self.ner_config: dict = ner_config
        self.config: Config = config
        #
        for k in ["config_name", "algorithms"]:
            if not k in ner_config:
                raise ConfigError(f"No key {k} in ner engine config : {ner_config} !")
        #
        self.config_name: str = ner_config["config_name"]
        #
        self.algorithms: list[NER_Algorithm] = []
        self.coefs_algorithms: list[float] = []
        #
        for algo_config in ner_config["algorithms"]:
            #
            for k in ["type", "coef"]:
                if not k in algo_config:
                    raise ConfigError(f"No key {k} in ner algorithm config : {algo_config} (from engine config : {self.config_name} !)")
            #
            algo_type: str = algo_config["type"]
            #
            if not algo_type in ALGORITHMS:
                raise UserWarning(f"Unknown NER algorithm: {algo_type}")
            #
            algo: NER_Algorithm = ALGORITHMS[algo_type](algo_config, config)
            self.algorithms.append(algo)
            self.coefs_algorithms.append(float(algo_config["coef"]))

    #
    def main_recognize(self, txt: str) -> list[ tuple[int, str, str] ]:
        """
        Point d'entrée principal pour utiliser la reconnaissance d'entités nommés.
        Appelle un ou plusieurs algorithmes de NER et combine les résultats.
        La combinaison des résultats est juste l'union de tous les résultats des sous-algorithmes de NER.
        Si intersection, on prend le résultat du premier algorithme de NER avec le plus gros coefficients.

        Args:
            txt (str): Le texte dont on veut extraire les entités nommés.

        Returns:
            list[ tuple[int, str, str] ]: La liste des entités nommés reconnues, sous le format (position dans la chaîne `txt`, texte de l'entité, type de l'entité).
        """

        # Contiendra la liste des résultats temporaires, avec indication de l'algorithme d'où chaque résultat vient (pour gérer les collisions).
        pre_results: list[ tuple[ int, tuple[int, str, str] ] ] = []

        # Pour chaque algorithme de NER
        id_algo: int
        for id_algo in range(len(self.algorithms)):

            # On va récupérer les résultats de l'algorithme
            algo_results: list[ tuple[int, str, str] ] = self.algorithms[id_algo].recognize(txt)
            bon_results: list[ tuple[ int, tuple[int, str, str] ] ] = []

            # Pour chaque résultat
            for res in algo_results:

                # On va vérifier qu'il ne collisionne pas avec un résultat déjà existant, pour cela, on va tous les parcourir et tester la collision
                collide: int  = -1
                id_pres: int
                for id_pres in range(len(pre_results)):
                    # Test de collision linéaire sur les segments
                    if linear_collision(res[0], res[0]+len(res[1]), pre_results[id_pres][1][0], pre_results[id_pres][1][0]+len(pre_results[id_pres][1][1])):
                        collide = id_pres
                        break

                #
                if collide >= 0:
                    # S'il y a une collision, on va prioriser le premier algo avec le coefficient le plus élevé
                    if self.coefs_algorithms[id_algo] > self.coefs_algorithms[pre_results[collide][0]]:
                        # Si seulement cet algorithme est prioritaire, on va supprimer le résultat précédent et ajouter celui-là
                        del pre_results[collide]
                        bon_results.append( (id_algo, res) )

                else:
                    # Si pas de collision, on est bon, on peut rajouter le résultat
                    bon_results.append( (id_algo, res) )

            # Ok, donc maintenant, on va juste ajouter tous les bon résultats à pre_results
            for br in bon_results:
                pre_results.append(br)

        #
        #print(f"MAIN RECOGNIZE ||| Input msgs: {txt} | results : {pre_results}")

        #
        return [pr[1] for pr in pre_results]

