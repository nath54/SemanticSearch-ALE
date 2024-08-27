
// Liste de toutes les pages
const all_pages = ["loading_page", "base_page", "error_page", "engine_config_page", "benchmark_page", "benchmark_result_page"];

// Titres des pages de chaque page
const all_pages_titles = {
    "loading_page": "Chargement",
    "base_page": "Tableau des benchmarks",
    "error_page": "Erreur",
    "engine_config_page": "Moteur de recherche",
    "benchmark_page": "Détails d'un benchmark",
    "benchmark_result_page": "Détails d'un résultat"
}

// Page actuelle
var current_page = "loading_page";

// Machine support par défaut
var default_support_platform = "CPU: AMD Ryzen 5 PRO 4650U with Radeon Graphics - GPU: ";

// Machine support actuelle
var current_support_platform = null;

// Liste de toutes les machines supports
var all_support_platforms = [];

// Benchmarks, pour toutes les machines supports
var benchmarks_all_support_platforms = {};

// Liste de tous les tests pour la machine support actuelle
var current_platform_all_benchmarks = [];

// Liste de toutes les configs pour la machine support actuelle
var current_platform_all_engine_configs = [];

// Liste de la colonne de tri actuelle
var current_sort_button = "engine_name_sort_button";
var current_sort_direction = "ascending";

// Colonne de benchmark actuellement survolée
var current_benchmark_col = "";

// Ligne de moteur de recherche actuellement survolée
var current_engine_row = "";


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

    // On affiche la bonne page
    set_display_page();
    // On met à jour le titre de la page
    document.getElementById("page_subtitle").innerText = all_pages_titles[current_page];

}

// Affiche la page d'erreur et affiche le message d'erreur
function display_error(error_message){
    // On va sur la page d'erreur
    current_page = "error_page";
    // On affiche le message d'erreur
    document.getElementById("error_message").innerText = error_message;
    // On met à jour l'affichage
    update_display();
}

// Affiche la page de chargement
function display_loading_page(){
    // On change la page
    current_page = "loading_page";
    // On met à jour l'affichage
    update_display();
}

// Affiche la page de base des résultats
function display_base_page(){
    // On change la page
    current_page = "base_page";
    // On met à jour l'affichage
    update_display();
}

// Ajoute le choix de la machine support dans le menu de sélection des machines supports
function add_support_platform_option(platform_name){
    var option = document.createElement("option");
    option.innerText = platform_name;
    option.setAttribute("value", platform_name);
    option.setAttribute("onclick", "on_current_platform_change(\"" + platform_name + "\");");

    document.getElementById("select_platform").appendChild(option);
}

// Fonction qui va récupérer la liste de toutes les machines supports dans les résultats des benchmarks
function get_all_support_platforms(){

    // On va nettoyer tous les tableaux
    current_support_platform = null;
    all_support_platforms = [];
    benchmarks_all_support_platforms = {};
    current_platform_all_benchmarks = [];
    current_platform_all_engine_configs = [];

    // On va parcourir tous les résultats de benchmarks que l'on a
    for(benchmark_result_id of Object.keys(benchmark_results)){

        // On va vérifier que ce benchmark est bien un benchmark de recherche
        if(!benchmark_result_id.startsWith("conversation_benchmark - ")){
            continue;
        }

        // On va récupérer les infos de ce résultat
        var result_support_platform = benchmark_results[benchmark_result_id]["platform_name"];

        // On va tester si cette machine support n'a pas déjà été vue
        if( benchmarks_all_support_platforms[result_support_platform] == undefined ){
            // On va l'ajouter
            benchmarks_all_support_platforms[result_support_platform] = {};
            all_support_platforms.push(result_support_platform);
        }

        // On va ajouter ce résultat de benchmark à la machine support actuelle
        benchmarks_all_support_platforms[result_support_platform][benchmark_result_id] = benchmark_results[benchmark_result_id];
    }

    // On va mettre à jour l'affichage au niveau du choix des machines supports
    document.getElementById("select_platform").innerHTML = "";
    for(platform_name of all_support_platforms){
        add_support_platform_option(platform_name);
    }

}

//
function get_benchmark_result_id_from_benchmark_name_engine_name_and_current_plaform(benchmark_name, engine_name){
    return "conversation_benchmark - " + benchmark_name + " - conversation engine - " + engine_name + " | " + current_support_platform;
}

// Fonction qui va parser la liste de tous les benchmarks et de toutes les configs de moteur de recherche pour la machine support actuelle
function current_platform_parse_benchmarks_and_engines(){

    // On va nettoyer les tableaux
    current_platform_all_benchmarks = [];
    current_platform_all_engine_configs = [];

    // On va parcourir tous les benchmarks de cette platforme
    for(benchmark_result_id of Object.keys(benchmarks_all_support_platforms[current_support_platform])){

        // On va récupérer le nom de la config du moteur de recherche et le nom du benchmark
        var conversation_engine_name = benchmarks_all_support_platforms[current_support_platform][benchmark_result_id]["conversation_engine_name"];
        var benchmark_name = benchmarks_all_support_platforms[current_support_platform][benchmark_result_id]["benchmark_name"];

        // On va ajouter le benchmark à la liste des benchmarks pour cette machine support s'il n'y est pas encore
        if(!current_platform_all_benchmarks.includes(benchmark_name)){
            current_platform_all_benchmarks.push(benchmark_name);
        }

        // On va ajouter le moteur de recherche à la liste des moteurs de recherche pour cette machine support s'il n'y est pas encore
        if(!current_platform_all_engine_configs.includes(conversation_engine_name)){
            current_platform_all_engine_configs.push(conversation_engine_name);
        }
    }

    // On va trier dans l'ordre lexicographique les benchmarks et les moteurs de recherche
    current_platform_all_benchmarks.sort();
    current_platform_all_engine_configs.sort();

}

