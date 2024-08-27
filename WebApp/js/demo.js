/*
Script pour la page demo.html

Auteur: Nathan Cerisara
*/


/* Variables globales */

//
const webapp_type = "demo";

// Tant que l'on attends un message du serveur indiquant que la connexion a bien été établie
var awaiting_connection_success = true;

// Tant que la connexion au websocket est active
var connection_active = true;

// Liste de toutes les rbi disponibles | dict[str, dict]
var all_rbi = {};

// Liste de toutes les découpes des conversations de toutes les RBI
var all_rbi_conversation_cuts = {};

// RBI actuellement sélectionnée, vaut nulle si aucune rbi n'est sélectionnée, sinon, vaut la clé de la rbi dans le dictionnaire all_rbi
var current_rbi = null;

// Liste de toutes les configurations de moteur disponibles
var all_engine_configs = {}

// Configuration de moteur de recherche actuelle
var current_engine_config = null;

// Liste de tous les boutons pour sélectionner une configuration de moteur de recherche
var all_engine_config_buttons = {}

// Bouton actuel activé pour la configuration du moteur de recherche
var current_engine_config_button = null;

// Liste de toutes les pages (ne pas toucher à celles d'index 0 et 1)
const all_pages = ["select_rbi_page", "loading_rbi_page", "search_page", "bubbles_page", "bubble_conversation_page", "users_page", "engine_config_page", "error_connection_page", "connection_loading_page", "import_bubble_page", "request_waiting_import_bubble_page", "doing_import_bubble_page"];

// Page de démo actuelle, si une rbi est sélectionnée
var current_page = "connection_loading_page";

// Bulle actuellement sélectionnée
var current_bubble = null;

// Utilisateur actuellement sélectionné
var current_bubble_user = null;

// éléments pour les messages d'une bulle actuellement sélectionnée
var current_bubble_messages_elements = {};

// éléments pour les utilisateurs d'une bulle actuellement sélectionnée
var current_bubble_users_elements = {};

// Résultats de recherche
var search_results = {}

// Indique la recherche dont on attends les résultats
var current_search_awaiting = null;

// Indique l'utilisateur qui a été sélectionné
var current_search_user = null;

//
const button_cut_conversations_default_text = "Découpe des conversations";
const button_cut_conversations_waiting_results_text = "Attente des résultats...";
const button_cut_conversation_remove_conversations_text = "Enlever les conversations";

//
var current_bubble_import_data = {
    "bubble_name": "",
    "msgs_processed": 0,
    "nb_msgs": 0
}


/* Fonctions */


// Affiche la bonne page
function set_display_page(){
    // On parcours toutes les pages
    for(page of all_pages){
        // On affiche la bonne
        if(page == current_page){
            document.getElementById(page).style.display = "flex";
        }
        // On cache les autres
        else{
            document.getElementById(page).style.display = "none";
        }
    }
}

// Met à jour l'affichage
function update_display(){

    // Si la connexion n'est plus active, on n'affiche que la page d'erreur
    if(!connection_active){
        current_page = "error_connection_page";
        set_display_page();
        //
        document.getElementById("union_title").style.display = "none";
        document.getElementById("name_current_rbi").style.display = "none";
        document.getElementById("header_2").style.display = "none";
        //
    }

    // Si la connexion n'est plus active, on n'affiche que la page d'erreur
    else if(awaiting_connection_success){
        current_page = "connection_loading_page";
        set_display_page();
        //
        document.getElementById("union_title").style.display = "none";
        document.getElementById("name_current_rbi").style.display = "none";
        document.getElementById("header_2").style.display = "none";
        //
    }

    // Si l'on n'a pas de Rbi, il faut en sélectionner une
    else if(current_rbi == null){
        current_page = all_pages[0];
        set_display_page();
        //
        document.getElementById("union_title").style.display = "none";
        document.getElementById("name_current_rbi").style.display = "none";
        document.getElementById("header_2").style.display = "none";
    }

    //
    else{

        // La rbi est en train de charger
        if(all_rbi[current_rbi]["state"] != 2){
            current_page = all_pages[1];
            set_display_page();
            //
            document.getElementById("union_title").style.display = "none";
            document.getElementById("name_current_rbi").style.display = "none";
            document.getElementById("header_2").style.display = "none";
            //
        }

        // Sinon, on est dans l'une des pages de la démo
        else{
            document.getElementById("union_title").style.display = "inline";
            document.getElementById("name_current_rbi").style.display = "inline";
            document.getElementById("name_current_rbi").innerText = all_rbi[current_rbi]["server_name"];
            document.getElementById("header_2").style.display = "flex";
            //
            set_display_page();
        }
    }
}

// Sort de la RBI actuellement sélectionnée
function quit_current_rbi(){
    current_rbi = null;
    update_display();
}

//
function replace_underscore_by_spaces(txt){
    var new_txt = txt;
    while(new_txt.includes("_")){
        new_txt = new_txt.replace("_", " ");
    }
    return new_txt;
}

