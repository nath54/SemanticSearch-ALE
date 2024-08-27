/*
_summary_

Auteur: Nathan Cerisara
*/


const container_results = document.getElementById("container_results");
const margin = 15;
const task_box_height = 20;

const line_stroke = 1.5;
const border_height = 10;
const border_width = 2;
const font_size = 12;

var task_hover = null;

var current_task_name_viewer = "";
var current_id_exec_task_name_viewer = 0;

var current_zoom = 1.0;

//
document.body.onresize = function (event){
    display_tasks_lines(current_task_name_viewer);
}

//
function min(a, b){
    if(a <= b){
        return a;
    }
    return b;
}

//
function max(a, b){
    if(a >= b){
        return a;
    }
    return b;
}

//
function clean(){
    container_results.innerHTML = "";
}

//
function escapeHtml(text) {
    const map = {
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
    };

    text=text.toLowerCase();

    for(c of Object.keys(map)){
        while(text.includes(c)){
            text = text.replace(c, map[c]);
        }
    }

    return text;
}

//
function task_name_to_css_attribute(task_name){
    var res = "task_name_" + escapeHtml(task_name);
    return res;
}

//
function truncate_task_name(task_name){
    var i = task_name.indexOf("_|");
    if(i == -1){
        return task_name;
    }
    else{
        return task_name.substring(0, i);
    }
}

//
function create_line(height, time_start, time_end, custom_time_fraction=1.0){

    var line = document.createElement("div");
    line.style.position = "absolute";
    line.style.left = "" + margin + "px";
    if(custom_time_fraction != 1.0){
        line.style.width = "" + ((container_results.offsetWidth - 2*margin)*custom_time_fraction) + "px";
    }
    else{
        line.style.right = "" + margin + "px";
    }
    line.style.top = "" + height + "px";
    line.style.height = "" + line_stroke + "px";
    line.style.backgroundColor = "white";

    var left_border = document.createElement("div");
    left_border.style.position = "absolute";
    left_border.style.left = "" + (margin - border_width / 2.0) + "px";
    left_border.style.top = "" + (height - (border_height / 2.0 - line_stroke / 2.0)) + "px"
    left_border.style.width = "" + border_width + "px";
    left_border.style.height = "" + border_height + "px";
    left_border.style.backgroundColor = "white";

    var left_border_text = document.createElement("span");
    left_border_text.style.position = "absolute";
    left_border_text.style.top = "" + (height + (border_height / 2.0) + font_size + 5) + "px"
    left_border_text.style.left = "" + (margin - 5) + "px";
    left_border_text.classList.add("font_small");
    left_border_text.innerText = "" + time_start + " sec"

    var right_border = document.createElement("div");
    right_border.style.position = "absolute";
    right_border.style.right = "" + (margin - border_width / 2.0) + "px";
    right_border.style.top = "" + (height - (border_height / 2.0 - line_stroke / 2.0)) + "px"
    right_border.style.width = "" + border_width + "px";
    right_border.style.height = "" + border_height + "px";
    right_border.style.backgroundColor = "white";

    var right_border_text = document.createElement("span");
    right_border_text.style.position = "absolute";
    right_border_text.style.top = "" + (height + (border_height / 2.0) + font_size + 5) + "px"
    right_border_text.style.right = "" + (margin - 5) + "px";
    right_border_text.classList.add("font_small");
    right_border_text.innerText = "" + time_end + " sec"

    container_results.appendChild(line);
    container_results.appendChild(left_border);
    container_results.appendChild(right_border);
    container_results.appendChild(left_border_text);
    container_results.appendChild(right_border_text);

}

//
function create_task_box(task_name, id_exec, time_start, time_end, line_time_start, line_time_end, line_height, tl_line=0, color="purple", enable_click=true){

    const line_width = container_results.offsetWidth - 2*margin;
    const tot_line_time = line_time_end - line_time_start;
    var left_position = 0;
    var box_time_start = line_time_start;
    if(time_start > line_time_start){
        left_position = ((time_start - line_time_start) / tot_line_time) * line_width;
        box_time_start = time_start;
    }

    var task_box = document.createElement("div");
    task_box.classList.add(task_name_to_css_attribute(task_name));
    task_box.style.border = "1px solid black";
    task_box.style.overflow = "hidden";
    task_box.style.position = "absolute";
    task_box.style.left = "" + (margin + left_position) + "px";
    //

    task_box.style.width = "" + (((min(time_end, line_time_end) - box_time_start) / tot_line_time) * line_width) + "px";

    //
    task_box.style.height = "" + task_box_height + "px";
    task_box.style.top = "" + (line_height - task_box_height * (tl_line+1) - line_stroke) + "px";
    task_box.style.backgroundColor = color;
    if(enable_click){
        task_box.setAttribute("onmouseenter", "task_hover_start(\""+task_name+"\", "+id_exec+");");
        task_box.setAttribute("onmouseout", "task_hover_stop(\""+task_name+"\");");
        task_box.setAttribute("onclick", "task_page(\"" + task_name + "\");");
    }

    var span_task_box = document.createElement("span");
    span_task_box.classList.add("center_v", "center_h");
    span_task_box.classList.add("font_small");
    span_task_box.style.backgroundColor = "none";
    span_task_box.style.background = "none";
    span_task_box.innerText = truncate_task_name(task_name);

    task_box.appendChild(span_task_box);

    container_results.appendChild(task_box);
}