// Nettoyage de table benchmark
function clean_benchmark_table(){
    while(document.getElementsByClassName("table_clean").length > 0){
        for(node of document.getElementsByClassName("table_clean")){
            node.remove();
        }
    }
}

// Remplace tous les mauvais caractères (' ', '-', '\n') par des '_'
function replace_all_bad_characters(txt){
    var ttxt = txt;
    //
    while(ttxt.includes(" ")){
        ttxt = ttxt.replace(" ", "_");
    }
    //
    while(ttxt.includes("-")){
        ttxt = ttxt.replace("-", "_");
    }
    //
    return ttxt;
}

// Donne l'id du bouton qui permet de trier selon la colonne score du benchmark demandé
function get_score_sort_button_id(benchmark_name){
    return "score_sort_button_" + replace_all_bad_characters(benchmark_name);;
}

// Donne l'id du bouton qui permet de trier selon la colonne vitesse du benchmark demandé
function get_speed_sort_button_id(benchmark_name){
    return "speed_sort_button_" + replace_all_bad_characters(benchmark_name);
}

// Donne l'id de la ligne de résultats de benchmarks du moteur de recherche demandé
function get_row_engine_benchmark_results_id(engine_name){
    return "row_benchmark_results_" + replace_all_bad_characters(engine_name);
}

// Donne l'id du résultat de score moyen de résultats pour le moteur de recherche demandé
function get_avg_score_engine_benchmark_results_id(engine_name){
    return "avg_score_" + replace_all_bad_characters(engine_name);
}

// Donne l'id du résultat de score pour le moteur de recherche demandé et le benchmark demandé
function get_score_engine_benchmark_id(engine_name, benchmark_name){
    return "score_engine_" + replace_all_bad_characters(engine_name) + "_benchmark_" + replace_all_bad_characters(benchmark_name);
}

//  Donne l'id du résultat de vitesse pour le moteur de recherche demandé et le benchmark demandé
function get_speed_engine_benchmark_id(engine_name, benchmark_name){
    return "speed_engine_" + replace_all_bad_characters(engine_name) + "_benchmark_" + replace_all_bad_characters(benchmark_name);
}

// Donne le nom de la classe pour le moteur de recherche
function get_engine_row_class(engine_name){
    return "engine_class_" + replace_all_bad_characters(engine_name);
}

// Donne le nom de la classe pour le benchmark
function get_benchmark_col_class(benchmark_name){
    return "benchmark_class_" + replace_all_bad_characters(benchmark_name);
}

// Ajout header benchmark name
function add_benchmark_header(benchmark_name){

    //
    var header_name = document.createElement("th");
    header_name.classList.add("table_clean", "table_benchmark_name");
    header_name.classList.add(get_benchmark_col_class(benchmark_name));
    header_name.setAttribute("onmouseenter", "on_mouse_enter_benchmark_col(\""+get_benchmark_col_class(benchmark_name)+"\");");
    header_name.setAttribute("colspan", "2");
    header_name.innerText = benchmark_name;
    if(Object.keys(benchmarks).includes(benchmark_name)){
        header_name.setAttribute("onclick", "on_benchmark_details_clicked(\""+benchmark_name+"\");");
        header_name.classList.add("clickable");
    }
    document.getElementById("benchmark_table_header_row1").appendChild(header_name);

    //
    var header_col_score = document.createElement("th");
    header_col_score.classList.add("table_clean", "table_engine_score");
    header_col_score.classList.add(get_benchmark_col_class(benchmark_name));
    header_col_score.setAttribute("onmouseenter", "on_mouse_enter_benchmark_col(\""+get_benchmark_col_class(benchmark_name)+"\");");
    document.getElementById("benchmark_table_header_row2").appendChild(header_col_score);

    var score_sort_button = document.createElement("span");
    score_sort_button.innerText = "\\/";
    score_sort_button.classList.add("sort_arrow", "font_small", "clickable");
    score_sort_button.setAttribute("id", get_score_sort_button_id(benchmark_name));
    score_sort_button.setAttribute("onclick", "sort_by_benchmark_score(\""+ benchmark_name +"\");");
    header_col_score.appendChild(score_sort_button);

    var score_sort_span = document.createElement("span");
    score_sort_span.classList.add("sort_span");
    score_sort_span.innerText = "score";
    header_col_score.appendChild(score_sort_span);

    //
    var header_col_speed = document.createElement("th");
    header_col_speed.classList.add("table_clean", "table_engine_speed");
    header_col_speed.classList.add(get_benchmark_col_class(benchmark_name));
    header_col_speed.setAttribute("onmouseenter", "on_mouse_enter_benchmark_col(\""+get_benchmark_col_class(benchmark_name)+"\");");
    document.getElementById("benchmark_table_header_row2").appendChild(header_col_speed);

    var speed_sort_button = document.createElement("span");
    speed_sort_button.setAttribute("onclick", "sort_by_benchmark_speed(\""+ benchmark_name +"\");");
    speed_sort_button.innerText = "\\/";
    speed_sort_button.setAttribute("id", get_speed_sort_button_id(benchmark_name));
    speed_sort_button.classList.add("sort_arrow", "font_small", "clickable");
    header_col_speed.appendChild(speed_sort_button);

    var speed_sort_span = document.createElement("span");
    speed_sort_span.classList.add("sort_span");
    speed_sort_span.innerText = "vitesse";
    header_col_speed.appendChild(speed_sort_span);

}

