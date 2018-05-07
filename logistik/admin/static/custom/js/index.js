$(document).ready(function () {
    $('#handlers').DataTable({
        "paging": false,
        "info": false,
        "searching": false,
        "order": [[ 0, "desc" ]]
    });

    $('#stats').DataTable({
        "paging": false,
        "info": false,
        "order": [[ 0, "desc" ]]
    });
});
