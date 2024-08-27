
// Ip du serveur websocket
const IP_WS_SERVER = "localhost";

// Port du serveur websocket
const PORT_WS_SERVER = 42042;

/**
 * Envoie un messsage (de type dictionnaire) au websocket.
 * @param {WebSocket} ws
 * @param {Dictionnary} msg_dict
 */
function ws_send_msg(ws, msg_dict){

    // On convertit le message dictionnaire en un message textuel avec json
    var msg_str = JSON.stringify(msg_dict);

    // On envoie le message au serveur websocket
    ws.send(msg_str);

}


// On vérifie que le navigateur web utilisé supporte les websockets, et on lance la connexion
if("WebSocket" in window){

    // On se connecte au serveur websocket
    // On enregistre la websocket dans la window pour pouvoir y accéder facilement dans un autre script js
    window.ws = new WebSocket("ws://" + IP_WS_SERVER + ":" + PORT_WS_SERVER);

    // Quand le client websocket s'est bien connecté au serveur
    window.ws.onopen = function(event) {
        // On affiche un message indiquant la bonne connexion
        console.log("Bien connecté au serveur!");
    };

    // Si le client n'arrive pas à se connecter au serveur
    window.ws.onerror = function(event) {
        // On affiche un message indiquant l'erreur
        console.log("Il y a eu une erreur sur le websocket.");
    };

    // Quand le client websocket reçoit des messages
    window.ws.onmessage = function(event) {
        // On récupère le message
        const message = event.data;
        //
        traite_message_recu(message);
    };

    // Quand la connexion websocket se ferme
    window.ws.onclose = function (event) {

        // On récupère la raison de la fermeture du socket.
        var reason;
        // See https://www.rfc-editor.org/rfc/rfc6455#section-7.4.1
        {
            if (event.code == 1000)
                reason = "Normal closure, meaning that the purpose for which the connection was established has been fulfilled.";
            else if(event.code == 1001)
                reason = "An endpoint is \"going away\", such as a server going down or a browser having navigated away from a page.";
            else if(event.code == 1002)
                reason = "An endpoint is terminating the connection due to a protocol error";
            else if(event.code == 1003)
                reason = "An endpoint is terminating the connection because it has received a type of data it cannot accept (e.g., an endpoint that understands only text data MAY send this if it receives a binary message).";
            else if(event.code == 1004)
                reason = "Reserved. The specific meaning might be defined in the future.";
            else if(event.code == 1005)
                reason = "No status code was actually present.";
            else if(event.code == 1006)
            reason = "The connection was closed abnormally, e.g., without sending or receiving a Close control frame";
            else if(event.code == 1007)
                reason = "An endpoint is terminating the connection because it has received data within a message that was not consistent with the type of the message (e.g., non-UTF-8 [https://www.rfc-editor.org/rfc/rfc3629] data within a text message).";
            else if(event.code == 1008)
                reason = "An endpoint is terminating the connection because it has received a message that \"violates its policy\". This reason is given either if there is no other sutible reason, or if there is a need to hide specific details about the policy.";
            else if(event.code == 1009)
            reason = "An endpoint is terminating the connection because it has received a message that is too big for it to process.";
            else if(event.code == 1010) // Note that this status code is not used by the server, because it can fail the WebSocket handshake instead.
                reason = "An endpoint (client) is terminating the connection because it has expected the server to negotiate one or more extension, but the server didn't return them in the response message of the WebSocket handshake. <br /> Specifically, the extensions that are needed are: " + event.reason;
            else if(event.code == 1011)
                reason = "A server is terminating the connection because it encountered an unexpected condition that prevented it from fulfilling the request.";
            else if(event.code == 1015)
                reason = "The connection was closed due to a failure to perform a TLS handshake (e.g., the server certificate can't be verified).";
            else
                reason = "Unknown reason";
        }

        on_websocket_connection_closed(reason);

        // On indique la fermeture de la connexion websocket et on affiche la raison de la fermeture
        console.log("Fermeture de la websocket.\nRaison: " + reason);
    };
}
else{
    alert("Le WebSocket n'est pas supporté par votre navigateur web, veuillez changer de navigateur web.");
}


