using System;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Collections.Generic;
using System.Text.Json;
using Rainbow.SimpleJSON;
using Rainbow;
using static System.Net.Mime.MediaTypeNames;
using System.IO;
using Sharp.Xmpp.Client;
using static System.Runtime.InteropServices.JavaScript.JSType;
using System.Security.Cryptography.X509Certificates;
using System.Runtime.InteropServices;



static class Constants
{
    /// <summary>
    /// Classe qui contient toutes les constantes qui seront utilisées dans ce code.
    /// </summary>

    // Constante qui indique la taille maximale d'un message que l'on peut recevoir depuis le serveur socket python
    public const int SOCKET_MAX_MSG_SIZE = 16384;
}

public class UsefulFunctions
{
    /// <summary>
    /// Fonction qui convertit un message de type Rainbow.Model.Message en un dictionnaire qui sera compréhensible par le serveur.
    /// </summary>
    /// <param name="message">Message à convertir</param>
    /// <param name="rbSDKApi">Un lien vers le rainbowSDKApi qui contient des fonctions pour convertir des JID en ID</param>
    /// <returns>Le message converti en dictionnaire</returns>
    public async Task<Dictionary<string, object>> ConvertMessageToDictToSendToSocketServer(Rainbow.Model.Message message, RainbowSDKApi rbSDKApi)
    {
        // On récupère les infos sur l'auteur du message et de la bulle dont le message est
        string author_id = await rbSDKApi.getContactIdFromContactJid(message.FromJid);
        string author_name = await rbSDKApi.GetContactNameById(author_id);
        string bubble_id = await rbSDKApi.GetBubbleIdFromBubbleJid(message.FromBubbleJid);
        string bubble_name = await rbSDKApi.GetBubbleNameById(bubble_id);

        // On récupère l'id du message dont ce message est une réponse s'il existe
        string answered_message_id = "";
        if (message.ReplyMessage != null)
        {
            answered_message_id = message.ReplyMessage.Id;
        }

        // On renvoie le dictionnaire
        return new Dictionary<string, object>
        {
            ["id"] = message.Id,
            ["content"] = message.Content,
            ["date"] = message.Date,
            ["author_id"] = author_id,
            ["author_name"] = author_name,
            ["bubble_id"] = bubble_id,
            ["bubble_name"] = bubble_name,
            ["answered_message_id"] = answered_message_id
        };
    }

    /// <summary>
    /// Fonction qui convertit une liste de messages de type Rainbow.Model.Message en une liste de dictionnaires qui sera compréhensible par le serveur.
    /// </summary>
    /// <param name="message_list">Liste des messages à convertir</param>
    /// <param name="rbSDKApi">Un lien vers le rainbowSDKApi qui contient des fonctions pour convertir des JID en ID</param>
    /// <returns>La liste des messages convertis en dictionnaire</returns>
    public async Task<List<Dictionary<string, object>>> ConvertMessageListToSendToSocketServer(List<Rainbow.Model.Message> message_list, RainbowSDKApi rbSDKApi)
    {
        List<Dictionary<string, object>> converted_list = [];
        foreach (Rainbow.Model.Message msg in message_list)
        {
            converted_list.Add( await ConvertMessageToDictToSendToSocketServer(msg, rbSDKApi) );
        }
        return converted_list;
    }
}


public class JsonConverter
{
    public Dictionary<string, JsonElement> ConvertJsonElementToDictionary(JsonElement jsonElement)
    {
        var dictionary = new Dictionary<string, JsonElement>();

        foreach (var property in jsonElement.EnumerateObject())
        {
            dictionary.Add(property.Name, property.Value);
        }

        return dictionary;
    }

    public Dictionary<string, string> ConvertJsonElementToDictionaryString(JsonElement jsonElement)
    {
        var dictionary = new Dictionary<string, string>();

        foreach (var property in jsonElement.EnumerateObject())
        {
            string? value = property.Value.GetString();
            if(value == null)
            {
                value = "";
            }
            dictionary.Add(property.Name, value);
        }

        return dictionary;
    }
}


public class Config
{
    /// <summary>
    /// Classe qui contient toutes les éléments de configurations de cette application
    /// </summary>

    // Elements pour la connection à l'api de rainbow
    public string dev_account_login_email = "";
    public string dev_account_login_password = "";
    public string application_id = "";
    public string application_secret = "";
    public string api_host = "";

    // Elements pour la connection au socket python
    public string python_ws_adress = "";
    public int python_ws_port = 0;
    public string socket_messages_delimiter = "";

    // Element pour l'application de base
    public string rbi_name = "";
    public int nb_msgs_batch = 0;
    public string bot_user_id = "";
    public string on_bot_connection_message = "";
    public string on_bot_disconnection_message = "";

    /// <summary>
    /// Constructeur de la classe. Initialisation de la config.
    /// </summary>
    /// <param name="config_file_path">Chemin du fichier de configuration à charger.</param>
    public Config(string config_file_path)
    {

        // On récupère le texte du fichier de configuration
        string jsonString = File.ReadAllText(config_file_path);
        // On parse ce texte en dictionnaire
        var dictionary = JsonSerializer.Deserialize<Dictionary<string, string>>(jsonString);
        // S'il n'y a pas de problèmes
        if(dictionary != null)
        {
            // On récupère toutes les valeurs (et on convertit vers le type souhaité selon le type de la variable)
            this.dev_account_login_email = dictionary.GetValueOrDefault("bot_account_login_email", "");
            this.dev_account_login_password = dictionary.GetValueOrDefault("bot_account_login_password", "");
            this.application_id = dictionary.GetValueOrDefault("application_id", "");
            this.application_secret = dictionary.GetValueOrDefault("application_secret", "");
            this.api_host = dictionary.GetValueOrDefault("api_host", "");
            this.python_ws_adress = dictionary.GetValueOrDefault("python_ws_adress", "");
            this.python_ws_port = int.Parse(dictionary.GetValueOrDefault("python_ws_port", "0"));
            this.socket_messages_delimiter = dictionary.GetValueOrDefault("socket_messages_delimiter", "");
            this.rbi_name = dictionary.GetValueOrDefault("rbi_name", "");
            this.nb_msgs_batch = int.Parse(dictionary.GetValueOrDefault("nb_msgs_batch", "256"));
            this.bot_user_id = dictionary.GetValueOrDefault("bot_user_id", "");
            this.on_bot_connection_message = dictionary.GetValueOrDefault("on_bot_connection_message", "");
            this.on_bot_disconnection_message = dictionary.GetValueOrDefault("on_bot_disconnection_message", "");
        }
    }
}



public class RainbowSDKApi
{
    /// <summary>
    /// Classe principale qui va s'occuper de la connexion à l'api de Rainbow, et qui va gérer les différents événemments reçus.
    /// </summary>

    // Configuration
    readonly Config config;
    // Fonctions Utilitaires
    readonly UsefulFunctions usefulFunctions;
    // Indique si le programme est arreté / doit s'arrêter.
    bool endProgram = false;
    // Indique si l'on est actuellement connecté à l'api de rainbow ou non.
    bool authentifiedToApi = false;
    // Indique si tout a bien été initialisé du côté de l'api de rainbow
    bool programInitialized = false;
    // Application SSK Rainbow
    readonly Rainbow.Application rbApp;
    // Module d'auto-reconnection à l'api de Rainbow
    readonly Rainbow.AutoReconnection rbAutoReconnection;
    // Module de management des bulles dans Rainbow
    readonly Rainbow.Bubbles rbBubbles;
    // Module de management des conversations dans Rainbow
    readonly Rainbow.Conversations rbConversations;
    // Module de management des contacts dans Rainbow
    readonly Rainbow.Contacts rbContacts;
    // Module de management des messages dans Rainbow
    readonly Rainbow.InstantMessaging rbInstantMessaging;