// On ajoute la rbi à la liste des rbis disponnibles
function add_to_available_rbi_list(rbi_name, nb_messages=0, nb_bubbles=0, nb_users=0){
    //
    const rbi_div_id = "div_rbi_"+escapeHtml(rbi_name);
    //
    var node = document.getElementById(rbi_div_id);
    if(node){
        node.remove();
    }

    //
    var rbi_div = document.createElement("div");
    rbi_div.id = rbi_div_id;
    rbi_div.classList.add("rbi_div_select");

    var span_rbi_name = document.createElement("span");
    span_rbi_name.classList.add("font_larger", "m_5p");
    span_rbi_name.innerText = replace_underscore_by_spaces(rbi_name);
    rbi_div.appendChild(span_rbi_name);

    if(nb_bubbles != 0 || nb_users != 0 || nb_messages != 0){

        var bottom_row = document.createElement("div");
        bottom_row.classList.add("row", "m_5p", "p_5p");
        rbi_div.appendChild(bottom_row);

        var span_nb_bubbles = document.createElement("span");
        span_nb_bubbles.classList.add("font_smaller", "m_t_5p");
        span_nb_bubbles.innerText = "" + nb_bubbles + " bubbles";
        bottom_row.appendChild(span_nb_bubbles);

        var span_sep_1 = document.createElement("span");
        span_sep_1.classList.add("font_smaller", "m_5p");
        span_sep_1.innerText = " - ";
        bottom_row.appendChild(span_sep_1);

        var span_nb_users = document.createElement("span");
        span_nb_users.classList.add("font_smaller", "m_5p");
        span_nb_users.innerText = "" + nb_users + " users";
        bottom_row.appendChild(span_nb_users);

        var span_sep_2 = document.createElement("span");
        span_sep_2.classList.add("font_smaller", "m_5p");
        span_sep_2.innerText = " - ";
        bottom_row.appendChild(span_sep_2);

        var span_nb_msgs = document.createElement("span");
        span_nb_msgs.classList.add("font_smaller", "m_5p");
        span_nb_msgs.innerText = "" + nb_messages + " messages";
        bottom_row.appendChild(span_nb_msgs);

    }

    rbi_div.setAttribute("onclick", "rbi_selected(\""+rbi_name+"\");");

    document.getElementById("available_rbi_list").appendChild(rbi_div);
}

// On ajoute la configuration du moteur de recherche à la liste des rbis disponnibles
function add_to_available_engine_config_list(engine_config_name){
    //
    var engine_config_div = document.createElement("div");
    engine_config_div.classList.add("engine_config_item", "col", "m_5p", "clickable");
    engine_config_div.setAttribute("onclick", "engine_config_selected(\""+engine_config_name+"\");")

    // Ajout du bouton dans la liste des boutons
    all_engine_config_buttons[engine_config_name] = engine_config_div;

    var row1 = document.createElement("div");
    row1.classList.add("row", "w_100", "h_auto");

    var nom_config = document.createElement("span");
    nom_config.innerText = all_engine_configs[engine_config_name]["config_name"];

    row1.appendChild(nom_config);

    var row2 = document.createElement("div");
    row2.classList.add("row", "w_100", "h_auto");

    first = true;
    for(algo_config of all_engine_configs[engine_config_name]["algorithms"]){
        // Trait d'union
        if(!first){
            var union = document.createElement("span");
            union.style.marginLeft = "5px";
            union.style.marginRight = "5px";
            union.classList.add("font_smaller");
            union.innerText = " - ";
            row2.appendChild(union);
        }
        else{
            first = false;
        }
        // Nom de l'algo (avec son coefficient)
        var algo_name = document.createElement("span");
        algo_name.classList.add("font_smaller");
        if(algo_config["type"] == "SimpleEmbedding"){
            algo_name.innerText = algo_config["model_name"];
        }
        else{
            algo_name.innerText = algo_config["type"];
        }
        // algo_name.innerText += " (" + algo_config["coef"] + ")";
        row2.appendChild(algo_name);
    }

    engine_config_div.appendChild(row1);
    engine_config_div.appendChild(row2);

    document.getElementById("available_engine_configs_list").appendChild(engine_config_div);
}

// On ajoute le message correspondant au résultat de la recherche
function add_search_result(search_result){

    // On va récupérer le message du résultat
    var id_msg_res = search_result["msg_id"];
    var msg_res = all_rbi[current_rbi]["messages"][id_msg_res];

    if(msg_res == undefined){
        console.error("Cannot find message of id : ", id_msg_res);
        return;
    }

    // On récupère les infos qu'on a besoin
    var bubble_name = all_rbi[current_rbi]["bubbles"][msg_res["bubble_id"]]["name"];
    var author_name = all_rbi[current_rbi]["users"][msg_res["author_id"]]["name"];
    var date = msg_res["date"];

    //
    var search_result_div = document.createElement("div");
    search_result_div.setAttribute("onclick", "on_result_search_selected_msg_id("+id_msg_res+");");
    search_result_div.classList.add("search_result", "col", "clickable");

    var row1 = document.createElement("span");
    var span_distance = document.createElement("span");
    span_distance.innerText = search_result["distance"];
    row1.appendChild(span_distance);
    var span_union_1 = document.createElement("span");
    span_union_1.innerText = " - ";
    row1.appendChild(span_union_1);
    var span_bubble = document.createElement("span");
    span_bubble.innerText = bubble_name;
    row1.appendChild(span_bubble);
    var span_union_2 = document.createElement("span");
    span_union_2.innerText = " - ";
    row1.appendChild(span_union_2);
    var span_user = document.createElement("span");
    span_user.innerText = author_name;
    row1.appendChild(span_user);
    var span_union_3 = document.createElement("span");
    span_union_3.innerText = " - ";
    row1.appendChild(span_union_3);
    var span_date = document.createElement("span");
    span_date.innerText = date;
    row1.appendChild(span_date);
    var span_union_4 = document.createElement("span");
    span_union_4.innerText = " | ";
    row1.appendChild(span_union_4);
    var span_msg_id = document.createElement("span");
    span_msg_id.innerText = " msg id : " + id_msg_res;
    row1.appendChild(span_msg_id);

    row2 = document.createElement("span");
    row2.innerText = msg_res["content"];

    search_result_div.appendChild(row1);
    search_result_div.appendChild(row2);

    document.getElementById("container_search_results").appendChild(search_result_div);
}

