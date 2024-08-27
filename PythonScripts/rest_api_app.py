"""
_summary_

Auteur: Nathan Cerisara
"""

from typing import Optional, Callable
import requests
import base64
import hashlib
import json
from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn


#
class WebhookData(BaseModel):
    message: str
    sender: str


#
class RestApiApp:
    """
    Classe principale pour l'application qui va intéragir avec l'API Rest de Rainbow, qui va écouter les requêtes entrantes (demandes de recherche, un message a été envoyé dans une bulle -> il faut le pré-traiter (cache d'embedding + cache de traduction))
    """

    #
    def __init__(self, config: dict) -> None:
        # Configurations
        self.config: dict = config
        self.config_dev_account_login_email: str = config["dev_account_login_email"]
        self.config_dev_account_login_password: str = config["dev_account_login_password"]
        self.config_application_id: str = config["application_id"]
        self.config_application_secret: str = config["application_secret"]
        self.config_rest_request_host_prefix: str = config["rest_request_host_prefix"]
        self.config_rest_protocol: str = config["rest_protocol"]
        self.config_rest_port: int = config["rest_port"]

        # Routes FastApi Requêtes entrantes
        self.fast_api_request_routes: dict[str, Callable] = {
            "/webhook": self.webhook
        }

        # Token d'authentification
        self.auth_token: Optional[str] = None

        # Instance de FastAPI
        self.fast_api_app = FastAPI()

        # Définir les routes
        for route, route_fn in self.fast_api_request_routes.items():
            self.fast_api_app.post(route)(route_fn)

    # Fonction pour récupérer le token d'authentification
    def authenticate(self) -> bool:
        """
        Authentification au Serveur de Rainbow via l'API Rest.

        Returns:
            bool: Renvoie True si l'on s'est bien connecté au serveur Rainbow via l'API Rest. Sinon, renvoie False.
        """

        # Encodage en base64
        auth = base64.b64encode(f"{self.config_dev_account_login_email}:{self.config_dev_account_login_password}".encode()).decode()
        app_auth = base64.b64encode(f"{self.config_application_id}:{hashlib.sha256((self.config_application_secret + self.config_dev_account_login_password).encode()).hexdigest()}".encode()).decode()

        # Envoi de la requête GET avec les en-têtes appropriés
        auth_response: Optional[dict]  = self.send_request("/api/rainbow/authentication/v1.0/login", {
            "Accept": "application/json",
            "Authorization": f"Basic {auth}",
            "x-rainbow-app-auth": f"Basic {app_auth}"
        })

        #
        if auth_response:
            self.auth_token = auth_response.get("token")
            print(f"Token d'authentification reçu, bien connecté !")
            return True
        else:
            print("Erreur lors de l'authentification")
            return False

    # Fonction pour vérifier si le token est encore valide
    def check_token(self) -> Optional[dict]:
        """
        Vérifie si le token est encore valide.

        Returns:
            dict: La réponse de l'API.
        """

        return self.send_request("/api/rainbow/authentication/v1.0/validator", {
            "Authorization": f"Bearer {self.auth_token}",
            "Accept": "application/json"
        })

    # Fonction pour renouveler le token d'authentification.
    def renew_token(self) -> None:
        """
        Renouvelle le token d'authentification.

        Returns:
            Optional[str]: Le nouveau token, ou None en cas d'erreur.
        """

        response: dict = self.send_request("/api/rainbow/authentication/v1.0/renew", {
            "Authorization": f"Bearer {self.auth_token}",
            "Accept": "application/json"
        })

        self.auth_token = response.get("token", None)

    #
    def get_all_room_containers(self) -> Optional[dict]:
        """
        _summary_

        Returns:
            Optional[dict]: _description_
        """

        return self.send_request("/api/rainbow/enduser/v1.0/rooms/containers", {
            "Authorization": f"Bearer {self.auth_token}",
            "Accept": "application/json"
        })

    #
    def get_all_users(self) -> Optional[dict]:
        """
        _summary_

        Returns:
            Optional[dict]: _description_
        """

        return self.send_request("/api/rainbow/admin/v1.0/users", {
            "Authorization": f"Bearer {self.auth_token}",
            "Accept": "application/json"
        })

    #
    def get_all_conversations(self, user_id: str) -> Optional[dict]:
        """
        _summary_

        Returns:
            Optional[dict]: _description_
        """

        return self.send_request(f"/api/rainbow/enduser/v1.0/users/{user_id}/conversations", {
            "Authorization": f"Bearer {self.auth_token}",
            "Accept": "application/json"
        })

    #
    def show_all_matching_messages_for_a_given_peer(self, user_id: str) -> Optional[dict]:
        """
        _summary_

        Returns:
            Optional[dict]: _description_
        """

        return self.send_request(f"/api/rainbow/enduser/v1.0/users/{user_id}/conversations/search/hits", {
            "Authorization": f"Bearer {self.auth_token}",
            "Accept": "application/json"
        })

    # Fonction pour envoyer une requête vers l'api
    def send_request(self, request_url: str, header_dict: dict, request_data: Optional[dict] = None) -> Optional[dict]:
        """
        Envoie une requête  d'utilisateur.

        Args:
            token (str): Token d'authentification.
            request_url (str): url pour la requête
            request_data (dict?): Données à envoyer avec la requête ? (Pas sûr du type de la variable, ni de si c'est le bon argument pour ca)

        Returns:
            dict: La réponse de l'API.
        """
        try:
            #
            full_url = f"{self.config_rest_protocol}{self.config_rest_request_host_prefix}:{self.config_rest_port}{request_url}"

            #
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Accept": "application/json"
            }

            #
            response = requests.get(
                url=full_url,
                headers=header_dict,
                data = request_data
            )
            response.raise_for_status()  # Lève une exception pour les erreurs HTTP
            return response.json()  # Retourne la réponse

        except requests.exceptions.RequestException as err:
            print(f"Erreur lors de la recherche: {err}")
            return None

    # Fonction qui va recevoir toutes les requêtes pour les traiter
    async def webhook(data: WebhookData):
        """
        Fonction qui va recevoir toutes les requêtes pour les traiter

        Args:
            data (WebhookData): _description_
        """

        print(f"Requête reçue: {data}")

        # Traitement des requêtes ici

    # On va lancer l'application, qui va écouter les requêtes entrantes
    def api_run(self) -> None:
        """
        On va lancer l'écoute des requêtes depuis l'api
        """

        #
        uvicorn.run(app, host="0.0.0.0")


#
if __name__ == "__main__":

    # On charge la config
    config_dict: dict = {}
    with open("rest_api_config.json", "r", encoding="utf-8") as f:
        config_dict = json.load(f)

    # On crée notre application
    app: RestApiApp = RestApiApp(config_dict)

    # On essaie de se connecter
    if not app.authenticate():
        raise UserWarning("Cannot connect to Rainbow Rest API")

    # Test
    print(f"app.get_all_room_containers() -> {app.get_all_room_containers()}")
    res: dict = app.get_all_users()
    print(f"app.get_all_users() -> {res}")
    first_user_id: str = res["data"][0]["id"]
    print(f"app.get_all_conversations(user_id={first_user_id}) -> {app.get_all_conversations(user_id=first_user_id)}")
    print(f"app.show_all_matching_messages_for_a_given_peer(user_id={first_user_id}) -> {app.show_all_matching_messages_for_a_given_peer(user_id=first_user_id)}")

    # On lance l'écoute de l'application
    app.api_run()