    // Fonction pour envoyer des messages au serveur socket python
    private readonly Func<Dictionary<string, object>, Task<bool>> send_to_socket_server;

    // Cache (au cas ou il n'y en a pas déjà dans le SDK) pour accélérer la recherche d'ids de contacts, car  j'en fait beaucoup dans ce script
    private Dictionary<string, string> CacheContactsIdFromJid = [];

    /// <summary>
    /// Constructeur - Initialialisation des variables de base de la classe.
    /// </summary>
    /// <param name="config">Configuration générale de cette application (Api SDK Rainbow + Socket Python)</param>
    public RainbowSDKApi(Config config, UsefulFunctions usefulFunctions, Func<Dictionary<string, object>, Task<bool>> send_to_socket_server)
    {
        //
        this.send_to_socket_server = send_to_socket_server;
        //
        this.config = config;
        this.usefulFunctions = usefulFunctions;
        this.rbApp = new Rainbow.Application();
        this.rbAutoReconnection = this.rbApp.GetAutoReconnection();
        this.rbBubbles = this.rbApp.GetBubbles();
        this.rbConversations = this.rbApp.GetConversations();
        this.rbContacts = this.rbApp.GetContacts();
        this.rbInstantMessaging = this.rbApp.GetInstantMessaging();
    }

    /// <summary>
    /// Lancement de l'api SDK Rainbow - Connection à l'api
    /// </summary>
    public void Run()
    {

        Console.WriteLine("Début Lancement Rainbow SDK Api...");

        // Set events that we want to follow
        this.rbApp.AuthenticationFailed += RbApplication_AuthenticationFailed; // This method will be called when the authentication process will fail
        this.rbApp.AuthenticationSucceeded += RbApplication_AuthenticationSucceeded; // This method will be called when the authentication process will succeed
        this.rbApp.ConnectionStateChanged += RbApplication_ConnectionStateChanged; // This method will be called when the Connection State will change
        this.rbApp.InitializationPerformed += RbApplication_InitializationPerformed; // This method will be called when the Initialization process will succeed


        // Set events that we want to follow from Rainbow.AutoReconnection
        this.rbAutoReconnection.Started += RbAutoReconnection_Started; // This method will be called when the AutoReconnection service is started
        this.rbAutoReconnection.Cancelled += RbAutoReconnection_Cancelled; // This method will be called when the AutoReconnection service is cancelled / stopped
        this.rbAutoReconnection.MaxNbAttemptsReached += RbAutoReconnection_MaxNbAttemptsReached; // This method will be called when the AutoReconnection service tried too many times to reconnect to the server
        this.rbAutoReconnection.OneNetworkInterfaceOperational += RbAutoReconnection_OneNetworkInterfaceOperational; // This method will be called when the AutoReconnection service has found at least one network interface which is "operational". Event used onkly if CheckNetworkInterface is set to True
        this.rbAutoReconnection.TokenExpired += RbAutoReconnection_TokenExpired; // This method will be called when the AutoReconnection service when the authentication token has expired.
        this.rbAutoReconnection.MaxNbAttempts = 10;

        // Set events that we want to follow from Rainbow.InstantMessaging
        this.rbInstantMessaging.MessageReceived += RbInstantMessaging_MessageReceived; // This method will be called when the InstantMessaging service will receive a new message

        this.rbApp.SetApplicationInfo(this.config.application_id, this.config.application_secret);
        this.rbApp.SetHostInfo(this.config.api_host);

        // Start login
        this.rbApp.Login(this.config.dev_account_login_email, this.config.dev_account_login_password);

        Console.WriteLine("All API authentification requests sent, waiting for result...");

        // => Here, the code continues immediately since the Login method is asynchronous.

        // We need loop until we want to end the program.
        // If this loop is not done, the program will exit before the login process has ended - due to error (bad pwd for example) or on success
        do
        {
            Thread.Sleep(100);

        } while (!this.endProgram && !this.programInitialized);
    }

    /// <summary>
    /// Envoie un message indiquant que le bot est connecté dans l'une des bulles
    /// </summary>
    public async Task<bool> SendConnectionMessage()
    {
        List<Rainbow.Model.Bubble>? bubble_lists = await GetAllBubbles();
        if (bubble_lists == null || bubble_lists.Count == 0)
        {
            return false;
        }
        Rainbow.Model.Conversation? conv = await GetConversationByBubbleId(bubble_lists[0].Id);
        if (conv == null)
        {
            return false;
        }
        this.rbInstantMessaging.SendMessageToConversationId(conv.Id, this.config.on_bot_connection_message, []);

        return true;
    }

    /// <summary>
    /// Envoie un message indiquant que le bot est déconnecté dans l'une des bulles
    /// </summary>
    public async Task<bool> SendDisconnectionMessage()
    {
        List<Rainbow.Model.Bubble>? bubble_lists = await GetAllBubbles();
        if (bubble_lists == null || bubble_lists.Count == 0)
        {
            return false;
        }
        Rainbow.Model.Conversation? conv = await GetConversationByBubbleId(bubble_lists[0].Id);
        if (conv == null)
        {
            return false;
        }
        this.rbInstantMessaging.SendMessageToConversationId(conv.Id, this.config.on_bot_disconnection_message, []);
        return true;
    }

    /// <summary>
    /// Evenement qui indique que tout a bien été initialisé du côté de l'api sdk rainbow, on peut continuer la suite.
    /// </summary>
    /// <param name="sender"></param>
    /// <param name="e">Paramètres de l'évenement.</param>
    void RbApplication_InitializationPerformed(object? sender, EventArgs e)
    {
        // On affiche un message dans la console pour que suivre ce qu'il se passe
        Console.WriteLine($"InitializationPerformed");

        // On indique au programme que tout a bien été initialisé
        this.programInitialized = true;

        // DEBUG | TEST // On envoie un message lorsque l'on est connecté dans la première conversation que l'on trouve
        Task.Run( async () =>
        {
            await SendConnectionMessage();
        });

    }

    /// <summary>
    /// Evenement qui indique que l'état de la connexion a changé.
    /// </summary>
    /// <param name="sender"></param>
    /// <param name="e">Paramètres de l'évenement.</param>
    void RbApplication_ConnectionStateChanged(object? sender, Rainbow.Events.ConnectionStateEventArgs e)
    {
        // On affiche un message dans la console pour que suivre ce qu'il se passe
        Console.WriteLine($"ConnectionStateChanged: [{e.ConnectionState.State}]");

        // Si jamais la connexion est déconnectée, on quitte le programme.
        if (e.ConnectionState.State == Rainbow.Model.ConnectionState.Disconnected)
        {
            // On indique au programme qu'il doit s'arrêter
            this.endProgram = true;
        }
    }

