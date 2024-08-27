
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
        if(!benchmark_result_id.startsWith("search_benchmark - ")){
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
    return "search_benchmark - " + benchmark_name + " - search engine - " + engine_name + " | " + current_support_platform;
}

// Fonction qui va parser la liste de tous les benchmarks et de toutes les configs de moteur de recherche pour la machine support actuelle
function current_platform_parse_benchmarks_and_engines(){

    // On va nettoyer les tableaux
    current_platform_all_benchmarks = [];
    current_platform_all_engine_configs = [];

    // On va parcourir tous les benchmarks de cette platforme
    for(benchmark_result_id of Object.keys(benchmarks_all_support_platforms[current_support_platform])){

        // On va récupérer le nom de la config du moteur de recherche et le nom du benchmark
        var search_engine_name = benchmarks_all_support_platforms[current_support_platform][benchmark_result_id]["search_engine_name"];
        var benchmark_name = benchmarks_all_support_platforms[current_support_platform][benchmark_result_id]["benchmark_name"];

        // On va ajouter le benchmark à la liste des benchmarks pour cette machine support s'il n'y est pas encore
        if(!current_platform_all_benchmarks.includes(benchmark_name)){
            current_platform_all_benchmarks.push(benchmark_name);
        }

        // On va ajouter le moteur de recherche à la liste des moteurs de recherche pour cette machine support s'il n'y est pas encore
        if(!current_platform_all_engine_configs.includes(search_engine_name)){
            current_platform_all_engine_configs.push(search_engine_name);
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

        if(benchmark_result != undefined && benchmark_result["avg_score"] != undefined){
            score = parseFloat(parseFloat(benchmark_result["avg_score"]).toFixed(4));
            scores.push(score);
        }
        if(benchmark_result != undefined && benchmark_result["total_benchmark_time"] != undefined){
            speed = parseFloat(parseFloat(benchmark_result["total_benchmark_time"]).toFixed(4));
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
    document.getElementById("benchmark_details_rbi").innerText = benchmark["rbi_path"];
    document.getElementById("benchmark_details_nb_searchs").innerText = benchmark["searchs"].length;
    document.getElementById("benchmark_details_searchs").innerHTML = "";

    for(search of benchmark["searchs"]){

        var div_search = document.createElement("div");
        div_search.classList.add("benchmark_details_search", "col", "left_align");

        var span_search_input = document.createElement("span");
        span_search_input.innerText = search["search_input"];
        span_search_input.classList.add("m_5p", "left_align");
        div_search.appendChild(span_search_input);

        var div_row_bottom = document.createElement("div");
        div_row_bottom.classList.add("row", "left_align", "w_100");

        var span_awaited_msg_id_label = document.createElement("span");
        span_awaited_msg_id_label.innerText = "Id du message attendu : "
        span_awaited_msg_id_label.classList.add("left_align", "m_5p", "flex", "font_small");
        div_row_bottom.appendChild(span_awaited_msg_id_label);

        var span_awaited_msg_id = document.createElement("span");
        span_awaited_msg_id.innerText = search["awaited_result_message"];
        span_awaited_msg_id.classList.add("left_align", "m_5p", "m_r_auto", "flex", "font_small");
        div_row_bottom.appendChild(span_awaited_msg_id);

        var empty_separation_div = document.createElement("div");
        empty_separation_div.classList.add("flex", "flexgrow_1");
        div_row_bottom.appendChild(empty_separation_div);

        var span_user_id_label = document.createElement("span");
        span_user_id_label.innerText = "Id de l'utilisateur : "
        span_user_id_label.classList.add("right_align", "m_5p", "m_l_auto", "flex", "font_small");
        div_row_bottom.appendChild(span_user_id_label);

        var span_user_id = document.createElement("span");
        span_user_id.innerText = search["user_id"];
        span_user_id.classList.add("right_align", "m_5p", "flex", "font_small");
        div_row_bottom.appendChild(span_user_id);

        div_search.appendChild(div_row_bottom);

        document.getElementById("benchmark_details_searchs").appendChild(div_search);
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
    if(engine_config["max_message_length"] <= 0){
        document.getElementById("benchmark_engine_config_max_msg_length").innerText = "pas de limite";
    }
    else{
        document.getElementById("benchmark_engine_config_max_msg_length").innerText = engine_config["max_message_length"];
    }
    if(engine_config["nb_threads"] > 1){
        document.getElementById("benchmark_engine_config_nb_threads").innerText = engine_config["nb_threads"] + " threads";
    }
    else{
        document.getElementById("benchmark_engine_config_nb_threads").innerText = "unique thread, pas de parallélisation";
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


// On ajoute le message correspondant au résultat de la recherche
function add_search_result(result_id, distance, msg_res_id, msg_res_data, benchmark_awaited_results){

    if(msg_res_data == undefined){
        msg_res_data = {
            "id": "[NULL]",
            "date": "[NULL]",
            "content": "[NULL]",
            "author_id": "[NULL]",
            "author_name": "[NULL]",
            "bubble_id": "[NULL]"
        }
    }

    // On récupère les infos qu'on a besoin
    var date = msg_res_data["date"];

    //
    var search_result_div = document.createElement("div");
    search_result_div.classList.add("search_result", "col");

    //
    if(typeof(benchmark_awaited_results) == "number"){
        if(msg_res_data["id"] == benchmark_awaited_results){
            search_result_div.classList.add("good_search_result");
        }
    }
    else if(typeof(benchmark_awaited_results) == "object"){
        for(bar of benchmark_awaited_results){
            console.log("DEBUG | bar = ", bar, " | msg_res_data[\"id\"] = ", msg_res_data["id"]);
            if(String(bar) == String(msg_res_data["id"])){
                search_result_div.classList.add("good_search_result");
                break;
            }
        }
    }

    var row1 = document.createElement("span");
    var span_distance = document.createElement("span");
    span_distance.innerText = distance;
    row1.appendChild(span_distance);
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
    span_msg_id.innerText = " msg id : " + msg_res_data["id"];
    row1.appendChild(span_msg_id);

    row2 = document.createElement("span");
    row2.innerText = msg_res_data["content"];

    search_result_div.appendChild(row1);
    search_result_div.appendChild(row2);

    document.getElementById("benchmark_result_div_msgs").appendChild(search_result_div);
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
    document.getElementById("benchmark_result_score").innerText = benchmark_result["avg_score"];
    document.getElementById("benchmark_result_total_time").innerText = benchmark_result["total_benchmark_time"];
    document.getElementById("benchmark_result_div_absolute_scores").innerHTML = "";

    var i;
    for(i=0; i<benchmark_result["absolute_scores"].length; i++){

        var score_search = benchmark_result["absolute_scores"][i];
        var time_search = parseFloat(benchmark_result["search_times"][i]).toFixed(4);

        var div_score = document.createElement("div");
        div_score.classList.add("benchmark_result_absolute_score", "clickable");
        div_score.setAttribute("onclick", "display_result_search_details(\""+benchmark_name+"\", \"" + engine_name + "\", " + i + ");");

        var span_score = document.createElement("span")
        span_score.innerText = score_search;
        span_score.classList.add("m_auto", "font_smaller");
        if(score_search < 0){
            span_score.classList.add("very_bad_value");
        }
        if(score_search <= 1){
            span_score.classList.add("good_value");
        }
        else if(score_search <= 3){
            span_score.classList.add("acceptable_value");
        }
        else if(score_search <= 5){
            span_score.classList.add("bad_value");
        }
        else{
            span_score.classList.add("very_bad_value");
        }
        div_score.appendChild(span_score);

        var span_time = document.createElement("span");
        span_time.style.display = "none";
        span_time.classList.add("m_auto", "m_l_5p", "font_smaller");
        span_time.innerText = "(" + time_search + " sec)";
        div_score.appendChild(span_time);

        document.getElementById("benchmark_result_div_absolute_scores").appendChild(div_score);
    }

    // Nettoyage des résultats précédents
    document.getElementById("benchmark_result_div_msgs").innerHTML = "";
    //
    document.getElementById("benchmark_result_search_input").innerText = "___";


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
function display_result_search_details(benchmark_name, engine_name, search_idx){

    // On récupère l'élément sur lequel on va afficher les détails
    var benchmark_result_id = get_benchmark_result_id_from_benchmark_name_engine_name_and_current_plaform(benchmark_name, engine_name);
    var benchmark_result = benchmarks_all_support_platforms[current_support_platform][benchmark_result_id];

    // Nettoyage des résultats précédents
    document.getElementById("benchmark_result_div_msgs").innerHTML = "";

    //
    document.getElementById("benchmark_result_search_input").innerText = benchmarks[benchmark_name]["searchs"][search_idx]["search_input"];

    //
    benchmark_awaited_results = benchmarks[benchmark_name]["searchs"][search_idx]["awaited_result_message"];

    //
    for(i=0; i<benchmark_result["result_ids"][search_idx].length; i++){

        var msg_res_distance = benchmark_result["result_ids"][search_idx][i][0]
        var msg_res_id = benchmark_result["result_ids"][search_idx][i][1];
        if(typeof(msg_res_id) == "object"){
            msg_res_id = msg_res_id[0];
        }
        if(typeof(msg_res_id) == "number" || typeof(msg_res_id) == "string"){
            var msg_res_data = benchmark_result["result_msgs"][msg_res_id];
            if(msg_res_data == undefined && Number.isInteger(msg_res_id)){
                msg_res_data = benchmark_result["result_msgs"][parseInt(msg_res_id)];
            }
            add_search_result(i, msg_res_distance, msg_res_id, msg_res_data, benchmark_awaited_results);
        }
        else{
            console.error("ERROR | msg_res_id is no string or number (msg_res_id=", msg_res_id, ")");
        }
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
