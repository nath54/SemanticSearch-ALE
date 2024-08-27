"""
Un objet de la classe Global sera lancé pour chaque programme Main, (et sera accessibles de partout par tous les threads etc..).
J'ai essayé de ne pas avoir de variables globales le plus possible, mais cela commencait à être nécessaire car sinon le code allait commencer à ne plus ressembler à rien, avec beaucoup de paramètres ou d'arguments, etc...

Auteur: Nathan Cerisara
"""

from typing import cast, Optional

import os
import json
from threading import Lock

from embeddings_cache import EmbeddingCache
from language_translation import LanguageTranslation
from embedding_calculator import MessageEmbedding


GLOBAL_VARIABLE_NAME: str = "global_variables"


#
class GlobalVariables:
    def __init__(self, config: dict) -> None:

        #
        self.config = config

        #
        self.mutex_embedding_cache_modification: Lock = Lock()

        #
        self.NER_dicts: dict[str, dict[str, str]] = {}

        #
        self.mutex_NER_dicts: Lock = Lock()

        #
        self.embedding_caches: dict[str, EmbeddingCache] = {}

        #
        self.mutex_embedding_caches: Lock = Lock()

        #
        self.language_translations: dict[str, LanguageTranslation] = {}

        #
        self.mutex_language_translations: Lock = Lock()

    #
    def get_NER_dict(self, NER_dict_name: str) -> dict[str, str]:

        # Test si il est déjà chargé
        if NER_dict_name in self.NER_dicts:
            return self.NER_dicts[NER_dict_name]

        # Sinon, il faut le charger

        # On vérifie que le fichier existe
        file_path: str = f"{self.config.ner_dicts_dir}{NER_dict_name}.json"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Erreur: le fichier {file_path} n'existe pas!")

        # On charge le fichier
        with open(file_path, "r", encoding="utf-8") as f:
            self.NER_dicts[NER_dict_name] = json.load(f)

        # On renvoie le NER dict
        return self.NER_dicts[NER_dict_name]

    #
    def get_NER_dict_keys(self, NER_dict_name: str) -> list[str]:
        #
        return list(self.get_NER_dict(NER_dict_name).keys())

    #
    def get_embedding_cache(self, model_name: str, txt_key: str) -> Optional[MessageEmbedding]:
        #
        if not model_name in self.embedding_caches:
            return None
        #
        return self.embedding_caches[model_name].get(txt_key)

    #
    def set_embedding_cache(self, model_name: str, txt_key: str, message_embedding: MessageEmbedding) -> None:
        #
        if not model_name in self.embedding_caches:
            self.mutex_embedding_caches.acquire()
            try:
                self.embedding_caches[model_name] = EmbeddingCache(model_name, self.config)
            finally:
                self.mutex_embedding_caches.release()
        #
        self.embedding_caches[model_name].set(txt_key, message_embedding)

    #
    def translate(self, txt_to_translate: str, dest_lang: str = "en") -> str:
        #
        if not dest_lang in self.language_translations:
            self.mutex_language_translations.acquire()
            try:
                self.language_translations[dest_lang] = LanguageTranslation("easyNMT", self.config, dest_lang)
            finally:
                self.mutex_language_translations.release()
        #
        return self.language_translations[dest_lang].translate(txt_to_translate)

    #
    def save(self):
        #
        for lang in self.language_translations:
            self.language_translations[lang].save()
        #
        for model_name in self.embedding_caches:
            self.embedding_caches[model_name].save()


#
def init_global_variables(config: dict) -> None:
    #
    if GLOBAL_VARIABLE_NAME in globals():
        if not isinstance(globals()[GLOBAL_VARIABLE_NAME], GlobalVariables):
            raise SystemError("There is already a thing at the place of the Global object that is not a Global object!")
        #
        raise SystemError("The Global object has already been initialised.")

    #
    globals()[GLOBAL_VARIABLE_NAME] = GlobalVariables(config)

#
def get_global_variables() -> GlobalVariables:
    #
    if not GLOBAL_VARIABLE_NAME in globals():
        raise SystemError("Error : Trying to access to the Global object while it has not been initialised.")
    #
    return globals()[GLOBAL_VARIABLE_NAME]

#
def save_global_variables() -> None:
    #
    if GLOBAL_VARIABLE_NAME in globals():
        #
        globals()[GLOBAL_VARIABLE_NAME].save()

#
def free_global_variables() -> None:
    #
    if GLOBAL_VARIABLE_NAME in globals():
        #
        globals()[GLOBAL_VARIABLE_NAME].save()
        #
        del globals()[GLOBAL_VARIABLE_NAME]