    /// <summary>
    /// Evenement qui indique que le processus d'authentification a bien réussi.
    /// </summary>
    /// <param name="sender"></param>
    /// <param name="e">Paramètres de l'évenement.</param>
    void RbApplication_AuthenticationSucceeded(object? sender, EventArgs e)
    {
        // On affiche un message dans la console pour que suivre ce qu'il se passe
        Console.WriteLine($"AuthenticationSucceeded");

        // On indique que l'on est bien authentifié à l'api
        this.authentifiedToApi = true;
    }

    /// <summary>
    /// Evenement qui se produit lors du processus d'authentification lorsque l'authentification a échouée.
    /// </summary>
    /// <param name="sender"></param>
    /// <param name="e">Paramètres de l'évenement.</param>
    void RbApplication_AuthenticationFailed(object? sender, Rainbow.Events.SdkErrorEventArgs e)
    {
        // On affiche un message dans la console pour que suivre ce qu'il se passe
        Console.WriteLine($"AuthenticationFailed\r\n[{e.SdkError}");

        // On indique au programme qu'il doit s'arrêter
        this.endProgram = true;
    }

    /// <summary>
    /// Evenement qui se produit lorsque le service d'auto-reconnexion a été annulé / s'est arrêté.
    /// </summary>
    /// <param name="sender"></param>
    /// <param name="e">Paramètres de l'évenement.</param>
    void RbAutoReconnection_Cancelled(object? sender, Rainbow.Events.StringEventArgs e)
    {
        // On récupère les informations de pourquoi cela s'est arrêté
        var connectionState = this.rbAutoReconnection.GetServerDisconnectionInformation();
        // On affiche un message dans la console pour que suivre ce qu'il se passe
        Console.WriteLine($"AutoReconnection service has been cancelled / stopped - Reason:[{e.Value}] - connectionState:[{connectionState}] ");

        // On indique au programme qu'il doit s'arrêter
        endProgram = true;
    }

    /// <summary>
    /// Evenement qui se produit lors du processus d'auto-reconnexion lorsque le processus d'auto-reconnexion a commencé.
    /// </summary>
    /// <param name="sender"></param>
    /// <param name="e">Paramètres de l'évenement.</param>
    void RbAutoReconnection_Started(object? sender, EventArgs e)
    {
        // On affiche un message dans la console pour que suivre ce qu'il se passe
        Console.WriteLine($"AutoReconnection service has started");
    }

    /// <summary>
    /// Evenement qui se produit lors du processus d'auto-reconnexion lorsque le token d'authentification a expiré.
    /// </summary>
    /// <param name="sender"></param>
    /// <param name="e">Paramètres de l'évenement.</param>
    void RbAutoReconnection_TokenExpired(object? sender, EventArgs e)
    {
        // On affiche un message dans la console pour que suivre ce qu'il se passe
        Console.WriteLine($"User token has expired");

        // On indique que l'on est plus connecté à l'api
        this.authentifiedToApi = false;
    }

    /// <summary>
    /// Evenement qui se produit lors du processus d'auto-reconnexion lorsque l'on reçoit des informations sur une interface de réseau qui serait opérationelle.
    /// </summary>
    /// <param name="sender"></param>
    /// <param name="e">Paramètres de l'évenement.</param>
    void RbAutoReconnection_OneNetworkInterfaceOperational(object? sender, Rainbow.Events.BooleanEventArgs e)
    {
        // On sait qu'il y a au moins une interface réseau opérationnelle.
        if (e.Value)
        {
            // On affiche un message dans la console pour que suivre ce qu'il se passe
            Console.WriteLine($"At least one network interface is operational");
        }

        // AUCUNE interface réseau n'est opérationnelle.
        else
        {
            // On affiche un message dans la console pour que suivre ce qu'il se passe
            Console.WriteLine($"NO network interface is operational");
        }
    }

    /// <summary>
    /// Evenement qui se produit lors du processus d'auto-reconnexion lorsque le nombre de tentatives maximales pour se connecter au serveur a été atteint.
    /// </summary>
    /// <param name="sender"></param>
    /// <param name="e">Paramètres de l'évenement.</param>
    void RbAutoReconnection_MaxNbAttemptsReached(object? sender, EventArgs e)
    {
        // On affiche un message dans la console pour que suivre ce qu'il se passe
        Console.WriteLine($"Max number of attempts to connect to the server has been reached");
    }

    /// <summary>
    /// Evenement qui se produit lorsque le service de messagerie instantannée reçoit un nouveau message
    /// </summary>
    /// <param name="sender"></param>
    /// <param name="e">Paramètres de l'évenement.</param>
    async void RbInstantMessaging_MessageReceived(object? sender, Rainbow.Events.MessageEventArgs e)
    {
        Console.WriteLine($"Message received : \"{e.Message.Content}\" From \"{await GetContactNameById(await getContactIdFromContactJid(e.Message.FromJid))}\".");
        // On récupère le message reçu
        Rainbow.Model.Message received_new_message = e.Message;
        string author_id = await getContactIdFromContactJid(received_new_message.FromJid);
        if(author_id == this.config.bot_user_id)
        {
            // On ignore les messages du bots
            return;
        }
        //
        string bubble_id = "";
        if(received_new_message.FromBubbleJid == null || received_new_message.FromBubbleJid == "")
        {
            // Message p2p
            bubble_id = "CONTACT_" + await getContactIdFromContactJid(received_new_message.ToJid);
        }
        else {
            bubble_id = await GetBubbleIdFromBubbleJid(received_new_message.FromBubbleJid);
        }
        // On envoie le message reçu au serveur
        await this.send_to_socket_server(new Dictionary<string, object>
        {
            ["type"] = "new_msg",
            ["rbi_name"] = this.config.rbi_name,
            ["bubble_id"] = bubble_id,
            ["msg"] = await this.usefulFunctions.ConvertMessageToDictToSendToSocketServer(received_new_message, this)
        });
    }

    /// <summary>
    /// Fonction pour récupérer la liste de toutes les conversations accessibles par l'utilisateur dont on est connecté.
    /// </summary>
    /// <returns>La liste de toutes les conversations accessibles par l'utilisateur dont on est connecté.</returns>
    public async Task<List<Rainbow.Model.Conversation>?> GetAllConversations()
    {
        // Pour attendre le résultat du callback
        var tcs = new TaskCompletionSource<List<Rainbow.Model.Conversation>?>();

        // On appelle la fonction du SDK pour tout récupérer
        this.rbConversations.GetAllConversations(

            // Fonction lambda qui va envoyer le résultat au TaskCompletionSource
            (Rainbow.SdkResult<List<Rainbow.Model.Conversation>?> res) =>
            {
                if (res.Result.Success)
                {
                    tcs.SetResult(res.Data);
                }
                else
                {
                    tcs.SetResult(null);
                }
            }

        );

        // On attent le résultat du callback, puis on renvoie le résultat
        return await tcs.Task;
    }

