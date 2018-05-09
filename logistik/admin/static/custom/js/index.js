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

    $.getJSON('http://localhost:5656/api/graph', function (graph) {
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
        groups: {
          model: {
            shape: 'icon',
            icon: {
              face: 'FontAwesome',
              code: '\uf085',
              size: 30
            }
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
        },
        nodes: {
          shape: 'dot'
        },
        edges: {
          font: {
            align: 'bottom'
          },
          arrows: 'to'
        }
      };
      new vis.Network(container, data, options);
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
});
