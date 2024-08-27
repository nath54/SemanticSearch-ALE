"""
_summary

Auteur: Nathan Cerisara
"""

from typing import Optional

import os
import torch
from transformers import AutoModel, AutoTokenizer
from optimum.onnxruntime import ORTModelForFeatureExtraction, QuantizationConfig
from optimum.onnxruntime import ORTOptimizer, ORTQuantizer
from optimum.onnxruntime.configuration import OptimizationConfig, AutoQuantizationConfig

from config import Config
from lib import HFAutoModelError
from lib import escapeCharacters
from lib_embedding import MessageEmbedding

from profiling import profiling_task_start, profiling_last_task_ends


#
class EmbeddingCalculator():
    """
    Conteneur pour modèle de type Bert ou autres compatibles
    """

    #
    def __init__(self, config: dict, conf: Config) -> None:

        # Profiling 1 - start
        # profiling_task_start(f"emb_calc_init_[{escapeCharacters(config['model_name'])}]")

        self.models_path: str = conf.models_path
        self.model_name: str = config["model_name"]
        self.model_type: str = config["model_type"]
        self.model: AutoModel | ORTModelForFeatureExtraction | None = None
        self.embeddings: torch.nn.Module | None = None
        self.tokenizer: AutoTokenizer | None = None
        self.use_cuda: bool = int(config["use_cuda"]) == 1
        #
        if self.use_cuda and not torch.cuda.is_available():
            raise SystemError("Try to use cuda, but cuda is not available")
        #
        self.device: str = "cpu"
        if self.use_cuda:
            self.device = "cuda"
        #
        self.model_optimisations: str = ""
        if "model_optimisations" in config:
            self.model_optimisations = config["model_optimisations"]

        # Profiling 2 - start
        # profiling_task_start(f"emb_get_model_[{escapeCharacters(config['model_name'])}]")

        self.get_model()

        # Profiling 2 - end
        # profiling_last_task_ends()

        # Profiling 1 - end
        # profiling_last_task_ends()

    #
    def get_attention_from_model(self) -> torch.nn.Module | None:
        """
        Renvoie la première couche d'attention du modèle

        Returns:
            torch.nn.Module | None: La première couche d'attention
        """

        # Si le modèle n'existe pas, on ne peut rien faire
        if self.model is None:
            return None

        # Sinon, on peut renvoyer la première couche d'attention
        return self.model.encoder.layer[0].attention

    #
    def get_model(self) -> None:
        """
        Charge un modèle téléchargé ou le télécharge au besoin.
        """

        if self.model_optimisations == "optimum":

            # On teste si le dossier contenant le modèle existe ou pas sur le disque dur
            #   et on appelle ensuite la bonne fonction correspondante
            if not os.path.exists(f"./{self.models_path}/{self.model_name}/model.onnx"):
                self.download_model()

            if not os.path.exists(f"./{self.models_path}/{self.model_name}/model-quantized.onnx"):
                self.load_downloaded_model(pre_optimum=True)
                self.optimize_optimum()

            self.load_downloaded_model(pre_optimum=False)

        else:

            # On teste si le dossier contenant le modèle existe ou pas sur le disque dur
            #   et on appelle ensuite la bonne fonction correspondante
            if not os.path.exists(f"./{self.models_path}/{self.model_name}"):
                self.download_model()
            else:
                self.load_downloaded_model()

            # # Improve models
            # self.model.to_bettertransformer()

    #
    def load_downloaded_model(self, pre_optimum: bool = True, verbose=True) -> None:
        """
        Charge un modèle qui a déjà été téléchargé.

        Raises:
            SystemError: Erreur lors du chargement du modèle.
            SystemError: Erreur lors du chargement du tokeniseur.
        """

        #
        if verbose:
            print(f"Loading local model {self.model_name}...")

        # Charge depuis le disque dur le modèle
        if self.model_optimisations == "optimum":
            if pre_optimum or not os.path.exists(f"./{self.models_path}/{self.model_name}/model-quantized.onnx"):
                self.model = ORTModelForFeatureExtraction.from_pretrained(f"./{self.models_path}/{self.model_name}", file_name="model.onnx")
            else:
                self.model = ORTModelForFeatureExtraction.from_pretrained(f"./{self.models_path}/{self.model_name}", file_name="model-quantized.onnx")
        else:
            self.model = AutoModel.from_pretrained(f"./{self.models_path}/{self.model_name}")

        # On vérifie que le modèle a bien été chargé
        if not self.model:
            raise HFAutoModelError("Erreur lors du chargement du modèle.")

        # Charge depuis le disque dur le tokeniseur
        self.tokenizer = AutoTokenizer.from_pretrained(f"./{self.models_path}/{self.model_name}")

        # On vérifie que le tokeniseur a bien été chargé
        if not self.tokenizer:
            raise HFAutoModelError("Erreur lors du chargement du tokeniseur.")

        #
        if verbose:
            print(f"Le modèle {self.model_name} a bien été chargé avec succès.")

    #
    def download_model(self, verbose=True) -> None:
        """
        Télécharge un modèle.

        Raises:
            HFAutoModelError: Erreur lors du téléchargement du modèle
            HFAutoModelError: Erreur lors du téléchargement du Tokeniseur
        """

        #
        if verbose:
            print(f"Téléchargement du modèle {self.model_name}...")

        if self.model_optimisations == "optimum":
            self.model = ORTModelForFeatureExtraction.from_pretrained(self.model_name)
        else:
            # On télécharge le modèle
            self.model = AutoModel.from_pretrained(self.model_name)

        # On vérifie si le modèle a bien été téléchargé
        if not self.model:
            raise HFAutoModelError(f"Erreur lors du téléchargement du modèle depuis {self.model_name}")

        # On télécharge le tokeniseur
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

        # On vérifie si le tokeniseur a bien été téléchargé
        if not self.tokenizer:
            raise HFAutoModelError(f"Erreur lors du téléchargement du Tokeniseur depuis {self.model_name}")

        # On enregistre sur le disque dur le modèle
        self.model.save_pretrained(f"./{self.models_path}/{self.model_name}")

        # On enregistre sur le disque dur le tokeniseur
        self.tokenizer.save_pretrained(f"./{self.models_path}/{self.model_name}")

        #
        if verbose:
            print(f"{self.model_name} modèle bien téléchargé et enregistré à l'endroit ./{self.models_path}/{self.model_name}")

    #
    def optimize_optimum(self) -> None:

        if self.model is None:
            raise UserWarning("Error while loading optimizer!")

        # On ne peut pas optimiser qui n'a pas d'attribut "pipeline_task"
        if not hasattr(self.model, "pipeline_task"):
            return

        # create ORTOptimizer and define optimization configuration
        optimizer: ORTOptimizer = ORTOptimizer.from_pretrained(self.model_name, feature=self.model.pipeline_task)
        optimization_config: OptimizationConfig = OptimizationConfig(optimization_level=99) # enable all optimizations

        if optimizer is None:
            raise UserWarning("Error while loading optimizer!")

        # apply the optimization configuration to the model
        optimizer.export(
            onnx_model_path=f"./{self.models_path}/{self.model_name}/model.onnx",
            onnx_optimized_model_output_path=f"./{self.models_path}/{self.model_name}/model-optimized.onnx",
            optimization_config=optimization_config,
        )

        # create ORTQuantizer and define quantization configuration
        dynamic_quantizer: ORTQuantizer = ORTQuantizer.from_pretrained(self.model_name, feature=self.model.pipeline_task)
        dqconfig: QuantizationConfig = AutoQuantizationConfig.avx512_vnni(is_static=False, per_channel=False)

        if dynamic_quantizer is None:
            raise UserWarning("Error while dynamic quantizer !")

        # apply the quantization configuration to the model
        dynamic_quantizer.export(
            onnx_model_path=f"./{self.models_path}/{self.model_name}/model-optimized.onnx",
            onnx_quantized_model_output_path=f"./{self.models_path}/{self.model_name}/model-quantized.onnx",
            quantization_config=dqconfig,
        )

    #
    def get_messages_embeddings(self, messages: list[str]) -> list[MessageEmbedding]:
        """
        Fonction qui va appeler le modèle pour générer les embeddings, va utiliser le modèle directement sur le batch messages.
        Fonction adaptée pour les modèles de type XLM_Roberta

        Args:
            messages (list[str]): Liste des messages à Tokeniser

        Returns:
            list[MessageEmbedding]: Liste des vecteurs d'embeddings de chaque texte
        """

        # On vérifie que tout le système est bien en place
        if self.tokenizer is None:
            raise SystemError("Error, no tokenizer!")

        if self.model is None:
            raise SystemError("Error, no model!")

        # Liste des embeddings calculés pour chaque message dans l'ordre
        embeddings: list[MessageEmbedding] = []

        # torch.no_grad() signifie que l'on est bien en mode inférence
        with torch.no_grad():

            # Profiling 1 - start
            # profiling_task_start(f"embedding_tokenization_|_{self.model_name}_|_{escapeCharacters(messages[0])}")

            # On tokenize les messages
            inputs = self.tokenizer(messages,
                                    max_length=512,
                                    truncation=True,
                                    padding='max_length',
                                    return_tensors="pt",
                                    return_attention_mask=True)

            # Profiling 1 - end
            # profiling_last_task_ends()

            # Profiling 1 - start
            # profiling_task_start(f"embedding_model_|_{self.model_name}_|_{escapeCharacters(messages[0])}")

            # On utilise le modèle sur le texte tokenisé
            outputs = self.model(**inputs)

            # Profiling 1 - end
            # profiling_last_task_ends()

            # Profiling 1 - start
            # profiling_task_start(f"embedding_prepare_return_results_|_{self.model_name}_|_{escapeCharacters(messages[0])}")

            # On récupère la derniere couche cachée (du dernier FeedForward du dernier encodeur sans doute)
            #   celle que l'on utilise comme embedding
            last_hidden_state: torch.Tensor = outputs.last_hidden_state

            # On convertit les vecteurs pytorch en vecteurs numpy qui retournent sur le CPU
            embeddings += [
                            MessageEmbedding(
                                txt=messages[i],
                                tokens=inputs["input_ids"][i],
                                attention_mask=inputs["attention_mask"][i],
                                last_hidden_state=last_hidden_state[i]
                            )
                            for i in range(len(messages))
                        ]

            # Profiling 1 - end
            # profiling_last_task_ends()

        # On renvoie le résultat
        return embeddings

    #
    def get_embeddings(self, messages: list[str]) -> list[MessageEmbedding]:
        """
        Fonction qui va appeler le modèle pour générer les embeddings, va utiliser le modèle directement sur le batch messages.

        Args:
            messages (list[str]): Liste des messages à Tokeniser

        Returns:
            list[MessageEmbedding]: Liste des vecteurs d'embeddings de chaque texte
        """

        #
        pre_processed_messages: list[str] = messages

        if self.model_type == "e5":
            pre_processed_messages = ["query: " + m for m in messages]

        return self.get_messages_embeddings(pre_processed_messages)