// Attribue ou non une couleur à la case de score value
function set_score_value_color(node, value){
    if(value >= 0.7){
        node.classList.add("good_value");
    }
    else if(value >= 0.55){
        node.classList.add("acceptable_value");
    }
    else if(value >= 0.4){
        node.classList.add("bad_value");
    }
    else{
        node.classList.add("very_bad_value");
    }
}

// Ajout benchmark result engine ligne
function add_benchmark_result_engine_row(engine_name){

    // ligne complete
    var row_engine_results = document.createElement("tr");
    row_engine_results.setAttribute("id", get_row_engine_benchmark_results_id(engine_name));
    row_engine_results.classList.add("engine_result_row", "table_clean", "table_clean_body");
    row_engine_results.classList.add(get_engine_row_class(engine_name));
    row_engine_results.setAttribute("onmouseenter", "on_mouse_enter_engine_row(\""+get_engine_row_class(engine_name)+"\");");
    row_engine_results.setAttribute("engine_name", engine_name);

    // Nom moteur de recherche
    var col_engine_name = document.createElement("td");
    col_engine_name.innerText = engine_name;
    col_engine_name.classList.add("table_engine_name");
    col_engine_name.classList.add(get_engine_row_class(engine_name));
    col_engine_name.setAttribute("onmouseenter", "on_mouse_enter_engine_row(\""+get_engine_row_class(engine_name)+"\");");

    if(Object.keys(platforms_engines_config).includes(current_support_platform) && Object.keys(platforms_engines_config[current_support_platform]).includes(engine_name)){
        col_engine_name.setAttribute("onclick", "on_engine_config_clicked(\""+engine_name+"\");");
        col_engine_name.classList.add("clickable");
    }

    row_engine_results.appendChild(col_engine_name);

    // Score moyen
    var col_avg_score = document.createElement("td");
    col_avg_score.setAttribute("id", get_avg_score_engine_benchmark_results_id(engine_name));
    col_avg_score.classList.add("table_engine_avg")

    row_engine_results.appendChild(col_avg_score);

    // Pour calculer le score moyen
    var scores = [];
    var no_data_scores = false;

    // score et vitesse pour chaque benchmark
    for(benchmark_name of current_platform_all_benchmarks){

        var score = null;
        var speed = null;

        var benchmark_result_id = get_benchmark_result_id_from_benchmark_name_engine_name_and_current_plaform(benchmark_name, engine_name);
        var benchmark_result = benchmarks_all_support_platforms[current_support_platform][benchmark_result_id];

        if(benchmark_result != undefined && benchmark_result["score"] != undefined){
            score = parseFloat(parseFloat(benchmark_result["score"]).toFixed(4));
            scores.push(score);
        }
        if(benchmark_result != undefined && benchmark_result["time"] != undefined){
            speed = parseFloat(parseFloat(benchmark_result["time"]).toFixed(4));
        }

        // Score
        var col_score = document.createElement("td");
        col_score.setAttribute("id", get_score_engine_benchmark_id(engine_name, benchmark_name));
        col_score.classList.add("table_engine_score");
        col_score.classList.add(get_benchmark_col_class(benchmark_name));
        col_score.setAttribute("onmouseenter", "on_mouse_enter_benchmark_col(\""+get_benchmark_col_class(benchmark_name)+"\");");
        if(score == null){
            col_score.innerText = "ND";
            no_data_scores = true;
        }
        else{
            col_score.innerText = "" + score;
            set_score_value_color(col_score, score);
        }
        row_engine_results.appendChild(col_score);

        // Speed
        var col_speed = document.createElement("td");
        col_speed.setAttribute("id", get_speed_engine_benchmark_id(engine_name, benchmark_name));
        col_speed.classList.add("table_engine_speed");
        col_speed.classList.add(get_benchmark_col_class(benchmark_name));
        col_speed.setAttribute("onmouseenter", "on_mouse_enter_benchmark_col(\""+get_benchmark_col_class(benchmark_name)+"\");");
        if(speed == null){
            col_speed.innerText = "ND";
        }
        else{
            col_speed.innerText = "" + speed + " sec";
        }

        // Ajout click
        if(benchmark_result != undefined && Object.keys(platforms_engines_config).includes(current_support_platform) && Object.keys(platforms_engines_config[current_support_platform]).includes(engine_name)){
            col_score.setAttribute("onclick", "on_benchmark_result_clicked(\""+benchmark_name+"\", \""+engine_name+"\");");
            col_score.classList.add("clickable");
            col_speed.setAttribute("onclick", "on_benchmark_result_clicked(\""+benchmark_name+"\", \""+engine_name+"\");");
            col_speed.classList.add("clickable");
        }

        row_engine_results.appendChild(col_speed);
    }

    // On calcule le score moyen
    if(no_data_scores){
        col_avg_score.innerText = "ND";
    }
    else{
        var avg_score = ((scores.reduce((partialSum, a) => partialSum + a, 0)) / (scores.length)).toFixed(4);
        col_avg_score.innerText = "" + avg_score;
        set_score_value_color(col_avg_score, avg_score);

    }

    //
    document.getElementById("benchmark_table_body").appendChild(row_engine_results);
}