// On ajoute l'utilisateur à la liste des utilisateurs
function add_user(rbi_name, user_id){
    //
    var user_div = document.createElement("div");
    user_div.classList.add("user_item", "row");

    // Logo utilisateur
    var user_logo = document.createElement("img");
    user_logo.classList.add("user_logo", "center_v");
    user_logo.setAttribute("src", "res/logo_user2.svg");
    user_div.appendChild(user_logo);

    // Nom utilisateur + (Nb bulles + Nb messages utilisateur)
    var right_div = document.createElement("div");
    right_div.classList.add("col");
    user_div.appendChild(right_div);

    // Nom utilisateur
    var user_name = document.createElement("span");
    user_name.innerText = all_rbi[rbi_name]["users"][user_id]["name"];
    right_div.appendChild(user_name);

    // Nombre de bulles dont l'utilisateur + nombre de messages utilisateur
    var user_nb_messages = document.createElement("span");
    user_nb_messages.innerText = "" + all_rbi[rbi_name]["users"][user_id]["bubbles_ids"].length + " bulle(s) - " + all_rbi[rbi_name]["users"][user_id]["messages_ids"].length + " message(s)";
    right_div.appendChild(user_nb_messages);

    document.getElementById("users_list").appendChild(user_div);
}

// On ajoute l'utilisateur au choix des utilisateurs
function add_to_user_option(user_id){
    //
    var user_option = document.createElement("option");
    user_option.setAttribute("value", user_id);
    user_option.innerText = all_rbi[current_rbi]["users"][user_id]["name"];

    //
    document.getElementById("select_user").appendChild(user_option);
}

// On ajoute la bulle à la liste des bulles disponibles
function add_bubble(rbi_name, bubble_id){
    //
    var bubble_div = document.createElement("div");
    bubble_div.setAttribute("onclick", "bubble_selected(\""+bubble_id+"\");");
    bubble_div.classList.add("bubble_item", "row", "clickable");

    // Logo bulle
    var bubble_logo = document.createElement("img");
    bubble_logo.classList.add("bubble_logo", "center_v");
    bubble_logo.setAttribute("src", "res/logo_bubble3.svg");
    bubble_div.appendChild(bubble_logo);

    // Nom bulle + (Nb utilisateurs + Nb messages bulle)
    var right_div = document.createElement("div");
    right_div.classList.add("col");
    bubble_div.appendChild(right_div);

    // Nom bulle
    var user_name = document.createElement("span");
    user_name.innerText = all_rbi[rbi_name]["bubbles"][bubble_id]["name"];
    right_div.appendChild(user_name);

    // Nombre d'utilisateurs dans la bulle + Nombre de messages dans la bulle
    var bubbles_nb_messages = document.createElement("span");
    bubbles_nb_messages.innerText = "" + all_rbi[rbi_name]["bubbles"][bubble_id]["members_ids"].length + " - utilisateur(s) " + all_rbi[rbi_name]["bubbles"][bubble_id]["messages_ids"].length + " message(s)";
    right_div.appendChild(bubbles_nb_messages);

    document.getElementById("bubbles_list").appendChild(bubble_div);
}

// On ajoute un message à la bulle actuellement sélectionnée
function add_message_to_current_bubble(msg_id){

    var msg_div = document.createElement("div");
    msg_div.id = "msg_" + msg_id;
    msg_div.classList.add("bubble_conversation_message");
    msg_div.setAttribute("tabindex", "-1");

    var msg_content = document.createElement("span");
    msg_content.classList.add("bubble_conversation_message_content");
    msg_content.innerText = all_rbi[current_rbi]["messages"][msg_id]["content"];
    msg_div.appendChild(msg_content);

    var msg_author_and_date = document.createElement("span");
    msg_author_and_date.classList.add("bubble_conversation_message_author_and_date", "font_small");
    msg_author_and_date.innerText = all_rbi[current_rbi]["users"][all_rbi[current_rbi]["messages"][msg_id]["author_id"]]["name"] + " - " + all_rbi[current_rbi]["messages"][msg_id]["date"] + " - msg id : " + msg_id;
    msg_div.appendChild(msg_author_and_date);

    var msg_conversation = document.createElement("span");
    msg_conversation.id = "msg_conversation_" + msg_id;
    msg_conversation.classList.add("bubble_conversation_message_author_and_date", "font_small");
    msg_conversation.style.display = "none";
    msg_conversation.innerText = "conversation: /";
    msg_div.appendChild(msg_conversation);

    current_bubble_messages_elements[msg_id] = msg_div;
    document.getElementById("bubble_conversation_messages").appendChild(msg_div);
}