//
function times_collide(start_t1, end_t1, start_t2, end_t2){

    if(start_t1 >= start_t2){
        if(start_t1 < end_t2){
            return true;
        }
        return false;
    }
    else{
        if(end_t1 >= start_t2){
            return true;
        }
        return false;
    }
}

//
function display_tasks_lines(){
    // On nettoie l'affichage
    clean();

    if(current_task_name_viewer == ""){
        if(results_data["session_name"] != ""){
            document.getElementById("page_title").innerText = "Profiling Result : global timeline";
        } else{
            document.getElementById("page_title").innerText = "Profiling Result : " + results_data["session_name"];
        }
    }
    else{
        document.getElementById("page_title").innerText = "Profiling Result : " + truncate_task_name(current_task_name_viewer) + " - execution n° "+ current_id_exec_task_name_viewer + "/" + (results_data["tasks"][current_task_name_viewer]["task_executions_starts"].length - 1);
    }

    // On va récupérer toutes les tâches que nous allons traiter
    //   Va contenir (task_name, id_exec)
    var tasks_names = [];

    //
    var min_time = null;
    var max_time = null;

    //
    if(current_task_name_viewer == ""){
        min_time = results_data["time_app_started"];
        max_time = results_data["time_app_finished"];
    }
    else{
        min_time = results_data["tasks"][current_task_name_viewer]["task_executions_starts"][current_id_exec_task_name_viewer];
        max_time = results_data["tasks"][current_task_name_viewer]["task_executions_ends"][current_id_exec_task_name_viewer][0];
    }

    // Pour cela, on parcours toutes les sous-tâches de la tâche actuelle
    for(task_name of Object.keys(results_data["tasks"])){
        //
        for(id_exec=0; id_exec < results_data["tasks"][task_name]["task_executions_starts"].length; id_exec++){
            if(results_data["tasks"][task_name]["task_executions_parent_tasks"][id_exec][0] == current_task_name_viewer){
                tasks_names.push([task_name, id_exec]);
            }
        }
    }

    if(max_time <= min_time){
        max_time = min_time + 0.0001;
    }

    //
    if(min_time == null || max_time == null || max_time <= min_time){
        alert("Erreur dans les données!");
        stop();
    }

    // On va calculer le temps d'une time_line.
    const time_tot = max_time - min_time;

    // Cas où l'on a pas de sous-tâches
    if(tasks_names.length == 0){

        // On ne va afficher qu'une seule ligne
        create_line(100, min_time, max_time);

        // On va afficher un blank élément dessus
        var name = current_task_name_viewer;
        if(name == ""){
            name = results_data["session_name"];
            //
            if(name == ""){
                name = "Your Application"
            }
        }

        create_task_box(name, 0, min_time, max_time, min_time, max_time, 100, 0, color="grey", enable_click=false);

        container_results.style.height = "400px";

        return;
    }

    // S'il y a des tâches

    // Unité de temps de base, quel intervalle de temps par ligne
    const line_time_unit = (max_time - min_time) / current_zoom;

    if(line_time_unit <= 0){
        alert("Erreur ligne de temps : " + line_time_unit);
        return;
    }

    var times_lines_intervals = []
    var times_lines_nb_lignes = []
    var times_lines_tasks_executions = [] // Va contenir des tuples (task_name, id_exec, ligne)

    var crt_time = min_time;
    while(crt_time < max_time){

        end_interval = min(crt_time + line_time_unit, max_time);

        times_lines_intervals.push([crt_time, end_interval]);

        crt_time += line_time_unit;

        times_lines_tasks_executions.push([]);
        times_lines_nb_lignes.push(1);
    }

    // On va grouper toutes les activités qu'il y a pour chaque ligne de temps

    // Pour cela, on va parcourir chaque ligne de temps
    for(id_time_line=0; id_time_line < times_lines_intervals.length; id_time_line++){

        // Chaque couple (tâche, id_exec) qu'il faudra afficher
        for(id_te=0; id_te < tasks_names.length; id_te++){
            //
            var task_name = tasks_names[id_te][0];
            var id_exec = tasks_names[id_te][1];
            //
            var task = results_data["tasks"][task_name];
            //
            if( times_collide(
                task["task_executions_starts"][id_exec],
                task["task_executions_ends"][id_exec][0],
                times_lines_intervals[id_time_line][0],
                times_lines_intervals[id_time_line][1]
            )
            ){

                var tasks_lines_collisions = [];
                for(i=0; i<times_lines_nb_lignes[id_time_line]; i++){
                    tasks_lines_collisions.push(false);
                }

                // On va chercher la bonne ligne qui ne collisionne pas avec les autres tâches
                for(tlte of times_lines_tasks_executions[id_time_line]){
                    if( times_collide(
                            task["task_executions_starts"][id_exec],
                            task["task_executions_ends"][id_exec][0],
                            results_data["tasks"][tlte[0]]["task_executions_starts"][tlte[1]],
                            results_data["tasks"][tlte[0]]["task_executions_ends"][tlte[1]]
                    ) ){
                        tasks_lines_collisions[tlte[2]] = true;
                    }
                }

                var first_dispo_task_line = -1;

                for(i=0; i<tasks_lines_collisions.length; i++){
                    if(!tasks_lines_collisions[i]){
                        first_dispo_task_line = i;
                        break;
                    }
                }

                // S'il n'y a plus de lignes disponibles
                if(first_dispo_task_line == -1){
                    // On va en créer une nouvelle
                    first_dispo_task_line = times_lines_nb_lignes[id_time_line];
                    times_lines_nb_lignes[id_time_line]++;
                }

                //
                times_lines_tasks_executions[id_time_line].push([task_name, id_exec, first_dispo_task_line]);

            }
        }

    }

    // On va afficher chaque ligne

    var current_height = 10;

    // Pour cela, on va parcourir chaque ligne de temps
    for(id_time_line=0; id_time_line < times_lines_intervals.length; id_time_line++){

        // On va calculer sa hauteur
        current_height += (50 + times_lines_nb_lignes[id_time_line] * task_box_height);

        var t_start = times_lines_intervals[id_time_line][0];
        var t_end = times_lines_intervals[id_time_line][1];

        create_line(current_height, t_start, t_end, (t_end - t_start) / line_time_unit);

        // On va afficher les tasks box

        for(itbe of times_lines_tasks_executions[id_time_line]){

            //
            var task = results_data["tasks"][itbe[0]];

            create_task_box(
                task_name=itbe[0],
                id_exec=itbe[1],
                time_start=task["task_executions_starts"][itbe[1]],
                time_end=task["task_executions_ends"][itbe[1]][0],
                line_time_start=t_start,
                line_time_end=t_end,
                line_height=current_height,
                tl_line=itbe[2]
            )
        }

    }


    container_results.style.height = "" + (current_height + 300) + "px";

}