// Fonction qui va nettoyer et rafficher le tableau de résultats pour la machine support actuelle
function current_platform_update_benchmark_results_table(){

    // On va nettoyer la table précédent
    clean_benchmark_table();

    // On va ajouter les titres de colonnes pour les noms des benchmarks
    for(benchmark_name of current_platform_all_benchmarks){
        add_benchmark_header(benchmark_name);
    }

    // On va ajouter les lignes de résultats de benchmarks pour chaque configuration de moteur de recherche testée sur cette machine support
    for(engine_name of current_platform_all_engine_configs){
        add_benchmark_result_engine_row(engine_name);
    }

}

// Fonction qui va être appelée quand on change de machine support
function on_current_platform_change(new_platform){

    // On va mettre sur la page de chargement en attendant
    display_loading_page();

    // On va mettre à jour la machine support actuelle
    current_support_platform = new_platform;

    // On va mettre à jour l'affichage des options
    document.getElementById("select_platform").setAttribute("value", new_platform);

    // On va parser tous les benchmarks et configs de moteur de recherche que l'on a avec la machine support actuelle
    current_platform_parse_benchmarks_and_engines();

    // On va afficher le tableau
    current_platform_update_benchmark_results_table();

    // On va ensuite trier par meilleur score moyen décroissant
    current_sort_button = null;
    sort_by_avg_score();

    // On va se mettre sur la page de base une fois que le tableau a bien été calculé
    display_base_page();
}

// Fonction qui va être appelée lors de la fin du chargement de la page web
function on_page_loaded(){

    // On va récupérer toutes les machines supports de ces benchmarks
    get_all_support_platforms();

    // On va tester s'il y a au moins une machine support détectée
    if(all_support_platforms.length == 0){
        display_error("Erreur: Benchmarks vides.");
        return;
    }

    // On va tester si la machine support par défaut est dans les machines détectées
    if(all_support_platforms.includes(default_support_platform)){
        on_current_platform_change(default_support_platform);
        document.getElementById("select_platform").value = default_support_platform;
    }
    // Sinon, on va prendre la première machine support détectée
    else{
        on_current_platform_change(all_support_platforms[0]);
    }
}

// Fonction qui va mettre un bouton en sort ascending
function set_sort_button_ascending(button_id){
    var bt = document.getElementById(button_id);
    bt.innerText = "/\\";
    if(bt.classList.contains("sort_arrow_descending")){
        bt.classList.remove("sort_arrow_descending");
    }
    bt.classList.add("sort_arrow_ascending");
}

// Fonction qui va mettre un bouton en sort descending
function set_sort_button_descending(button_id){
    var bt = document.getElementById(button_id);
    bt.innerText = "\\/";
    if(bt.classList.contains("sort_arrow_ascending")){
        bt.classList.remove("sort_arrow_ascending");
    }
    bt.classList.add("sort_arrow_descending");
}

// Fonction qui va remettre à zéro un bouton
function reset_sort_button(button_id){
    var bt = document.getElementById(button_id);
    bt.innerText = "-";
    if(bt.classList.contains("sort_arrow_descending")){
        bt.classList.remove("sort_arrow_descending");
    }
    if(bt.classList.contains("sort_arrow_ascending")){
        bt.classList.remove("sort_arrow_ascending");
    }
}

// Fonction qui va remettre à zéro tous les boutons de tris
function reset_all_sort_buttons(){
    //
    reset_sort_button("engine_name_sort_button");
    reset_sort_button("avg_score_sort_button");
    //
    for(benchmark_name of current_platform_all_benchmarks){
        reset_sort_button(get_score_sort_button_id(benchmark_name));
        reset_sort_button(get_speed_sort_button_id(benchmark_name));
    }
}

// Fonction qui va être appelée quand on va vouloir lancer un tri
function sort_engines_results_rows(button_id, function_get_attribute_to_sort, default_direction){

    //
    reset_all_sort_buttons();
    //

    var sort_direction = default_direction;

    if(current_sort_button == button_id && current_sort_direction == default_direction){
        if(default_direction == "ascending"){
            sort_direction = "descending";
        }
        else{
            sort_direction = "ascending";
        }
    }

    if(sort_direction == "ascending"){
        set_sort_button_ascending(button_id);
    }
    else{
        set_sort_button_descending(button_id);
    }

    current_sort_button = button_id;
    current_sort_direction = sort_direction;

    var switching = true;
    var max_switchs = 1000;
    var current_switchs = 0;

    var rows = document.getElementById("benchmark_table_body").children;

    // On va faire une boucle qui va continuer tant qu'il y a des éléments à échanger
    while (switching && current_switchs < max_switchs) {
        current_switchs += 1;

        switching = false;

        // On va parcourir toutes les lignes
        var i;
        for (i = 0; i < (rows.length - 1); i++) {

            // On commence en disant qu'il n'y a pas eu d'échange
            var shouldSwitch = false;

            // On récupère les deux éléments à comparer, l'un de la ligne actuelle et l'autre de la ligne suivante
            var engine_name_1 = rows[i].getAttribute("engine_name");
            var engine_name_2 = rows[i+1].getAttribute("engine_name");
            // On récupère leurs attributs
            var attribute_1 = function_get_attribute_to_sort(engine_name_1);
            var attribute_2 = function_get_attribute_to_sort(engine_name_2);

            // On teste si ces deux lignes devraient être échangées
            if (
                (sort_direction == "ascending" && attribute_1 > attribute_2) ||
                (sort_direction == "descending" && attribute_1 < attribute_2)
            ) {
                // Si oui, on dit qu'il faut échanger, et on sort de la boucle
                shouldSwitch = true;
                break;
            }
        }

        if (shouldSwitch) {
            // S'il faut échanger, on échange et on indique qu'il y a eu un échange
            var engine_name_1 = rows[i].getAttribute("engine_name");
            var engine_name_2 = rows[i+1].getAttribute("engine_name");

            rows[i].parentNode.insertBefore(rows[i+1], rows[i]);
            switching = true;
        }
    }
}

