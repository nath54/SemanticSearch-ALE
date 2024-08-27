"""
Fichier avec quelques éléments généraux qui seront utiles pour le projet.

Auteur: Nathan Cerisara
"""

from typing import Any, Generic, TypeVar, Optional

from parse import parse
import hashlib
import math
import numpy as np
import matplotlib.pyplot as plt


#
class Date:
    """
    Objet pour manipuler des Dates.
    """

    def __init__(self, years: int = 0, months: int = 0, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0, milliseconds: int = 0, from_txt_date: Optional[str] = None) -> None:
        self.years: int = years
        self.months: int = months
        self.days: int = days
        self.hours: int = hours
        self.minutes: int = minutes
        self.seconds: int = seconds
        self.milliseconds: int = milliseconds
        #
        if from_txt_date is not None:
            # On parse le résultat
            parsed = parse("{years}/{months}/{days} - {hours}h{minutes}", from_txt_date)
            if parsed is not None:
                #
                self.years = int(parsed["years"])
                self.months = int(parsed["months"])
                self.days = int(parsed["days"])
                self.hours = int(parsed["hours"])
                self.minutes = int(parsed["minutes"])
        #
        self.correct()

    def correct(self) -> None:
        # Conversions
        #
        while self.seconds >= 60:
            self.seconds -= 60
            self.minutes += 1
        #
        while self.minutes >= 60:
            self.minutes -= 60
            self.hours += 1
        #
        while self.hours >= 24:
            self.hours -= 24
            self.days += 1
        #
        while self.days >= 30:
            self.days -= 30
            self.months += 1
        #
        while self.months >= 12:
            self.months -= 12
            self.years += 1

    def to_seconds(self) -> float:
        """
        Renvoie cette date en secondes.

        Returns:
            float: Le nombre de secondes correspondant à cette date.
        """
        return self.seconds + 60 * (self.minutes + 60.0 * (self.hours + 24.0 * (self.days + 30.5 * (self.months + 12 * self.years))))

    def to_minutes(self) -> float:
        """
        Renvoie cette date en minutes.

        Returns:
            float: Le nombre de minutes correspondant à cette date.
        """
        return float(self.seconds) / 60.0 + self.minutes + 60.0 * (self.hours + 24.0 * (self.days + 30.5 * (self.months + 12 * self.years)))

    def to_hours(self) -> float:
        """
        Renvoie cette date en heures.

        Returns:
            float: Le nombre d'heures correspondant à cette date.
        """
        return ((float(self.seconds) / 60.0 + float(self.minutes)) / 60.0) + self.hours + 24.0 * (self.days + 30.5 * (self.months + 12 * self.years))

    def to_days(self) -> float:
        """
        Renvoie cette date en jours.

        Returns:
            float: Le nombre de jours correspondant à cette date.
        """
        return (((float(self.seconds) / 60.0 + float(self.minutes)) / 60.0) + float(self.hours)) / 24.0 + self.days + 30.5 * (self.months + 12 * self.years)

    def to_months(self) -> float:
        """
        Renvoie cette date en mois.

        Returns:
            float: Le nombre de mois correspondant à cette date.
        """
        return ((((float(self.seconds) / 60.0 + float(self.minutes)) / 60.0) + float(self.hours)) / 24.0 + float(self.days)) / 30.5 + self.months + 12 * self.years

    def to_years(self) -> float:
        """
        Renvoie cette date en années.

        Returns:
            float: Le nombre d'années correspondant à cette date.
        """
        return (((((float(self.seconds) / 60.0 + float(self.minutes)) / 60.0) + float(self.hours)) / 24.0 + float(self.days)) / 30.5 + self.months) / 12.0 + self.years

    def __str__(self) -> str:
        return f"{self.years:04}/{self.months:02}/{self.days:02} - {self.hours:02}h{self.minutes:02}"

    def display(self) -> str:
        txt: str = ""
        if self.years != 0:
            txt += f" {self.years} year"
            if self.years != 1:
                txt += "s"
        if self.months != 0:
            txt += f" {self.months} month"
            if self.months != 1:
                txt += "s"
        if self.days != 0:
            txt += f" {self.days} day"
            if self.days != 1:
                txt += "s"
        if self.hours != 0:
            txt += f" {self.hours} hour"
            if self.hours != 1:
                txt += "s"
        if self.minutes != 0:
            txt += f" {self.minutes} minute"
            if self.minutes != 1:
                txt += "s"
        if self.seconds != 0:
            txt += f"{ self.seconds} second"
            if self.seconds != 1:
                txt += "s"
        #
        if txt == "":
            txt = "empty time"
        #
        return txt.strip()