    /// <summary>
    /// Fonction pour récupérer la liste de toutes les bulles accesibles par l'utilisateur dont on est connecté.
    /// </summary>
    /// <returns>La liste de toutes les bulles accesibles par l'utilisateur dont on est connecté.</returns>
    public async Task<List<Rainbow.Model.Bubble>?> GetAllBubbles()
    {
        // Pour attendre le résultat du callback
        var tcs = new TaskCompletionSource<List<Rainbow.Model.Bubble>?>();

        // On appelle la fonction du SDK pour tout récupérer
        this.rbBubbles.GetAllBubbles(

            // Fonction lambda qui va envoyer le résultat au TaskCompletionSource
            (Rainbow.SdkResult<List<Rainbow.Model.Bubble>?> res) =>
            {
                if (res.Result.Success)
                {
                    tcs.SetResult(res.Data);
                }
                else
                {
                    tcs.SetResult(null);
                }
            }

        );

        // On attent le résultat du callback, puis on renvoie le résultat
        return await tcs.Task;
    }

    /// <summary>
    /// Fonction pour récupérer une liste d'un nombre précis de messages (ou moins si on a atteint la fin de la bulle) dans la bulle demandée. Récupère depuis l'index caché historyIndex (trouvé dans le code de l'API Web, mais ne peut pas le vérifier ni modifier cette variable car elle est cachée).
    /// </summary>
    /// <returns>Une liste d'un nombre précis de messages (ou moins si on a atteint la fin de la bulle) dans la bulle demandée</returns>
    public async Task<List<Rainbow.Model.Message>?> GetMessagesFromBubbleId(string bubble_id, int nb_messages)
    {
        // Pour attendre le résultat du callback
        var tcs = new TaskCompletionSource<List<Rainbow.Model.Message>?>();

        // On appelle la fonction du SDK pour tout récupérer
        this.rbInstantMessaging.GetMessagesFromBubbleId(bubble_id, nb_messages,

            // Fonction lambda qui va envoyer le résultat au TaskCompletionSource
            (Rainbow.SdkResult<List<Rainbow.Model.Message>?> res) =>
            {
                if (res.Result.Success)
                {
                    tcs.SetResult(res.Data);
                }
                else
                {
                    tcs.SetResult(null);
                }
            }

        );

        // On attent le résultat du callback, puis on renvoie le résultat
        return await tcs.Task;
    }

    /// <summary>
    /// Récupère la liste de tous les messages dans la bulle demandée jusqu'à un certain message demandé.
    /// </summary>
    /// <param name="bubble_id">Bulle demandée</param>
    /// <param name="message_id">Id du message où il faut s'arrêter</param>
    /// <returns>La liste de tous les messages dans la bulle demandée jusqu'à un certain message demandé.</returns>
    public async Task<List<Rainbow.Model.Message>> GetMessagesFromBubbleIdUntilMessageId(string bubble_id, string message_id)
    {
        // TODO: Reset the message history index to the last message sent on the bubble
        // Not sure that its that:
        // this.rbInstantMessaging.ClearAllMessagesFromBubbleIdFromCache(bubble_id);

        // On prépare la liste des messages à renvoyer
        List<Rainbow.Model.Message> message_list = [];

        // Tant qu'il reste des messages à parcourir et que l'on a pas trouvé le message souhaité
        while (true)
        {
            // On récupère un batch de message
            List<Rainbow.Model.Message>? tmp_msg_res_list = await GetMessagesFromBubbleId(bubble_id, this.config.nb_msgs_batch);
            // S'il n'y a plus de messages à lire, on s'arrête
            if(tmp_msg_res_list == null)
            {
                break;
            }

            // Pour indiquer que l'on a atteint le message demandé
            bool wanted_msg_reached = false;

            // on parcourt les messages
            foreach (Rainbow.Model.Message msg in tmp_msg_res_list)
            {
                // Si on détecte le message demandé, on s'arrête
                if(msg.Id == message_id)
                {
                    wanted_msg_reached = true;
                    break;
                }
                // Sinon, on ajoute le message dans la liste
                message_list.Add(msg);
            }

            // On a atteint le message demandé, donc on s'arrête
            if (wanted_msg_reached)
            {
                break;
            }

            // Plus rien à lire, on arrête
            if (tmp_msg_res_list.Count != this.config.nb_msgs_batch)
            {
                break;
            }
        }

        // On renvoie le résultat
        return message_list;
    }

    /// <summary>
    /// Fonction pour convertir le Jid en Id d'un contact
    /// </summary>
    /// <param name="contact_jid">Jid à convertir</param>
    /// <returns>Id du contact</returns>
    public async Task<string> getContactIdFromContactJid(string contact_jid)
    {
        if(this.CacheContactsIdFromJid.TryGetValue(contact_jid, out string? contactId) && contactId != null)
        {
            return contactId;
        }

        // On récupère la bulle depuis son Id
        Rainbow.Model.Contact?contact = await GetContactByJid(contact_jid);
        //
        if (contact == null)
        {
            return "[NULL]";
        }
        // On met en cache son Id
        this.CacheContactsIdFromJid.TryAdd(contact_jid, contact.Id);
        // On renvoie son Id
        return contact.Id;
    }

    /// <summary>
    /// Fonction pour récupérer une bulle depuis son JID
    /// </summary>
    /// <param name="bubble_jid">Jid de la bulle</param>
    /// <returns>Bulle correspondant au Jid</returns>
    public async Task<Rainbow.Model.Bubble?> GetBubbleByJid(string bubble_jid)
    {
        // Pour attendre le résultat du callback
        var tcs = new TaskCompletionSource<Rainbow.Model.Bubble?>();

        // On appelle la fonction du SDK pour tout récupérer
        this.rbBubbles.GetBubbleByJid(bubble_jid,

            // Fonction lambda qui va envoyer le résultat au TaskCompletionSource
            (Rainbow.SdkResult<Rainbow.Model.Bubble?> res) =>
            {
                if (res.Result.Success)
                {
                    tcs.SetResult(res.Data);
                }
                else
                {
                    tcs.SetResult(null);
                }
            }

        );

        // On attent le résultat du callback, puis on renvoie le résultat
        return await tcs.Task;
    }

    /// <summary>
    /// Fonction pour récupérer une bulle depuis son ID
    /// </summary>
    /// <param name="bubble_id">Id de la bulle</param>
    /// <returns>Bulle correspondant à l'Id</returns>
    public async Task<Rainbow.Model.Bubble?> GetBubbleById(string bubble_id)
    {
        // Pour attendre le résultat du callback
        var tcs = new TaskCompletionSource<Rainbow.Model.Bubble?>();

        // On appelle la fonction du SDK pour récupérer ce que l'on veut
        this.rbBubbles.GetBubbleById(bubble_id,

            // Fonction lambda qui va envoyer le résultat au TaskCompletionSource
            (Rainbow.SdkResult<Rainbow.Model.Bubble?> res) =>
            {
                if (res.Result.Success)
                {
                    tcs.SetResult(res.Data);
                }
                else
                {
                    tcs.SetResult(null);
                }
            }

        );

        // On attent le résultat du callback, puis on renvoie le résultat
        return await tcs.Task;
    }

    /// <summary>
    /// Fonction pour récupérer une conversation depuis l'id d'une bulle
    /// </summary>
    /// <param name="bubble_id">Id de la bulle</param>
    /// <returns>Conversation souhaitée</returns>
    public async Task<Rainbow.Model.Conversation?> GetConversationByBubbleId(string bubble_id)
    {
        // Pour attendre le résultat du callback
        var tcs = new TaskCompletionSource<Rainbow.Model.Conversation?>();

        // On appelle la fonction du SDK pour récupérer ce que l'on veut
        this.rbConversations.GetConversationFromBubbleId(bubble_id,

            // Fonction lambda qui va envoyer le résultat au TaskCompletionSource
            (Rainbow.SdkResult<Rainbow.Model.Conversation?> res) =>
            {
                if (res.Result.Success)
                {
                    tcs.SetResult(res.Data);
                }
                else
                {
                    tcs.SetResult(null);
                }
            }

        );

        // On attent le résultat du callback, puis on renvoie le résultat
        return await tcs.Task;
    }

