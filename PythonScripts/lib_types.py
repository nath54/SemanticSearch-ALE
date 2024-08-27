"""
Fichier qui contient un couche abtraite de types qui sont utilisés pour la webapp optimisation des hyper-paramètres.

Auteur: Nathan Cerisara
"""

from typing import cast, Optional, Any

from lib_embedding import DISTANCES_FUNCTIONS


#
CONVERSATION_ALGORITHMS: dict[str, int] = {
    "SimpleTimeDifferences_ConversationAlgorithm": 0,
    "ClusteringFusion_ConversationAlgorithm": 1,
    "ClusteringSeq_ConversationAlgorithm": 2
}

#
NER_ALGORITHMS: dict[str, int] = {
    "SimpleSyntaxic_NER_Algorithm": 0,
    "SpaCy_SM_NER_Algorithm": 1,
    "SpaCy_LG_NER_Algorithm": 2
}

#
SEARCH_ALGORITHMS: dict[str, int] = {
    "SimpleEmbedding_SearchAlgorithm": 0,
    "SimpleSyntaxic_SearchAlgorithm": 1,
    "SyntaxicFullSentenceLevenshtein_SearchAlgorithm": 2,
    "SyntaxicWordsLevenshtein_SearchAlgorithm": 3,
    "SimpleDictJaccard_NER_SearchAlgorithm": 4,
    "SimpleSearchByTime_SearchAlgorithm": 5,
    "SearchByUsers_SearchAlgorithm": 6,
    "SearchWith_NER_Engine_SearchAlgorithm": 7
}

#
GENERAL_CLASSES: dict[str, dict[str, int]] = {
    "ConversationAlgorithm": CONVERSATION_ALGORITHMS,
    "NER_Algorithm": NER_ALGORITHMS,
    "SearchAlgorithm": SEARCH_ALGORITHMS
}



# Classe abstraite des paramètres de la config pour les algorithmes et moteurs
# la clé correspond au nom du paramètre de la config, et la valeur est un tuple indiquant
#   (
    # 0 = type de la valeur
    # 1 = booléen indiquant si c'est une valeur à optimiser
    # 2 = contraintes sur les valeurs prises
    #       * Si c'est une liste, la valeur doit être dans cette liste
    #       * Si c'est un dictionnaire avec la forme {"type": "interval", "min": a, "max": b}, la valeur doit être entre ces deux valeurs
    #       * Sinon, c'est un None / null, et pas de contraintes particulières. On s'en fout, le paramètre peut prendre n'importe quelle valeur (sauf exception bien sûr, par exemple, pour les types qui sont dans la liste type, et surtout les listes)
    # 3 = valeur par défaut,
    # 4 = si c'est une clé nécessaire dans une config ou non. Si elle vaut 0, cela veut dire qu'on s'en fout si le paramètre n'est pas dans la config.
