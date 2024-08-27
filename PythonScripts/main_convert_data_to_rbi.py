"""
This script will convert a DataToImport dataset to a saved Fake Rainbow Instance.

Auteur: Nathan Cerisara
"""

from typing import cast, Optional
from enum import Enum

import os

from user import User
from bubble import Bubble
from message import Message
from rainbow_instance import RainbowInstance

from config import Config
from lib import FunctionResult, ResultError, ResultSuccess

from global_variables import GlobalVariables, init_global_variables, get_global_variables, free_global_variables


#
def cut_until_last_subtxt(txt: str, subtxt: str) -> FunctionResult[str]:
    """
    Coupe la chaîne txt jusqu'à avant la dernière occurence de subtxt, et renvoie la chaîne coupée.

    Args:
        txt (str): La chaine principale à couper
        subtxt (str): La sous chaîne

    Returns:
        FunctionResult[str]: Renvoie ResultSuccess en cas de succès, avec la chaîne coupée, sinon, ResultError
    """

    # On cherche le dernier index possible de la chaine subtxt dans la chaine txt
    i: int = txt.rfind(subtxt)

    # Si la chaine n'a pas été trouvée, on renvoie une erreur
    if i < 0:
        return ResultError(f"Erreur durant le coupage de texte, la chaine `{subtxt}` n'a pas été trouvée dans la chaine `{txt}`.")

    # Sinon, on renvoie la chaine coupée
    return ResultSuccess(txt[:i])

#
def get_last_until_last_subtxt(txt: str, subtxt: str) -> FunctionResult[str]:
    """
    Récupère la dernière partie chaîne txt jusqu'à la dernière occurence de subtxt.

    Args:
        txt (str): La chaine principale à couper
        subtxt (str): La sous chaîne délimiteur

    Returns:
        FunctionResult[str]: Renvoie ResultSuccess en cas de succès, avec la sous-chaine, sinon, ResultError
    """

    # On cherche le dernier index possible de la chaine subtxt dans la chaine txt
    i: int = txt.rfind(subtxt)

    # Si la chaine n'a pas été trouvée, on renvoie une erreur
    if i == -1:
        return ResultError(f"Erreur durant la recherche de texte, la chaine `{subtxt}` n'a pas été trouvée dans la chaine `{txt}`.")

    # Sinon, on renvoie la chaine coupée
    return ResultSuccess(txt[i+len(subtxt):])


#
DIGITS: str = "0123456789"

#
def get_last_int_from_txt(txt: str) -> FunctionResult[int]:
    """Récupérer le dernier entier dans la chaine de charactère txt

    Args:
        txt (str): La chaine de charactère où il faut récupérer le dernier entier

    Returns:
        FunctionResult[int]: Renvoie le dernier entier de la chaine txt en cas de succès
    """

    id_debut: int = len(txt) - 1

    if txt[id_debut] not in DIGITS:
        return ResultError(f"La chaine {txt} ne se termine pas par un entier.")

    while id_debut > 0 and txt[id_debut] in DIGITS:
        id_debut-=1

    return ResultSuccess(int(txt[id_debut+1:]))


#
MONTHS: list[str] = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