// On ajoute un message à la bulle actuellement sélectionnée
function add_user_to_current_bubble(user_id){

    var user_div = document.createElement("div");
    user_div.setAttribute("onclick", "on_current_bubble_user_selected(\""+user_id+"\")");
    user_div.classList.add("bubble_conversation_user", "clickable");

    // Logo
    var user_logo = document.createElement("img");
    user_logo.classList.add("bubble_conversation_user_logo");
    user_logo.setAttribute("src", "res/logo_user2.svg");
    user_div.appendChild(user_logo);

    // Nom et nb messages
    var right_div = document.createElement("div");
    right_div.classList.add("col");
    user_div.appendChild(right_div);

    // Nom
    var user_name = document.createElement("span");
    user_name.innerText = all_rbi[current_rbi]["users"][user_id]["name"];
    right_div.appendChild(user_name);

    // On va compter le nombre de messages qu'un utilisateur a envoyé dans cette bulle
    var nb_msgs_sent = 0;
    for(m_id of all_rbi[current_rbi]["bubbles"][current_bubble]["messages_ids"]){
        if(all_rbi[current_rbi]["messages"][m_id]["author_id"] == user_id){
            nb_msgs_sent += 1;
        }
    }
    var user_nb_msgs = document.createElement("span");
    user_nb_msgs.innerText = "" + nb_msgs_sent + " messages";
    right_div.appendChild(user_nb_msgs);

    current_bubble_users_elements[user_id] = user_div;
    document.getElementById("bubble_conversation_user_list").appendChild(user_div);
}

// Initialisation d'une rbi vide, quand on reçoit des données d'une qui n'existait pas encore
function init_empty_rbi(rbi_name, nb_bubbles, nb_users, nb_messages){
    all_rbi[rbi_name] = {
        "server_name": rbi_name,    // Le nom de la rbi
        "bubbles": {},      // Toutes les bulles de la rbi
        "messages": {},     // Tous les messages de la rbi
        "users": {},        // Tous les utilisateurs de la rbi
        "state": 0,         // 0 = unloaded ; 1 = loading ; 2 = loaded
        "nb_msgs": nb_messages,       // Le nombre de messages total dans la rbi
        "nb_bubbles": nb_bubbles,    // Le nombre de bulles au total dans la rbi
        "nb_users": nb_users        // Le nombre d'utilisateurs au total dans la rbi
    }

    // On va ajouter la rbi à la liste des rbi disponibles
    add_to_available_rbi_list(rbi_name, nb_messages, nb_bubbles, nb_users);
}

// Quand on reçoit le nom d'une rbi disponible
function on_received_data_rbi_name(rbi_name, nb_bubbles, nb_users, nb_messages){
    init_empty_rbi(rbi_name, nb_bubbles, nb_users, nb_messages);
}

// Pour tester si on a completement reçu les données d'une rbi
// Renvoie un booléen qui indique si une bulle est chargée ou non
function test_rbi_transfer_finished(rbi_name){

    //
    if(all_rbi[rbi_name] == undefined){
        return false;
    }

    //
    if(all_rbi[rbi_name]["state"] == 0){
        return false;
    }

    // On met à jour les valeurs sur la page

    var current_nb_bubbles = Object.keys(all_rbi[rbi_name]["bubbles"]).length;
    var current_nb_users = Object.keys(all_rbi[rbi_name]["users"]).length
    var current_nb_messages = Object.keys(all_rbi[rbi_name]["messages"]).length;

    document.getElementById("loading_nb_bubbles").innerText = '' + current_nb_bubbles;
    document.getElementById("loading_nb_users").innerText = '' + current_nb_users;
    document.getElementById("loading_nb_messages").innerText = '' + current_nb_messages;

    // On ne va pas plus loin si l'une des valeurs suivantes n'est pas complete
    if(current_nb_bubbles != all_rbi[rbi_name]["nb_bubbles"]){
        return false;
    }
    if(current_nb_users != all_rbi[rbi_name]["nb_users"]){
        return false;
    }
    if(current_nb_messages != all_rbi[rbi_name]["nb_messages"]){
        return false;
    }

    // Donc là, la RBI est complètement chargée, donc on va pouvoir bien charger la page
    current_rbi = rbi_name;
    all_rbi[current_rbi]["state"] = 2;
    navigation_search();

    // On va nettoyer tout ce qui pourrait trainer
    current_bubble = null;
    current_bubble_messages_elements = {};
    current_bubble_users_elements = {};
    search_results = {};
    document.getElementById("container_search_results").innerHTML = "";
    document.getElementById("bubbles_list").innerHTML = "";
    document.getElementById("users_list").innerHTML = "";
    while(document.getElementById("select_user").childNodes.length > 1){
        for(option of document.getElementById("select_user").childNodes){
            if(option.value != '-1'){
                document.getElementById("select_user").removeChild(option);
                option.remove();
            }
        }
    }

    // On va charger la liste des bulles de cette rbi
    for(bubble_id of Object.keys(all_rbi[current_rbi]["bubbles"])){
        add_bubble(current_rbi, bubble_id);
    }

    // On va charger la liste des utilisateurs de cette rbi
    for(user_id of Object.keys(all_rbi[current_rbi]["users"])){
        // On ajoute dans la page utilisateurs
        add_user(current_rbi, user_id);
        // On ajoute au choix de sélection de l'utilisateur pour la recherche
        add_to_user_option(user_id);
    }

    return true;
}

// Quand on reçoit la donnée d'une bulle d'une rbi
function on_received_data_bubble(rbi_name, bubble_dict){
    if(!rbi_name in all_rbi){
        init_empty_rbi(rbi_name, -1, -1, -1);
    }
    //
    all_rbi[rbi_name]["bubbles"][bubble_dict["id"]] = bubble_dict;
    //
    test_rbi_transfer_finished(rbi_name)
}

