sort_ol = $("#ordered");
itemsCount = $("#ordered ul").length;

var newItem = `
    <li class="ui-state-default">
      <span>&#x21C5;</span><input type="text"/>
    </li>
`;

function updateIndexes() {
  $("#ordered.outer input:hidden")
    .each(function (i) {
      $(this).val(i + 1);
      li = $(this).parent();
      var evenOrOdd = ( i % 2 === 0 ) ? "even" : "odd";
      var innerClass = "flex-container inner " + evenOrOdd;
      li.children(".inner").each(function () {
        $(this).attr("class", innerClass);
      });
    });
}

updateIndexes();

sort_ol.sortable({
  handle: ".drag",
  stop: function (event, ui) {
    updateIndexes();
  },
});

$("#addol").click(function () {
  sort_ol.append(newItem);
  updateIndexes();
});

$("#ordered.outer input:hidden").keyup(function (event) {
  if (event.keyCode == "13") {
    event.preventDefault();

    order = parseInt($(this).val());

    li = $(this).parent();

    if (order >= 1 && order <= itemsCount) {
      li.effect("drop", function () {
        li.detach();

        if (order == itemsCount) sort_ol.append(li);
        else li.insertBefore($("#ordered.outer li:eq(" + (order - 1) + ")"));

        updateIndexes();
        li.effect("slide");
      });
    } else {
      li.effect("highlight");
    }
  }
});
