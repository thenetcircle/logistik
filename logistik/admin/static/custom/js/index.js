$(document).ready(function () {
    $('#handlers').DataTable({
        'order': [[ 0, 'desc' ]]
    });

    $('#stats').DataTable({
        'order': [[ 0, 'desc' ]]
    });

    $('#aggregated').DataTable({
        'order': [[ 0, 'desc' ]]
    });

    $('#models').DataTable({
        'order': [[ 0, 'desc' ]]
    });

    $('#events').DataTable({
        'order': [[ 0, 'desc' ]],
        'bFilter': false,
        'bInfo': false
    });

    $('#consumers').DataTable({
        'order': [[ 0, 'desc' ]]
    });

    $('#timings').DataTable({
        'order': [[ 0, 'desc' ]]
    });

    $('#consul-services').DataTable({
        'order': [[ 2, 'desc' ]]
    });

    function secondsToString(seconds) {
        var n_days = Math.floor(seconds / 86400);
        var n_hours = Math.floor((seconds % 86400) / 3600);
        var n_minutes = Math.floor(((seconds % 86400) % 3600) / 60);
        var n_seconds = ((seconds % 86400) % 3600) % 60;
        if (n_days === 0 && n_hours === 0) {
            return n_minutes + "m " + n_seconds + "s";
        }
        if (n_days === 0) {
            return n_hours + "h " + n_minutes + "m " + n_seconds + "s";
        }
        return n_days + "d " + n_hours + "h " + n_minutes + "m " + n_seconds + "s";
    }

    $.each($('.uptime'), function(idx, el) {
        el.innerHTML = secondsToString(el.innerHTML);
    });

    $.getJSON(document.location + '/api/graph', function (graph) {
      var nodes = graph.data['nodes'];
      var edges = graph.data['edges'];

      nodes[0]['shape'] = 'box';
      nodes[0]['color'] = '#FFA807';

      var container = document.getElementById('network');
      var data = {
        nodes: nodes,
        edges: edges
      };
      var options = {
        physics: true,
        layout:{
          randomSeed: 42
        },
        nodes: {
        },
        edges: {
          font: {
            face: 'Roboto',
            align: 'bottom'
          },
          arrows: 'to'
        },
        groups: {
          model: {
            shape: 'icon',
            icon: {
              face: 'FontAwesome',
              code: '\uf085',
              size: 30
            }
          },
          canary: {
              color: '#D0BB57'
          },
          service: {
            shape: 'icon',
            icon: {
              face: 'FontAwesome',
              code: '\uf233',
              size: 30
            }
          },
          success: {
            shape: 'icon',
            icon: {
              face: 'FontAwesome',
              code: '\uf058',
              size: 30
            }
          },
          error: {
            shape: 'icon',
            icon: {
              face: 'FontAwesome',
              code: '\uf057',
              size: 30
            }
          },
          failure: {
            shape: 'icon',
            icon: {
              face: 'FontAwesome',
              code: '\uf06a',
              size: 30
            }
          }
        }
      };
      new vis.Network(container, data, options);
    });

    /*
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
            //var y_value = handler_iter + stats_iter - (Object.keys(agg_stats).length-1)/2;
            var y_value = total_stat_iter++;
            //y_value /= handler_iter + 1;
            console.log('y_value: ' + y_value);
            console.log(stat);
            console.log('n_stat_nodes: ' + n_stat_nodes);
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
    */
});