// Quand on reçoit la donnée d'un message d'une rbi
function on_received_data_message(rbi_name, message_dict){
    if(!rbi_name in all_rbi){
        init_empty_rbi(rbi_name, -1, -1, -1);
    }
    //
    all_rbi[rbi_name]["messages"][message_dict["id"]] = message_dict;
    //
    test_rbi_transfer_finished(rbi_name)
}

// Quand on reçoit la donnée d'un utilisateur d'une rbi
function on_received_data_user(rbi_name, user_dict){
    if(!rbi_name in all_rbi){
        init_empty_rbi(rbi_name, -1, -1, -1);
    }
    //
    all_rbi[rbi_name]["users"][user_dict["id"]] = user_dict;
    //
    test_rbi_transfer_finished(rbi_name)
}

// Quand on reçoit la préparation d'un transfert de donnée d'une rbi
function on_received_preparation_rbi_transfer(rbi_name, nb_bubbles, nb_users, nb_messages){
    if(all_rbi[rbi_name] == undefined){
        init_empty_rbi(rbi_name, nb_bubbles, nb_users, nb_messages);
    }
    //
    all_rbi[rbi_name]["nb_bubbles"] = nb_bubbles;
    all_rbi[rbi_name]["nb_users"] = nb_users;
    all_rbi[rbi_name]["nb_messages"] = nb_messages;
    all_rbi[rbi_name]["state"] = 1;
    //
    document.getElementById("loading_nb_bubbles").innerText = '0';
    document.getElementById("loading_tot_bubbles").innerText = '' + nb_bubbles;
    document.getElementById("loading_nb_users").innerText = '0';
    document.getElementById("loading_tot_users").innerText = '' + nb_users;
    document.getElementById("loading_nb_messages").innerText = '0';
    document.getElementById("loading_tot_messages").innerText = '' + nb_messages;
    //
    current_page = all_pages[1];
    current_rbi = rbi_name;
    update_display();
    //
    if(nb_bubbles == 0 && nb_users == 0 && nb_messages == 0){
        test_rbi_transfer_finished(rbi_name);
    }
}

// Quand on reçoit une configuration de moteur de recherche
function on_engine_config_received(config_name, config_dict){

    // On enregistre la configuration
    all_engine_configs[config_name] = config_dict;

    // On va rajouter l'élément dans la liste des configurations disponibles
    add_to_available_engine_config_list(config_name);
}

// Quand l'utilisateur sélectionne une configuration de moteur de recherche
function engine_config_selected(engine_config_name){

    // On met à jour la variable correspondante
    current_engine_config = engine_config_name;

    // On nettoie le précédent bouton sélectionné
    if(current_engine_config_button != null){
        current_engine_config_button.classList.remove("selected_engine_config_item");
        current_engine_config_button = null;
    }

    // On met à jour le bouton sélectionné
    current_engine_config_button = all_engine_config_buttons[current_engine_config];
    current_engine_config_button.classList.add("selected_engine_config_item");

}

// Quand l'utilisateur a sélectionné une rbi
function rbi_selected(rbi_name){

    // On teste s'il elle n'a pas été déjà chargée
    if(test_rbi_transfer_finished(rbi_name)){
        return;
    }

    // Sinon, on va demander des infos
    ws_send_msg(window.ws, {
        "type": "ask_for_rbi_infos",
        "rbi_name": rbi_name
    });
}

// Quand l'utilisateur veut voir le contenu d'une vulle
function bubble_selected(bubble_id){

    // Si la page de base n'est pas la page des bulles, on va d'abord la charger
    navigation_bubbles();

    // Si la bulle demandée est déjà chargée dans la page de conversation d'une bulle, on va juste se mettre à la page de la conversation d'une bulle
    if(current_bubble == bubble_id){
        current_page = "bubble_conversation_page";
        update_display();
        return;
    }

    // On nettoie l'ancien contenu d'une ancienne bulle

    // On nettoie les anciens message
    for(msg_id of Object.keys(current_bubble_messages_elements)){
        delete(current_bubble_messages_elements[msg_id]);
    }
    document.getElementById("bubble_conversation_messages").innerHTML = "";

    // On nettoie les anciens utilisateurs
    for(user_id of Object.keys(current_bubble_users_elements)){
        delete(current_bubble_users_elements[user_id]);
    }
    document.getElementById("bubble_conversation_user_list").innerHTML = "";
    current_bubble_user = null;

    // On met à jour le contenu
    current_bubble = bubble_id;

    // On met à jour le bouton
    document.getElementById("button_cut_conversations").innerText = button_cut_conversations_default_text;

    // On parcourt tous les utilisateurs de la bulle et on les ajoute
    for(user_id of all_rbi[current_rbi]["bubbles"][current_bubble]["members_ids"]){
        add_user_to_current_bubble(user_id);
    }

    // On trie les messages de la bulle par date croissante
    all_rbi[current_rbi]["bubbles"][current_bubble]["messages_ids"].sort(
        (m_id_a, m_id_b) => {
            var date_a = all_rbi[current_rbi]["messages"][m_id_a]["date"];
            var date_b = all_rbi[current_rbi]["messages"][m_id_b]["date"];
            if(date_a > date_b){
                return 1;
            }
            else if(date_a < date_b){
                return -1;
            }
            else{
                return 0;
            }
        }
    )

    // On parcourt tous les messages de la bulle et on les ajoute
    for(msg_id of all_rbi[current_rbi]["bubbles"][current_bubble]["messages_ids"]){
        add_message_to_current_bubble(msg_id);
    }

    // On change le nom de la bulle
    document.getElementById("current_bubble_name").innerText = all_rbi[current_rbi]["bubbles"][current_bubble]["name"];

    // On met à jour l'affichage
    current_page = "bubble_conversation_page";
    update_display();
}