// Fonction qui va être appelée quand on va vouloir lancer un tri sur le nom des moteurs de recherche
function sort_by_engine_name(){
    sort_engines_results_rows(
        "engine_name_sort_button",
        ((engine_name) =>
            engine_name.toLowerCase()
        ),
        "ascending"
    );
}

// Fonction qui va être appelée quand on va vouloir lancer un tri sur le score moyen d'un moteur de recherche
function sort_by_avg_score(){
    sort_engines_results_rows(
        "avg_score_sort_button",
        ((engine_name) =>
            parseFloat(document.getElementById(get_avg_score_engine_benchmark_results_id(engine_name)).innerHTML)
        ),
        "descending"
    );
}

// Fonction qui va être appelée quand on va vouloir lancer un tri sur un score d'un benchmark
function sort_by_benchmark_score(benchmark_name){
    sort_engines_results_rows(
        get_score_sort_button_id(benchmark_name),
        ((engine_name) =>
            parseFloat(document.getElementById(get_score_engine_benchmark_id(engine_name, benchmark_name)).innerHTML)
        ),
        "descending"
    );
}

// Fonction qui va être appelée quand on va vouloir lancer un tri sur un temps d'un benchmark
function sort_by_benchmark_speed(benchmark_name){
    sort_engines_results_rows(
        get_speed_sort_button_id(benchmark_name),
        ((engine_name) =>
            parseFloat(document.getElementById(get_speed_engine_benchmark_id(engine_name, benchmark_name)).innerHTML)
        ),
        "ascending"
    );
}

//
function on_benchmark_details_clicked(benchmark_name){

    // à regarder : benchmarks[benchmark_name]
    // On récupère les détails du benchmark à afficher
    var benchmark = benchmarks[benchmark_name];

    // On va afficher les nouvelles valeurs
    document.getElementById("benchmark_details_title").innerText = benchmark_name;
    document.getElementById("benchmark_details_description").innerText = benchmark["description"];
    document.getElementById("benchmark_detail_conversation_messages").innerHTML = "";


    const nb_cls_correct = Math.max(...benchmark["conversation_colors"]) + 1;

    // On va afficher tous les messages originaux
    var i;
    for(i=0; i<benchmark["messages"].length; i++){

        const cl_correct = benchmark["conversation_colors"][i];

        const msg_txt = benchmark["messages"][i]["content"];
        const msg_author = benchmark["messages"][i]["author"];
        const msg_date = benchmark["messages"][i]["date"];

        var div_msg_original = create_div_msg_original(msg_txt, msg_author, msg_date, cl_correct, nb_cls_correct, i);

        document.getElementById("benchmark_detail_conversation_messages").appendChild(div_msg_original);
    }

    // On va changer la page
    current_page = "benchmark_page";
    // et on va mettre à jour l'affichage
    update_display();
}

//
function on_engine_config_clicked(engine_name){

    // à regarder : platforms_engines_config[current_support_platform][engine_name]
    var engine_config = platforms_engines_config[current_support_platform][engine_name];

    // On va afficher les nouvelles valeurs
    document.getElementById("benchmark_engine_config_support_platform").innerText = current_support_platform;
    document.getElementById("benchmark_engine_config_config_name").innerText = engine_name;
    if(Object.keys(engine_config).includes("description")){
        document.getElementById("benchmark_engine_config_description").innerText = engine_config["description"];
    }
    else{
        document.getElementById("benchmark_engine_config_description").innerText = "no description";
    }
    document.getElementById("benchmark_engine_config_algos").innerHTML = "";

    //
    for(algo of engine_config["algorithms"]){

        var div_algo = document.createElement("div");
        div_algo.classList.add("engine_config_details_search_algorithms", "col", "left_align");

        var div_row_top = document.createElement("div");
        div_row_top.classList.add("row");

        var b_algo_type = document.createElement("b");
        b_algo_type.innerText = "• " + algo["type"];
        b_algo_type.classList.add("m_5p", "left_align");
        div_row_top.appendChild(b_algo_type);

        var span_algo_coef = document.createElement("span");
        span_algo_coef.innerText = " ( coefficient : " + algo["coef"] + " )";
        span_algo_coef.classList.add("m_5p", "left_align");
        div_row_top.appendChild(span_algo_coef);

        div_algo.appendChild(div_row_top);

        var div_col_algo_args = document.createElement("div");
        div_col_algo_args.classList.add("col", "left_align", "w_100", "m_l_15p");

        for(algo_key of Object.keys(algo)){
            if(!["type", "coef", "models_path"].includes(algo_key)){

                var div_row_arg = document.createElement("div");
                div_row_arg.classList.add("row");

                var span_arg_label = document.createElement("span");
                span_arg_label.innerText = " - " + algo_key + " : ";
                span_arg_label.classList.add("left_align", "flex", "font_normal", "m_l_5p");
                div_row_arg.appendChild(span_arg_label);

                var span_arg_value = document.createElement("span");
                span_arg_value.innerText = algo[algo_key];
                span_arg_value.classList.add("left_align", "flex", "font_normal", "m_l_5p");
                div_row_arg.appendChild(span_arg_value);

                div_col_algo_args.appendChild(div_row_arg);
            }
        }

        div_algo.appendChild(div_col_algo_args);

        document.getElementById("benchmark_engine_config_algos").appendChild(div_algo);
    }

    // On va changer la page
    current_page = "engine_config_page";
    // et on va mettre à jour l'affichage
    update_display();
}

