<h2>{{graph_name}}</h2>
%graph_id = graph_name.replace('.','').replace('-','_') # disallowed in var names
%import json
        <div class="chart_container flot" id="chart_container_flot_{{graph_id}}">
            <div class="chart" id="chart_flot_{{graph_id}}" height="300px" width="700px"></div>
            <div class="legend" id="legend_flot_{{graph_id}}" height="300px" width="50px" style="height:300px; width: 50px"></div>
            <form class="toggler" id="line_stack_form_flot_{{graph_id}}"></form>
        </div>
        <script language="javascript">
	    $(document).ready(function () {
		var graph_data = {{!json.dumps(graph_data)}};
		var defaults = {
		    url: "{{graphite_url}}/render/",
		    from: "-24hours",
		    until: "now",
		    height: "300",
		    width: "740",
		    line_stack_toggle: 'line_stack_form_flot_{{graph_id}}',
		    series: {stack: true, lines: { show: true, lineWidth: 0, fill: true }},
		    xaxis: { mode: "time" },
		    legend: { container: '#legend_flot_{{graph_id}}', noColumns: 1 },
		};
		var graph_flot_{{graph_id}} = $.extend({}, defaults, graph_data);
	        $("#chart_flot_{{graph_id}}").graphiteFlot(graph_flot_{{graph_id}}, function(err) { console.log(err); });
	});
        </script>
