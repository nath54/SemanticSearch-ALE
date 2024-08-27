"""
Fichier qui va contenir la classe pour gérer la traduction.

Auteur: Nathan Cerisara
"""


from typing import Optional

import os
import json
import re

from langdetect import detect as language_detection
from translate import Translator
from easynmt import EasyNMT

from config import Config

from profiling import profiling_task_start, profiling_last_task_ends


# liste de toutes les méthodes de traduction implémentées
ALL_TRANSLATION_METHODS: set[str] = {
    "Translator",
    "easyNMT"
}



#
def detect_language(txt: str) -> str:
    """
    Détecte le langage principale du texte demandé.

    Args:
        txt (str): Texte dont on veut savoir la langue

    Returns:
        str: Code indiquant le langage détecté (ex: en, fr, es, ...)
    """

    lang: str
    try:
        lang = language_detection(txt)
    except:
        lang = ""

    return lang

#
def remove_emojis(data: str) -> str:
    """
    Enlève les émojis et les autres mauvais caractères.

    Args:
        data (str): chaîne à traiter

    Returns:
        str: chaîne nettoyée
    """

    emoj = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        # u"\U00002500-\U00002BEF"  # chinese char
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642"
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"  # dingbats
        u"\u3030"
                    "]+", re.UNICODE)
    #
    return re.sub(emoj, '', data)


#
class LanguageTranslation:
    """
    Classe qui va gérer la traduction.
    """

    def __init__(self, translation_method: str, conf: Config, language: str="en") -> None:
        # Configuration générale de l'application
        self.conf: Config = conf
        # Langage cible vers lequel traduire
        self.language: str = language
        # Méthode utilisée pour la traduction
        self.method_used: str = translation_method
        # On vérifie que la méthode demandée est bien supportée
        if not translation_method in ALL_TRANSLATION_METHODS:
            raise ValueError(f"The translation method \"{translation_method}\" is not in {ALL_TRANSLATION_METHODS}.")
        # Objet Translator si on utilise la méthode Translator
        self.translator: Optional[Translator] = None
        if translation_method == "Translator":
            self.translator = Translator(to_lang=language)
        # Modèles de traduction depuis HuggingFace, si on utilise cette méthode
        self.easy_nmt_model = EasyNMT('opus-mt')
        # Cache de traduction
        self.translation_cache: dict[str, dict[str, str]] = {}

        # à chaque fois que l'on rajoute un message dans le cache, on a tant de chance de sauvegarder le cache sur le disque
        self.translation_cache_save_chance: float = 0.2

        print(f"DEBUG | conf = {conf}")

        #
        self.path_translation_cache: str = f"{self.conf.cache_translations_json}_{self.language}.json"

        # On va charger le cache
        if os.path.exists(self.path_translation_cache):
            with open(self.path_translation_cache, "r", encoding="utf-8") as f:
                self.translation_cache = json.load(f)

    #
    def save(self) -> None:
        """
        Enregistre dans un fichier json le cache des traductions.
        """

        # On enregistre le cache
        with open(self.path_translation_cache, "w", encoding="utf-8") as f:
            json.dump(self.translation_cache, f)
        #
        print("Translation Cache saved")

    #
    def translate_translator(self, txt: str) -> str:
        """
        Traduit le texte demandé (méthode Translator)

        Args:
            txt (str): Texte à traduire

        Returns:
            str: Texte traduit
        """

        if self.translator is None:
            raise UserWarning("Error, Translator is None!")

        # On utilise l'api translate pour traduire le texte
        res: str = self.translator.translate(txt)
        return res

    #
    def translate(self, txt: str) -> str:
        """
        Fonction principale pour la traduction qui va utiliser la méthode demandée pour la traduction.

        Args:
            txt (str): Texte à traduire

        Returns:
            str: Texte traduit
        """

        #
        res: str

        # On teste si on a pas déjà traduit ce message
        if self.language in self.translation_cache and txt in self.translation_cache[self.language]:
            res = self.translation_cache[self.language][txt]

            # Affichage de débug
            # print(f"\nCached translation to {self.language}\n:  - \"{txt}\"\n  -> \"{res}\"\n")

            #
            return res

        # On détecte la langue
        lang_detected: str = detect_language(txt)

        # On vérifie s'il y a vraiment besoin de traduire
        if lang_detected == self.language:
            res = txt
            #
            return res

        #
        if self.method_used == "Translator":
            # nettoyage du texte
            txt = remove_emojis(txt)
            #
            res = self.translate_translator(txt)
        #
        elif self.method_used == "easyNMT":
            # nettoyage du texte
            txt = remove_emojis(txt)
            #
            if lang_detected in ["fr", "es", "zh"]:
                res = self.easy_nmt_model.translate(txt, source_lang=lang_detected, target_lang="en")
            else:
                res = txt
        # Pas de méthode, on renvoie directement le texte alors
        else:
            res = txt
            #
            return res

        # On ajoute le langage cible de la traduction dans le cache s'il n'y est pas déjà
        if not self.language in self.translation_cache:
            self.translation_cache[self.language] = {}

        # On ajoute la traduction dans le cache
        self.translation_cache[self.language][txt] = res

        # Affichage de débug
        print(f"\nTranslated from {lang_detected} to {self.language}\n:  - \"{txt}\"\n  -> \"{res}\"\n")

        #
        return res