#
ESCAPE_CHARS: dict[str, str] = {
    ' ': '',
    '(': '__lp__',
    ')': '__rp__',
    '.': '__d__',
    '<': '__lt__',
    '>': '__gt__',
    '"': '__q__',
    "'": '__sq__',
    '/': '__s__',
    '\\': '__as__',
    '?': '__qm__',
    ',': '__cm__',
    ':': '__cl__',
    '*': '__a__',
    '|': '__p__',
    '\n': '__nl__',
    '\r': '__rc__',
    '\t': '__t__',
    '\b': '__b__',
    '!': '__e__'
}

#
def escapeCharacters(text: str) -> str:
    """
    Traite un texte et remplacer les mauvais caractères pour protéger contre des attaques par insertion et pour avoir un nom de fichier utilisable dans tout système de fichier.

    Args:
        text (str): texte a traiter

    Returns:
        str: texte traité
    """

    #
    text=text.lower()

    #
    for c in ESCAPE_CHARS:
        text = text.replace(c, ESCAPE_CHARS[c])

    #
    return text

#
# Average function
T_avg = TypeVar('T_avg')
def avg(l: list[Generic[T_avg]]) -> Generic[T_avg]:
    """
    Calcule la moyenne d'une liste de valeurs

    Args:
        l (list): liste de valeurs dont on veut calculer la moyenne

    Returns:
        float: La moyenne de la liste
    """

    #
    if len(l) == 0:
        return 0
    #
    return sum(l)/len(l)

#
# Median function
T_med = TypeVar('T_med')
def median(l: list[Generic[T_med]]) -> Generic[T_med]:
    """
    Renvoie la valeur médiane de la liste, en supposant que celle-ci est triée.

    Args:
        l (list[Generic[T_med]]): Liste triée

    Returns:
        Generic[T_med]: La valeur médiane de la liste
    """
    #
    if len(l) == 0:
        return 0
    #
    return l[math.floor(float(len(l))/2.0)]

#
# first quartile function
T_1_4 = TypeVar('T_1_4')
def first_quartile(l: list[Generic[T_1_4]]) -> Generic[T_1_4]:
    """
    Renvoie le premier quartile de la liste, en supposant que celle-ci est triée.

    Args:
        l (list[Generic[T_1_4]]): Liste triée

    Returns:
        Generic[T_1_4]: La valeur du premier quartile de la liste
    """
    #
    if len(l) == 0:
        return 0
    #
    return l[math.floor(float(len(l))/4.0)]

#
# Median function
T_3_4 = TypeVar('T_3_4')
def third_quartile(l: list[Generic[T_3_4]]) -> Generic[T_3_4]:
    """
    Renvoie le troisième quartile de la liste, en supposant que celle-ci est triée.

    Args:
        l (list[Generic[T_3_4]]): Liste triée

    Returns:
        Generic[T_3_4]: La valeur du troisième quartile de la liste
    """
    #
    if len(l) == 0:
        return 0
    #
    return l[math.floor((float(len(l))*3.0)/4.0)]


#
def linear_collision(start_1: int, end_1: int, start_2: int, end_2: int) -> bool:
    """
    Détection de collisions linéaires entre deux segments.

    Args:
        start_1 (int): début du premier segment.
        end_1 (int): fin du premier segment.
        start_2 (int): début du second segment.
        end_2 (int): fin du second segment.

    Returns:
        bool: True si les segments se collisionnent, False sinon.
    """
    if start_1 >= start_2:
        if start_1 < end_2:
            return True
        return False
    else:
        if end_1 >= start_2:
            return True
        return False