//
function main_page(){
    //
    current_task_name_viewer = "";
    current_id_exec_task_name_viewer = 0;
    //
    display_tasks_lines();
}

//
function task_page(task_name, id_exec=0){
    //
    current_task_name_viewer = task_name;
    current_id_exec_task_name_viewer = id_exec
    //
    display_tasks_lines();
}

//
function go_to_parent_task(){
    if(current_task_name_viewer != ""){
        //
        try{
            current_task_name_viewer = results_data["tasks"][current_task_name_viewer]["task_executions_parent_tasks"][current_id_exec_task_name_viewer][0];
            current_id_exec_task_name_viewer = results_data["tasks"][current_task_name_viewer]["task_executions_parent_tasks"][current_id_exec_task_name_viewer][1];
            //
            display_tasks_lines();
        } catch {
            main_page();
        }
    }else{
        main_page();
    }
}

//
function zoom(){
    current_zoom += 1.0;
    //
    display_tasks_lines();
}

//
function un_zoom(){
    if(current_zoom > 1.0){
        current_zoom -= 1.0;
        //
        display_tasks_lines();
    }
}

//
function reset_zoom(){
    current_zoom = 10.0;
    //
    display_tasks_lines();
}

//
function task_hover_start(task_name, id_exec){
    // console.log("task name = ", task_name);
    //
    if(task_hover != null){
        for(n of document.getElementsByClassName(task_name_to_css_attribute(task_hover))){
            n.classList.remove("white_aura");
            n.classList.remove("white_aura");
        }
    }
    //
    task_hover = task_name;
    document.getElementById("task_hover_div").style.display = "flex";
    document.getElementById("task_hover_name").innerText = truncate_task_name(escapeHtml(task_name));
    document.getElementById("task_hover_duration").innerText = (results_data["tasks"][task_name]["task_executions_ends"][id_exec][0] - results_data["tasks"][task_name]["task_executions_starts"][id_exec]);
    //
    for(n of document.getElementsByClassName(task_name_to_css_attribute(task_hover))){
        n.classList.add("white_aura");
    }
}

//
function task_hover_stop(task_name){

    // task_hover = null;
    // document.getElementById("task_hover_div").style.display = "none";

}