#
def bubble_headline_parser(bubble_line: str) -> FunctionResult[tuple[str, str]]:
    """
    Parse un header d'une bulle Rainbow sous le format : (user_name, date).
    Avec date sous le format aaaa/mm/jj-hh:mm (On utilise ce format de date car il est correct pour les comparaisons lexicographiques).

    Exemple de format d'un header d'un message d'une bulle Rainbow exportée:
    `Enzo Ferrari Tuesday, November 14, 2023 3:32 PM`


    Args:
        bubble_line (str): Ligne d'un header d'un message d'une bulle de Rainbow à parser

    Returns:
        FunctionResult[tuple[str, str]]: Renvoie le résultat sour la forme (user_name, date) si succès
    """

    bubble_line = bubble_line.strip()

    # Retours de fonctions
    res: FunctionResult

    # On va convertir la date sous le format jj/mm/aaaa - hh:mm
    day: int = 0
    month: int = 0
    year: int = 0
    hour: int = 0
    minute: int = 0

    # On récupère la période de la journée
    if bubble_line.endswith("PM"):
        hour += 12
    elif not bubble_line.endswith("AM"):
        return ResultError(f"Mauvais format d'heure dans la ligne {bubble_line}, il faut soit que cela se termine par ` AM`, soit par ` PM`.")

    # On récupère les minutes
    res = cut_until_last_subtxt(bubble_line, " ")
    if isinstance(res, ResultError):
        return cast(FunctionResult[tuple[str, str]], res)
    bubble_line = res.get_return_value()
    #
    res = get_last_int_from_txt(bubble_line)
    if isinstance(res, ResultError):
        return cast(FunctionResult[tuple[str, str]], res)
    minute = res.get_return_value()

    # On récupère l'heure
    res = cut_until_last_subtxt(bubble_line, ":")
    if isinstance(res, ResultError):
        return cast(FunctionResult[tuple[str, str]], res)
    bubble_line = res.get_return_value()
    #
    res = get_last_int_from_txt(bubble_line)
    if isinstance(res, ResultError):
        return cast(FunctionResult[tuple[str, str]], res)
    hour += res.get_return_value()

    # On récupère l'année
    res = cut_until_last_subtxt(bubble_line, " ")
    if isinstance(res, ResultError):
        return cast(FunctionResult[tuple[str, str]], res)
    bubble_line = res.get_return_value()
    #
    res = get_last_int_from_txt(bubble_line)
    if isinstance(res, ResultError):
        return cast(FunctionResult[tuple[str, str]], res)
    year = res.get_return_value()

    # On récupère le numéro du jour
    res = cut_until_last_subtxt(bubble_line, ",")
    if isinstance(res, ResultError):
        return cast(FunctionResult[tuple[str, str]], res)
    bubble_line = res.get_return_value()
    #
    res = get_last_int_from_txt(bubble_line)
    if isinstance(res, ResultError):
        return cast(FunctionResult[tuple[str, str]], res)
    day = res.get_return_value()

    # On récupère le mois
    res = cut_until_last_subtxt(bubble_line, " ")
    if isinstance(res, ResultError):
        return cast(FunctionResult[tuple[str, str]], res)
    bubble_line = res.get_return_value()
    #
    res = get_last_until_last_subtxt(bubble_line, " ")
    if isinstance(res, ResultError):
        return cast(FunctionResult[tuple[str, str]], res)
    month_name: str = res.get_return_value()
    #
    if not month_name in MONTHS:
        return ResultError(f"Mauvaise valeur pour le mois : {month_name}")
    month = MONTHS.index(month_name)

    # On skippe le nom du jour
    res = cut_until_last_subtxt(bubble_line, " ")
    if isinstance(res, ResultError):
        return cast(FunctionResult[tuple[str, str]], res)
    bubble_line = res.get_return_value()

    # On récupère le nom de l'utilisateur, qui est le reste de la ligne
    res = cut_until_last_subtxt(bubble_line, " ")
    if isinstance(res, ResultError):
        return cast(FunctionResult[tuple[str, str]], res)
    user_name: str = res.get_return_value()

    # On formate la date
    date: str = f"{year}/{'0' if month < 10 else ''}{month}/{'0' if day < 10 else ''}{day}-" \
                f"{'0' if hour < 10 else ''}{hour}:{'0' if minute < 10 else ''}{minute}"

    # On renvoie le résultat
    return ResultSuccess((user_name, date))