    /// <summary>
    /// Fonction pour récupérer une conversation depuis l'id d'une bulle
    /// </summary>
    /// <param name="bubble_id">Id de la bulle</param>
    /// <returns>Conversation souhaitée</returns>
    public async Task<Rainbow.Model.Conversation?> GetConversationByContactId(string contact_id)
    {
        // Pour attendre le résultat du callback
        var tcs = new TaskCompletionSource<Rainbow.Model.Conversation?>();

        // On appelle la fonction du SDK pour récupérer ce que l'on veut
        this.rbConversations.GetConversationFromContactId(contact_id,

            // Fonction lambda qui va envoyer le résultat au TaskCompletionSource
            (Rainbow.SdkResult<Rainbow.Model.Conversation?> res) =>
            {
                if (res.Result.Success)
                {
                    tcs.SetResult(res.Data);
                }
                else
                {
                    tcs.SetResult(null);
                }
            }
        );

        // On attent le résultat du callback, puis on renvoie le résultat
        return await tcs.Task;
    }

    /// <summary>
    /// Fonction pour récupérer un contact depuis son ID
    /// </summary>
    /// <param name="contact_id">Id du contact</param>
    /// <returns>Contact correspondant à son Id</returns>
    public async Task<Rainbow.Model.Contact?> GetContactById(string contact_id)
    {
        // Pour attendre le résultat du callback
        var tcs = new TaskCompletionSource<Rainbow.Model.Contact?>();

        // On appelle la fonction du SDK pour récupérer ce que l'on veut
        this.rbContacts.GetContactFromContactIdFromServer(contact_id,

            // Fonction lambda qui va envoyer le résultat au TaskCompletionSource
            (Rainbow.SdkResult<Rainbow.Model.Contact?> res) =>
            {
                if (res.Result.Success)
                {
                    tcs.SetResult(res.Data);
                }
                else
                {
                    tcs.SetResult(null);
                }
            }

        );

        // On attent le résultat du callback, puis on renvoie le résultat
        return await tcs.Task;
    }

    /// <summary>
    /// Fonction pour récupérer un contact depuis son JID
    /// </summary>
    /// <param name="contact_jid">Jid du contact</param>
    /// <returns>Contact correspondant à son Jid</returns>
    public async Task<Rainbow.Model.Contact?> GetContactByJid(string contact_jid)
    {
        // Pour attendre le résultat du callback
        var tcs = new TaskCompletionSource<Rainbow.Model.Contact?>();

        // On appelle la fonction du SDK pour récupérer ce que l'on veut
        this.rbContacts.GetContactFromContactJidFromServer(contact_jid,

            // Fonction lambda qui va envoyer le résultat au TaskCompletionSource
            (Rainbow.SdkResult<Rainbow.Model.Contact?> res) =>
            {
                if (res.Result.Success)
                {
                    tcs.SetResult(res.Data);
                }
                else
                {
                    tcs.SetResult(null);
                }
            }

        );

        // On attent le résultat du callback, puis on renvoie le résultat
        return await tcs.Task;
    }

    /// <summary>
    /// Fonction pour convertir le Jid d'une bulle en Id de la bulle.
    /// </summary>
    /// <param name="bubble_jid">Jid de la bulle à convertir</param>
    /// <returns>Id de la bulle</returns>
    public async Task<string> GetBubbleIdFromBubbleJid(string bubble_jid)
    {
        // On récupère la bulle depuis son Jid
        Rainbow.Model.Bubble? bubble = await GetBubbleByJid(bubble_jid);
        // On renvoie son ID
        if(bubble == null)
        {
            return "[NULL]";
        }
        return bubble.Id;
    }

    /// <summary>
    /// Récupère le nom d'une bulle depuis son Id
    /// </summary>
    /// <param name="bubble_id">Id de la bulle dont l'on veut le nom</param>
    /// <returns>Nom de la bulle demandée</returns>
    public async Task<string> GetBubbleNameById(string bubble_id)
    {
        // On récupère la bulle depuis son Id
        Rainbow.Model.Bubble? bubble = await GetBubbleById(bubble_id);
        //
        if(bubble == null)
        {
            return "[NULL]";
        }
        // On renvoie son Nom
        return bubble.Name;
    }

    /// <summary>
    /// Récupère le nom d'un contact depuis son Id
    /// </summary>
    /// <param name="contact_id">Id du contact dont l'on veut le nom</param>
    /// <returns>Nom du contact demandé</returns>
    public async Task<string> GetContactNameById(string contact_id)
    {
        // On récupère le contact depuis son Id
        Rainbow.Model.Contact? contact = await GetContactById(contact_id);
        //
        if(contact == null)
        {
            return "[NULL]";
        }
        // On renvoie son Nom
        return contact.FirstName + " " + contact.LastName;
    }


    /// <summary>
    /// Envoie un message dans une bulle
    /// </summary>
    /// <param name="bubble_id">Id de la bulle où envoyer le message</param>
    /// <param name="message_content">Message à envoyer</param>
    public void SendMessageInBubble(string bubble_or_contact_id, string message_content)
    {
        if (bubble_or_contact_id.StartsWith("CONTACT_"))
        {
            string contact_id = bubble_or_contact_id.Substring(8);
            if(contact_id == "[NULL]")
            {
                return;
            }
            this.rbInstantMessaging.SendMessageToContactId(contact_id, message_content);
        }
        else
        {
            if(bubble_or_contact_id == "[NULL]")
            {
                return;
            }
            this.rbInstantMessaging.SendMessageToBubbleId(bubble_or_contact_id, message_content, []);
        }
    }

    /// <summary>
    /// Réponds à un message
    /// </summary>
    /// <param name="bubble_id">Bulle où est le message</param>
    /// <param name="msg_id">Id du message</param>
    /// <param name="message_content">Message à envoyer</param>
    public async void ReplyToMessage(string bubble_or_contact_id, string msg_id, string message_content)
    {
        if (bubble_or_contact_id.StartsWith("CONTACT_"))
        {
            string contact_id = bubble_or_contact_id.Substring(8);
            if (contact_id == "[NULL]")
            {
                return;
            }
            //
            Rainbow.Model.Conversation? conv = await GetConversationByContactId(contact_id);
            //
            if (conv == null)
            {
                Console.WriteLine($"Error, cannot reply to message : conversation is null (contact_id={contact_id}, msg_id={msg_id}, message_content={message_content}).");
                SendMessageInBubble(contact_id, message_content);
                return;
            }
            //
            this.rbInstantMessaging.ReplyToMessage(conv.Id, msg_id, message_content, (Rainbow.SdkResult<Rainbow.Model.Message> res) => { });
        }
        else
        {
            if (bubble_or_contact_id == "[NULL]")
            {
                return;
            }
            //
            Rainbow.Model.Conversation? conv = await GetConversationByBubbleId(bubble_or_contact_id);
            //
            if (conv == null)
            {
                Console.WriteLine($"Error, cannot reply to message : conversation is null (bubble_id={bubble_or_contact_id}, msg_id={msg_id}, message_content={message_content}).");
                SendMessageInBubble(bubble_or_contact_id, message_content);
                return;
            }
            //
            this.rbInstantMessaging.ReplyToMessage(conv.Id, msg_id, message_content, (Rainbow.SdkResult<Rainbow.Model.Message> res) => { });
        }
    }


