/*
Script pour la page hyper_parameters_optimisation.html

Auteur: Nathan Cerisara
*/



/* Variables globales */

//
const webapp_type = "hyper_parameters_optimisation";

//
var types = null;

//
var general_classes = null;

// Tant que l'on attends un message du serveur indiquant que la connexion a bien été établie
var awaiting_connection_success = true;

// Tant que la connexion au websocket est active
var connection_active = true;

// Liste de toutes les pages (ne pas toucher à celles d'index 0 et 1)
const all_pages = ["select_task_page", "error_connection_page", "connection_loading_page", "loading_task_page", "select_config_page", "create_edit_config_page", "manual_test_page", "manual_test_graphs_page", "algorithmic_optimization_page", "loading_configs_page", "algorithmic_optimization_graphs_page"];

// Page de démo actuelle, si une rbi est sélectionnée
var current_page = "connection_loading_page";

// Tâche actuellement sélectionnée
var current_task = "";

// Liste de toutes les tâches
const all_tasks = ["NER", "conversation_cut", "search"];

// Passage de la tache actuelle au type de base des configurations de moteurs
const tasks_to_base_config = {
    "NER": "NER_Engine",
    "conversation_cut": "ConversationEngine",
    "search": "SearchEngine"
}

// Les données pour chacune des tâches
var data_tasks = {};

//
var all_engine_config_buttons = {};

//
var current_engine_config = "";

//
var current_engine_config_button = null;

//
var create_edit_mode = "create";

//
var edit_config_config_name = "";

//
var current_create_or_edit_config = {};

//
var current_drop_down_button_displayed = null;

//
var current_optimisable_hyper_parameters_keys = [];

//
var selected_keys_to_curve_list = [];

//
const max_nb_keys_to_curve_list = 1;

//
var awaiting_test_benchmark_result_requests = null;

//
var awaiting_test_benchmark_result_type = null;

//
var awaiting_test_benchmark_request_task = null;

//
var awaiting_test_benchmark_request_config = null;

//
var awaiting_test_benchmark_curve_results = null;

//
var awaiting_test_benchmark_result_input_dim = 1;

// Possible values : "avg" or a benchmark_name
var current_curve_benchmark_display = "avg";

//
const MAX_NB_PTS_INTERMEDIATE = 1000;

//
var curve_request_error = false;

//
var hpo_algorithms = {};

//
var current_hpo_algorithm_selected = "";

//
var optimization_processes = {};

//
var current_awaiting_optimization_process = null;


/**
 * @param {Object} configDict
 * @param {Array<string|number>} keysOfTheValue
 * @returns {string|number}
 */
function getValueFromConfig(configDict, keysOfTheValue) {
    let currentDictOrValue = configDict;
    for (const k of keysOfTheValue) {
        if (Array.isArray(k)) {
            currentDictOrValue = currentDictOrValue[k[0]];
        } else {
            currentDictOrValue = currentDictOrValue[k];
        }
    }
    return currentDictOrValue;
}

/**
 * @param {Object} configDict
 * @param {Array<string|number>} keysOfTheValue
 * @param {string|number} value
 * @returns {Object}
 */
function setValueToConfig(configDict, value, keysOfTheValue) {
    let currentDictOrValue = configDict;
    for (const k of keysOfTheValue.slice(0, -1)) {
        if (Array.isArray(k)) {
            currentDictOrValue = currentDictOrValue[k[0]];
        } else {
            currentDictOrValue = currentDictOrValue[k];
        }
    }

    const lastKey = keysOfTheValue[keysOfTheValue.length - 1];
    if (Array.isArray(lastKey)) {
        currentDictOrValue[lastKey[0]] = value;
    } else {
        currentDictOrValue[lastKey] = value;
    }

    return configDict;
}

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
        document.getElementById("header_2").style.display = "none";
        //
    }

    // Si la connexion n'est plus active, on n'affiche que la page d'erreur
    else if(awaiting_connection_success){
        current_page = "connection_loading_page";
        set_display_page();
        //
        document.getElementById("header_2").style.display = "none";
        //
    }

    //
    else{
        //
        if(current_page != all_pages[0]){
            //
            document.getElementById("header_2").style.display = "flex";
        }
        else{
            //
            document.getElementById("header_2").style.display = "none";
        }
        //
        set_display_page();
    }
}

// On désactive l'ancienne navigation sélectionnée
function clean_navigation_selected(){
    // On désactive l'ancienne navigation sélectionnée
    for(nav of document.getElementsByClassName("navigation_selected")){
        if(nav != undefined && nav.classList != undefined){
            nav.classList.remove("navigation_selected");
            nav.classList.remove("navigation_selected");
        }
    }
}

//
function go_to_page(page_name){
    // On ne va que sur les pages qui existent
    if(!all_pages.includes(page_name)){
        return;
    }

    //
    if( current_engine_config == "" && ["manual_test_page", "manual_test_graphs_page", "algorithmic_optimization_page"].includes(page_name)){
        alert("Il faut sélectionner une configuration avant !");
        return;
    }

    // On désactive l'ancienne navigation sélectionnée
    clean_navigation_selected();

    // On met à jour la navigation actuellement sélectionnée
    if(page_name == "select_config_page" || page_name == "create_edit_config_page"){
        document.getElementById("navigation_config").classList.add("navigation_selected");
    }
    else if(page_name == "manual_test_page" || page_name == "manual_test_graphs_page"){
        document.getElementById("navigation_manual_tests").classList.add("navigation_selected");
    }
    else if(page_name == "algorithmic_optimization_page" || page_name == "algorithmic_optimization_graphs_page"){
        document.getElementById("navigation_algorithmic_optmization").classList.add("navigation_selected");
    }

    // On va sur la page
    current_page = page_name;
    update_display();
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
    go_to_page("loading_configs_page");

    // On va demander les types / classes
    ws_send_msg(window.ws, {
        "type": "hpo_ask_types_and_classes"
    });
}

//
function on_types_and_classes_received(types_, general_classes_){

    // On récupère les valeurs
    types = types_;
    general_classes = general_classes_;

    // On met à jour la page et on met à jour l'affichage
    go_to_page("select_task_page");

}