// Quand l'utilisateur a sélectionné un utilisateur dans l'affichage de la conversatoin d'une bulle
function on_current_bubble_user_selected(user_id){

    if(document.getElementById("button_cut_conversations").innerText != button_cut_conversations_default_text){
        return;
    }

    // On va désélectionner les messages d'un ancien utilisateur sélectionné si jamais
    if(current_bubble_user != null){
        for(msg_id of all_rbi[current_rbi]["users"][current_bubble_user]["messages_ids"]){
            if(current_bubble_messages_elements[msg_id] == undefined){
                continue;
            }
            current_bubble_messages_elements[msg_id].classList.remove("bubble_conversation_message_user_selected");
        }
        current_bubble_users_elements[current_bubble_user].classList.remove("bubble_conversation_user_selected");
    }

    if(current_bubble_user == user_id){
        current_bubble_user = null;
        return;
    }

    current_bubble_user = user_id;
    // On va sélectionner les messages du nouveau utilisateur sélectionné
    for(msg_id of all_rbi[current_rbi]["users"][current_bubble_user]["messages_ids"]){
        if(current_bubble_messages_elements[msg_id] == undefined){
            continue;
        }
        current_bubble_messages_elements[msg_id].classList.add("bubble_conversation_message_user_selected");
    }
    current_bubble_users_elements[current_bubble_user].classList.add("bubble_conversation_user_selected");
}

// Quand l'utilisateur a cliqué sur un résultat de recherche -> On va pointer vers le
function on_result_search_selected_msg_id(msg_id){

    // On va d'abord charger la conversation de la bulle
    bubble_selected(all_rbi[current_rbi]["messages"][msg_id]["bubble_id"]);

    // On va se mettre en focus sur le message pointé
    current_bubble_messages_elements[msg_id].focus();
    current_bubble_messages_elements[msg_id].classList.remove("highlight");
    current_bubble_messages_elements[msg_id].classList.add("highlight");
}

// Quand on reçoit une préparation à un transfert de résultat de recherche depuis le serveur
function on_search_result_preparation(search_input, nb_results){

    // On vérifie que l'on a bien un résultat de recherche dont on attendait
    if(search_input != current_search_awaiting){
        return;
    }

    // On prépare pour recevoir les résultats de recherche
    search_results[search_input] = {
        "nb_results": nb_results,
        "results": {}
    };

    if(nb_results == 0){
        test_search_results_transfer_finished(search_input);
    }
}

// Quand on reçoit un résultat de recherche depuis le serveur
function on_search_result(search_input, index_result, msg_id, distance){

    // On vérifie que l'on a bien un résultat de recherche dont on attendait
    if(search_input != current_search_awaiting){
        return;
    }

    // S'il n'y a pas encore de résultats de recherche pour cette
    if(search_results[search_input] == undefined){
        search_results[search_input] = {
            "nb_results": -1,
            "results": {}
        };
    }

    // On enregistre le résultat de la recherche
    search_results[search_input]["results"][index_result] = {
        "msg_id": msg_id,
        "distance": distance
    };

    // On vérifie si c'était le dernier résultat attendu
    test_search_results_transfer_finished(search_input);
}

// On teste si le transfert du résultat de recherche a fini ou pas
function test_search_results_transfer_finished(search_input){

    // On teste si la recherche est finie
    if(Object.keys(search_results[search_input]["results"]).length != search_results[search_input]["nb_results"]){
        return;
    }

    // Recherche finie, on va afficher les résultats

    // On va d'abord nettoyer les résultats précédents
    document.getElementById("container_search_results").innerHTML = "";

    // On affiche le titre des résultats
    document.getElementById("search_result_title").style.display = "flex";
    document.getElementById("search_result_input").innerText = search_input;
    document.getElementById("search_result_user").innerText = current_search_user;

    // On affiche les resultats
    for(result of Object.keys(search_results[search_input]["results"])){
        add_search_result(search_results[search_input]["results"][result]);
    }

    // On met à jour l'animation au niveau de la barre de recherche
    search_animation_off();

    // On nettoie la variable current_search_awaiting
    current_search_awaiting = null;

    // On nettoie
    delete(search_results[search_input]);

}

// On désactive l'ancienne navigation sélectionnée
function clean_navigation_selected(){
    // On désactive l'ancienne navigation sélectionnée
    for(nav of document.getElementsByClassName("navigation_selected")){
        if(nav != undefined && nav.classList != undefined){
            nav.classList.remove("navigation_selected");
        }
    }
}

// On va dans la page pour faire des recherches
function navigation_search(){

    // On désactive l'ancienne navigation sélectionnée
    clean_navigation_selected();

    // On met à jour la navigation actuellement sélectionnée
    document.getElementById("navigation_search").classList.add("navigation_selected");

    // On change la page et on met à jour l'affichage
    current_page = "search_page";
    update_display();
}