    public string GetBotId()
    {
        return this.config.bot_user_id;
    }
}





class MainRainbowAppSDKApi
{

    public RainbowSDKApi? rainbowSDKApi = null; // Objet qui gère le SDK Api Rainbow
    private readonly NetworkStream? stream = null; // Module qui permet de lire depuis le socket
    private readonly StreamWriter? streamWriter = null; // Module qui permet d'écrire sur le socket
    private Thread? threadSocketPythonListener = null; // Thread qui contient la fonction qui écoute depuis le socket
    private readonly TcpClient? client = null; // Client TCP qui est connecté au socket python
    private readonly Config? config = null; // Configuration globale de l'app
    private readonly UsefulFunctions usefulFunctions; // Fonctions utiles pour la conversion de modèles en dictionnaires

    public bool ok = false; // Variable qui sert à indiquer que l'initialisation de la connection socket s'est bien passée

    private string[] files_to_import = []; // Bulles à importer

    private Mutex mutex = new Mutex();
    private Dictionary<string, Dictionary<int, Tuple<string, double, string, string, string>>> search_results = [];
    private Dictionary<string, int> search_nb_results = [];
    private Dictionary<string, Tuple<string, string, double>> search_data = [];

    /// <summary>
    /// Constructeur, initialisation des variables, initialisation de la connection au socket.
    /// </summary>
    public MainRainbowAppSDKApi(string config_file_path, string[] files_to_import_)
    {

        // On récupère ces fonctions utiles pour la conversion
        this.usefulFunctions = new();

        // On affiche un message dans la console pour que suivre ce qu'il se passe
        Console.WriteLine("Début de l'initialisation de l'aplication...");
        this.config = new Config(config_file_path);

        Console.WriteLine($"On va essayer de se connecter au client socket TCP à l'adresse {this.config.python_ws_adress} au port {this.config.python_ws_port}...");
        try
        {
            // On se connecte au serveur socket python
            this.client = new TcpClient(config.python_ws_adress, config.python_ws_port);
            // On affiche un message dans la console pour que suivre ce qu'il se passe
            Console.WriteLine($"Connected to server at {config.python_ws_adress}:{config.python_ws_port}");
        }
        catch (ArgumentNullException e)
        {
            // On affiche un message dans la console pour que suivre ce qu'il se passe
            Console.WriteLine($"ArgumentNullException: {e}");
            // On arrête tout
            return;
        }
        catch (SocketException e)
        {
            // On affiche un message dans la console pour que suivre ce qu'il se passe
            Console.WriteLine($"SocketException: {e}");
            // On arrête tout
            return;
        }

        //
        Console.WriteLine($"On est bien connecté au serveur à l'adresse {this.config.python_ws_adress} au port {this.config.python_ws_port} !\nRécupération du stream...");

        // On récupère l'objet qui nous permettra de lire depuis la socket et d'y envoyer des messages.
        this.stream = client.GetStream();
        this.streamWriter = new StreamWriter(this.stream);
        this.streamWriter.AutoFlush = true;

        Console.WriteLine($"Ok, l'initialisation de base de l'application s'est bien passée !");

        // On indique que l'initialisation s'est bien passée
        this.ok = true;
    }

    /// <summary>
    /// Fonction qui sert à envoyer un message au serveur socket python.
    /// </summary>
    /// <param name="messageDict">Message à envoyer</param>
    public async Task<bool> SendMessageToSocket(Dictionary<string, object> messageDict)
    {
        // S'il y a un problème, on s'arrête
        if (this.streamWriter == null || this.config == null)
        {
            return false;
        }

        // On convertit le dictionnaire en chaîne de caractères
        string message = JsonSerializer.Serialize(messageDict) + this.config.socket_messages_delimiter;
        // On écrit le message sur le socket
        await this.streamWriter.WriteAsync(message);

        return true;
    }

    /// <summary>
    /// Fonction pour lancer cette application.
    /// </summary>
    public void Run()
    {
        // On vérifie que tout est bon avant de ne faire quoi que soit.
        if (!this.ok || this.streamWriter == null || this.stream == null || this.client == null || this.config == null)
        {
            // On affiche un message d'erreur pour prévenir qu'il y a eu une erreur
            Console.WriteLine($"Erreur: On ne peut pas lancer l'application, il y a eu une erreur lors de l'initialisation!");
            return;
        }

        Console.WriteLine("Début lancement application...");

        // On crée l'objet qui va gérer l'api Rainbow
        this.rainbowSDKApi = new(this.config, this.usefulFunctions, SendMessageToSocket);
        // On lance la connexion à l'api Rainbow
        this.rainbowSDKApi.Run();

        // Ok, maintenant, on est bien connecté à l'api
        Console.WriteLine("L'application a bien démarrée !");

        // On envoie un message au socket pour initialiser l'environnement Rainbow, et que le serveur socket nous envoie les derniers messages qu'il a de chaque bulle, pour lui envoyer les nouveaux messages qu'il y a eu depuis, et les nouvelles bulles.
        Task.Run(() => SendMessageToSocket(new Dictionary<string, object>
        {
            ["type"] = "init_rbi",
            ["rbi_name"] = this.config.rbi_name,
            ["bot_id"] = this.rainbowSDKApi.GetBotId()
        }));

        // On met la lecture des messages depuis le serveur socket python dans un thread, qui va lancer des fonctions asynchrones lorsqu'un message est reçu pour les traiter.
        this.threadSocketPythonListener = new Thread(
            new ThreadStart(ListenPythonSocketServer)
        );
        this.threadSocketPythonListener.Start();

        // On tourne tant que le thread d'écoute du serveur socket python est actif (et qu'il n'y a pas de problèmes au niveau de du sdk api Rainbow)
        this.threadSocketPythonListener.Join();

        // On ferme le socket
        this.stream.Close();
        this.client.Close();

        // On affiche un message dans la console pour que suivre ce qu'il se passe
        Console.WriteLine("\n Press Enter to continue...");
        Console.Read();
    }