//
function add_available_config_item(task, config){
    //
    const engine_config_name = config["config_name"];
    //
    var engine_config_div = document.createElement("div");
    engine_config_div.setAttribute("id", "config_div_button_"+engine_config_name);
    engine_config_div.classList.add("engine_config_item", "row", "m_5p", "clickable");
    engine_config_div.setAttribute("onclick", "engine_config_selected(\""+engine_config_name+"\");")

    //
    var engine_left_col = document.createElement("div");
    engine_left_col.classList.add("col", "flexgrow_10");
    engine_left_col.style.maxWidth = "95%";
    engine_left_col.style.overflow = "hidden";
    engine_config_div.appendChild(engine_left_col);

    //
    var engine_right_col = document.createElement("div");
    engine_right_col.classList.add("col");
    engine_right_col.style.position = "relative";
    engine_config_div.appendChild(engine_right_col);

    // Ajout du bouton dans la liste des boutons
    all_engine_config_buttons[engine_config_name] = engine_config_div;

    //
    var row1 = document.createElement("div");
    row1.classList.add("row", "w_100", "h_auto");

    //
    var nom_config = document.createElement("span");
    nom_config.innerText = config["config_name"];
    row1.appendChild(nom_config);

    //
    var row2 = document.createElement("div");
    row2.classList.add("row", "w_100", "h_auto");
    first = true;
    for(algo_config of config["algorithms"]){
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

    //
    engine_left_col.appendChild(row1);
    engine_left_col.appendChild(row2);

    //
    var three_dots_buttons = document.createElement("img");
    three_dots_buttons.src = "res/logo_three_dots.svg";
    three_dots_buttons.classList.add("size_normal");
    three_dots_buttons.addEventListener('click', function(event) {
        // Your code here
        toggle_engine_config_drop_down_button(engine_config_name);

        // Stop the event from propagating
        event.stopPropagation();
    });

    //
    engine_right_col.appendChild(three_dots_buttons);


    // menu quand on clique sur les trois petits points
    // TODO
    var div_drop_down_menu = document.createElement("div");
    div_drop_down_menu.id = "drop_down_" + escapeHtml(engine_config_name);
    div_drop_down_menu.classList.add("col");
    div_drop_down_menu.style.zIndex = 5;
    div_drop_down_menu.style.display = "none";
    div_drop_down_menu.style.border = "1px solid black";
    div_drop_down_menu.style.borderCollapse = "collapse";
    div_drop_down_menu.style.backgroundColor = "white";
    div_drop_down_menu.style.position = "absolute";
    div_drop_down_menu.style.top = "var(--size_normal)";
    div_drop_down_menu.style.right = 0;
    div_drop_down_menu.style.minWidth = 100;
    div_drop_down_menu.style.minHeight = 100;
    engine_right_col.appendChild(div_drop_down_menu);


    //
    var drop_down_button_edit = document.createElement("div");
    drop_down_button_edit.classList.add("row", "clickable", "p_5p");
    drop_down_button_edit.style.border = "1px solid black";
    drop_down_button_edit.style.borderCollapse = "collapse";
    div_drop_down_menu.appendChild(drop_down_button_edit);
    drop_down_button_edit_icon = document.createElement("img");
    drop_down_button_edit_icon.src = "res/logo_edit.svg";
    drop_down_button_edit_icon.classList.add("size_small", "m_5p", "center_v");
    drop_down_button_edit.appendChild(drop_down_button_edit_icon);
    drop_down_button_edit_text = document.createElement("span");
    drop_down_button_edit_text.classList.add("center_v");
    drop_down_button_edit_text.innerText = "Modifier"
    drop_down_button_edit.appendChild(drop_down_button_edit_text);
    drop_down_button_edit.addEventListener('click', function(event) {
        // Your code here
        config_edit_or_create_new(engine_config_name);
    });


    //
    var drop_down_button_duplicate = document.createElement("div");
    drop_down_button_duplicate.classList.add("row", "clickable", "p_5p");
    drop_down_button_duplicate.style.border = "1px solid black";
    drop_down_button_duplicate.style.borderCollapse = "collapse";
    div_drop_down_menu.appendChild(drop_down_button_duplicate);
    drop_down_button_duplicate_icon = document.createElement("img");
    drop_down_button_duplicate_icon.src = "res/logo_duplicate.svg";
    drop_down_button_duplicate_icon.classList.add("size_small", "m_5p");
    drop_down_button_duplicate.appendChild(drop_down_button_duplicate_icon);
    drop_down_button_duplicate_text = document.createElement("span");
    drop_down_button_duplicate_text.classList.add("center_v");
    drop_down_button_duplicate_text.innerText = "Dupliquer"
    drop_down_button_duplicate.appendChild(drop_down_button_duplicate_text);
    drop_down_button_duplicate.addEventListener('click', function(event) {
        // Your code here
        on_duplicate_button_click(engine_config_name);
    });


    //
    var drop_down_button_delete = document.createElement("div");
    drop_down_button_delete.classList.add("row", "clickable", "p_5p");
    drop_down_button_delete.style.border = "1px solid black";
    drop_down_button_delete.style.borderCollapse = "collapse";
    drop_down_button_delete.setAttribute("onclick", "alert(\"delete - " + engine_config_name + "\");");
    div_drop_down_menu.appendChild(drop_down_button_delete);
    drop_down_button_delete_icon = document.createElement("img");
    drop_down_button_delete_icon.src = "res/logo_delete.svg";
    drop_down_button_delete_icon.classList.add("size_small", "m_5p");
    drop_down_button_delete.appendChild(drop_down_button_delete_icon);
    drop_down_button_delete_text = document.createElement("span");
    drop_down_button_delete_text.classList.add("center_v");
    drop_down_button_delete_text.innerText = "Supprimer"
    drop_down_button_delete.appendChild(drop_down_button_delete_text);
    drop_down_button_delete.addEventListener('click', function(event) {
        // Your code here
        on_delete_button_click(engine_config_name);
    });


    //
    document.getElementById("available_configs_list").appendChild(engine_config_div);
}

//
function toggle_engine_config_drop_down_button(engine_config_name){
    if(document.getElementById("drop_down_" + escapeHtml(engine_config_name)).style.display == "none"){
        show_engine_config_drop_down_button(engine_config_name);
    }
    else{
        hide_engine_config_drop_down_button(engine_config_name);
    }
}

//
function show_engine_config_drop_down_button(engine_config_name){
    document.getElementById("drop_down_" + escapeHtml(engine_config_name)).style.display = "flex";
    current_drop_down_button_displayed = engine_config_name;
}

//
function hide_engine_config_drop_down_button(engine_config_name){
    document.getElementById("drop_down_" + escapeHtml(engine_config_name)).style.display = "none";
    current_drop_down_button_displayed = null;
}

//
function task_selected(task){
    //
    if(!all_tasks.includes(task)){
        return;
    }
    //
    if(current_task != task){
        awaiting_test_benchmark_request_config = null;
        awaiting_test_benchmark_request_task = null;
        document.getElementById("bt_send_test_request_manual_tests").disabled = false;
        document.getElementById("bt_send_draw_curve_request_manual_tests").disabled = false;
    }
    //
    current_task = task;
    // On envoie la requête pour la recherche
    if(!test_transfer_finished(task)){
        ws_send_msg(window.ws, {
            "type": "hpo_task_configs_and_benchmarks",
            "task": current_task
        });
        //
        current_page = "loading_task_page";
        update_display();
    }
    else{
        on_transfer_finished(task);
    }
}

//
function init_hpo_algorithms_select(){
    // nettoyage
    document.getElementById("select_optimization_algorithm").innerHTML = "";

    // Pour chaque algorithme, on lui ajoute son option
    for(algo_name in hpo_algorithms){
        //
        var option_algo = document.createElement("option");
        option_algo.innerText = algo_name;
        option_algo.value = algo_name;
        //
        document.getElementById("select_optimization_algorithm").appendChild(option_algo);
    }

    // On va choisir le 1er algo s'il y en a au moins 1
    if(Object.keys(hpo_algorithms).length > 0){
        //
        var algo_name = Object.keys(hpo_algorithms)[0];
        //
        document.getElementById("select_optimization_algorithm").value = algo_name;
        current_hpo_algorithm_selected = algo_name;
        on_hpo_algorithm_selected(algo_name);
    }
}

//
function on_hpo_algorithm_selected(algo_name){
    // Nettoyage
    document.getElementById("optimization_algorithm_params").innerHTML = "";

    // On va ajouter une ligne d'input pour chaque paramètre de l'algorithme sélectionné
    for(var i=0; i < Object.keys(hpo_algorithms[algo_name]).length; i++){
        var algo_parameter_name = Object.keys(hpo_algorithms[algo_name])[i];
        if(hpo_algorithms[algo_name][algo_parameter_name][0] == "number"){
            add_number_input_hpo_algorithms_row(algo_parameter_name, hpo_algorithms[algo_name][algo_parameter_name][1]);
        }
    }

}


//
function add_number_input_hpo_algorithms_row(algo_parameter_name, default_value){
    //
    var div_row = document.createElement("div");
    div_row.classList.add("row", "center_h");
    div_row.style.margin = "5px";
    div_row.style.marginLeft = "30px";
    //
    var label = document.createElement("label");
    label.classList.add("center_v");
    label.innerText = algo_parameter_name + " : ";
    div_row.appendChild(label);
    //
    var input = document.createElement("input");
    input.classList.add("center_v");
    input.setAttribute("id", get_hpo_algo_parameter_id(algo_parameter_name));
    input.style.marginLeft = "5px";
    input.style.marginRight = "30px";
    input.style.maxWidth = "5vw";
    input.style.width = "5vw";
    input.style.minWidth = "50px";
    input.value = default_value;
    input.type = "number";
    div_row.appendChild(input);
    //
    document.getElementById("optimization_algorithm_params").appendChild(div_row);
    //
}


//
function on_hpo_prepare_transfer(task, nb_configs, nb_benchmarks, hpo_algorithms_, default_config=""){
    //
    if(data_tasks[task] == undefined){
        data_tasks[task] = {
            "state": 0,     // 0 = loading, 1 = loaded
            "nb_configs": nb_configs,
            "nb_benchmarks": nb_benchmarks,
            "configs": {},
            "benchmarks_names": [],
            "default_config": default_config
        };
    }
    else{
        data_tasks[task]["state"] = 0;
        data_tasks[task]["nb_configs"] = nb_configs;
        data_tasks[task]["nb_benchmarks"] = nb_benchmarks;
        data_tasks[task]["default_config"] = default_config;
    }
    //
    if(hpo_algorithms_ != hpo_algorithms){
        hpo_algorithms = hpo_algorithms_;
        init_hpo_algorithms_select();
    }
}

//
function test_transfer_finished(task){
    //
    if(data_tasks[task] == undefined){
        return false;
    }
    //
    if(data_tasks[task]["state"] == 1){
        return true;
    }
    //
    if(Object.keys(data_tasks[task]["configs"]).length == data_tasks[task]["nb_configs"] && data_tasks[task]["benchmarks_names"].length == data_tasks[task]["nb_benchmarks"]){
        data_tasks[task]["state"] = 1;
        return true;
    }
    //
    return false;
}

//
function on_transfer_finished(task){
    // Nettoyage
    document.getElementById("available_configs_list").innerHTML = "";
    all_engine_config_buttons = {};
    selected_keys_to_curve_list = [];

    // On ajoute toutes les configs
    for(config of Object.values(data_tasks[task]["configs"])){
        //
        add_available_config_item(task, config);
    }

    //
    if(data_tasks[task]["default_config"] != ""){
        engine_config_selected(data_tasks[task]["default_config"]);
    }

    // On nettoie la liste des benchmarks dans la page des tests manuels
    document.getElementById("manual_tests_benchmarks_results").innerHTML = "";

    // On nettoie la liste des benchmarks dans la page optimisation algorithmique
    document.getElementById("optimization_algorithm_benchmark_selection").innerHTML = "";

    // On nettoie la liste de sélection de l'affichage des graphes dans la page d'affichage des graphes dans la page des tests manuels
    document.getElementById("graphs_benchmark_select").innerHTML = "";

    // Bouton de base de sélection de graphe valeur moyenne
    add_benchmark_graph_select("avg");
    current_curve_benchmark_display = "avg";

    // On ajoute la liste des benchmarks dans la page des tests manuels et dans la page optimisation algorithmique
    for(benchmark_name of data_tasks[current_task]["benchmarks_names"]){
        add_benchmark_result_div(benchmark_name);
        add_benchmark_selection_div(benchmark_name);
        add_benchmark_graph_select(benchmark_name);
    }

    // On change la page
    go_to_page("select_config_page");
}

//
function add_benchmark_graph_select(benchmark_name){
    var bt = document.createElement("button");
    bt.style.border = "1px solid black";
    bt.style.borderRadius = "none";
    bt.style.padding = "5px";
    bt.style.textAlign = "center";
    bt.style.marginTop ="5px";
    bt.style.marginBottom = "5px";
    bt.style.marginLeft = "1px";
    bt.style.marginRight = "1px";
    bt.style.display = "flex";
    bt.style.boxShadow = "none";
    bt.innerText = benchmark_name;
    //
    bt.onclick = function(event){
        if(current_curve_benchmark_display != benchmark_name){
            current_curve_benchmark_display = benchmark_name;
            curve_display_graph();
        }
    }
    //
    document.getElementById("graphs_benchmark_select").appendChild(bt);
}

//
function add_benchmark_result_div(benchmark_name){
    //
    var div_container = document.createElement("div");
    div_container.classList.add("row", "flex_item_30", "m_10p", "benchmark_result_div_container");
    //
    var div_name = document.createElement("div");
    div_name.classList.add("flex", "flexgrow_2", "benchmark_result_div_name");
    div_container.appendChild(div_name);
    //
    var span_name = document.createElement("span");
    span_name.classList.add("center_h", "center_v");
    span_name.innerText = benchmark_name;
    div_name.appendChild(span_name);
    //
    var div_score = document.createElement("div");
    div_score.classList.add("flex", "flexgrow_1", "benchmark_result_div_score");
    div_container.appendChild(div_score);
    //
    var span_score = document.createElement("div");
    span_score.setAttribute("id", "benchmark_score_" + escapeHtml(benchmark_name));
    span_score.classList.add("center_h", "centre_v");
    span_score.innerText = "/";
    div_score.appendChild(span_score);
    //
    document.getElementById("manual_tests_benchmarks_results").appendChild(div_container);
}

//
function add_benchmark_selection_div(benchmark_name){
    //
    var div_row = document.createElement("div");
    div_row.classList.add("row", "m_5p");
    //
    var checkbox = document.createElement("input");
    checkbox.setAttribute("id", get_hpo_algo_benchmark_checkbox_id(benchmark_name));
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkbox.classList.add("center_v");
    div_row.appendChild(checkbox);
    //
    var span = document.createElement("span");
    span.classList.add("center_v", "m_l_5p", "m_r_5p");
    span.innerText = benchmark_name;
    div_row.appendChild(span);
    //
    var input_coef = document.createElement("input");
    input_coef.setAttribute("id", get_hpo_algo_benchmark_coef_id(benchmark_name));
    input_coef.type = "number";
    input_coef.classList.add("center_v", "m_l_5p");
    input_coef.value = 1.0;
    input_coef.style.width = "4vw";
    div_row.appendChild(input_coef);
    //
    document.getElementById("optimization_algorithm_benchmark_selection").appendChild(div_row);
}

//
function on_hpo_data_config(task, config){
    //
    if(data_tasks[task] == undefined){
        data_tasks[task] = {
            "state": -1,     // -1 = don't know, 0 = loading, 1 = loaded
            "nb_configs": -1,
            "nb_benchmarks": -1,
            "configs": {},
            "benchmarks_names": []
        };
    }
    //
    data_tasks[task]["configs"][config["config_name"]] = config;
    //
    if(test_transfer_finished(task)){
        on_transfer_finished(task);
    }
}

//
function on_hpo_data_benchmark(task, benchmark_name){
    //
    if(data_tasks[task] == undefined){
        data_tasks[task] = {
            "state": -1,     // -1 = don't know, 0 = loading, 1 = loaded
            "nb_configs": -1,
            "nb_benchmarks": -1,
            "configs": {},
            "benchmarks_names": []
        };
    }
    //
    data_tasks[task]["benchmarks_names"].push(benchmark_name);
    //
    if(test_transfer_finished(task)){
        on_transfer_finished(task);
    }
}

// Quand l'utilisateur sélectionne une configuration de moteur de recherche
function engine_config_selected(engine_config_name){

    //
    if(!data_tasks[current_task]){
        return;
    }

    // On met à jour la variable correspondante
    current_engine_config = engine_config_name;

    // On met à jour l'affichage le nom de la config sélectionnée à la page des tests manuels
    document.getElementById("manual_tests_selected_config").innerText = engine_config_name;

    // On nettoie le précédent bouton sélectionné
    if(current_engine_config_button != null){
        current_engine_config_button.classList.remove("selected_engine_config_item");
        current_engine_config_button = null;
    }

    // On met à jour le bouton sélectionné
    current_engine_config_button = all_engine_config_buttons[current_engine_config];
    current_engine_config_button.classList.add("selected_engine_config_item");

    // On nettoie la section des hyper paramètres à optimiser dans la page des tests manuels
    document.getElementById("edit_config_params").innerHTML = "";

    // On nettoie le score précédent moyen dans la page des tests manuels
    document.getElementById("benchmark_score_avg").innerText = "/";

    // On nettoie l'indication du nombre de tests à calculer dans la page des tests manuels
    document.getElementById("nb_benchmarks_calc").innerText = "0";

    // On nettoie la section des hyper paramètres à optimiser dans la page optimisation algorithmique
    document.getElementById("optimization_algorithm_selection_hyper_parameters").innerHTML = "";

    // On nettoie les boutons de lancer de tests de la page des tests manuels
    document.getElementById("bt_send_test_request_manual_tests").disabled = false;
    document.getElementById("bt_send_draw_curve_request_manual_tests").disabled = false;

    // On nettoie la liste des hyper paramètres à optimiser de l'ancienne configuration sélectionnée
    current_optimisable_hyper_parameters_keys = [];

    // On nettoie la liste des paramètres sélectionnés à tracer la courbe
    selected_keys_to_curve_list = [];

    // On récupère la liste des hyper paramètres à optimiser pour cette nouvelle configuration sélectionnée
    get_optimisable_hyper_parameters_from_configuration_dict(tasks_to_base_config[current_task], data_tasks[current_task]["configs"][current_engine_config]);

    // On ajoute chaque hyper paramètre à optimiser à la section des hyper paramètres à optimiser dans la page des tests manuels
    for(hp_keys of current_optimisable_hyper_parameters_keys){
        //
        var param_type = get_type_from_config_keys(tasks_to_base_config[current_task], hp_keys);
        //
        if(param_type == null){
            continue;
        }
        //
        if(param_type[0] != "number"){
            continue;
        }
        //
        var value = get_value_from_config_keys(current_engine_config, hp_keys);
        //
        add_number_input_manual_tests_row(hp_keys, value);
        //
        add_hyper_parameter_selection_div(hp_keys);
    }

}

//
function keysEscapeHtml(keys){
    //
    const key_type = typeof(keys);
    //
    if(key_type != "object"){
        if(key_type == "string"){
            return escapeHtml(keys);
        }
        else if(key_type == "number"){
            return "" + keys;
        }
        else{
            return "";
        }
    }
    else if(Array.isArray(keys)){
        var fkeys = [];
        for(k of keys){
            fkeys.push(keysEscapeHtml(k));
        }
        return fkeys;
    }
    else{
        var fkeys = {};
        for(k in keys){
            fkeys[k] = keysEscapeHtml(keys[k]);
        }
        return fkeys;
    }
}

//
function keysJoin(keys, join_string="__"){
    if(typeof(keys) != "object"){
        return keys;
    }
    else if(Array.isArray(keys)){
        var txt = "";
        for(var i=0; i<keys.length; i++){
            if(i!=0){
                txt += join_string;
            }
            txt += keysJoin(keys[i]);
        }
        return txt;
    }
    else{
        var txt = "";
        for(var i=0; i<Object.keys(keys).length; i++){
            //
            var k = Object.keys(keys)[i];
            //
            if(i!=0){
                txt += join_string;
            }
            txt += k + join_string + keysJoin(keys[k]);
        }
        return txt;
    }
}

//
function get_hpo_algo_benchmark_checkbox_id(benchmark_name){
    return "hpo_algo_benchmark_checkbox_" + escapeHtml(benchmark_name);
}

//
function get_hpo_algo_benchmark_coef_id(benchmark_name){
    return "hpo_algo_benchmark_coef_" + escapeHtml(benchmark_name);
}

//
function get_hpo_algo_parameter_id(algo_parameter_name){
    return "hpo_algo_parameter_" + algo_parameter_name;
}

//
function get_hp_value_manual_tests_id(keys){
    return "hp_value_manual_tests_" + keysJoin(keysEscapeHtml(keys), "___");
}

//
function get_hp_manual_tests_add_to_curve_interval_min_id(keys){
    return "hp_manual_tests_interval_min_" + keysJoin(keysEscapeHtml(keys), "___");
}

//
function get_hp_manual_tests_add_to_curve_interval_max_id(keys){
    return "hp_manual_tests_interval_max_" + keysJoin(keysEscapeHtml(keys), "___");
}

//
function get_hp_manual_tests_add_to_curve_interval_nb_pts_id(keys){
    return "hp_manual_tests_interval_nb_pts_" + keysJoin(keysEscapeHtml(keys), "___");
}

//
function get_hp_algorithmic_optimization_constraints_min_id(keys){
    return "hp_algorithmic_optimization_constraints_min_" + keysJoin(keysEscapeHtml(keys), "___");
}

//
function get_hp_algorithmic_optimization_constraints_max_id(keys){
    return "hp_algorithmic_optimization_constraints_max_" + keysJoin(keysEscapeHtml(keys), "___");
}

//
function get_hp_algorithmic_optimization_constraint_checkbox_id(keys){
    return "hp_algorithmic_optimization_constraint_checkbox_" + keysJoin(keysEscapeHtml(keys), "___");
}

//
function add_hyper_parameter_selection_div(keys){
    //
    var key = "";
    for(k of keys){
        if(key != ""){
            key += "/";
        }
        if(Array.isArray(k)){
            key += "" + k[1];
        }
        else{
            key += k;
        }
    }
    //
    if(key.length >= 100){
        key = "..." + key.slice(-100);
    }
    //
    var div_row = document.createElement("div");
    div_row.classList.add("row", "m_5p");
    //
    var checkbox = document.createElement("input");
    checkbox.setAttribute("id", get_hp_algorithmic_optimization_constraint_checkbox_id(keys))
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkbox.classList.add("center_v");
    div_row.appendChild(checkbox);
    //
    var span = document.createElement("span");
    span.classList.add("center_v", "m_l_5p", "m_r_5p");
    span.innerText = key;
    div_row.appendChild(span);
    //
    var label_interval_min = document.createElement("span");
    label_interval_min.classList.add("center_v", "m_l_10p", "m_r_5p");
    label_interval_min.innerText = "- intervalle min : ";
    div_row.appendChild(label_interval_min);
    //
    var input_interval_min = document.createElement("input");
    input_interval_min.setAttribute("id", get_hp_algorithmic_optimization_constraints_min_id(keys));
    input_interval_min.type = "number";
    input_interval_min.classList.add("center_v", "m_l_5p");
    input_interval_min.value = 0.0;
    input_interval_min.style.width = "4vw";
    div_row.appendChild(input_interval_min);
    //
    var label_interval_max = document.createElement("span");
    label_interval_max.classList.add("center_v", "m_l_10p", "m_r_5p");
    label_interval_max.innerText = " - intervalle max : ";
    div_row.appendChild(label_interval_max);
    //
    var input_interval_max = document.createElement("input");
    input_interval_max.setAttribute("id", get_hp_algorithmic_optimization_constraints_max_id(keys));
    input_interval_max.type = "number";
    input_interval_max.classList.add("center_v", "m_l_5p");
    input_interval_max.value = 1.0;
    input_interval_max.style.width = "4vw";
    div_row.appendChild(input_interval_max);
    //
    document.getElementById("optimization_algorithm_selection_hyper_parameters").appendChild(div_row);
}

//
function add_number_input_manual_tests_row(keys, value){
    //
    var key = "";
    for(k of keys){
        if(key != ""){
            key += "/";
        }
        if(Array.isArray(k)){
            key += "" + k[1];
        }
        else{
            key += k;
        }
    }

    //
    if(key.length >= 100){
        key = "..." + key.slice(-100);
    }

    //
    var div_row = document.createElement("div");
    div_row.classList.add("row");
    div_row.style.margin = "5px";
    div_row.style.marginLeft = "30px";
    //
    var label = document.createElement("label");
    label.classList.add("center_v");
    label.innerText = key + " : ";
    div_row.appendChild(label);
    //
    var input = document.createElement("input");
    input.classList.add("center_v");
    input.setAttribute("id", get_hp_value_manual_tests_id(keys));
    input.style.marginLeft = "5px";
    input.style.marginRight = "30px";
    input.style.maxWidth = "5vw";
    input.style.width = "5vw";
    input.style.minWidth = "50px";
    input.value = value;
    input.type = "number";
    div_row.appendChild(input);
    //
    input.onchange = function(event){
        // TODO
    }
    //
    var bt_add_to_curve_list = document.createElement("button");
    bt_add_to_curve_list.classList.add("center_v");
    bt_add_to_curve_list.style.border = "1px solid black";
    bt_add_to_curve_list.innerText = "+";
    bt_add_to_curve_list.style.textAlign = "center";
    bt_add_to_curve_list.style.width = "3vh";
    bt_add_to_curve_list.style.height = "3vh";
    div_row.appendChild(bt_add_to_curve_list);
    //
    var bt_del_to_curve_list = document.createElement("button");
    bt_del_to_curve_list.classList.add("center_v");
    bt_del_to_curve_list.style.border = "1px solid black";
    bt_del_to_curve_list.style.display = "none";
    bt_del_to_curve_list.innerText = "x";
    bt_del_to_curve_list.style.textAlign = "center";
    bt_del_to_curve_list.style.width = "3vh";
    bt_del_to_curve_list.style.height = "3vh";
    div_row.appendChild(bt_del_to_curve_list);
    //
    var span_add_to_curve_list = document.createElement("span");
    span_add_to_curve_list.classList.add("center_v", "m_l_5p");
    span_add_to_curve_list.innerText = "ajouter à tracer la courbe";
    div_row.appendChild(span_add_to_curve_list);
    //
    var span_start_curve_list = document.createElement("span");
    span_start_curve_list.classList.add("center_v", "m_l_5p");
    span_start_curve_list.innerText = "deb : ";
    span_start_curve_list.style.display = "none";
    div_row.appendChild(span_start_curve_list);
    //
    var input_start_curve_list = document.createElement("input");
    input_start_curve_list.setAttribute("id", get_hp_manual_tests_add_to_curve_interval_min_id(keys));
    input_start_curve_list.classList.add("center_v", "m_l_5p");
    input_start_curve_list.type = "number";
    input_start_curve_list.style.maxWidth = "5vw";
    input_start_curve_list.style.width = "5vw";
    input_start_curve_list.style.minWidth = "50px";
    input_start_curve_list.style.display = "none";
    div_row.appendChild(input_start_curve_list);
    //
    var span_end_add_to_curve_list = document.createElement("span");
    span_end_add_to_curve_list.classList.add("center_v", "m_l_5p");
    span_end_add_to_curve_list.innerText = "fin";
    span_end_add_to_curve_list.style.display = "none";
    div_row.appendChild(span_end_add_to_curve_list);
    //
    var input_end_curve_list = document.createElement("input");
    input_end_curve_list.setAttribute("id", get_hp_manual_tests_add_to_curve_interval_max_id(keys));
    input_end_curve_list.classList.add("center_v", "m_l_5p");
    input_end_curve_list.type = "number";
    input_end_curve_list.style.maxWidth = "5vw";
    input_end_curve_list.style.width = "5vw";
    input_end_curve_list.style.minWidth = "50px";
    input_end_curve_list.style.display = "none";
    div_row.appendChild(input_end_curve_list);
    //
    var span_nb_pts_inter_add_to_curve_list = document.createElement("span");
    span_nb_pts_inter_add_to_curve_list.classList.add("center_v", "m_l_5p");
    span_nb_pts_inter_add_to_curve_list.innerText = "nb pts intermédiaires";
    span_nb_pts_inter_add_to_curve_list.style.display = "none";
    div_row.appendChild(span_nb_pts_inter_add_to_curve_list);
    //
    var input_nb_pts_inter_curve_list = document.createElement("input");
    input_nb_pts_inter_curve_list.setAttribute("id", get_hp_manual_tests_add_to_curve_interval_nb_pts_id(keys));
    input_nb_pts_inter_curve_list.classList.add("center_v", "m_l_5p");
    input_nb_pts_inter_curve_list.type = "number";
    input_nb_pts_inter_curve_list.style.maxWidth = "5vw";
    input_nb_pts_inter_curve_list.style.width = "5vw";
    input_nb_pts_inter_curve_list.style.minWidth = "50px";
    input_nb_pts_inter_curve_list.style.display = "none";
    div_row.appendChild(input_nb_pts_inter_curve_list);
    //
    document.getElementById("edit_config_params").appendChild(div_row);
    //
    bt_add_to_curve_list.onclick = function(event) {
        //
        if(selected_keys_to_curve_list.length >= max_nb_keys_to_curve_list){
            alert("Il ne peut pas y avoir plus de " + max_nb_keys_to_curve_list + " hyper-paramètres sélectionnés le traçage de courbe.")
            return;
        }
        //
        selected_keys_to_curve_list.push(keys);
        //
        bt_add_to_curve_list.style.display = "none";
        span_add_to_curve_list.style.display = "none";
        bt_del_to_curve_list.style.display = "flex";
        span_start_curve_list.style.display = "flex";
        input_start_curve_list.style.display = "flex";
        span_end_add_to_curve_list.style.display = "flex";
        input_end_curve_list.style.display = "flex";
        span_nb_pts_inter_add_to_curve_list.style.display = "flex";
        input_nb_pts_inter_curve_list.style.display = "flex";
    }
    //
    bt_del_to_curve_list.onclick = function(event) {
        //
        var idx = selected_keys_to_curve_list.indexOf(keys);
        if(idx != -1){
            selected_keys_to_curve_list.splice(idx, 1);
        }
        //
        bt_add_to_curve_list.style.display = "flex";
        span_add_to_curve_list.style.display = "flex";
        bt_del_to_curve_list.style.display = "none";
        span_start_curve_list.style.display = "none";
        input_start_curve_list.style.display = "none";
        span_end_add_to_curve_list.style.display = "none";
        input_end_curve_list.style.display = "none";
        span_nb_pts_inter_add_to_curve_list.style.display = "none";
        input_nb_pts_inter_curve_list.style.display = "none";
    }
    //
}

//
function aux_get_type_from_config_keys(config, keys_left){
    if(keys_left.length == 0){
        return config;
    }
    else if(keys_left.length == 1){
        return config[keys_left[0]];
    }
    if(!Object.keys(config).includes(keys_left[0])){
        return null;
    }
    //
    if(Array.isArray(config[keys_left[0]])){
        if(config[keys_left[0]].length != 5){
            return null;
        }
        if(config[keys_left[0]][0] == "number" || config[keys_left[0]][0] == "string"){
            return null;
        }
        if(config[keys_left[0]][0].startsWith("list|")){
            if(keys_left.length <= 1){
                return null;
            }
            if(!Array.isArray(keys_left[1]) || keys_left[1].length != 2){
                return null;
            }
            //
            return aux_get_type_from_config_keys(types[keys_left[1][1]], keys_left.slice(2));
        }
        else{
            return aux_get_type_from_config_keys(types[config[keys_left[0]][0]], keys_left.slice(1));
        }
    }
    else{
        return aux_get_type_from_config_keys(config[keys_left[0]], keys_left.slice(1));
    }
}

//
function get_type_from_config_keys(base_type, keys){
    //
    if(!Object.keys(types).includes(base_type)){
        console.error("Error, no type : ", base_config_type);
        return null;
    }

    //
    return aux_get_type_from_config_keys(types[base_type], keys);
}

//
function aux_get_value_from_config_keys(config, keys_left){
    if(keys_left.length == 0){
        return config;
    }
    else if(keys_left.length == 1){
        return config[keys_left[0]];
    }
    //
    if(Array.isArray(keys_left[0])){
        return aux_get_value_from_config_keys(config[keys_left[0][0]], keys_left.slice(1));
    }
    else{
        if(!Object.keys(config).includes(keys_left[0])){
            return null;
        }
        return aux_get_value_from_config_keys(config[keys_left[0]], keys_left.slice(1));
    }
}

//
function get_value_from_config_keys(engine_config_name, keys){
    //
    return aux_get_value_from_config_keys(data_tasks[current_task]["configs"][engine_config_name], keys);
}

//
function aux_set_value_from_config_keys(config, value, keys_left){
    if(keys_left.length == 0){
        config = value;
    }
    else if(keys_left.length == 1){
        config[keys_left[0]] = value;
    }
    //
    if(Array.isArray(keys_left[0])){
        aux_set_value_from_config_keys(config[keys_left[0][0]], value, keys_left.slice(1));
    }
    else{
        if(!Object.keys(config).includes(keys_left[0])){
            return;
        }
        aux_set_value_from_config_keys(config[keys_left[0]], value, keys_left.slice(1));
    }
}

//
function set_value_from_config_keys(engine_config_name, keys, value){
    //
    return aux_set_value_from_config_keys(data_tasks[current_task]["configs"][engine_config_name], value, keys);
}

//
function add_number_input_row(keys, value, parent_div=null){
    //
    const key = keys.slice(-1);
    //
    const id_input_key = keysJoin(keysEscapeHtml(keys));
    //
    var div_row = document.createElement("div");
    div_row.classList.add("row");
    div_row.style.margin = "5px";
    div_row.style.marginLeft = "30px";
    //
    var label = document.createElement("label");
    label.classList.add("center_v");
    label.innerText = key + " : ";
    div_row.appendChild(label);
    //
    var input = document.createElement("input");
    input.setAttribute("id", id_input_key);
    input.classList.add("center_v");
    input.style.marginLeft = "5px";
    input.style.width = "3vw";
    input.style.minWidth = "50px";
    input.value = parseFloat(value);
    input.type = "number";
    div_row.appendChild(input);
    //
    input.onchange = function(event){
        // TODO
    }
    //
    if(parent_div == null){
        document.getElementById("create_edit_config_elements").appendChild(div_row);
    }
    else{
        parent_div.appendChild(div_row);
    }
}

//
function add_text_input_row(keys, value, parent_div=null){
    //
    const key = keys.slice(-1);
    //
    const id_input_key = keysJoin(keysEscapeHtml(keys));
    //
    var div_row = document.createElement("div");
    div_row.classList.add("row");
    div_row.style.margin = "5px";
    div_row.style.marginLeft = "30px";
    //
    var label = document.createElement("label");
    label.classList.add("center_v");
    label.innerText = key + " : ";
    div_row.appendChild(label);
    //
    var input = document.createElement("input");
    input.setAttribute("id", id_input_key);
    input.classList.add("center_v");
    input.style.marginLeft = "5px";
    input.style.width = "20vw";
    input.style.minWidth = "150px";
    input.value = value;
    input.type = "text";
    div_row.appendChild(input);
    //
    input.onchange = function(event){
        // TODO
    }
    //
    if(parent_div == null){
        document.getElementById("create_edit_config_elements").appendChild(div_row);
    }
    else{
        parent_div.appendChild(div_row);
    }
}

//
function add_option_input_row(keys, value, constraint_values, default_value, parent_div=null){
    //
    const key = keys.slice(-1);
    //
    const id_input_key = keysJoin(keysEscapeHtml(keys));
    //
    var div_row = document.createElement("div");
    div_row.classList.add("row");
    div_row.style.margin = "5px";
    div_row.style.marginLeft = "30px";
    //
    var label = document.createElement("label");
    label.classList.add("center_v");
    label.innerText = key + " : ";
    div_row.appendChild(label);
    //
    var input = document.createElement("select");
    input.setAttribute("id", id_input_key);
    input.classList.add("center_v");
    input.style.marginLeft = "5px";
    input.style.width = "15vw";
    input.style.minWidth = "100px";
    div_row.appendChild(input);
    //
    input.onchange = function(event){
        // TODO
    }
    //
    for(option_value of constraint_values){
        var option = document.createElement("option");
        option.innerText = option_value;
        option.value = option_value;
        input.appendChild(option);
    }
    //
    if(!constraint_values.includes(value)){
        if(default_value != null && constraint_values.includes(default_value)){
            input.value = default_value;
        }
    }
    else{
        input.value = value;
    }
    //
    if(parent_div == null){
        document.getElementById("create_edit_config_elements").appendChild(div_row);
    }
    else{
        parent_div.appendChild(div_row);
    }
}

//
function my_custom_typeof(value){
    var t = typeof(value);
    if(t == "object"){
        if (Array.isArray(value)) {
            return 'array';
        } else if (value !== null) {
            return 'dictionary';
        } else {
            return 'neither';
        }
    }
    //
    return t;
}

//
function get_sub_divs_id(keys){
    return "sub_divs_" + keysJoin(keysEscapeHtml(keys), "___");
}

//
function get_add_input_id(keys){
    return "add_input_" + keysJoin(keysEscapeHtml(keys), "___");
}

//
function get_sub_block_div_id(keys){
    return "sub_block_div_" + keysJoin(keysEscapeHtml(keys), "___");
}

//
function display_configuration_dict_params(base_config_type, config_params, previous_keys=[], parent_div=null){

    //
    if(!Object.keys(types).includes(base_config_type)){
        console.error("Error, no type : ", base_config_type);
        return;
    }

    var value_type_key = "";
    // On parcours toutes les clés de ce type de configuration
    for(value_type_key of Object.keys(types[base_config_type])){

        //
        var new_keys = previous_keys.slice(0);
        new_keys.push(value_type_key);

        // Si la clé n'est pas dans la configuration
        if(!Object.keys(config_params).includes(value_type_key)){
            // Si c'est une valeur importante
            if(types[base_config_type][value_type_key][4] == 1){
                alert("Error in the configuration, the key '"+value_type_key+"' is not in the config, you should delete it, and create a correct new one!");
                go_to_page("select_config_page");
                return;
            }
            // Sinon, on l'ignore
            continue;
        }

        // Si on arrive ici, c'est que la clé est bien dans la configuration
        const key_type = types[base_config_type][value_type_key][0];
        if(types[base_config_type][value_type_key][2] != null && my_custom_typeof(types[base_config_type][value_type_key][2]) == "array"){
            add_option_input_row(new_keys, config_params[value_type_key], types[base_config_type][value_type_key][2], types[base_config_type][value_type_key][3], parent_div);
        }
        else if(key_type == "string"){
            add_text_input_row(new_keys, config_params[value_type_key], parent_div);
        }
        else if(key_type == "number"){
            add_number_input_row(new_keys, config_params[value_type_key], parent_div);
        }
        else if(Object.keys(types).includes(key_type) || key_type.startsWith("list|")){
            //
            var block_div = document.createElement("div");
            block_div.classList.add("col");
            block_div.style.margin = "5px";
            block_div.style.marginLeft = "30px";
            //
            var span = document.createElement("b");
            span.innerText = value_type_key + " : ";
            block_div.appendChild(span);
            //
            var sub_divs_id = get_sub_divs_id(new_keys);
            //
            var sub_divs = document.createElement("div");
            sub_divs.setAttribute("id", sub_divs_id);
            sub_divs.style.margin = "5px";
            sub_divs.classList.add("col");
            //
            if(parent_div == null){
                document.getElementById("create_edit_config_elements").appendChild(block_div);
            }
            else{
                parent_div.appendChild(block_div);
            }
            //
            if(key_type.startsWith("list|")){
                //
                const real_key_type = key_type.slice(5);
                //
                if(Object.keys(general_classes).includes(real_key_type)){
                    //
                    var add_div_row = document.createElement("div");
                    add_div_row.classList.add("row");
                    add_div_row.style.margin = "5px";
                    add_div_row.style.marginLeft = "30px";
                    //
                    var add_label = document.createElement("label");
                    add_label.classList.add("center_v");
                    add_label.innerText = "Ajouter un élément : ";
                    add_div_row.appendChild(add_label);
                    //
                    var add_input_id = get_add_input_id(new_keys);
                    //
                    var add_input = document.createElement("select");
                    add_input.setAttribute("id", add_input_id);
                    add_input.classList.add("center_v");
                    add_input.style.marginLeft = "5px";
                    add_input.style.width = "35vw";
                    add_input.style.minWidth = "200px";
                    add_div_row.appendChild(add_input);
                    //
                    for(option_value of Object.keys(general_classes[real_key_type])){
                        var add_option = document.createElement("option");
                        add_option.innerText = option_value;
                        add_option.value = option_value;
                        add_input.appendChild(add_option);
                    }
                    //
                    var add_button = document.createElement("button");
                    add_button.classList.add("center_v");
                    add_button.style.border = "1px solid black";
                    add_button.style.padding = "2px";
                    add_button.innerText = "ajouter";
                    add_button.setAttribute("onclick", "on_button_add_click("+JSON.stringify(new_keys)+", \""+sub_divs_id+"\", \""+add_input_id+"\");");
                    //
                    add_div_row.appendChild(add_button);
                    //
                    block_div.appendChild(add_div_row);
                    //
                }
                //
                var i = 0;
                for(sub_config_params of config_params[value_type_key]){
                    //
                    var sub_config_new_keys = new_keys.slice(0);
                    sub_config_new_keys.push(i);
                    //
                    var sub_block_div_id = get_sub_block_div_id(sub_config_new_keys);
                    //
                    var sub_block_div = document.createElement("div");
                    sub_block_div.setAttribute("id", sub_block_div_id);
                    sub_block_div.classList.add("col");
                    sub_block_div.style.margin = "5px";
                    sub_block_div.style.marginLeft = "30px";
                    //
                    var sub_block_first_row = document.createElement("div");
                    sub_block_first_row.classList.add("row");
                    sub_block_div.appendChild(sub_block_first_row);
                    //
                    var sub_span = document.createElement("b");
                    sub_span.innerText = "" + i + " : ";
                    sub_block_first_row.appendChild(sub_span);
                    //
                    var sub_bt_remove = document.createElement("button");
                    sub_bt_remove.classList.add("center_v");
                    sub_bt_remove.style.border = "1px solid black";
                    sub_bt_remove.style.padding = "2px";
                    sub_bt_remove.style.maxWidth = "100px";
                    sub_bt_remove.style.textAlign = "center";
                    sub_bt_remove.innerText = "enlever";
                    sub_block_first_row.appendChild(sub_bt_remove);
                    //
                    sub_bt_remove.setAttribute("onclick", "on_button_remove_click(" + JSON.stringify(sub_config_new_keys) + ",  \"" + value_type_key + "\", " + i + ", \"" + sub_block_div_id + "\");");
                    //
                    var sub_sub_divs = document.createElement("div");
                    sub_sub_divs.style.margin = "5px";
                    sub_sub_divs.classList.add("col");
                    sub_block_div.appendChild(sub_sub_divs);
                    //
                    sub_divs.appendChild(sub_block_div);
                    //
                    if(Object.keys(general_classes).includes(real_key_type)){
                        display_configuration_dict_params(sub_config_params["type"], sub_config_params, sub_config_new_keys, sub_sub_divs);
                    }
                    else{
                        display_configuration_dict_params(real_key_type, sub_config_params, sub_config_new_keys, sub_sub_divs);
                    }
                    i++;
                }
            }
            else{
                display_configuration_dict_params(key_type, config_params[value_type_key], new_keys, sub_divs);
            }
            //
            block_div.appendChild(sub_divs);
            //
        }
        else{
            console.error("Unkown key type : '"+key_type+"' !");
        }
    }
}

//
function on_button_add_click(keys, sub_divs_id, add_input_id) {
    //
    const algo_type = document.getElementById(add_input_id).value;
    var new_algo_config = init_empty_default_configuration(algo_type, types[algo_type]);
    //
    var number_of_already_here_items = getValueFromConfig(current_create_or_edit_config, keys).length
    //
    const new_i = number_of_already_here_items;
    keys.push(new_i);
    //
    setValueToConfig(current_create_or_edit_config, new_algo_config, keys);
    //
    var sub_block_div_id = get_sub_block_div_id(keys);
    //
    var sub_block_div = document.createElement("div");
    sub_block_div.setAttribute("id", sub_block_div_id);
    sub_block_div.classList.add("col");
    sub_block_div.style.margin = "5px";
    sub_block_div.style.marginLeft = "30px";
    //
    var sub_block_first_row = document.createElement("div");
    sub_block_first_row.classList.add("row");
    sub_block_div.appendChild(sub_block_first_row);
    //
    var sub_span = document.createElement("b");
    sub_span.innerText = "" + new_i + " : ";
    sub_block_first_row.appendChild(sub_span);
    //
    var sub_bt_remove = document.createElement("button");
    sub_bt_remove.classList.add("center_v");
    sub_bt_remove.style.border = "1px solid black";
    sub_bt_remove.style.padding = "2px";
    sub_bt_remove.style.maxWidth = "100px";
    sub_bt_remove.style.textAlign = "center";
    sub_bt_remove.innerText = "enlever";
    sub_block_first_row.appendChild(sub_bt_remove);
    //
    sub_bt_remove.setAttribute("onclick", "on_button_remove_click(" + JSON.stringify(keys) + ",  \"" + value_type_key + "\", " + new_i + ", \"" + sub_block_div_id + "\");");
    //
    var sub_sub_divs = document.createElement("div");
    sub_sub_divs.style.margin = "5px";
    sub_sub_divs.classList.add("col");
    sub_block_div.appendChild(sub_sub_divs);
    //
    document.getElementById(sub_divs_id).appendChild(sub_block_div);
    //
    display_configuration_dict_params(algo_type, new_algo_config, keys, sub_sub_divs);
    //
}

//
function on_button_remove_click(keys, value_type_key_, i_, sub_block_div_id) {
    setValueToConfig(current_create_or_edit_config, null, keys);
    document.getElementById(sub_block_div_id).remove();
}

//
function get_optimisable_hyper_parameters_from_configuration_dict(base_config_type, config_params, previous_keys=[]){

    //
    if(!Object.keys(types).includes(base_config_type)){
        console.error("Error, no type : ", base_config_type);
        return;
    }

    // On parcours toutes les clés de ce type de configuration
    for(value_type_key of Object.keys(types[base_config_type])){

        //
        var new_keys = previous_keys.slice(0);
        new_keys.push(value_type_key);

        // Si la clé n'est pas dans la configuration
        if(!Object.keys(config_params).includes(value_type_key)){
            // Si c'est une valeur importante
            if(types[base_config_type][value_type_key][4] == 1){
                return;
            }
            // Sinon, on l'ignore
            continue;
        }

        // Si on arrive ici, c'est que la clé est bien dans la configuration
        const key_type = types[base_config_type][value_type_key][0];
        if(key_type == "number" && types[base_config_type][value_type_key][1]){
            current_optimisable_hyper_parameters_keys.push(new_keys);
        }
        else if(Object.keys(types).includes(key_type) || key_type.startsWith("list|")){
            //
            if(key_type.startsWith("list|")){
                //
                const real_key_type = key_type.slice(5);
                //
                var i = 0;
                for(sub_config_params of config_params[value_type_key]){
                    //
                    var sub_config_new_keys = new_keys.slice(0);
                    //
                    if(Object.keys(general_classes).includes(real_key_type)){
                        sub_config_new_keys.push([i, sub_config_params["type"]]);
                        get_optimisable_hyper_parameters_from_configuration_dict(sub_config_params["type"], sub_config_params, sub_config_new_keys);
                    }
                    else{
                        sub_config_new_keys.push([i, real_key_type]);
                        get_optimisable_hyper_parameters_from_configuration_dict(real_key_type, sub_config_params, sub_config_new_keys);
                    }
                    i++;
                }
            }
            else{
                get_optimisable_hyper_parameters_from_configuration_dict(key_type, config_params[value_type_key], new_keys);
            }
        }
    }
}

//
function test_if_config_name_already_exists(name){
    return name in data_tasks[current_task]["configs"];
}

//
function config_edit_or_create_new(config_name){
    //
    if(config_name != "" && (!(config_name in data_tasks[current_task]["configs"]))){
        return;
    }
    //
    if(config_name == ""){
        //
        create_edit_mode = "create";
        edit_config_config_name = "";
        //
        var new_config_name = "New config";
        var i = 1;
        while(test_if_config_name_already_exists(new_config_name + " " + i)){
            i += 1;
        }
        //
        if(current_task == "NER"){
            current_create_or_edit_config = init_empty_default_configuration("NER_Engine", types["NER_Engine"]);
        }
        else if(current_task == "conversation_cut"){
            current_create_or_edit_config = init_empty_default_configuration("ConversationEngine", types["ConversationEngine"]);
        }
        else if(current_task == "search"){
            current_create_or_edit_config = init_empty_default_configuration("SearchEngine", types["SearchEngine"]);
        }
        else{
            return;
        }
    }
    else{
        //
        create_edit_mode = "edit";
        edit_config_config_name = config_name;
        current_create_or_edit_config = data_tasks[current_task]["configs"][config_name];
    }
    // Nettoyage
    document.getElementById("create_edit_config_elements").innerHTML = "";
    //
    display_configuration_dict_params(tasks_to_base_config[current_task], current_create_or_edit_config);

    // On va à la page
    go_to_page("create_edit_config_page");
}

//
function filter_null_values_of_arrays_from_config_dict(config_dict){
    // Cas d'arrêt de la fonction récursive
    if(typeof(config_dict) != "object"){
        return config_dict;
    }
    // Ce cas ne devrait pas arriver, mais je met ce cas là aussi comme ca, au cas où d'une utilisation autre que mon projet initial
    if(Array.isArray(config_dict)){
        // Initialisation de la liste que l'on va trier
        var final_config_arr = [];
        // On trie chaque élément de la liste
        for(elt of config_dict){
            if(elt != null){
                final_config_arr.push( filter_null_values_of_arrays_from_config_dict(elt) )
            }
        }
        // On renvoie la liste finale
        return final_config_arr;
    }
    // Sinon, on a notre dictionnaire
    var final_config_dict = {};
    // On parcours chaque entrée du dictionnaire
    var config_key = "";
    for(config_key of Object.keys(config_dict)){
        if(Array.isArray(config_dict[config_key])){
            //
            const config_key_ = config_key;
            //
            var arr = config_dict[config_key_];
            // Initialisation de la liste que l'on va trier
            final_config_dict[config_key_] = [];
            // On trie chaque élément de la liste
            var j = 0;
            for(j=0; j < arr.length; j++){
                var elt = arr[j];
                if(elt != null){
                    final_config_dict[config_key_].push( filter_null_values_of_arrays_from_config_dict(elt) );
                }
            }
        }
        else{
            // Sinon, on trie la valeur de la clé
            final_config_dict[config_key] = filter_null_values_of_arrays_from_config_dict(config_dict[config_key]);
        }
    }
    // On renvoie le dictionnaire final
    return final_config_dict;
}

//
function rec_get_all_config_parameters_from_edit_page(base_config_obj, previous_keys=[]){
    //
    if(typeof(base_config_obj) != "object" || base_config_obj == null){
        return null;
    }
    //
    if(Array.isArray(base_config_obj)){
        //
        var new_base_config_arr = [];
        //
        for(var i = 0; i < base_config_obj.length; i++){
            //
            var new_previous_keys = previous_keys.slice(0);
            new_previous_keys.push(i);
            //
            if(typeof(base_config_obj[i]) != "object" || base_config_obj[i] == null){
                //
                const id_input_key = keysJoin(keysEscapeHtml(new_previous_keys));
                //
                var node_input = document.getElementById(id_input_key);
                if(node_input == undefined){
                    continue;
                }
                //
                new_base_config_arr.push(node_input.value);
            }
            //
            else{
                new_base_config_arr.push( rec_get_all_config_parameters_from_edit_page(base_config_obj[i], new_previous_keys) );
            }
        }
        //
        return new_base_config_arr;
        //
    }
    //
    else{
        //
        var new_config_dict = {};
        for(key in base_config_obj){
            //
            var new_previous_keys = previous_keys.slice(0);
            new_previous_keys.push(key);
            //
            if(typeof(base_config_obj[key]) != "object" || base_config_obj[key] == null){
                //
                const id_input_key = keysJoin(keysEscapeHtml(new_previous_keys));
                //
                var node_input = document.getElementById(id_input_key);
                if(node_input == undefined){
                    continue;
                }
                //
                const new_value = node_input.value;
                //
                new_config_dict[key] = new_value;
            }
            //
            else{
                //
                new_config_dict[key] = rec_get_all_config_parameters_from_edit_page(base_config_obj[key], new_previous_keys);
            }
        }
        //
        return new_config_dict;
        //
    }
}

//
function get_all_config_parameters_from_edit_page(){
    return rec_get_all_config_parameters_from_edit_page(current_create_or_edit_config);
}

//
function save_edited_or_created_config_to_server(){
    //
    var final_config = filter_null_values_of_arrays_from_config_dict(get_all_config_parameters_from_edit_page());
    //
    if(!test_config_correct(final_config, tasks_to_base_config[current_task], types[tasks_to_base_config[current_task]])){
        alert("Erreur: La configuration n'est pas correcte !");
        return;
    }
    //
    if(create_edit_mode == "create"){
        // Test de s'il y a déjà une config avec le même nom ou pas
        if( Object.keys(data_tasks[current_task]["configs"]).includes(final_config["config_name"]) ){
            alert("Erreur: Une config avec le même nom existe déjà !");
            return;
        }
        //
        ws_send_msg(window.ws, {
            "type": "hpo_create_new_config_file",
            "task": current_task,
            "engine_config_name": final_config["config_name"],
            "config": final_config
        });
        //
        update_current_task_page();
    }
    //
    else if(create_edit_mode == "edit"){
        // On envoie la requête
        ws_send_msg(window.ws, {
            "type": "hpo_save_edited_config_file",
            "task": current_task,
            "engine_config_name": current_create_or_edit_config["config_name"],
            "config": final_config
        });
        //
        update_current_task_page();
    }
}

//
function on_duplicate_button_click(config_name){
    //
    if(!Object.keys(data_tasks[current_task]["configs"]).includes(config_name)){
        return;
    }
    //
    var new_config = filter_null_values_of_arrays_from_config_dict(data_tasks[current_task]["configs"][config_name]);
    //
    var i = 2;
    //
    while(Object.keys(data_tasks[current_task]["configs"]).includes(config_name + "_" + i)){
        i += 1;
    }
    //
    var new_name = config_name + "_" + i;
    //
    new_config["config_name"] = new_name;
    //
    ws_send_msg(window.ws, {
        "type": "hpo_create_new_config_file",
        "task": current_task,
        "engine_config_name": new_name,
        "config": new_config
    });
    //
    update_current_task_page();
}

//
function on_delete_button_click(config_name){
    current_drop_down_button_displayed = null;
    if(confirm("Êtes vous vraiment sûr de vouloir supprimer la configuration : \""+config_name+"\"")){
        send_config_deletion_to_server(config_name);
    }
}

//
function send_config_deletion_to_server(config_name){
    // On envoie la requête
    ws_send_msg(window.ws, {
        "type": "hpo_delete_config_file",
        "task": current_task,
        "engine_config_name": config_name
    });

    // Si c'est cette config qui est sélectionnée, on la déselectionne
    if(current_engine_config == config_name){
        current_engine_config = "";
        current_engine_config_button = null;
    }

    // On nettoie le div button
    var div_bt = document.getElementById("config_div_button_"+config_name);
    if(div_bt){
        div_bt.remove();
    }
}

//
function update_current_task_page(){
    //
    const current_task_ = current_task;
    current_task = "";
    //
    delete data_tasks[current_task_];
    //
    go_to_page("select_task_page");
    //
    task_selected(current_task_);
}

//
function test_hyper_parameter_correct(value, type_details){
    /*
    Rappel de la structure d'un type :

    (
        0 = type de la valeur;
        1 = booléen indiquant si c'est une valeur à optimiser;
        2 = contraintes sur les valeurs prises
            * Si c'est une liste, la valeur doit être dans cette liste
            * Si c'est un dictionnaire avec la forme {"type": "interval", "min": a, "max": b}, la valeur doit être entre ces deux valeurs
            * Sinon, c'est un None / null, et pas de contraintes particulières. On s'en fout, le paramètre peut prendre n'importe quelle valeur (sauf exception bien sûr, par exemple, pour les types qui sont dans la liste type, et surtout les listes)
        3 = valeur par défaut,
        4 = si c'est une clé nécessaire dans une config ou non. Si elle vaut 0, cela veut dire qu'on s'en fout si le paramètre n'est pas dans la config.
    )

    */

    // On vérifie quand même que le type est correct.
    if(type_details == null || type_details.length != 5){
        console.error("Error: Incorrect type : ", type_details);
        return false;
    }

    if(Array.isArray(type_details[2])){
        // Contraintes de valeurs, on renvoie faux si la valeur n'est pas dans la liste
        if(!type_details[2].includes(value)){
            return false;
        }
    }
    else if(typeof(type_details[2]) == "object" && type_details[2] != null){
        //
        if(type_details[2]["type"] == "interval"){
            // Intervalle, on renvoie faux si la valeur est hors de l'intervalle.
            if(value < type_details[2]["min"] || value > type_details[2]["max"]){
                return false;
            }
        }
    }

    // Si on arrive jusque là, c'est que tout est bon, pas de problèmes détectés
    return true;
}

//
function test_config_correct(config_dict_or_value, config_base_type_name, config_type_dict_or_type_details){

    // Si problèmes de type de base
    if( !Object.keys(types).includes(config_base_type_name)){
        //  && !( Object.keys(general_classes).includes(config_base_type_name) && general_classes[config_base_type_name].includes(config_dict["type"]) )
        return false;
    }

    //
    if(Array.isArray(config_type_dict_or_type_details) && (!config_type_dict_or_type_details[0].startsWith("list|") || Object.keys(types).includes(config_type_dict_or_type_details[0]))){
        return test_hyper_parameter_correct(config_dict_or_value, config_type_dict_or_type_details);
    }

    var value_type_key = "";
    // On parcours toutes les clés de ce type de configuration
    for(value_type_key of Object.keys(config_type_dict_or_type_details)){

        //
        const value_type_key_ = value_type_key;

        // Si la clé n'est pas dans la configuration
        if(!Object.keys(config_dict_or_value).includes(value_type_key_)){
            // Si c'est une valeur importante
            if(types[config_base_type_name][value_type_key_][4] == 1){
                return false;
            }
            // Sinon, on l'ignore
            continue;
        }

        // Si on arrive ici, c'est que la clé est bien dans la configuration
        const key_type = types[config_base_type_name][value_type_key_][0];
        //
        if(Object.keys(types).includes(key_type) || key_type.startsWith("list|")){
            //
            if(key_type.startsWith("list|")){
                //
                const real_key_type = key_type.slice(5);
                //
                var i = 0;
                for(sub_config_params of config_dict_or_value[value_type_key_]){
                    //
                    if(Object.keys(general_classes).includes(real_key_type)){
                        //
                        var res_bon = test_config_correct(config_dict_or_value[value_type_key_][i], sub_config_params["type"], types[sub_config_params["type"]]);
                        if(!res_bon){
                            return false;
                        }
                    }
                    else{
                        //
                        var res_bon = test_config_correct(config_dict_or_value[value_type_key_][i], real_key_type, types[real_key_type]);
                        if(!res_bon){
                            return false;
                        }
                    }
                    i++;
                }
            }
            else{
                var res_bon = test_config_correct(config_dict_or_value[value_type_key_], key_type, config_type_dict_or_type_details[value_type_key_]);
                if(!res_bon){
                    return false;
                }
            }
        }
    }
    return true;
}

//
function init_empty_default_configuration(config_base_type_name, config_type_dict_or_type_details){

    // Si problèmes de type de base
    if( config_type_dict_or_type_details == null ){
        //  && !( Object.keys(general_classes).includes(config_base_type_name) && general_classes[config_base_type_name].includes(config_dict["type"]) )
        return null;
    }

    //
    if(Array.isArray(config_type_dict_or_type_details) && (!config_type_dict_or_type_details[0].startsWith("list|") || Object.keys(types).includes(config_type_dict_or_type_details[0]))){

        // Si valeur par défaut
        if(config_type_dict_or_type_details[3] != null){
            if(config_type_dict_or_type_details[0] == "number"){
                return parseFloat(config_type_dict_or_type_details[3]);
            }
            return config_type_dict_or_type_details[3];
        }

        // Sinon si,
        if(Object.keys(types).includes(config_type_dict_or_type_details[0])){
            return init_empty_default_configuration(config_type_dict_or_type_details[0], types[config_type_dict_or_type_details[0]])
        }

        // Sinon si il y a une contrainte sur les valeurs
        if(config_type_dict_or_type_details[2] != null){
            if(Array.isArray(config_type_dict_or_type_details[2])){
                if(config_type_dict_or_type_details[2].length == 0){
                    return null;
                }
                else if(config_type_dict_or_type_details[2].includes("")){
                    return "";
                }
                else if(config_type_dict_or_type_details[2].includes(0)){
                    return 0;
                }
                else{
                    return config_type_dict_or_type_details[2][0];
                }
            }
        }

        // Sinon, on renvoie une valeur neutre en fonction du type
        if(config_type_dict_or_type_details[0] == "number"){
            return 0;
        }
        else if(config_type_dict_or_type_details[0] == "string"){
            return "";
        }
        else{
            return null;
        }
    }

    // Si on arrive jusque là,
    var new_params = {};

    // On parcours toutes les clés de ce type de configuration
    for(value_type_key of Object.keys(config_type_dict_or_type_details)){

        //
        const key_type = types[config_base_type_name][value_type_key][0];
        if(key_type.startsWith("list|")){
            //
            new_params[value_type_key] = [];
        }
        else if(value_type_key == "type"){
            //
            new_params[value_type_key] = config_base_type_name;
        }
        else{
            //
            new_params[value_type_key] = init_empty_default_configuration(key_type, config_type_dict_or_type_details[value_type_key]);
        }
    }
    return new_params;
}

//
function on_test_button_clicked_manual_tests_page(){

    // On va dupliquer le fichier de configuration du moteur de recherche de la configuration sélectionnée
    var test_config = filter_null_values_of_arrays_from_config_dict(data_tasks[current_task]["configs"][current_engine_config]);

    // Et on va modifier les valeurs des hyper-paramètres optimisables depuis la page des tests manuels
    for(keys of current_optimisable_hyper_parameters_keys){
        var id_input_key = get_hp_value_manual_tests_id(keys);
        //
        var value = document.getElementById(id_input_key).value;
        //
        if(value == null || value == ""){
            alert("Erreur, valeur non valide de l'hyper paramètre " + keys.join("/") + " !");
            return;
        }
        //
        setValueToConfig(test_config, parseFloat(value), keys);
    }

    //
    awaiting_test_benchmark_request_task = current_task;
    awaiting_test_benchmark_request_config = test_config;
    awaiting_test_benchmark_result_type = "single_test";
    document.getElementById("bt_send_test_request_manual_tests").disabled = true;
    document.getElementById("bt_send_draw_curve_request_manual_tests").disabled = true;

    // On va envoyer la requête
    ws_send_msg(window.ws, {
        "type": "hpo_test_config_all_benchmarks",
        "task": current_task,
        "config_dict": test_config,
        "test_benchmark_type": "single_test"
    });
}

//
function on_hpo_single_test_benchmark_results(task, config, benchmark_results, test_benchmark_type){

    // On vérifie qu'on obtient bien le résultat que l'on attendait
    if(task != current_task || awaiting_test_benchmark_request_task != task || JSON.stringify(awaiting_test_benchmark_request_config) != JSON.stringify(config)){
        return;
    }

    //
    awaiting_test_benchmark_request_config = null;
    awaiting_test_benchmark_request_task = null;
    document.getElementById("bt_send_test_request_manual_tests").disabled = false;
    document.getElementById("bt_send_draw_curve_request_manual_tests").disabled = false;

    //
    var sum = 0.0;

    //
    for(benchmark_name of Object.keys(benchmark_results)){
        if(!isNaN(parseFloat(benchmark_results[benchmark_name]))){
            sum += benchmark_results[benchmark_name];
            document.getElementById("benchmark_score_" + escapeHtml(benchmark_name)).innerText = parseFloat(parseFloat(benchmark_results[benchmark_name]).toFixed(4));
            //
            if(benchmark_results[benchmark_name] >= 0.9){
                document.getElementById("benchmark_score_" + escapeHtml(benchmark_name)).classList.add("very_good_value");
            }
            else if(benchmark_results[benchmark_name] >= 0.8){
                document.getElementById("benchmark_score_" + escapeHtml(benchmark_name)).classList.add("good_value");
            }
            else if(benchmark_results[benchmark_name] >= 0.6){
                document.getElementById("benchmark_score_" + escapeHtml(benchmark_name)).classList.add("acceptable_value");
            }
            else if(benchmark_results[benchmark_name] >= 0.4){
                document.getElementById("benchmark_score_" + escapeHtml(benchmark_name)).classList.add("bad_value");
            }
            else{
                document.getElementById("benchmark_score_" + escapeHtml(benchmark_name)).classList.add("very_bad_value");
            }
        }
    }
}

//
function get_curve_param_pts_id_dict_key(param_pts_ids){
    return Array(Object.values(param_pts_ids)).join("_");
}

//
function curve_display_graph(){
    //
    var still_awaiting_points = false;

    // Graphe en 2d
    if(awaiting_test_benchmark_result_input_dim == 1){

        // On prépare les points à afficher
        var graph_pts = [{}];
        var animated_pts = {};
        var value_min = null;
        var value_max = null;
        var max_value_input = "/";
        var input_min = null;
        var input_max = null;
        //
        for(pt of Object.keys(awaiting_test_benchmark_curve_results).keys()){
            //
            if(input_min == null || pt < input_min){
                input_min = pt;
            }
            if(input_max == null || pt > input_max){
                input_max = pt;
            }
            //
            if(awaiting_test_benchmark_curve_results[pt] != null){
                //
                var pt_input_value = awaiting_test_benchmark_curve_results[pt]["input_values"][0];
                //
                if(value_min == null || awaiting_test_benchmark_curve_results[pt][current_curve_benchmark_display] < value_min){
                    value_min = awaiting_test_benchmark_curve_results[pt][current_curve_benchmark_display];
                }
                if(value_max == null || awaiting_test_benchmark_curve_results[pt][current_curve_benchmark_display] > value_max){
                    value_max = awaiting_test_benchmark_curve_results[pt][current_curve_benchmark_display];
                    max_value_input = "" + pt_input_value;
                }
                //
                graph_pts[0][pt] = {
                    "x": pt_input_value,
                    "y": awaiting_test_benchmark_curve_results[pt][current_curve_benchmark_display]
                };
            }
            else{
                animated_pts[pt] = true;
            }
        }
        //
        document.getElementById("graphs_benchmark_nb_pts_calculated").innerText = "" + Object.keys(graph_pts).length;
        //
        if(input_min == null || input_max == null){
            return;
        }
        //
        if(value_min == null || value_max == null){
            value_max = 1.0;
            value_min = 0.0;
        }
        else{
            document.getElementById("graphs_benchmark_score_max").innerText = value_max;
            document.getElementById("graphs_benchmark_value_score_max").innerText = max_value_input;
        }
        //
        for(pt of Object.keys(awaiting_test_benchmark_curve_results).keys()){
            if(awaiting_test_benchmark_curve_results[pt] == null){
                //
                graph_pts[0][pt] = {
                    "x": 0,
                    "y": (value_max + value_min) / 2.0
                };
            }
        }

        //
        if(Object.keys(animated_pts).length > 0){
            still_awaiting_points = true;
        }

        // On crée le nouveau graphe
        var new_graph = generate_2d_svg_graph(graph_pts, input_min, input_max, value_min, value_max, width=250, height=100, arrow_size=5, contour_stroke_width=2, points_stroke_width=2, points_circle_radius=2, animated_points=animated_pts);
        new_graph.classList.add("graph_svg");

        // On nettoie l'ancien graphe
        document.getElementById("graphs_benchmark_graph_div").innerHTML = "";

        // On affiche le nouveau graphe
        document.getElementById("graphs_benchmark_graph_div").appendChild(new_graph);
    }

    //
    return still_awaiting_points;
}

//
function opti_algo_curve_display_graph(){

    // On prépare les points à afficher
    var graph_pts = [];
    var value_min = null;
    var value_max = null;
    var max_value_config = null;
    var input_min = null;
    var input_max = null;
    //
    for(pt of Object.keys(optimization_processes[current_awaiting_optimization_process]["updates"]).keys()){
        //
        if(input_min == null || pt < input_min){
            input_min = pt;
        }
        if(input_max == null || pt > input_max){
            input_max = pt;
        }
        //
        if(optimization_processes[current_awaiting_optimization_process]["updates"][pt] != null){
            //
            if(value_min == null || optimization_processes[current_awaiting_optimization_process]["updates"][pt]["score"] < value_min){
                value_min = optimization_processes[current_awaiting_optimization_process]["updates"][pt]["score"];
            }
            if(value_max == null || optimization_processes[current_awaiting_optimization_process]["updates"][pt]["score"] > value_max){
                value_max = optimization_processes[current_awaiting_optimization_process]["updates"][pt]["score"];
                max_value_config = optimization_processes[current_awaiting_optimization_process]["updates"][pt]["config"];
            }
            //
            var point_color = optimization_processes[current_awaiting_optimization_process]["updates"][pt]["color"];
            if(point_color < 0 || typeof(point_color) != "number"){
                point_color = 0;
            }
            else{
                // On s'assurce que c'est bien un entier
                point_color = Math.ceil(point_color);
            }
            //
            while(graph_pts.length <= point_color){
                graph_pts.push({});
            }
            //
            graph_pts[point_color][pt] = {
                "x": pt,
                "y": optimization_processes[current_awaiting_optimization_process]["updates"][pt]["score"]
            };
        }
    }
    //
    if(input_min == null || input_max == null){
        return;
    }
    //
    if(value_min == null || value_max == null){
        value_max = 1.0;
        value_min = 0.0;
    }
    else{
        document.getElementById("algo_opti_graphs_score_max").innerText = value_max;
        document.getElementById("algo_opti_graphs_config_score_max").value = JSON.stringify(max_value_config);
    }

    // On crée le nouveau graphe
    var new_graph = generate_2d_svg_graph(graph_pts, input_min, input_max, value_min, value_max, width=250, height=100, arrow_size=5, contour_stroke_width=2, points_stroke_width=2, points_circle_radius=2);
    new_graph.classList.add("graph_svg");

    // On nettoie l'ancien graphe
    document.getElementById("algo_opti_graphs_graph_div").innerHTML = "";

    // On affiche le nouveau graphe
    document.getElementById("algo_opti_graphs_graph_div").appendChild(new_graph);
}

//
function duplicate_obj(obj){
    if(typeof(obj) != "object"){
        return obj;
    }
    else if(Array.isArray(obj)){
        var nobj = [];
        for(elt of obj){
            nobj.push(duplicate_obj(elt));
        }
        return nobj;
    }
    else{
        var nobj = {};
        for(k in obj){
            nobj[k] = duplicate_obj(obj[k]);
        }
        return nobj;
    }
}

//
function on_hpo_curve_test_benchmark_results(task, config, benchmark_results, test_benchmark_type, param_values, param_pts_ids){

    // On vérifie qu'on obtient bien le résultat que l'on attendait
    if(task != current_task || awaiting_test_benchmark_request_task != task){
        return;
    }

    //
    benchmark_results["input_values"] = param_values;

    //
    awaiting_test_benchmark_curve_results[get_curve_param_pts_id_dict_key(param_pts_ids)] = benchmark_results;

    //
    var still_awaiting_points = curve_display_graph();

    //
    if(!still_awaiting_points){
        // Calcul fini, tous les points ont été calculés
        document.getElementById("bt_send_test_request_manual_tests").disabled = false;
        document.getElementById("bt_send_draw_curve_request_manual_tests").disabled = false;
    }

}

//
function rec_add_parameter_to_curve_requests(id_param, requests_to_send, prev_id_params_values = {}, param_pts_ids = {}){

    // On récupère les valeurs
    var start_value = parseFloat(document.getElementById(get_hp_manual_tests_add_to_curve_interval_min_id(selected_keys_to_curve_list[id_param])).value);
    var end_value = parseFloat(document.getElementById(get_hp_manual_tests_add_to_curve_interval_max_id(selected_keys_to_curve_list[id_param])).value);
    var nb_intermediate_points = parseInt(document.getElementById(get_hp_manual_tests_add_to_curve_interval_nb_pts_id(selected_keys_to_curve_list[id_param])).value);

    // Test de bonne configuration
    if(start_value >= end_value || nb_intermediate_points <= 0 || nb_intermediate_points > MAX_NB_PTS_INTERMEDIATE){
        curve_request_error = true;
        alert("Erreur, valeur non valide de l'hyper paramètre " + keys.join("/") + " !");
        return;
    }

    //
    var j=0;
    for(j=0; j<nb_intermediate_points; j++){

        //
        var key_value = parseFloat(start_value) + (parseFloat(j)/parseFloat(nb_intermediate_points)) * (parseFloat(end_value) - parseFloat(start_value));

        prev_id_params_values[id_param] = parseFloat(key_value);
        param_pts_ids[id_param] = parseInt(j);

        //
        if(key_value == null || typeof key_value != "number"){
            alert("Erreur ! valeur non valide de l'hyper paramètre " + selected_keys_to_curve_list[id_param].join("/") + " !");
            curve_request_error = true;
            return;
        }

        if(id_param >= selected_keys_to_curve_list.length - 1){
            // Cas d'arrêt

            // On va dupliquer le fichier de configuration du moteur de recherche de la configuration sélectionnée
            var test_config = filter_null_values_of_arrays_from_config_dict(data_tasks[current_task]["configs"][current_engine_config]);

            // On va appliquer les hyper-paramètres de base, qui ne sont pas dans le add_to_curve
            for(base_keys of current_optimisable_hyper_parameters_keys){
                // Test qui vérifie que les clés ne sont pas dans la liste des hyper paramètres à optimiser
                var in_curve_list = true;
                for(curve_keys of selected_keys_to_curve_list){
                    if(base_keys == curve_keys){
                        in_curve_list = false;
                        break;
                    }
                }
                if(in_curve_list){
                    continue;
                }

                //
                var id_input_key = get_hp_value_manual_tests_id(base_keys);
                //
                var value = document.getElementById(id_input_key).value;
                //
                if(value == null || value == ""){
                    alert("Erreur, valeur non valide de l'hyper paramètre " + base_keys.join("/") + " !");
                    return;
                }
                //
                setValueToConfig(test_config, parseFloat(value), base_keys);
            }

            // On applique les valeurs des paramètres des courbes
            for(id_par of Object.keys(prev_id_params_values)){
                setValueToConfig(test_config, prev_id_params_values[id_param], selected_keys_to_curve_list[id_param]);
            }

            // On prépare pour recevoir les points
            if(awaiting_test_benchmark_curve_results == null){
                awaiting_test_benchmark_curve_results = {};
            }
            //
            if(awaiting_test_benchmark_result_requests == null){
                awaiting_test_benchmark_result_requests = {}
            }
            //
            awaiting_test_benchmark_curve_results[get_curve_param_pts_id_dict_key(param_pts_ids)] = null;

            //
            var req = {
                "type": "hpo_test_config_all_benchmarks",
                "test_benchmark_type": "curve_test",
                "param_values": duplicate_obj(prev_id_params_values),
                "param_pts_ids": duplicate_obj(param_pts_ids),
                "task": current_task,
                "config_dict": test_config
            };

            //
            awaiting_test_benchmark_result_requests[get_curve_param_pts_id_dict_key(param_pts_ids)] = req;

            // On va envoyer la requête
            requests_to_send.push(req);
        }
        else{
            rec_add_parameter_to_curve_requests(id_param+1, requests_to_send, prev_id_params_values, param_pts_ids);
        }
    }
}

//
function on_draw_curve_button_clicked_manual_tests_page(){
    //
    if(selected_keys_to_curve_list.length == 0 || selected_keys_to_curve_list.length > max_nb_keys_to_curve_list){
        alert("Error : bad number of elements to curve list (" + selected_keys_to_curve_list.length + ")");
        return;
    }

    //
    var requests_to_send = [];

    //
    awaiting_test_benchmark_curve_results = {};

    //
    curve_request_error = false;

    // On va préparer toutes les requêtes à envoyer au serveur
    rec_add_parameter_to_curve_requests(0, requests_to_send);

    //
    awaiting_test_benchmark_result_input_dim = selected_keys_to_curve_list.length;

    //
    if(curve_request_error){
        return;
    }

    //
    if(requests_to_send.length == 0){
        alert("Error : No points to calculate for curve drawing ("+requests_to_send.length+")");
        return;
    }
    //
    if(requests_to_send.length > 1000){
        alert("Error : Too much points to calculate for curve drawing ("+requests_to_send.length+")");
        return;
    }

    //
    awaiting_test_benchmark_request_task = current_task;
    awaiting_test_benchmark_request_config = data_tasks[current_task]["configs"][current_engine_config];
    awaiting_test_benchmark_result_type = "curve_test";
    document.getElementById("bt_send_test_request_manual_tests").disabled = true;
    document.getElementById("bt_send_draw_curve_request_manual_tests").disabled = true;

    // On prépare la page
    document.getElementById("graphs_benchmark_config_name").innerText = current_engine_config;
    document.getElementById("graphs_benchmark_nb_pts_tot").innerText = Object.keys(awaiting_test_benchmark_curve_results).length;
    document.getElementById("graphs_benchmark_nb_pts_calculated").innerText = "0";
    document.getElementById("graphs_benchmark_score_max").innerText = "/";
    document.getElementById("graphs_benchmark_value_score_max").innerText = "/";

    //   On affiche le graphe vide
    curve_display_graph();

    // On va sur la page
    go_to_page("manual_test_graphs_page");

    // On envoie toutes les requêtes
    for(request of requests_to_send){
        ws_send_msg(window.ws, request);
    }

}

//
function on_see_previous_curves_button_clicked_manual_tests_page(){
    // TODO
}

//
function on_hpo_algo_optimization_button_clicked(){
    //
    var id_optimization_process = Math.floor(randomNumber(0, Number.MAX_SAFE_INTEGER));
    while(id_optimization_process in optimization_processes){
        id_optimization_process = Math.floor(randomNumber(0, Number.MAX_SAFE_INTEGER));
    }
    //
    var hp_to_optimize = [];
    //
    for(hp_keys of current_optimisable_hyper_parameters_keys){
        if(document.getElementById(get_hp_algorithmic_optimization_constraint_checkbox_id(hp_keys)).checked){
            hp_to_optimize.push({
                "keys": hp_keys,
                "value_min": parseFloat(document.getElementById(get_hp_algorithmic_optimization_constraints_min_id(hp_keys)).value),
                "value_max": parseFloat(document.getElementById(get_hp_algorithmic_optimization_constraints_max_id(hp_keys)).value)
            });
        }
    }
    //
    if(Object.keys(hp_to_optimize).length == 0){
        alert("No hyper-parameters to optimize, operation aborted!");
        return;
    }
    //
    var benchmarks_to_optimize = {};
    //
    for(benchmark_name of data_tasks[current_task]["benchmarks_names"]){
        if(document.getElementById(get_hpo_algo_benchmark_checkbox_id(benchmark_name)).checked){
            benchmarks_to_optimize[benchmark_name] = parseFloat(document.getElementById(get_hpo_algo_benchmark_coef_id(benchmark_name)).value);
        }
    }
    //
    if(Object.keys(benchmarks_to_optimize).length == 0){
        alert("No benchmarks to optimize, operation aborted!");
        return;
    }
    //
    var algorithm_parameters = {};
    //
    for(algo_parameter_name of Object.keys(hpo_algorithms[current_hpo_algorithm_selected])){
        if(hpo_algorithms[current_hpo_algorithm_selected][algo_parameter_name][0] == "number"){
            algorithm_parameters[algo_parameter_name] = parseFloat(document.getElementById(get_hpo_algo_parameter_id(algo_parameter_name)).value);
        }
    }
    //
    var request = {
        "type": "hpo_algorithmic_optimization",
        "id_request": id_optimization_process,
        "task": current_task,
        "base_engine_config": data_tasks[current_task]["configs"][current_engine_config],
        "hyper_parameters_to_optimize": hp_to_optimize,
        "benchmarks_to_optimize": benchmarks_to_optimize,
        "algorithm_parameters": algorithm_parameters,
        "algo_name": current_hpo_algorithm_selected
    };
    //
    optimization_processes[id_optimization_process] = {
        "request": request,
        "updates": {},
        "result": null
    };
    //
    current_awaiting_optimization_process = id_optimization_process;
    //
    ws_send_msg(window.ws, request);
    //
    opti_algo_curve_display_graph();
    go_to_page("algorithmic_optimization_graphs_page");
}

//
function on_hpo_algo_opti_update(id_request, update_config_score){
    //
    if(! id_request in optimization_processes){
        return;
    }

    //
    optimization_processes[id_request]["updates"][update_config_score["iter"]] = update_config_score;
    //
    document.getElementById("algo_opti_graphs_nb_pts_calculated").innerText = "" + (parseInt(update_config_score["iter"])+1);

    //
    opti_algo_curve_display_graph();
}

//
function on_hpo_algo_opti_result(id_request, config_optimized_hp, config_optimized_score){
    //
    if(current_awaiting_optimization_process != id_request){
        return;
    }

    //
    document.getElementById("algo_opti_graphs_score_max").innerText = config_optimized_score;
    document.getElementById("algo_opti_graphs_config_score_max").value = JSON.stringify(config_optimized_hp);

    //
    current_awaiting_optimization_process = null;
}

//
function on_select_optimization_algorithm_changed(){
    current_hpo_algorithm_selected = document.getElementById("select_optimization_algorithm").value;
    on_hpo_algorithm_selected(current_hpo_algorithm_selected);
}

//
document.onclick = function(){
    if(current_drop_down_button_displayed != null){
        hide_engine_config_drop_down_button(current_drop_down_button_displayed);
    }
}

