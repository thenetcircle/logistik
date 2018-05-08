$(document).ready(function () {
    $('#handlers').DataTable({
        'paging': false,
        'info': false,
        'searching': false,
        'order': [[ 0, 'desc' ]]
    });

    $('#stats').DataTable({
        'paging': false,
        'info': false,
        'order': [[ 0, 'desc' ]]
    });

    $('#aggregated').DataTable({
        'paging': false,
        'info': false,
        'order': [[ 0, 'desc' ]]
    });

    var agg_stats = {};
    var n_stat_nodes = 0;

    $.getJSON('http://localhost:5656/api/stats/aggregated', function (data) {
      $.each(data.data, function(key, s) {
        if (agg_stats[s.service_id] === undefined) {
          agg_stats[s.service_id] = new Array();
        }
        agg_stats[s.service_id].push(s);
        console.log(s);
        n_stat_nodes++;
      });
    }).then($.getJSON('http://localhost:5656/api/handlers', function (data) {
      $('#graph').remove();
      $('#graph-container').html('<div id="graph"></div>');

      var s = new sigma('graph');

      s.graph.addNode({
        id: '0',
        label: 'logistik',
        x: 0,
        y: (n_stat_nodes - 1) / 2,
        size: 1,
        color: '#00f'
      });

      var handler_iter = 0;
      var total_stat_iter = 0;
      var n_handler_nodes = data.data.length;
      $.each(data.data, function (key, h) {
        var color = '#f00';
        if (h.enabled) {
          color = '#ff0'
        }

        var handler_y = handler_iter * (n_stat_nodes / n_handler_nodes) + 1;
        console.log('handler_y: ' + handler_y + ', handler_iter: ' + handler_iter);
        s.graph.addNode({
          id: h.identity,
          label: h.service_id,
          x: 1,
          y: handler_y,
          size: 1,
          color: color
        });
        s.graph.addEdge({
          id: 'e' + h.identity,
          source: '0',
          target: h.identity
        });

        if (agg_stats[h.service_id] === undefined) {
          console.log('no stats for service_id: ' + h.service_id);
        }
        else {
          var stats_iter = 0;
          $.each(agg_stats[h.service_id], function(s_key, stat) {
            var node_id = h.identity + '-' + stats_iter;
            var y_value = total_stat_iter++;
            s.graph.addNode({
              id: node_id,
              label: stat.stat_type + ': ' + stat.count,
              x: 2,
              y: y_value,
              size: 1,
              color: color
            });
            s.graph.addEdge({
              id: 'e' + node_id,
              source: h.identity,
              target: node_id
            });
            stats_iter++;
          });
        }
        handler_iter++;
      });

      s.refresh();
    }));
});
