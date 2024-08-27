

// Escape Bad Html Characters
function escapeHtml(text) {
    if(!(typeof text === 'string' || text instanceof String)){
        return "";
    }

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

// Returns the minimum value between two values.
function min(a, b){
    if(a <= b){
        return a;
    }
    return b;
}

// Returns the minimum value of a list
function min_lst(lst){
    if(lst.length == 0){
        return Infinity;
    }
    var min_v = lst[0];
    for(i=1; i<lst; i++){
        if(min_v == null || (lst[i] != null && lst[i] < min_v)){
            min_v = lst[i];
        }
    }
    //
    return min_v;
}

// Clamp a value between min and max
function clamp(value, min_v, max_v){
    if(value < min_v){
        return min_v;
    }
    if(value > max_v){
        return max_v;
    }
    return value;
}

//
function randomNumber(min, max) {
    return Math.random() * (max - min) + min;
}

//
const cl_intervals = [0.0, 155.0];
const freq = 2.24;
const base = 1.32;
//
function get_rgb_bg_fg_from_conv_id(conv_id){
    //
    var i = base + conv_id * 3;
    var cl = [];
    //
    for(j = 0; j < 3; j++){
        cl.push( cl_intervals[0] + ((Math.sin(i) + 1.0) / 2.0) * (cl_intervals[1] - cl_intervals[0]) );
        i += freq;
    }
    //
    return {
        "fg": "rgba("+cl[0]+", "+cl[1]+", "+cl[2]+", 1)",
        "bg": "rgba("+cl[0]+", "+cl[1]+", "+cl[2]+", 0.1)"
    }
}

//
function createSvgNode(node_element_name, parameters) {
    var node = document.createElementNS("http://www.w3.org/2000/svg", node_element_name);
    for (var param_key in parameters){
        node.setAttributeNS(null, param_key, parameters[param_key]);
    }
    return node;
}

//
function get_svg_point_graph_coordinate(px, py, min_x, max_x, min_y, max_y, width, height, arrow_size){
    const spx = arrow_size + width * ((px - min_x) / (max_x - min_x));
    const spy = arrow_size + height * (1.0 - ((py - min_y) / (max_y - min_y)));
    return {
        "x": spx,
        "y": spy
    };
}

//
function get_svg_path_point_graph_coordinate(px, py, min_x, max_x, min_y, max_y, width, height, arrow_size){
    var r = get_svg_point_graph_coordinate(px, py, min_x, max_x, min_y, max_y, width, height, arrow_size);
    return " " + r["x"] + " " + r["y"];
}

//
function generate_2d_svg_graph(points_curves, min_x, max_x, min_y, max_y, width=150, height=100, arrow_size=5, contour_stroke_width=2, points_stroke_width=2, points_circle_radius=4, animated_points={}, point_colors=["purple", "orange", "blue", "grey", "cyan"]){

    //
    if(min_x == max_x){
        min_x -= 0.1;
        max_x += 0.1;
    }
    if(min_y == max_y){
        min_y -= 0.1;
        max_y += 0.1;
    }

    //
    var main_svg_graph_node = createSvgNode("svg", {
        "viewBox": "0 0 " + (width+2*arrow_size) + " " + (height+2*arrow_size)
    });

    //
    var svg_out_graph_lines = createSvgNode("path", {
        "d": "M 0 " + arrow_size + " L " + arrow_size + " 0 L " + (2*arrow_size) + " " + arrow_size + " M " + arrow_size + " 0 L " + arrow_size + " " + height + " L " + (width + arrow_size) + " " + height + " M "+width+" "+(height - arrow_size)+" L "+(width + arrow_size)+" "+height+" L "+width+" " + (height + arrow_size),
        "stroke": "black",
        "stroke-width": ""+contour_stroke_width,
        "fill": "none",
        "fill-opacity":"0"
    });
    main_svg_graph_node.appendChild(svg_out_graph_lines);

    //
    for(var d=0; d < points_curves.length; d++){
        //
        var points = points_curves[d];

        //
        var points_path = "";
        var i = 0;
        for(pt of Object.keys(points)){
            if(i==0){
                points_path += "M" + get_svg_path_point_graph_coordinate(pt, points[pt]["y"], min_x, max_x, min_y, max_y, width-(arrow_size*2), height-(arrow_size), arrow_size);
            }
            else{
                points_path += "L" + get_svg_path_point_graph_coordinate(pt, points[pt]["y"], min_x, max_x, min_y, max_y, width-(arrow_size*2), height-(arrow_size), arrow_size);
            }
            i++;
        }

        //
        var svg_points = createSvgNode("path", {
            "d": points_path,
            "stroke": point_colors[d % point_colors.length],
            "stroke-width": ""+points_stroke_width,
            "stroke-dasharray": "2,1",
            "fill": "none"
        });
        main_svg_graph_node.appendChild(svg_points);

        //
        for(pt of Object.keys(points)){
            //
            var r = get_svg_point_graph_coordinate(pt, points[pt]["y"], min_x, max_x, min_y, max_y, width-(arrow_size*2), height-(arrow_size), arrow_size);

            //
            var pointCircle = createSvgNode("circle", {
                "cx": "" + r["x"],
                "cy": "" + r["y"],
                "r": points_circle_radius,
                "color": point_colors[d % point_colors.length]
            });

            //
            var pointText = createSvgNode("text", {
                "x": "" + (r["x"] - 50),
                "y": "" + (r["y"] - 20),
                "font-family": "Verdana",
                "color": "black",
                "font-size": 16,
                "text": "(" + points[pt]["x"] + ", " + points[pt]["y"] + ")"
            });
            pointText.innerHTML = "(" + points[pt]["x"] + ", " + points[pt]["y"] + ")";

            //
            pointCircle.classList.add("svg_graph_point");
            pointCircle.appendChild(pointText);

            //
            if(pt in animated_points && animated_points[pt]){
                pointCircle.classList.add("graph_animated_point");
            }

            //
            main_svg_graph_node.appendChild(pointCircle);
        }
    }

    //
    return main_svg_graph_node;
}