    /// <summary>
    /// Fonction pour gérer le message reçu depuis le socket python de type "rbi_ini".
    /// </summary>
    /// <param name="messageDict">Message reçu depuis le socket python</param>
    /// <returns>Nothing</returns>
    private async void Handle_RbiInit(Dictionary<string, JsonElement> messageDict)
    {
        // On vérifie que tout va bien
        if(messageDict == null || this.config == null || this.rainbowSDKApi == null || !messageDict.TryGetValue("rbi_name", out JsonElement rbi_name) || rbi_name.GetString() != this.config.rbi_name)
        {
            // Affichage Warning Error
            Console.WriteLine($"Warning / Error: Appel à Handle_RbiInit avec de mauvaises valeurs!");
            // S'il y a un problème, on arrête
            return;
        }

        if(!messageDict.TryGetValue("bubbles_last_msgs_ids", out JsonElement elt_dict))
        {
            // Affichage Warning Error
            Console.WriteLine($"Warning / Error: Appel à Handle_RbiInit avec de mauvaises valeurs!");
            // S'il y a un problème, on arrête
            return;
        }

        JsonConverter converter = new JsonConverter();

        // On récupère le dictionnaire {bubble_id -> last_Msg_Id}
        // Dictionary<string, string>? bubblesLastMsgsIds = JsonSerializer.Deserialize<Dictionary<string, string>>(messageDict.GetValueOrDefault("bubbles_last_msgs_ids", "{}"));
        Dictionary<string, string>? bubblesLastMsgsIds = converter.ConvertJsonElementToDictionaryString(elt_dict);
        //
        if (bubblesLastMsgsIds == null)
        {
            // S'il y a un problème, on arrête
            return;
        }

        // Là, l'idée, ca va être de parcourir chaque bulle de Rainbow, et pour chaque bulle -> envoyer tous les derniers messages tant que l'on a pas rencontré le message avec l'id recherché
        List<Rainbow.Model.Bubble>? bubbles = await this.rainbowSDKApi.GetAllBubbles();

        if(bubbles == null)
        {
            bubbles = [];
        }

        // On parcours chaque bulle
        foreach (Rainbow.Model.Bubble bubble in bubbles)
        {
            // On récupère l'id du dernier message de cette bulle
            string last_message_id = bubblesLastMsgsIds.GetValueOrDefault(bubble.Id, "");

            // On récupère la liste des nouveaux messages qu'il y a eu depuis cette bulle
            List<Rainbow.Model.Message> msgs_to_send = await this.rainbowSDKApi.GetMessagesFromBubbleIdUntilMessageId(bubble.Id, last_message_id);

            // On filtre les messages du bots
            List<Rainbow.Model.Message> msgs_to_send_filtered = [];
            foreach (Rainbow.Model.Message msg in msgs_to_send)
            {
                string author_id = await this.rainbowSDKApi.getContactIdFromContactJid(msg.FromJid);
                if (author_id == this.config.bot_user_id)
                {
                    // On ignore les messages du bots
                    continue;
                }
                // Sinon, on peut le rajouter dans la liste filtrée
                msgs_to_send_filtered.Add(msg);
            }

            // On envoie la liste des nouveaux messages au socket python
            await this.SendMessageToSocket(new Dictionary<string, object>
            {
                ["type"] = "update_bubble",
                ["rbi_name"] = this.config.rbi_name,
                ["bubble_id"] = bubble.Id,
                ["bubble_name"] = bubble.Name,
                ["msgs"] = await this.usefulFunctions.ConvertMessageListToSendToSocketServer(msgs_to_send_filtered, this.rainbowSDKApi)
            });
        }
    }

    /// <summary>
    /// Fonction pour gérer le message reçu depuis le socket python de type "prepare_search_results".
    /// </summary>
    /// <param name="messageDict">Message reçu depuis le socket python</param>
    private void Handle_PrepareSearchResults(Dictionary<string, JsonElement> messageDict)
    {
        // On vérifie que tout va bien
        if (messageDict == null || this.config == null || this.rainbowSDKApi == null || !messageDict.TryGetValue("search_input", out JsonElement je_search_input) || !messageDict.TryGetValue("nb_results", out JsonElement je_nb_results) || !messageDict.TryGetValue("search_msg_id", out JsonElement je_search_msg_id) || !messageDict.TryGetValue("search_msg_bubble_id", out JsonElement je_search_msg_bubble_id) || !messageDict.TryGetValue("search_time", out JsonElement je_search_time))
        {
            // Affichage Warning Error
            Console.WriteLine($"Warning / Error: Appel à Handle_PrepareSearchResults avec de mauvaises valeurs!");
            // S'il y a un problème, on arrête
            return;
        }

        // On récupère les valeurs
        string? search_input = je_search_input.GetString();
        int nb_results = je_nb_results.GetInt32();
        string? search_msg_id = je_search_msg_id.GetString();
        string? search_msg_bubble_id = je_search_msg_bubble_id.GetString();
        double search_time = je_search_time.GetDouble();

        if (search_input == null || nb_results < 0 || search_msg_id == null || search_msg_bubble_id == null || search_time < 0) { return; }

        this.mutex.WaitOne();
        this.search_results.Add(search_input, []);
        this.search_nb_results.Add(search_input, nb_results);
        this.search_data.Add(search_input, new Tuple<string, string, double>(search_msg_id, search_msg_bubble_id, search_time));
        this.mutex.ReleaseMutex();

        if(nb_results == 0)
        {
            SearchResultsFinished(search_input, nb_results, []);
        }
    }

    /// <summary>
    /// Fonction pour gérer le message reçu depuis le socket python de type "search_result".
    /// </summary>
    /// <param name="messageDict">Message reçu depuis le socket python</param>
    private void Handle_SearchResult(Dictionary<string, JsonElement> messageDict)
    {
        // On vérifie que tout va bien
        if (messageDict == null || this.config == null || this.rainbowSDKApi == null || !messageDict.TryGetValue("search_input", out JsonElement je_search_input) || !messageDict.TryGetValue("index_result", out JsonElement je_index_result) || !messageDict.TryGetValue("distance", out JsonElement je_distance) || !messageDict.TryGetValue("msg_id", out JsonElement je_msg_id) || !messageDict.TryGetValue("msg_content", out JsonElement je_msg_content) || !messageDict.TryGetValue("msg_author_name", out JsonElement je_msg_author_name) || !messageDict.TryGetValue("msg_bubble_name", out JsonElement je_msg_bubble_name))
        {
            // Affichage Warning Error
            Console.WriteLine($"Warning / Error: Appel à Handle_PrepareSearchResults avec de mauvaises valeurs!");
            // S'il y a un problème, on arrête
            return;
        }

        // On récupère les valeurs
        string? search_input = je_search_input.GetString();
        int index_result = je_index_result.GetInt32();
        double result_distance = je_distance.GetDouble();
        string? msg_id = je_msg_id.GetString();
        string? msg_content = je_msg_content.GetString();
        if(msg_content == null)
        {
            msg_content = "[ERROR]";
        }
        string? msg_author_name = je_msg_author_name.GetString();
        if (msg_author_name == null)
        {
            msg_author_name = "[ERROR]";
        }
        string? msg_bubble_name = je_msg_bubble_name.GetString();
        if (msg_bubble_name == null)
        {
            msg_bubble_name = "[ERROR]";
        }

        if (search_input == null || msg_id == null || index_result < 0 || !this.search_results.TryGetValue(search_input, out Dictionary<int, Tuple<string, double, string, string, string>>? dict_results) || dict_results == null || !this.search_nb_results.TryGetValue(search_input, out int nb_results) || nb_results < 0) { return; }

        this.mutex.WaitOne();
        dict_results.Add(index_result, new Tuple<string, double, string, string, string> (msg_id, result_distance, msg_content, msg_author_name, msg_bubble_name));
        this.mutex.ReleaseMutex();

        Console.WriteLine($"DEBUG | dict_results = {dict_results.Count} / nb_results = {nb_results}");

        if (dict_results.Count() >= nb_results)
        {
            Task.Run(() => SearchResultsFinished(search_input, nb_results, dict_results));
        }
    }