// Teste si toutes les clés demandées sont bien dans un dictionnaire donné
function test_all_keys_of_dict(keys, dict){
    for(key of keys){
        if(dict[key] == undefined){
            console.error("Missing key ", key, "from ", dict);
            return false;
        }
    }
    return true;
}

// message is a string
function traite_message_recu(message){

    // On parse le message reçu au format JSON
    data = JSON.parse(message);

    // Tous les messages corrects on une clé `type`
    if(data["type"] == undefined){
        // Message incorrect
        return;
    }

    // console.log("Received message : ", data)

    if(webapp_type == "demo"){
        //
        switch(data["type"]){
            // Si on reçoit des données sur le nom d'une rbi disponible
            case "data_rbi_name":
                if(test_all_keys_of_dict(["rbi_name", "nb_bubbles", "nb_users", "nb_messages"], data)){
                    on_received_data_rbi_name(data["rbi_name"], data["nb_bubbles"], data["nb_users"], data["nb_messages"]);
                }
                break;
            // Si on reçoit des données sur une bulle d'une RBI
            case "data_bubble":
                if(test_all_keys_of_dict(["rbi_name", "data_bubble"], data)){
                    on_received_data_bubble(data["rbi_name"], data["data_bubble"]);
                }
                break;
            // Si on reçoit des données sur un utilisateur d'une RBI
            case "data_user":
                if(test_all_keys_of_dict(["rbi_name", "data_user"], data)){
                    on_received_data_user(data["rbi_name"], data["data_user"]);
                }
                break;
            // Si on reçoit des données sur un message d'une RBI
            case "data_message":
                if(test_all_keys_of_dict(["rbi_name", "data_message"], data)){
                    on_received_data_message(data["rbi_name"], data["data_message"]);
                }
                break;
            // Si on reçoit la préparation d'un transfert de donnée depuis une rbi
            case "rbi_prepare_transfer":
                if(test_all_keys_of_dict(["rbi_name", "nb_bubbles", "nb_users", "nb_messages"], data)){
                    on_received_preparation_rbi_transfer(data["rbi_name"], data["nb_bubbles"], data["nb_users"], data["nb_messages"]);
                }
                break;
            // Si on reçoit une configuration de moteur de recherche
            case "search_engine_configuration":
                if(test_all_keys_of_dict(["config_name", "config_dict"], data)){
                    on_engine_config_received(data["config_name"], data["config_dict"]);
                }
                break;
            // Si on reçoit une configuration par défaut du moteur de recherche
            case "default_search_engine_config_name":
                if(test_all_keys_of_dict(["config_name"], data)){
                    engine_config_selected(data["config_name"]);
                }
                break;
            // Préparation à la réception de résultats de recherche
            case "prepare_search_results":
                if(test_all_keys_of_dict(["search_input", "nb_results"], data)){
                    on_search_result_preparation(data["search_input"], data["nb_results"]);
                }
                break;
            // Résultat de recherche
            case "search_result":
                if(test_all_keys_of_dict(["search_input", "index_result", "msg_id", "distance"], data)){
                    on_search_result(data["search_input"], data["index_result"], data["msg_id"], data["distance"]);
                }
                break;
            // Acquittement de connexion positif
            case "connected":
                on_websocket_connection_active();
                break;
            // Le serveur va commencer à traiter la demande de recherche
            case "search_will_be_done":
                if(test_all_keys_of_dict(["search_input"], data)){
                    on_search_server_begin_process(data["search_input"]);
                }
                break;
            // Le serveur a annulé la demande de recherche
            case "search_cancelled":
                if(test_all_keys_of_dict(["search_input"], data)){
                    on_search_server_cancelled(data["search_input"]);
                }
                break;
            //
            case "conversation_cut_results":
                if(test_all_keys_of_dict(["current_rbi", "current_bubble", "nb_conversations", "msgs_colors"], data)){
                    on_cut_conversation_results_received(data["nb_conversations"], data["msgs_colors"], data["current_rbi"], data["current_bubble"]);
                }
                break;
            //
            case "bubble_import_error":
                if(test_all_keys_of_dict(["rbi_name", "bubble_name", "error"], data)){
                    on_bubble_import_error(data["rbi_name"], data["bubble_name"], data["error"]);
                }
                break;
            //
            case "bubble_import_started":
                if(test_all_keys_of_dict(["rbi_name", "bubble_name", "nb_msgs", "estimated_time"], data)){
                    on_bubble_import_started(data["rbi_name"], data["bubble_name"], data["nb_msgs"], data["estimated_time"]);
                }
                break;
            //
            case "bubble_import_progress_update":
                if(test_all_keys_of_dict(["rbi_name", "bubble_name", "msgs_processed", "estimated_time"], data)){
                    on_bubble_import_progress_update(data["rbi_name"], data["bubble_name"], data["msgs_processed"], data["estimated_time"]);
                }
                break;
            //
            case "bubble_import_finished":
                if(test_all_keys_of_dict(["rbi_name", "bubble_name", "bubble_id"], data)){
                    on_bubble_import_finished(data["rbi_name"], data["bubble_name"], data["bubble_id"]);
                }
                break;
            // On ne connait pas le type: on ignore
            default:
                break;
        }
    }
    else if(webapp_type == "hyper_parameters_optimisation"){
        //
        switch(data["type"]){
            // Acquittement de connexion positif
            case "connected":
                on_websocket_connection_active();
                break;
            //
            case "hpo_prepare_transfer":
                if(test_all_keys_of_dict(["task", "nb_configs", "nb_benchmarks", "hpo_algorithms"], data)){
                    if("default_config" in data){
                        on_hpo_prepare_transfer(data["task"], data["nb_configs"], data["nb_benchmarks"], data["hpo_algorithms"], data["default_config"]);
                    }
                    else{
                        on_hpo_prepare_transfer(data["task"], data["nb_configs"], data["nb_benchmarks"], data["hpo_algorithms"]);
                    }
                }
                break;
            //
            case "hpo_data_config":
                if(test_all_keys_of_dict(["task", "config"], data)){
                    on_hpo_data_config(data["task"], data["config"]);
                }
                break;
            //
            case "hpo_data_benchmark":
                if(test_all_keys_of_dict(["task", "benchmark_name"], data)){
                    on_hpo_data_benchmark(data["task"], data["benchmark_name"]);
                }
                break;
            //
            case "hpo_types_and_classes":
                if(test_all_keys_of_dict(["types", "general_classes"], data)){
                    on_types_and_classes_received(data["types"], data["general_classes"]);
                }
                break;
            //
            case "hpo_single_test_benchmark_results":
                if(test_all_keys_of_dict(["task", "config", "benchmark_results", "test_benchmark_type"], data)){
                    on_hpo_single_test_benchmark_results(data["task"], data["config"], data["benchmark_results"], data["test_benchmark_type"]);
                }
                break;
            //
            case "hpo_curve_test_benchmark_results":
                if(test_all_keys_of_dict(["task", "config", "benchmark_results", "test_benchmark_type", "param_values", "param_pts_ids"], data)){
                    on_hpo_curve_test_benchmark_results(data["task"], data["config"], data["benchmark_results"], data["test_benchmark_type"], data["param_values"], data["param_pts_ids"]);
                }
                break;
            //
            case "hpo_algo_opti_update":
                if(test_all_keys_of_dict(["id_request", "update_config_score"], data)){
                    on_hpo_algo_opti_update(data["id_request"], data["update_config_score"]);
                }
                break;
            //
            case "hpo_algo_opti_result":
                if(test_all_keys_of_dict(["id_request", "config_optimized_hp", "config_optimized_score"], data)){
                    on_hpo_algo_opti_result(data["id_request"], data["config_optimized_hp"], data["config_optimized_score"]);
                }
                break;
            //
            case "____":
                if(test_all_keys_of_dict(["____", "____", "____"], data)){
                    on_something_function(data["____"], data["____"], data["____"]);
                }
                break;
            //
            case "____":
                if(test_all_keys_of_dict(["____", "____", "____"], data)){
                    on_something_function(data["____"], data["____"], data["____"]);
                }
                break;
            // On ne connait pas le type: on ignore
            default:
                break;
        }
    }
}
