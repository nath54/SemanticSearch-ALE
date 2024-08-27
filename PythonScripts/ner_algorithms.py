"""
Algorithmes de NER utilisés par un moteur de NER.

Auteur: Nathan Cerisara
"""


from dataclasses import dataclass
from typing import Optional, Any, cast

import spacy
from langdetect import detect as language_detection

from config import Config
from lib import ConfigError

from profiling import profiling_task_start, profiling_last_task_ends


#
class NER_Algorithm:
    """
    Algorithme de NER. Classe abstraite.
    """

    def __init__(self, algo_config: dict, config: Config) -> None:
        self.algo_config: dict = algo_config
        self.config: Config = config
        #

    #
    def recognize(self, txt: str) -> list[ tuple[int, str, str] ]:
        """
        Schéma Abstrait de la fonction de reconnaissance d'entité nommée.
        Normalement, aucun algorithme ne va renvoyer de résultats qui se collisionnent.

        Args:
            txt (str): Le texte dont on veut extraire les entités nommés.

        Returns:
            list[ tuple[int, str, str] ]: La liste des entités nommés reconnues, sous le format (position dans la chaîne `txt`, texte de l'entité, type de l'entité).
        """
        return []


#
class SimpleSyntaxic_NER_Algorithm(NER_Algorithm):
    """
    Algorithme de NER qui se base sur des règles syntaxiques basiques.
    """

    def __init__(self, algo_config: dict, config: Config) -> None:
        super().__init__(algo_config, config)

    #
    def recognize(self, txt: str) -> list[ tuple[int, str, str] ]:
        """
        Reconnaissance d'entité nommée par des règles syntaxiques de bases:
            - Un mot qui commence par une majuscule et qui n'est pas le premier mot d'une phrase a de fortes chances d'être une entité nommée
            - Un mot qui est tout en majuscule a de fortes chance d'être une entité nommée

        Args:
            txt (str): Le texte dont on veut extraire les entités nommés.

        Returns:
            list[ tuple[int, str, str] ]: La liste des entités nommés reconnues, sous le format (position dans la chaîne `txt`, texte de l'entité, type de l'entité).
        """

        # Variables utiles
        current_sentence: int = 0
        sentences: list[list[int]] = [[]]
        words: list[str] = []
        words_positions: list[int] = []
        are_words_entities: list[Optional[str]] = []

        SEP_SENTENCES: set[str] = {'?', '.', '!', '\n', '\r'}
        SEP_WORDS: set[str] = {' ', '?', '!', '.', '\n', '\r', "'", '"', '(', ')', '[', ']', '/', '\\', ':', ',', ';', '>', '<', '{', '}'}
        CHARS_IN_NER: set[str] = {'@', '#', '&', '_', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'}

        txt_len: int = len(txt)
        txt_cursor: int = 0
        # On s'assure de parcourir tout le texte
        while txt_cursor < txt_len:

            # Tant que l'on a des caractères séparateurs, on skippe
            while txt_cursor < txt_len and txt[txt_cursor] in SEP_WORDS:
                #
                if txt[txt_cursor] in SEP_SENTENCES:
                    if len(sentences[current_sentence]) > 0:
                        sentences.append([])
                        current_sentence += 1
                #
                txt_cursor += 1

            # On a atteint la fin du texte
            if txt_cursor >= txt_len:
                break

            # On va lire tout le mot
            deb_cursor: int = txt_cursor
            while txt_cursor < txt_len and txt[txt_cursor] not in SEP_WORDS:
                txt_cursor += 1

            # On récupère le mot
            word: str = txt[deb_cursor: txt_cursor]

            # Ce ne devrais normalement pas arriver, mais au cas où, si le mot est vide, on passe au mot suivant
            if len(word) == 0:
                continue

            # On va tester si ce mot est une entité nommée ou nom avec des tests syntaxiques basiques
            is_entity: Optional[str] = None

            # Si le mot contient
            if not len(sentences[current_sentence]) == 0 and word[0].isupper():
                is_entity = ""
            elif len(word) > 1 and any([c in word[1:] for c in CHARS_IN_NER]):
                is_entity = ""
            elif len(word) > 1 and word.isupper():
                is_entity = ""

            # On ajoute ce mot aux mots trouvés
            sentences[current_sentence].append(len(words))
            words.append(word)
            words_positions.append(deb_cursor)
            are_words_entities.append(is_entity)

        # Liste des résultats que l'on va renvoyer
        resultats: list[ tuple[int, str, str] ] = []

        for idw in range(len(words)):
            if are_words_entities[idw] is not None:
                resultats.append( (words_positions[idw], words[idw], are_words_entities[idw]) )

        # On renvoie les résultats
        return resultats


#
class SpaCy_SM_NER_Algorithm(NER_Algorithm):
    """
    Algorithme de NER qui se base sur SpaCy.
    """

    def __init__(self, algo_config: dict, config: Config) -> None:
        super().__init__(algo_config, config)
        #
        self.nlp_en: spacy.language.Language = spacy.load("en_core_web_sm")
        self.nlp_fr: spacy.language.Language = spacy.load("fr_core_news_sm")

    #
    def recognize(self, txt: str) -> list[ tuple[int, str, str] ]:
        """
        Reconnaissance d'entité nommée par des règles syntaxiques de bases:
            - Un mot qui commence par une majuscule et qui n'est pas le premier mot d'une phrase a de fortes chances d'être une entité nommée
            - Un mot qui est tout en majuscule a de fortes chance d'être une entité nommée

        Args:
            txt (str): Le texte dont on veut extraire les entités nommés.

        Returns:
            list[ tuple[int, str, str] ]: La liste des entités nommés reconnues, sous le format (position dans la chaîne `txt`, texte de l'entité, type de l'entité).
        """

        # Liste des résultats que l'on va renvoyer
        resultats: list[ tuple[int, str, str] ] = []

        # On détecte le langage pour savoir quel modèle de spacy utiliser
        lang: str
        try:
            lang = language_detection(txt)
        except:
            lang = ""

        # On utilise spacy
        doc: spacy.tokens.Doc
        if lang == "fr":
            doc = self.nlp_fr(txt)
        else:
            doc = self.nlp_en(txt)

        # On récupère les résultats de spacy
        for ent in doc.ents:
            # resultats.append( (ent.start_char, ent.text, ent.label_) )
            resultats.append( (ent.start_char, ent.text, "") )

        # On renvoie les résultats
        return resultats


#
class SpaCy_LG_NER_Algorithm(NER_Algorithm):
    """
    Algorithme de NER qui se base sur SpaCy.
    """

    def __init__(self, algo_config: dict, config: Config) -> None:
        super().__init__(algo_config, config)
        #
        self.nlp_en: spacy.language.Language = spacy.load("en_core_web_lg")
        self.nlp_fr: spacy.language.Language = spacy.load("fr_core_news_lg")

    #
    def recognize(self, txt: str) -> list[ tuple[int, str, str] ]:
        """
        Reconnaissance d'entité nommée par des règles syntaxiques de bases:
            - Un mot qui commence par une majuscule et qui n'est pas le premier mot d'une phrase a de fortes chances d'être une entité nommée
            - Un mot qui est tout en majuscule a de fortes chance d'être une entité nommée

        Args:
            txt (str): Le texte dont on veut extraire les entités nommés.

        Returns:
            list[ tuple[int, str, str] ]: La liste des entités nommés reconnues, sous le format (position dans la chaîne `txt`, texte de l'entité, type de l'entité).
        """

        # Liste des résultats que l'on va renvoyer
        resultats: list[ tuple[int, str, str] ] = []

        # On détecte le langage pour savoir quel modèle de spacy utiliser
        lang: str
        try:
            lang = language_detection(txt)
        except:
            lang = ""

        # On utilise spacy
        doc: spacy.tokens.Doc
        if lang == "fr":
            doc = self.nlp_fr(txt)
        else:
            doc = self.nlp_en(txt)

        # On récupère les résultats de spacy
        for ent in doc.ents:
            # resultats.append( (ent.start_char, ent.text, ent.label_) )
            resultats.append( (ent.start_char, ent.text, "") )

        # On renvoie les résultats
        return resultats