#   )
#
TYPES: dict[str, dict[str, tuple[str, int, Optional[Any], Optional[Any], int]]] = {

    "SimpleTimeDifferences_ConversationAlgorithm": {
        "type": ("string", 0, None, "SimpleTimeDifferencesAlgorithm", 1),
        "coef": ("number", 1, None, 1.0, 1),
        "treshold_value": ("number", 1, None, 60, 1),
        "treshold_type": ("string", 1, ["seconds", "minutes", "hours", "days"], "minutes", 1)
    },

    "ClusteringFusion_ConversationAlgorithm": {
        "type": ("string", 0, None, "ClusteringKmeansAlgorithm", 1),
        "coef": ("number", 1, None, 1.0, 1),
        "search_engine_config_dict": ("SearchEngine", 1, None, None, 1),
        "treshold_conversation_distance": ("number", 1, None, 1.4, 1)
    },

    "ClusteringSeq_ConversationAlgorithm": {
        "type": ("string", 0, None, "ClusteringSeqAlgorithm", 1),
        "coef": ("number", 1, None, 1.0, 1),
        "search_engine_config_dict": ("SearchEngine", 1, None, None, 1),
        "treshold_conversation_distance": ("number", 1, None, 1.4, 1)
    },

    "ConversationEngine": {
        "config_name": ("string", 0, None, "", 1),
        "algorithms": ("list|ConversationAlgorithm", 0, None, [], 1)
    },



    "SimpleSyntaxic_NER_Algorithm": {
        "type": ("string", 0, None, "SimpleSyntaxicNER", 1),
        "coef": ("number", 1, None, 1.0, 1)
    },

    "SpaCy_SM_NER_Algorithm": {
        "type": ("string", 0, None, "SpaCy_SM_NER", 1),
        "coef": ("number", 1, None, 1.0, 1)
    },

    "SpaCy_LG_NER_Algorithm": {
        "type": ("string", 0, None, "SpaCy_LG_NER", 1),
        "coef": ("number", 1, None, 1.0, 1)
    },

    "NER_Engine": {
        "config_name": ("string", 0, None, "", 1),
        "algorithms": ("list|NER_Algorithm", 0, None, [], 1)
    },



    "SimpleEmbedding_SearchAlgorithm": {
        "type": ("string", 0, None, "", 1),
        "coef": ("number", 1, None, 1.0, 1),
        "batch_size": ("number", 0, None, 1, 1),
        "use_cuda": ("number", 0, [0, 1], 0, 0),
        "distance_function": ("string", 0, list(DISTANCES_FUNCTIONS.keys()), "euclidian", 0),
        "model_name": ("string", 0, None, "optimum/all-MiniLM-L6-v2", 1),
        "model_type": ("string", 0, None, "sentence-transformers", 1),
        "model_optimisations": ("string", 0, ["optimum", ""], "optimum", 0),
        "translate_before": ("string", 0, ["", "en", "fr", "es", "zh", "ja", "de", "es"], "en", 0),
        "translate_method": ("string", 0, ["easyNMT", ""], "", 0),
        "NER_text_replacement": ("number", 0, [0, 1], 0, 0)
    },

    "SimpleSyntaxic_SearchAlgorithm": {
        "type": ("string", 0, None, "", 1),
        "coef": ("number", 1, None, 1.0, 1),
        "translate_before": ("string", 0, ["", "en", "fr", "es", "zh", "ja", "de", "es"], "en", 0),
        "translate_method": ("string", 0, ["easyNMT", ""], "", 0),
        "NER_text_replacement": ("number", 0, [0, 1], 0, 0)
    },

    "SyntaxicFullSentenceLevenshtein_SearchAlgorithm": {
        "type": ("string", 0, None, "", 1),
        "coef": ("number", 1, None, 1.0, 1),
        "translate_before": ("string", 0, ["", "en", "fr", "es", "zh", "ja", "de", "es"], "en", 0),
        "translate_method": ("string", 0, ["easyNMT", ""], "", 0),
        "NER_text_replacement": ("number", 0, [0, 1], 0, 0)
    },

    "SyntaxicWordsLevenshtein_SearchAlgorithm": {
        "type": ("string", 0, None, "", 1),
        "coef": ("number", 1, None, 1.0, 1),
        "close_words_factor": ("number", 1, None, 0.4, 1),
        "translate_before": ("string", 0, ["", "en", "fr", "es", "zh", "ja", "de", "es"], "en", 0),
        "translate_method": ("string", 0, ["easyNMT", ""], "", 0),
        "NER_text_replacement": ("number", 0, [0, 1], 0, 0)
    },

    "SimpleDictJaccard_NER_SearchAlgorithm": {
        "type": ("string", 0, None, "", 1),
        "coef": ("number", 1, None, 1.0, 1),
        "translate_before": ("string", 0, ["", "en", "fr", "es", "zh", "ja", "de", "es"], "en", 0),
        "translate_method": ("string", 0, ["easyNMT", ""], "", 0),
        "NER_text_replacement": ("number", 0, [0, 1], 0, 0)
    },

    "SimpleSearchByTime_SearchAlgorithm": {
        "type": ("string", 0, None, "", 1),
        "coef": ("number", 1, None, 1.0, 1),
        "translate_before": ("string", 0, ["", "en", "fr", "es", "zh", "ja", "de", "es"], "en", 0),
        "translate_method": ("string", 0, ["easyNMT", ""], "", 0),
        "NER_text_replacement": ("number", 0, [0, 1], 0, 0)
    },

    "SearchByUsers_SearchAlgorithm": {
        "type": ("string", 0, None, "", 1),
        "coef": ("number", 1, None, 1.0, 1),
        "translate_before": ("string", 0, ["", "en", "fr", "es", "zh", "ja", "de", "es"], "en", 0),
        "translate_method": ("string", 0, ["easyNMT", ""], "", 0),
        "NER_text_replacement": ("number", 0, [0, 1], 0, 0)
    },

    "SearchWith_NER_Engine_SearchAlgorithm": {
        "type": ("string", 0, None, "", 1),
        "coef": ("number", 1, None, 1.0, 1),
        "translate_before": ("string", 0, ["", "en", "fr", "es", "zh", "ja", "de", "es"], "en", 0),
        "translate_method": ("string", 0, ["easyNMT", ""], "", 0),
        "NER_text_replacement": ("number", 0, [0, 1], 0, 0),
        "ner_engine_config_dict": ("NER_Engine", 0, None, None, 1)
    },

    "SearchEngine": {
        "config_name": ("string", 0, None, "", 1),
        "nb_threads": ("number", 0, None, 1, 0),
        "max_message_length": ("number", 0, None, 200, 1),
        "nb_search_results": ("number", 0, None, 30, 1),
        "distance_limit": ("number", 0, None, None, 0),
        "algorithms": ("list|SearchAlgorithm", 0, None, None, 1)
    }
}