//
function create_div_msg_original(msg_txt, msg_author, msg_date, cl_correct, nb_cls_correct, msg_idx){

    var div_msg = document.createElement("div");

    div_msg.classList.add("div_msg_original_benchmark_conversations_results", "col");

    div_msg.style.width = "50%";
    div_msg.style.marginLeft = "" + (1 + (cl_correct / nb_cls_correct * 50.0)) + "%";
    div_msg.style.backgroundColor = get_rgb_bg_fg_from_conv_id(cl_correct)["bg"];
    div_msg.style.border = "1px solid "+get_rgb_bg_fg_from_conv_id(cl_correct)["fg"];

    var span_txt = document.createElement("span");
    span_txt.classList.add("left_align", "w_100", "font_smaller");
    span_txt.innerText = msg_txt;
    div_msg.appendChild(span_txt);

    var row_bottom = document.createElement("div");
    row_bottom.classList.add("row", "w_100", "m_t_5p");

    var span_msg_id = document.createElement("span");
    span_msg_id.classList.add("m_l_auto", "font_small");
    span_msg_id.innerText = "msg " + msg_idx + ", ";
    row_bottom.appendChild(span_msg_id);

    var span_author = document.createElement("span");
    span_author.classList.add("m_l_auto", "font_small");
    span_author.innerText = "auteur : " + msg_author;
    row_bottom.appendChild(span_author);

    var span_date = document.createElement("span");
    span_date.classList.add("m_l_5p", "font_small");
    span_date.innerText = "date : " + msg_date;
    row_bottom.appendChild(span_date);

    var span_cl = document.createElement("span");
    span_cl.classList.add("m_l_5p", "font_small");
    span_cl.innerText = "conversation : " + cl_correct;
    row_bottom.appendChild(span_cl);

    div_msg.appendChild(row_bottom);

    return div_msg;

}

//
function create_div_msg_algo_result(msg_txt, msg_author, msg_date, cl_algo, nb_cls_algo, msg_idx){

    var div_msg = document.createElement("div");
    div_msg.classList.add("div_msg_algo_benchmark_conversations_results", "col");
    div_msg.style.backgroundColor = get_rgb_bg_fg_from_conv_id(cl_algo)["bg"];
    div_msg.style.border = "1px solid "+get_rgb_bg_fg_from_conv_id(cl_algo)["fg"];

    var span_txt = document.createElement("span");
    span_txt.classList.add("left_align", "w_100", "font_smaller");
    span_txt.innerText = msg_txt;
    div_msg.appendChild(span_txt);

    var row_bottom = document.createElement("div");
    row_bottom.classList.add("row", "w_100", "m_t_5p");

    var span_msg_id = document.createElement("span");
    span_msg_id.classList.add("m_l_auto", "font_small");
    span_msg_id.innerText = "msg " + msg_idx + ", ";
    row_bottom.appendChild(span_msg_id);

    var span_author = document.createElement("span");
    span_author.classList.add("m_l_auto", "font_small");
    span_author.innerText = "auteur : " + msg_author;
    row_bottom.appendChild(span_author);

    var span_date = document.createElement("span");
    span_date.classList.add("m_l_5p", "font_small");
    span_date.innerText = "date : " + msg_date;
    row_bottom.appendChild(span_date);

    var span_cl = document.createElement("span");
    span_cl.classList.add("m_l_5p", "font_small");
    span_cl.innerText = "conversation : " + cl_algo;
    row_bottom.appendChild(span_cl);

    div_msg.appendChild(row_bottom);

    return div_msg;
}