    /// <summary>
    /// Fonction qui est appelée lorsque les résultats d'une recherche ont fini d'arriver.
    /// </summary>
    /// <param name="search_input">Texte en entrée.</param>
    /// <param name="nb_results">Nombre de résultats</param>
    /// <param name="dict_results">Les résultats</param>
    private void SearchResultsFinished(string search_input, int nb_results, Dictionary<int, Tuple<string, double, string, string, string>> dict_results)
    {

        if(this.rainbowSDKApi == null || !this.search_data.TryGetValue(search_input, out Tuple<string, string, double>? search_msg_tuple) || search_msg_tuple == null) { Console.WriteLine($"DEBUG | ERROR !!!"); return; }

        string search_msg_id = search_msg_tuple.Item1;
        string search_msg_bubble_id = search_msg_tuple.Item2;
        double search_time = search_msg_tuple.Item3;

        string msg_result = $"Search result for \"{search_input}\" ({search_time} sec) :";

        if(nb_results == 0)
        {
            msg_result += "\nNo results found.";
        }
        else
        {
            for (int i = 0; i < nb_results; i++)
            {
                if (!dict_results.TryGetValue(i, out Tuple<string, double, string, string, string>? res_msg_i) || res_msg_i == null)
                {
                    continue;
                }
                string msg_id = res_msg_i.Item1;
                double result_distance = res_msg_i.Item2;
                string msg_res_content = res_msg_i.Item3;
                string msg_res_author_name = res_msg_i.Item4;
                string msg_res_bubble_name = res_msg_i.Item5;
                if (msg_res_content.Length > 100)
                {
                    msg_res_content = msg_res_content.Substring(0, 100) + "...";
                }
                msg_result += $"\n\n  - ({i}) msg id : @{msg_id} ({result_distance})\n  > `{msg_res_content}` (from: {msg_res_author_name} - in: {msg_res_bubble_name})";
            }
        }

        Task.Run(() =>
        {
            //
            this.rainbowSDKApi.ReplyToMessage(search_msg_bubble_id, search_msg_id, msg_result);
            //
            this.search_nb_results.Remove(search_input);
            this.search_results.Remove(search_input);
            this.search_data.Remove(search_input);
        });
    }

    /// <summary>
    /// Fonction qui va écouter depuis le socket python.
    /// </summary>
    private void ListenPythonSocketServer()
    {
        if (!this.ok || this.streamWriter == null || this.stream == null || this.client == null || this.config == null)
        {
            Console.WriteLine($"Erreur: On ne peut pas lancer l'application, il y a eu une erreur lors de l'initialisation!");
            return;
        }

        byte[] data = new byte[Constants.SOCKET_MAX_MSG_SIZE];
        int bytes;
        while ((bytes = this.stream.Read(data, 0, data.Length)) != 0)
        {
            string receivedData = Encoding.UTF8.GetString(data, 0, bytes);
            string[] messages = receivedData.Split(this.config.socket_messages_delimiter, StringSplitOptions.RemoveEmptyEntries);

            foreach (string message in messages)
            {
                Console.WriteLine($"Received: {message}");

                try
                {
                    var messageDict = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(message, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });

                    if (messageDict == null)
                    {
                        Console.WriteLine($"Bad Message, cannot be deserialized: {message}");
                        continue;
                    }

                    // Log the entire dictionary to inspect its contents
                    Console.WriteLine("Deserialized Dictionary Contents:");
                    foreach (KeyValuePair<string, JsonElement> kvp in messageDict)
                    {
                        Console.WriteLine($"Key: {kvp.Key}, Value: {kvp.Value}, Type: {kvp.Value.GetType()}");
                    }

                    if (messageDict.TryGetValue("type", out JsonElement typeValueObj))
                    {
                        string? typeValue = typeValueObj.GetString();
                        if( typeValue == null)
                        {
                            Console.WriteLine($"Json error message, cannot retrieve \"type\" field: {message}");
                        }
                        else{
                            switch (typeValue)
                            {
                                case "rbi_state":
                                    Task.Run(() => Handle_RbiInit(messageDict));
                                    break;
                                case "connected":
                                    break;
                                case "prepare_search_results":
                                    Task.Run(() => Handle_PrepareSearchResults(messageDict));
                                    break;
                                case "search_result":
                                    Task.Run(() => Handle_SearchResult(messageDict));
                                    break;
                                default:
                                    Console.WriteLine($"Bad Json Message, doesn't have \"type\" field or has an unknown type: {message}");
                                    break;
                            }
                        }
                    }
                    else
                    {
                        Console.WriteLine($"Bad Json Message, doesn't have \"type\" field: {message}");
                    }
                }
                catch (JsonException jsonEx)
                {
                    Console.WriteLine($"JSON Deserialization error: {jsonEx.Message}");
                    if (jsonEx.InnerException != null)
                    {
                        Console.WriteLine($"Inner Exception: {jsonEx.InnerException.Message}");
                    }
                    Console.WriteLine($"Failed Message: {message}");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Unexpected error: {ex.Message}");
                    if (ex.InnerException != null)
                    {
                        Console.WriteLine($"Inner Exception: {ex.InnerException.Message}");
                    }
                    Console.WriteLine($"Failed Message: {message}");
                }
            }
        }
    }
}




class App()
{


    /// <summary>
    /// Point d'entrée du programme. Fonction Main.
    /// </summary>
    static void Main(string[] args)
    {

        int nb_args = args.Count();

        if (nb_args == 0)
        {
            Console.WriteLine("Error : No config file given !");
            Environment.Exit(0);
        }

        string config_file_path = args[0];

        if (!File.Exists(config_file_path)) {
            Console.WriteLine("Error : Config file doesn't exists !");
            Environment.Exit(0);
        }

        string[] files_to_import = [];

        if(nb_args >= 3)
        {
            if (args[1] == "-import")
            {
                for(int i = 2; i < nb_args; i++){
                    files_to_import.Append(args[i]);
                    Console.WriteLine($"File {args[i]} will tried to be imported.");
                }
            }
        }

        // On affiche un message dans la console pour suivre ce qu'il se passe
        Console.WriteLine($"Main: On va créer l'app.");

        // On initialise l'application
        MainRainbowAppSDKApi app = new(config_file_path, files_to_import);

        // On affiche un message dans la console pour suivre ce qu'il se passe
        Console.WriteLine($"Main: App created. OK : {app.ok}");

        //
        bool exited = false;

        /// <summary>
        /// Function that catchs an exit event
        /// </summary>
        void AtExit()
        {
            if (!exited)
            {
                exited = true;
            }
            else
            {
                return;
            }

            // DEBUG | TEST // On envoie un message lorsque l'on est déconnecté dans la première conversation que l'on trouve
            Task.Run(async () =>
            {
                if(app.rainbowSDKApi != null){
                    await app.rainbowSDKApi.SendDisconnectionMessage();
                }
            });
        }

        // On se connecte aux méthodes de déconnexion
        AppDomain.CurrentDomain.ProcessExit += delegate
        {
            AtExit();
        };
        AppDomain.CurrentDomain.DomainUnload += delegate
        {
            AtExit();
        }; ;
        Console.CancelKeyPress += delegate
        {
            AtExit();
        }; ;

        // Si l'initialisation c'est bien passé, on lance l'application
        if (app.ok)
        {
            app.Run();
        }

        Console.WriteLine($"Main: End of Main.");
    }

}