#
def dist_subsets(A: set[int], B: set[int]) -> float:
    """
    Calcul la distance entre deux sous-ensembles.

    Args:
        A (set[int]): Premier sous ensemble
        B (set[int]): Second sous ensemble

    Returns:
        float: Distance symmétrique entre ces deux ensembles
    """
    return len(A.symmetric_difference(B)) / 2.0

#
def set_edit_distance(set_A: list[set[str] | list[str] | tuple[str]], set_B: list[set[str] | list[str] | tuple[str]]) -> float:
    """
    Calcul la distance d'édition entre deux ensembles de sous-ensembles.

    Args:
        set_A (list[set[str] | list[str] | tuple[str]]): Premier ensemble de sous-ensembles
        set_B (list[set[str] | list[str] | tuple[str]]): Second ensemble de sous-ensembles

    Returns:
        float: La distance minimale d'édition entre ces deux ensembles
    """

    # TODO: convertir int en str pour id_msg

    # Récupération du nombre de sous-ensembles
    m: int = len(set_A)
    n: int = len(set_B)

    # Convertir les listes de sous-ensembles en listes de sets
    A: list[set[int]] = sorted([set(sorted([int(m) for m in subset])) for subset in set_A])
    B: list[set[int]] = sorted([set(sorted([int(m) for m in subset])) for subset in set_B])

    # Initialiser la matrice D de dimensions (m+1) x (n+1)
    D : list[list[float]] = [[0.0] * (n + 1) for _ in range(m + 1)]

    # Conditions de base
    for i in range(1, m + 1):
        D[i][0] = D[i-1][0] + len(A[i-1])
    for j in range(1, n + 1):
        D[0][j] = D[0][j-1] + len(B[j-1])

    # Remplir la matrice D
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            #
            cost_replace = dist_subsets(A[i-1], B[j-1])
            #
            D[i][j] = min(
                            D[i-1][j] + len(A[i-1]),    # Supprimer A[i-1]
                            D[i][j-1] + len(B[j-1]),    # Ajouter B[j-1]
                            D[i-1][j-1] + cost_replace  # Remplacer A[i-1] par B[j-1]
                        )

    # On renvoie le nombre de modifications minimales entre ces deux ensembles
    return D[m][n]

#
def get_sequence_separations(seq: list[int]) -> set[int]:
    """
    Retourne les positions où il y a une séparation dans une séquence donnée.

    Args:
        conv (list[int]): Une liste d'entiers représentant une séquence.

    Returns:
        set[int]: Un ensemble d'indices où des séparations sont observées.
    """

    separations: set[int] = set()

    #
    for i in range(1, len(seq)):
        if seq[i-1] != seq[i]:
            separations.add(i)

    return separations

#
def get_tp_fp_fn_from_two_sets(reference_set: set[int], try_set: set[int]) -> tuple[int, int, int]:
    """
    Calcule les nombres de vrais positifs, faux positifs et faux négatifs entre deux ensembles.

    Args:
        reference_set (set[int]): Ensemble de référence.
        try_set (set[int]): Ensemble à comparer avec l'ensemble de référence.

    Returns:
        tuple[int, int, int]: Un tuple contenant le nombre de vrais positifs, de faux positifs et de faux négatifs.
    """

    true_positives: int = len(try_set.intersection(reference_set))
    false_positives: int = len(try_set) - true_positives
    false_negatives: int = len(reference_set) - true_positives

    return (true_positives, false_positives, false_negatives)

#
def get_f1_score_from_tp_fp_fn(true_positives: int, false_positives: int, false_negatives: int) -> float:
    """
    Calcule le score F1 à partir des nombres de vrais positifs, faux positifs et faux négatifs.

    Args:
        true_positives (int): Nombre de vrais positifs.
        false_positives (int): Nombre de faux positifs.
        false_negatives (int): Nombre de faux négatifs.

    Returns:
        float: Le score F1, qui est une mesure combinée de précision et de rappel.
    """

    # Calcul de la précision
    P: float = 0
    if true_positives + false_positives != 0:
        P = float(true_positives) / float(true_positives + false_positives)

    # Calcul du rappel
    R: float = 0
    if true_positives + false_negatives != 0:
        R = float(true_positives) / float(true_positives + false_negatives)

    # Calcul du score F1
    F1: float = 0
    if P + R != 0:
        F1 = 2.0 * (P * R) / (P + R)

    # On renvoie le résultat
    return F1