#
def bubble_parser(rbi_path: str, bubble_path_or_name: str, rbi: RainbowInstance, import_from_txt: Optional[str] = None) -> FunctionResult[tuple[RainbowInstance, str]]:
    """
    Fonction principale pour parser une bulle d'une instance rainbow

    Args:
        rbi_path (str): Chemin vers l'instance rainbow
        bubble_path (str): Chemin vers la bulle
        rbi (RainbowInstance): Instance Rainbow qui contient la bulle à parser

    Returns:
        FunctionResult[tuple[RainbowInstance, int]]: Renvoie l'instance Rainbow avec les modifications, avec l'id de la nouvelle bulle créée
    """

    txt_bubble: str = ""

    # On vérifie que le fichier existe bien
    if import_from_txt is None:
        if not os.path.exists(f"{rbi_path}/{bubble_path_or_name}"):
            return ResultError(f"Le fichier {rbi_path}/{bubble_path_or_name} n'existe pas.")

        # On ouvre le fichier de la bulle à parser
        with open(f"{rbi_path}/{bubble_path_or_name}", encoding="utf-8") as f:
            txt_bubble = f.read()
    else:
        txt_bubble = import_from_txt

    #
    txt_bubble_lines = txt_bubble.split("\n")

    # Création de l'objet
    bubble: Bubble = Bubble()
    bubble.id = rbi.get_first_bubble_new_usable_id()
    bubble.name = bubble_path_or_name.split(".")[0]
    bubble.members_ids = set()
    bubble.messages_ids = set()

    # On ajoute la bulle à l'instance Rainbow
    rbi.bubbles[bubble.id] = bubble

    # On prépare les variables
    user_name: str = ""
    date: str = ""
    content: str = ""

    # On parse toutes les lignes
    for line in txt_bubble_lines:

        # Pour enlever les \n et trailing spaces
        line = line.strip()

        # On parse l'en tête
        res: FunctionResult = bubble_headline_parser(line)
        if isinstance(res, ResultError):
            # Contenu

            # Pas de header encore lu, on ignore
            if user_name == "" or date == "":
                continue

            # On ajoute la ligne actuelle au contenu
            if content == "":
                content = line
            else:
                content += "\n" + line

        else:
            # Header

            # On teste s'il y avait un message précédent à enregistrer
            if user_name != "" and date != "":

                # Si l'utilisateur n'existe pas, on le crée
                if not user_name in rbi.users_names:
                    user: User = User()
                    user.id = rbi.get_first_user_new_usable_id()
                    user.name = user_name
                    user.bubbles_ids.add(bubble.id)
                    #
                    rbi.users[user.id] = user
                    rbi.users_names[user.name] = user.id

                user_id: str = rbi.users_names[user_name]

                # On ajoute l'utilisateur à la bulle s'il n'y est pas déjà
                if not user_id in bubble.members_ids:
                    bubble.members_ids.add(user_id)

                # On ajoute la bulle à l'utilisateur s'il elle n'y est pas déjà
                if not bubble.id in rbi.users[user_id].bubbles_ids:
                    rbi.users[user_id].bubbles_ids.add(bubble.id)

                # On crée le message
                msg: Message = Message()
                msg.id = rbi.get_first_message_new_usable_id()
                msg.author_id = user_id
                msg.answered_message_id = ""
                msg.bubble_id = bubble.id
                msg.content = content.strip()
                msg.date = date

                # On ajoute le message à l'instance Rainbow
                rbi.messages[msg.id] = msg

                # On ajoute le message à l'utilisateur
                rbi.users[user_id].messages_ids.add(msg.id)

                # On ajoute le message à la bulle
                bubble.messages_ids.add(msg.id)

            # On récupère les résultats du header
            user_name = res.get_return_value()[0]
            date = res.get_return_value()[1]
            content = ""

    # On parse le dernier message
    if user_name != "" and date != "":

        # Si l'utilisateur n'existe pas, on le crée
        if not user_name in rbi.users_names:
            user = User()
            user.id = rbi.get_first_user_new_usable_id()
            user.name = user_name
            user.bubbles_ids.add(bubble.id)
            #
            rbi.users[user.id] = user
            rbi.users_names[user.name] = user.id

        user_id = rbi.users_names[user_name]

        # On ajoute l'utilisateur à la bulle s'il n'y est pas déjà
        if not user_id in bubble.members_ids:
            bubble.members_ids.add(user_id)

        # On ajoute la bulle à l'utilisateur s'il elle n'y est pas déjà
        if not bubble.id in rbi.users[user_id].bubbles_ids:
            rbi.users[user_id].bubbles_ids.add(bubble.id)

        # On crée le message
        msg = Message()
        msg.id = rbi.get_first_message_new_usable_id()
        msg.author_id = user_id
        msg.author_name = user_name
        msg.answered_message_id = -1
        msg.bubble_id = bubble.id
        msg.content = content.strip()
        msg.date = date

        # On ajoute le message à l'instance Rainbow
        rbi.messages[msg.id] = msg

        # On ajoute le message à l'utilisateur
        rbi.users[user_id].messages_ids.add(msg.id)

        # On ajoute le message à la bulle
        bubble.messages_ids.add(msg.id)


    # Si on est arrivé jusqu'ici, c'est que tout a bien été parsé
    return ResultSuccess((rbi, bubble.id))

#
def rbi_parser(base_path: str, rbi_name: str, conf: Config) -> FunctionResult:
    """
    Fonction qui va parser un fichier de donnée RBI sous le format d'export de Rainbow, et sauvegarder les données sous un format plus facilement réutilisable avec du json.

    Args:
        base_path (str): Chemin de base où est situé ce fichier
        rbi_name (str): Le nom de la RBI
        conf (Config): Fichier de configuration général du projet

    Returns:
        FunctionResult: ResultSuccess si le parsing s'est bien passé, ResultError sinon
    """

    # On va créer l'objet
    rbi: RainbowInstance = RainbowInstance(rbi_name, conf)

    # On va charger toutes les bulles
    for bubble_file in os.listdir(f"{base_path}{rbi_name}/"):
        res: FunctionResult = bubble_parser(f"{base_path}{rbi_name}", bubble_file, rbi)
        if isinstance(res, ResultError):
            return res

    # Ici, on va donc sauvegarder la fake RainbowInstance
    rbi.save()

    # Si on est arrivé jusqu'ici, c'est que tout a bien été parsé
    return ResultSuccess()


#
if __name__ == "__main__":

    # On charge le fichier de config
    conf: Config = Config("config.json")

    # On initialise les variables globales
    init_global_variables(conf)

    # Nom de la RBI en train d'être traitée
    rbi: str

    # Pour chaque Fake Rainbow Instance donnée à convertir
    for rbi in os.listdir(conf.base_data_to_convert_path):

        # On ne traite pas si un dossier RainbowSave existe déjà
        if os.path.exists(f"{conf.base_path_rbi_converted_saved}{rbi}"):
            print(f"Skipping {rbi}")
            continue

        # Affichage pour suivre ce qui se passe
        print(f"Parsing {rbi}...")

        # Sinon, chaque sous-fichier du dossier sera à parser vers une bulle
        res: FunctionResult = rbi_parser(conf.base_data_to_convert_path, rbi, conf)
        if isinstance(res, ResultError):
            print("Error during RBI parser!")
            print(cast(ResultError, res).get_error_message())
            exit(1)

        # Affichage pour suivre ce qui se passe
        print("Done.")

    #
    free_global_variables()