#
def test_hyper_parameter_correct(value: Any, type_details: tuple[str, int, Optional[Any], Optional[Any], int]) -> bool:
    """
    _summary_

    Args:
        value (Any): _description_
        type_details (tuple[str, int, Optional[Any], Optional[Any], int]): _description_

    Returns:
        bool: _description_
    """

    """
    Rappel de la structure d'un type :

    (
        0 = type de la valeur
        1 = booléen indiquant si c'est une valeur à optimiser
        2 = contraintes sur les valeurs prises
            * Si c'est une liste, la valeur doit être dans cette liste
            * Si c'est un dictionnaire avec la forme {"type": "interval", "min": a, "max": b}, la valeur doit être entre ces deux valeurs
            * Sinon, c'est un None / null, et pas de contraintes particulières. On s'en fout, le paramètre peut prendre n'importe quelle valeur (sauf exception bien sûr, par exemple, pour les types qui sont dans la liste type, et surtout les listes)
        3 = valeur par défaut,
        4 = si c'est une clé nécessaire dans une config ou non. Si elle vaut 0, cela veut dire qu'on s'en fout si le paramètre n'est pas dans la config.
    )

    """

    # On vérifie quand même que le type est correct.
    if(len(type_details) != 5):
        print("Error: Incorrect type : ", type_details)
        return False

    if(isinstance(type_details[2], list) or isinstance(type_details[2], tuple)):
        # Contraintes de valeurs, on renvoie faux si la valeur n'est pas dans la liste
        if(not type_details[2].includes(value)):
            return False

    elif(isinstance(type_details[2], dict) and type_details[2] != None):
        #
        if(type_details[2]["type"] == "interval"):
            # Intervalle, on renvoie faux si la valeur est hors de l'intervalle.
            if(value < type_details[2]["min"] or value > type_details[2]["max"]):
                return False

    # Si on arrive jusque là, c'est que tout est bon, pas de problèmes détectés
    return True

#
def test_config_correct(config_dict_or_value: dict | int | str, config_base_type_name: str, config_type_dict_or_type_details: dict | tuple[str, int, Optional[Any], Optional[Any], int]) -> bool:
    """_summary_

    Args:
        config_dict_or_value (dict | int | str): _description_
        config_base_type_name (str): _description_
        config_type_dict_or_type_details (dict | tuple[str, int, Optional[Any], Optional[Any], int]): _description_

    Returns:
        bool: _description_
    """

    # Si problèmes de type de base
    if config_base_type_name not in TYPES:
        #  and not ( Object.keys(general_classes).includes(config_base_type_name) and general_classes[config_base_type_name].includes(config_dict["type"]) )
        return False

    #
    if (isinstance(config_type_dict_or_type_details, list) or isinstance(config_type_dict_or_type_details, tuple)) and (not config_type_dict_or_type_details[0].startswith("list|") or config_type_dict_or_type_details[0] in TYPES.keys()):
        return test_hyper_parameter_correct(config_dict_or_value, config_type_dict_or_type_details)

    #
    res_bon: bool

    # On parcours toutes les clés de ce type de configuration
    for value_type_key in config_type_dict_or_type_details.keys():

        # Si la clé n'est pas dans la configuration
        if(value_type_key not in config_dict_or_value):
            # Si c'est une valeur importante
            if(TYPES[config_base_type_name][value_type_key][4] == 1):
                return False

            # Sinon, on l'ignore
            continue

        # Si on arrive ici, c'est que la clé est bien dans la configuration
        key_type: str = TYPES[config_base_type_name][value_type_key][0]
        if(key_type in TYPES or key_type.startswith("list|")):
            #
            if(key_type.startsWith("list|")):
                #
                real_key_type: str = key_type[5:]
                #
                i: int = 0
                for sub_config_params in config_dict_or_value[value_type_key]:
                    #
                    if(real_key_type in GENERAL_CLASSES):
                        res_bon = test_config_correct(config_dict_or_value[value_type_key][i], sub_config_params["type"], TYPES[sub_config_params["type"]])
                        if(not res_bon):
                            return False

                    else:
                        res_bon = test_config_correct(config_dict_or_value[value_type_key][i], real_key_type, TYPES[real_key_type])
                        if(not res_bon):
                            return False

                    #
                    i += 1


            else:
                #
                res_bon = test_config_correct(config_dict_or_value[value_type_key], key_type, config_type_dict_or_type_details[value_type_key])
                if(not res_bon):
                    return False

    #
    return True