// On va dans la page pour voir les bulles
function navigation_bubbles(){

    // On désactive l'ancienne navigation sélectionnée
    clean_navigation_selected();

    // On met à jour la navigation actuellement sélectionnée
    document.getElementById("navigation_bubbles").classList.add("navigation_selected");

    // On change la page et on met à jour l'affichage
    current_page = "bubbles_page";
    update_display();
}

// On va dans la page pour voir les utilisateurs
function navigation_users(){

    // On désactive l'ancienne navigation sélectionnée
    clean_navigation_selected();

    // On met à jour la navigation actuellement sélectionnée
    document.getElementById("navigation_users").classList.add("navigation_selected");

    // On change la page et on met à jour l'affichage
    current_page = "users_page";
    update_display();
}

// On va dans la page pour voir les configurations de moteur de recherche
function navigation_engine(){

    // On désactive l'ancienne navigation sélectionnée
    clean_navigation_selected();

    // On met à jour la navigation actuellement sélectionnée
    document.getElementById("navigation_engine").classList.add("navigation_selected");

    // On change la page et on met à jour l'affichage
    current_page = "engine_config_page";
    update_display();
}

// L'utilisateur veut faire une recherche
function search(){

    // On ne va pas faire de recherche tant qu'on est en train d'attendre un résultat
    if(current_search_awaiting != null){
        return
    }

    // On récupère les éléments HTML nécessaires pour avoir les infos à envoyer au serveur
    var search_settings = {};
    var search_input = document.getElementById("search_bar_input").value;
    var user_id = parseInt(document.getElementById("select_user").value);

    // On a besoin de faire la recherche à la place d'un utilisateur, donc il nous en faut un absolument
    if(user_id == -1){
        alert("Veuillez sélectionner un utilisateur pour faire la recherche.");
        return;
    }
    // Il nous faut aussi une configuration de moteur de recherche
    if(current_engine_config == null){
        alert("Veuillez sélectionner une configuration de moteur de recherche pour faire la recherche.");
        return;
    }

    // On nettoie les recherches précédentes
    if(current_search_awaiting != null){
        delete(search_results[current_search_awaiting]);
        current_search_awaiting = null;
    }

    // On met à jour l'utilisateur utilisé pour faire la recherche
    current_search_user = all_rbi[current_rbi]["users"][user_id]["name"];

    // On met à jour la recherche dont on va attendre les résultats
    current_search_awaiting = search_input;

    // On envoie la requête pour la recherche
    ws_send_msg(window.ws, {
        "type": "search_request",
        "rbi_name": current_rbi,
        "engine_config": current_engine_config,
        "user_id": user_id,
        "search_input": search_input,
        "search_settings": search_settings
    });

    // On met à jour l'animation au niveau de la barre de recherche
    search_animation_on("Waiting for search request processing...");
}

//
function search_animation_on(loading_text = "Searching..."){
    document.getElementById("search_bar_searching_animation_text").innerText = loading_text;
    document.getElementById("search_bar_searching_animation").style.flexGrow = 10;
    document.getElementById("search_bar_empty_space_animation").style.flexGrow = 0;
    document.getElementById("search_bar_button").style.display = 'none';
}

//
function search_animation_off(){
    document.getElementById("search_bar_searching_animation").style.flexGrow = 0;
    document.getElementById("search_bar_empty_space_animation").style.flexGrow = 10;
    document.getElementById("search_bar_button").style.display = 'flex';
}

//
function on_search_server_begin_process(search_input){
    if(current_search_awaiting == search_input){
        search_animation_on();
    }
}

//
function on_search_server_cancelled(search_input){
    if(current_search_awaiting == search_input){
        search_animation_off();
    }
}

// Quand l'utilisateur appuie sur la touche entrée sur la barre de recherche
function on_search_input_key_pressed(event){
    if(event.key == "Enter") {
        search();
    }
}

// Quand la connexion websocket est fermée
function on_websocket_connection_closed(error_message){

    // On indique que la connexion n'est plus active
    connection_active = false;

    // On met à jour
    document.getElementById("error_message").innerText = error_message;

    // On change la page actuelle et on met à jour l'affichage
    current_page = "error_connection_page";
    update_display();
}

// Quand on a bien reçu un acquittement de connexion positif
function on_websocket_connection_active(){

    // On l'indique
    awaiting_connection_success = false;

    // On met à jour la page et on met à jour l'affichage
    current_page = all_pages[0];
    update_display();
}

//
function display_standard_conversations(){

    for(div_msg of document.getElementById("bubble_conversation_messages").children){
        if(div_msg == undefined){
            continue;
        }
        //
        console.log("DEBUG | div_msg = ", div_msg, " | div_msg.style = ", div_msg.style);
        //
        div_msg.style.width = "50%";
        div_msg.style.marginLeft = "5px";
        div_msg.style.backgroundColor = "rgb(229, 223, 255)";
        div_msg.style.border = "none";
    }
}