//
function on_conversation_algo_result_clicked(id_conv, benchmark_name, engine_name){
    // Ca va récupérer tous les messages de cette conversation
    var benchmark_result_id = get_benchmark_result_id_from_benchmark_name_engine_name_and_current_plaform(benchmark_name, engine_name);
    var benchmark_result = benchmarks_all_support_platforms[current_support_platform][benchmark_result_id];

    // On va afficher tous les messages de cette conversation
    const algo_msgs_cl = benchmark_result["algo_msgs_cl"];
    const msgs_list = benchmarks[benchmark_name]["messages"];
    const nb_cls_algo = Math.max(...benchmark_result["algo_msgs_cl"]) + 1;

    // Nettoyage
    document.getElementById("benchmark_results_algos_messages").innerHTML = "";

    //
    var i;
    for(i=0; i<algo_msgs_cl.length; i++){
        if(algo_msgs_cl[i] == id_conv){

            const msg_txt = msgs_list[i]["content"];
            const msg_author = msgs_list[i]["author"];
            const msg_date = msgs_list[i]["date"];

            var div_msg = create_div_msg_algo_result(msg_txt, msg_author, msg_date, id_conv, nb_cls_algo);

            document.getElementById("benchmark_results_algos_messages").appendChild(div_msg);

        }
    }

    //
    document.getElementById("current_result_conversation_name").innerText = "Conversation " + id_conv;

    //
    document.getElementById("current_result_conversation_name_div").style.display = "flex";
    document.getElementById("benchmark_results_algos_messages").style.display = "flex";
    document.getElementById("benchmark_results_algos_conversations").style.display = "none";

}

//
function create_div_button_conv_title(conv_title, id_conv, benchmark_name, engine_name){

    var div_button = document.createElement("button");

    div_button.innerText = conv_title;

    div_button.classList.add("div_button_conv", "clickable", "row", "m_15p");
    div_button.setAttribute("onclick", "on_conversation_algo_result_clicked(" + id_conv + ", \"" + benchmark_name + "\", \"" + engine_name + "\");")

    return div_button;

}

//
function display_algo_results_msgs_conversations(benchmark_name, engine_name){

    // On récupère l'élément sur lequel on va afficher les détails
    var benchmark_result_id = get_benchmark_result_id_from_benchmark_name_engine_name_and_current_plaform(benchmark_name, engine_name);
    var benchmark_result = benchmarks_all_support_platforms[current_support_platform][benchmark_result_id];

    //
    const nb_cls_algo = Math.max(...benchmark_result["algo_msgs_cl"]) + 1;

    // Nettoyage
    document.getElementById("benchmark_results_algos_conversations").innerHTML = "";

    // TODO: générer/récupérer titres des conversations identifiées par l'algorithme???

    // On va afficher tous les titres des conversations
    for(i=0; i<nb_cls_algo; i++){

        var div_button_conv_title = create_div_button_conv_title("Conversation " + i, i, benchmark_name, engine_name);

        document.getElementById("benchmark_results_algos_conversations").appendChild(div_button_conv_title);

    }

    //
    document.getElementById("current_result_conversation_name_div").style.display = "none";
    document.getElementById("benchmark_results_algos_messages").style.display = "none";
    document.getElementById("benchmark_results_algos_conversations").style.display = "flex";

}