#
def hash_string_to_int(s: str) -> int:
    """
    Convertit une chaîne de caractères en un entier en utilisant une fonction de hachage.

    Args:
        s (str): La chaîne de caractères à hacher.

    Returns:
        int: Un entier obtenu en hachant la chaîne et en prenant le modulo de 10^8.
    """

    sha1_hash: str = hashlib.sha1(s.encode("utf-8")).hexdigest()
    return int(sha1_hash, 16) % (10 ** 8)


#
T = TypeVar('T')

#
class FunctionResult(Generic[T]):
    """
    Ceci est le résultat d'une fonction, classe générale.
    """

    def __init__(self, return_values: T) -> None:

        # On stocke ici les potentielles valeurs de sortie de la fonction
        self.return_values: Optional[T] = return_values

    #
    def get_return_value(self) -> T:
        """Renvoie la valeur de retour de la fonction

        Returns:
            T: Valeur de retour de la fonction

        Raises:
            UserWarning: Cette fonction n'a pas de valeur de retour
        """

        if self.return_values is not None:
            return self.return_values

        else:
            raise UserWarning("Cette fonction n'a pas de valeur de retour !")


#
class ResultError(FunctionResult):
    """
    Si la fonction a échoué, on a une erreur.
    """

    def __init__(self, error_message: str) -> None:
        super().__init__(None)

        # Le message d'erreur, pour savoir plus précisément qu'est-ce qui s'est mal passé
        self.error_message: str = error_message

    #
    def get_error_message(self) -> str:
        """Renvoie le message d'erreur

        Returns:
            str: Le message d'erreur
        """
        return self.error_message


#
class ResultSuccess(FunctionResult, Generic[T]):
    """
    Si la fonction s'est bien passée, on n'a pas d'erreurs.
    """

    def __init__(self, return_values: Optional[T] = None) -> None:
        super().__init__(return_values)


#
class ConfigError(Exception):
    """
    Erreur de paramètres manquants dans un dictionnaire de configuration
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


#
class MissingFileError(Exception):
    """
    Erreur, un fichier demandé n'existe pas
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


#
class HFAutoModelError(Exception):
    """
    Erreur, problème lors du téléchargement, de l'enregistrement ou du chargement local d'un modèle ou d'un tokeniseur de hugging face, ceci peut être causé par un manque de permissions pour écrire/lire depuis la mémoire, d'un problème de nom du modèle demandé, qui n'est pas accessible ou n'existe pas, ou bien encore un problème de réseau, où cette machine n'arrive pas à se connecter aux serveurs de Hugging Face.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)



#
def visualize_clusters(distances_matrix: np.ndarray, n_clusters: int = -1) -> None:
    # Centrer la matrice des distances
    n = distances_matrix.shape[0]
    H = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * H.dot(distances_matrix ** 2).dot(H)

    # Décomposition en valeurs singulières (SVD)
    U, S, _ = np.linalg.svd(B)
    points_2d = U[:, :2] * np.sqrt(S[:2])

    # Visualisation des clusters
    plt.figure(figsize=(10, 8))

    if n_clusters > 1:
        # Simple clustering en se basant sur la k-means "maison"
        centroids = points_2d[np.random.choice(n, n_clusters, replace=False)]
        for _ in range(10):  # Nombre d'itérations pour k-means
            distances_to_centroids = np.linalg.norm(points_2d[:, np.newaxis] - centroids, axis=2)
            labels = np.argmin(distances_to_centroids, axis=1)
            centroids = np.array([points_2d[labels == k].mean(axis=0) for k in range(n_clusters)])

        plt.scatter(points_2d[:, 0], points_2d[:, 1], c=labels, cmap='viridis', s=50, alpha=0.7)
        plt.colorbar(label='Cluster Label')
    else:
        plt.scatter(points_2d[:, 0], points_2d[:, 1], s=50, alpha=0.7)

    plt.title('SVD-based 2D Visualization of Clusters')
    plt.xlabel('Component 1')
    plt.ylabel('Component 2')
    plt.show()