//
function display_messages_conversations(){

    if(all_rbi_conversation_cuts[current_rbi] == undefined || all_rbi_conversation_cuts[current_rbi][current_bubble] == undefined){
        display_standard_conversations();
    }

    //
    for(node of document.getElementsByClassName("bubble_conversation_message_user_selected")){
        node.classList.remove("bubble_conversation_message_user_selected");
        node.classList.remove("bubble_conversation_message_user_selected");
    }

    //
    for(node of document.getElementsByClassName("bubble_conversation_user_selected")){
        node.classList.remove("bubble_conversation_user_selected");
        node.classList.remove("bubble_conversation_user_selected");
    }

    //
    const nb_conversations = all_rbi_conversation_cuts[current_rbi][current_bubble]["nb_conversations"];
    const msgs_colors = all_rbi_conversation_cuts[current_rbi][current_bubble]["msgs_colors"];
    for(msg_id of Object.keys(msgs_colors)){
        //
        var div_msg = document.getElementById("msg_" + msg_id);
        var msg_conversation_span = document.getElementById("msg_conversation_" + msg_id);
        //
        div_msg.style.width = "50%";
        div_msg.style.marginLeft = "" + (1 + (msgs_colors[msg_id] / nb_conversations * 50.0)) + "%";
        div_msg.style.backgroundColor = get_rgb_bg_fg_from_conv_id(msgs_colors[msg_id])["bg"];
        div_msg.style.border = "1px solid "+get_rgb_bg_fg_from_conv_id(msgs_colors[msg_id])["fg"];
        //
        msg_conversation_span.innerText = "conversation : " + msgs_colors[msg_id];
        msg_conversation_span.style.display = "flex";
    }
}

//
function on_cut_conversation_clicked(){

    if(document.getElementById("button_cut_conversations").innerText == button_cut_conversations_default_text){

        if(all_rbi_conversation_cuts[current_rbi] != undefined && all_rbi_conversation_cuts[current_rbi][current_bubble] != undefined){

            document.getElementById("button_cut_conversations").innerText = button_cut_conversation_remove_conversations_text;
            document.getElementById("button_cut_conversations").disabled = false;

            display_messages_conversations();

            return;
        }

        document.getElementById("button_cut_conversations").disabled = true;
        document.getElementById("button_cut_conversations").innerText = button_cut_conversations_waiting_results_text;


        // On envoie la requête pour la recherche
        ws_send_msg(window.ws, {
            "type": "conversation_cut_request",
            "rbi_name": current_rbi,
            "bubble_id": parseInt(current_bubble)
        });
    }
    else if(document.getElementById("button_cut_conversations").innerText == button_cut_conversation_remove_conversations_text){

        document.getElementById("button_cut_conversations").innerText = button_cut_conversations_default_text;
        document.getElementById("button_cut_conversations").disabled = false;

        display_standard_conversations();

    }

}

//
function on_cut_conversation_results_received(nb_conversations, msgs_colors, result_rbi, result_bubble){

    document.getElementById("button_cut_conversations").innerText = button_cut_conversation_remove_conversations_text;
    document.getElementById("button_cut_conversations").disabled = false;

    if(all_rbi_conversation_cuts[current_rbi] == undefined){
        all_rbi_conversation_cuts[current_rbi] = {};
    }

    all_rbi_conversation_cuts[current_rbi][current_bubble] = {
        "nb_conversations": nb_conversations,
        "msgs_colors": msgs_colors
    }

    if(current_rbi != result_rbi || current_bubble != result_bubble){
        return;
    }

    display_messages_conversations();

}

//
function go_to_import_bubble_page(){
    // On change la page et on met à jour l'affichage
    current_page = "import_bubble_page";
    update_display();
}

//
function send_import_request_to_server(){

    // On récupère la bulle à importer
    var bubble_name = document.getElementById("bubble_import_name").value;
    var text_to_import = document.getElementById("bubble_import_text").value;

    // On envoie la requête pour la recherche
    ws_send_msg(window.ws, {
        "type": "import_request",
        "rbi_name": current_rbi,
        "bubble_name": bubble_name,
        "bubble_text_to_import": text_to_import
    });

    // On change la page et on met à jour l'affichage
    current_page = "request_waiting_import_bubble_page";
    update_display();
}

//
function on_bubble_import_started(rbi_name, bubble_name, nb_msgs, estimated_time){
    //
    if(rbi_name != current_rbi){
        return;
    }
    //
    current_bubble_import_data["bubble_name"] = bubble_name;
    current_bubble_import_data["nb_msgs"] = nb_msgs;
    current_bubble_import_data["msgs_processed"] = 0;
    //
    document.getElementById("bubble_import_progress_bar").style.width = "0";
    //
    document.getElementById("bubble_import_nb_msgs").innerText = nb_msgs;
    document.getElementById("bubble_import_estimated_time_left").innerText = estimated_time;

    // On change la page et on met à jour l'affichage
    current_page = "doing_import_bubble_page";
    update_display();
}

//
function on_bubble_import_progress_update(rbi_name, bubble_name, msgs_processed, estimated_time){
    //
    if(current_bubble_import_data["bubble_name"] != bubble_name || rbi_name != current_rbi){
        return;
    }

    //
    current_bubble_import_data["msgs_processed"] = msgs_processed;
    //
    document.getElementById("bubble_import_progress_bar").style.width = "" + (msgs_processed / current_bubble_import_data["nb_msgs"] * 100.0) + "%";
    //
    document.getElementById("bubble_import_estimated_time_left").innerText = estimated_time;
}

//
function on_bubble_import_finished(rbi_name, bubble_id){
    if(rbi_name == current_rbi){
        bubble_selected(bubble_id);
    }
}

//
function on_bubble_import_error(rbi_name, bubble_name, error_msg){
    //
    if(current_bubble_import_data["bubble_name"] != bubble_name || rbi_name != current_rbi){
        return;
    }

    //
    go_to_import_bubble_page();

    //
    alert("Il y a eu une erreur lors de l'importation de la bulle : \""+error_msg+"\"");
}