//
function on_benchmark_result_clicked(benchmark_name, engine_name){

    // On récupère l'élément sur lequel on va afficher les détails
    var benchmark_result_id = get_benchmark_result_id_from_benchmark_name_engine_name_and_current_plaform(benchmark_name, engine_name);
    var benchmark_result = benchmarks_all_support_platforms[current_support_platform][benchmark_result_id];

    // On va afficher les nouvelles valeurs
    document.getElementById("benchmark_result_support_platform").innerText = current_support_platform;
    document.getElementById("benchmark_result_benchmark_name").innerText = benchmark_name;
    document.getElementById("benchmark_result_engine_name").innerText = engine_name;
    document.getElementById("benchmark_result_score").innerText = benchmark_result["score"];
    document.getElementById("benchmark_result_total_time").innerText = benchmark_result["time"];
    document.getElementById("benchmark_results_original_messages").innerHTML = "";
    document.getElementById("benchmark_results_algos_conversations").innerHTML = "";
    document.getElementById("benchmark_results_algos_messages").innerHTML = "";
    document.getElementById("benchmark_result_conversations_table_algo_clickable_title").setAttribute("onclick", "benchmark_results_go_to_results_conversations_list(\"" + benchmark_name + "\", \"" + engine_name + "\")");

    //
    const nb_cls_correct = Math.max(...Object.values(benchmark_result["correct_msgs_cl"])) + 1;
    const nb_cls_algo = Math.max(...Object.values(benchmark_result["algo_msgs_cl"])) + 1;

    // On va afficher tous les messages originaux
    var i;
    for(i=0; i<benchmarks[benchmark_name]["messages"].length; i++){

        const cl_correct = benchmark_result["correct_msgs_cl"][i];

        const msg_txt = benchmarks[benchmark_name]["messages"][i]["content"];
        const msg_author = benchmarks[benchmark_name]["messages"][i]["author"];
        const msg_date = benchmarks[benchmark_name]["messages"][i]["date"];

        var div_msg_original = create_div_msg_original(msg_txt, msg_author, msg_date, cl_correct, nb_cls_correct, i);

        document.getElementById("benchmark_results_original_messages").appendChild(div_msg_original);
    }


    // On va afficher tous les messages résultats
    var i;
    for(i=0; i<benchmarks[benchmark_name]["messages"].length; i++){

        const cl_algo = benchmark_result["algo_msgs_cl"][i];

        const msg_txt = benchmarks[benchmark_name]["messages"][i]["content"];
        const msg_author = benchmarks[benchmark_name]["messages"][i]["author"];
        const msg_date = benchmarks[benchmark_name]["messages"][i]["date"];

        var div_msg_result = create_div_msg_original(msg_txt, msg_author, msg_date, cl_algo, nb_cls_algo, i);

        document.getElementById("benchmark_results_algos_conversations").appendChild(div_msg_result);
    }

    // display_algo_results_msgs_conversations(benchmark_name, engine_name);

    // Si on a une matrice de distances des messages, on va l'afficher
    if(benchmark_result["distances_matrix"] != undefined){

        //
        document.getElementById("benchmark_result_distances_matrix_div").style.display = "flex";

        //
        for(idx_msg1=-1; idx_msg1<benchmarks[benchmark_name]["messages"].length; idx_msg1++){
            //
            var t_row = document.createElement("tr");
            document.getElementById("benchmark_result_distances_matrix_table").appendChild(t_row);
            //
            var row_header = document.createElement("td");
            t_row.appendChild(row_header);
            //
            if(idx_msg1 != -1){
                row_header.classList.add("row_" + idx_msg1, "benchmark_result_distances_matrix_table_element");
                row_header.innerText = "msg " + idx_msg1;
            }
            //
            for(idx_msg2=0; idx_msg2<benchmarks[benchmark_name]["messages"].length; idx_msg2++){
                // header
                if(idx_msg1 == -1){
                    var col_header = document.createElement("td");
                    t_row.appendChild(col_header);
                    col_header.classList.add("col_"+idx_msg2, "benchmark_result_distances_matrix_table_element");
                    //
                    if(idx_msg1 == -1){
                        col_header.innerText = "msg " + idx_msg2;
                    }
                }
                // Résultat
                else{
                    var value = '/';
                    //
                    if(benchmark_result["distances_matrix"][idx_msg1] != undefined && benchmark_result["distances_matrix"][idx_msg1][idx_msg2] != undefined){
                        value = benchmark_result["distances_matrix"][idx_msg1][idx_msg2];
                    }
                    //
                    var t_col = document.createElement("td");
                    t_row.appendChild(t_col);
                    t_col.innerText = parseFloat(value.toFixed(3));
                    t_col.classList.add("col_"+idx_msg2, "row_"+idx_msg1, "benchmark_result_distances_matrix_table_element");
                    //
                    if(value != '/'){
                        //
                        const best_color = [0, 255, 0];
                        const worst_color = [255, 0, 0];
                        const worst_value = 2.0;
                        //
                        var c = clamp(value / worst_value, 0, 1);

                        var r = parseInt(best_color[0] * (1.0 - c) + worst_color[0] * c);
                        var g = parseInt(best_color[1] * (1.0 - c) + worst_color[1] * c);
                        var b = parseInt(best_color[2] * (1.0 - c) + worst_color[2] * c);

                        //
                        t_col.style.color = "rgb(" + r + ", " + g + ", " + b + ")";
                    }
                }
            }
        }

    }

    // On va changer la page
    current_page = "benchmark_result_page";
    // et on va mettre à jour l'affichage
    update_display();
}

//
function toggle_div_score_time(div_score){
    var span_time = div_score.children[1];
    if(span_time.style.display == "none"){
        span_time.style.display = "inline";
    }
    else{
        span_time.style.display = "none";
    }
}

//
function on_base_page_title_clicked(){

    // On va changer la page
    current_page = "base_page";
    // et on va mettre à jour l'affichage
    update_display();
}

// Quand l'utilisateur appuie sur la touche échap, il retourne sur la page de base s'il est sur une sous page
document.onkeyup = function (event) {
    if(event.key == "Escape"){
        if(document.activeElement.tagName == "input" || document.activeElement.tagName == "button" || document.activeElement.tagName == "select" || document.activeElement.tagName == "option"){
            return;
        }
        //
        if(["engine_config_page", "benchmark_page", "benchmark_result_page"].includes(current_page)){
            // On change de page
            current_page = "base_page";
            // et on met à jour l'affichage
            update_display();
        }
    }
}

//
function on_mouse_enter_benchmark_col(benchmark_col_class_name){

    if(benchmark_col_class_name == current_benchmark_col){
        return;
    }

    // On nettoie
    var lst_nodes = document.getElementsByClassName("benchmark_hover");
    while(lst_nodes.length > 0){
        //
        for(node of lst_nodes){
            node.classList.remove("benchmark_hover");
            node.classList.remove("benchmark_hover");
            node.classList.remove("benchmark_hover");
        }
        //
        lst_nodes = document.getElementsByClassName("benchmark_hover");
    }

    // On ajoute
    for(node of document.getElementsByClassName(benchmark_col_class_name)){
        node.classList.add("benchmark_hover");
    }

}

//
function on_mouse_enter_engine_row(engine_row_class_name){

    if(engine_row_class_name == current_engine_row){
        return;
    }

    // On nettoie
    var lst_nodes = document.getElementsByClassName("engine_hover");
    while(lst_nodes.length > 0){
        //
        for(node of lst_nodes){
            node.classList.remove("engine_hover");
            node.classList.remove("engine_hover");
            node.classList.remove("engine_hover");
        }
        //
        lst_nodes = document.getElementsByClassName("engine_hover");
    }

    // On ajoute
    for(node of document.getElementsByClassName(engine_row_class_name)){
        node.classList.add("engine_hover");
    }

}

//
function benchmark_results_go_to_results_conversations_list(benchmark_name, engine_name){
    //
    display_algo_results_msgs_conversations(benchmark_name, engine_name);
}
