"""
_summary

Auteur: Nathan Cerisara
"""


from typing import cast, Callable
from dataclasses import dataclass

from torch import Tensor
import torch.nn.functional as F
import torch

from lib import escapeCharacters

from profiling import profiling_task_start, profiling_last_task_ends


#
@dataclass
class MessageEmbedding:

    # Le texte initial
    txt: str

    # n = nombre de tokens
    # d = dimension de l'embedding

    # Le texte tokenisé - Dimension: (n, dtype=int)
    tokens: Tensor

    # Le masque des tokens pour savoir sur quoi porter l'attention - Dimension: (n, dtype=float)
    attention_mask: Tensor

    # La dernière couche dans le modèle d'embedding - Dimension: (n, d, dtype=float)
    last_hidden_state: Tensor

    #
    def export_to_dict(self) -> dict:
        return {
            "txt": self.txt,
            "tokens": self.tokens.tolist(),
            "attention_mask": self.attention_mask.tolist(),
            "last_hidden_state": self.last_hidden_state.tolist()
        }


#
def load_message_embedding_from_dict(me_dict: dict) -> MessageEmbedding:
    txt: str = me_dict["txt"]
    tokens: Tensor = Tensor(me_dict["tokens"])
    attention_mask: Tensor = Tensor(me_dict["attention_mask"])
    last_hidden_state: Tensor = Tensor(me_dict["last_hidden_state"])
    #
    return MessageEmbedding(txt, tokens, attention_mask, last_hidden_state)

#
#Mean Pooling - Take attention mask into account for correct averaging
def mean_pooling(model_output: Tensor, attention_mask: Tensor) -> Tensor:
    token_embeddings = model_output[0] #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

#
# Moyenne des vecteurs d'embeddings, en prenant en compte le masque d'attention
def average_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    #
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=0) / attention_mask.sum(dim=0)[..., None]

#
def euclidian_norm(e1: torch.Tensor, e2: torch.Tensor) -> float:
    return cast(float, torch.norm(e1 - e2).item())

#
def dist_euclidian_norm(me1: MessageEmbedding, me2: MessageEmbedding, algo_config_dict: dict) -> float:
    """
    Calcule la distance euclidienne classique entre deux embeddings de messages
    On va calculer la distance euclidienne sur la moyenne des embeddings des tokens pour chaque message.

    Args:
        me1 (MessageEmbedding): Embedding 1
        me2 (MessageEmbedding): Embedding 2

    Returns:
        float: Norme euclidienne entre e1 et e2
    """

    # Profiling 1 - start
    # profiling_task_start(f"average_calc_|_{escapeCharacters(me1.txt)}_|_{escapeCharacters(me2.txt)}")

    e1: torch.Tensor = average_pool(me1.last_hidden_state, me1.attention_mask)
    e2: torch.Tensor = average_pool(me2.last_hidden_state, me2.attention_mask)

    # Profiling 1 - end
    # profiling_last_task_ends()

    # Profiling 1 - start
    # profiling_task_start(f"normalizing_|_{escapeCharacters(me1.txt)}_|_{escapeCharacters(me2.txt)}")

    # Normalize ?
    e1 = F.normalize(e1, p=2, dim=0)
    e2 = F.normalize(e2, p=2, dim=0)

    # Profiling 1 - end
    # profiling_last_task_ends()

    # Profiling 1 - start
    # profiling_task_start(f"euclidian_norm_|_{escapeCharacters(me1.txt)}_|_{escapeCharacters(me2.txt)}")

    # On renvoie donc la norme euclidienne entre ces deux vecteurs
    res: float = euclidian_norm(e1, e2)

    # Profiling 1 - end
    # profiling_last_task_ends()

    return res

#
def dist_cosine(me1: MessageEmbedding, me2: MessageEmbedding, algo_config_dict: dict) -> float:
    """
    Calcule la distance euclidienne classique entre deux embeddings de messages
    On va calculer la distance euclidienne sur la moyenne des embeddings des tokens pour chaque message.

    Args:
        me1 (MessageEmbedding): Embedding 1
        me2 (MessageEmbedding): Embedding 2

    Returns:
        float: Distance cosinus entre e1 et e2
    """

    # Profiling 1 - start
    # profiling_task_start(f"average_calc_|_{escapeCharacters(me1.txt)}_|_{escapeCharacters(me2.txt)}")

    e1: torch.Tensor = average_pool(me1.last_hidden_state, me1.attention_mask)
    e2: torch.Tensor = average_pool(me2.last_hidden_state, me2.attention_mask)

    # Profiling 1 - end
    # profiling_last_task_ends()

    # Profiling 1 - start
    # profiling_task_start(f"normalizing_|_{escapeCharacters(me1.txt)}_|_{escapeCharacters(me2.txt)}")

    # Normalize ?
    e1 = F.normalize(e1, p=2, dim=0)
    e2 = F.normalize(e2, p=2, dim=0)

    # Profiling 1 - end
    # profiling_last_task_ends()

    # Profiling 1 - start
    # profiling_task_start(f"cos_calc_|_{escapeCharacters(me1.txt)}_|_{escapeCharacters(me2.txt)}")

    cosine: torch.Tensor = torch.dot(e1, e2) / (torch.norm(e1) * torch.norm(e2))

    # On renvoie donc le taux de colinéarité entre ces deux vecteurs
    res: float = -cast(float, cosine.item())

    # Profiling 1 - end
    # profiling_last_task_ends()

    return res

#
def dist_poor_attention(me1: MessageEmbedding, me2: MessageEmbedding, algo_config_dict: dict) -> float:

    # Profiling 1 - start
    # profiling_task_start(f"distance_poor_attention_|_{escapeCharacters(me1.txt)}_|_{escapeCharacters(me2.txt)}")

    # TODO: vectoriser les calculs pour les rendre plus efficaces

    close_tokens: list[tuple[int, int, float]] = []

    # On parcours tous les tokens du premier message
    for i in range(len(me1.last_hidden_state)):

        # On vérifie que ce token est bien dans le masque d'attention
        if not me1.attention_mask[i]:
            continue

        # On parcours tous les tokens du second message
        for j in range(len(me2.last_hidden_state)):

            # On vérifie que ce token est bien dans le masque d'attention
            if not me2.attention_mask[i]:
                continue

            # On récupère les vecteurs
            e_i: torch.Tensor = me1.last_hidden_state[i]
            e_j: torch.Tensor = me2.last_hidden_state[j]

            # On les normalise
            e_i = F.normalize(e_i, p=2, dim=0)
            e_j = F.normalize(e_j, p=2, dim=0)

            # On calcule la distance entre ces deux éléments
            d = euclidian_norm(e_i, e_j)

            # Solution 0 : Treshold classique
            if d < 1.1:
                # On considère donc ces vecteurs comme "proches"
                close_tokens.append((i, j, d))

    # Si pas de vecteurs "proches"
    # On renvoie une très grande distance
    if len(close_tokens) == 0:
        return 10000.0

    # Sinon, on renvoie la moyenne des distances "proches"
    res: float = sum([t[2] for t in close_tokens])/float(len(close_tokens))

    # Profiling 1 - end
    # profiling_last_task_ends()

    return res


#
DISTANCES_FUNCTIONS: dict[str, Callable[[MessageEmbedding, MessageEmbedding, dict], float]] = {
    "euclidian": dist_euclidian_norm,
    "cosine": dist_cosine,
    "poor_attention": dist_poor_attention
}

