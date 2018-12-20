
function adminInit() {
   refreshData();
}

function approve(name) {
   $("#nameField").val(name);
   $("input[name=pos][value='normal']").prop("checked",true);
}

function deleteName(name) {
   $("#nameField").val(name);
   $("input[name=pos][value='remove']").prop("checked",true);
}

function updateHistory(q) {
   html = []
   q.forEach(function(obj) {
      actions = [];
      html.push('<div class="row">');
      html.push('<div class="col');
      if (! obj.valid) {
         html.push(" invalidName");
         actions.push('<a href="javascript:approve(\'');
         actions.push(obj.name);
         actions.push('\')">Add</a>');
      }
      html.push('">');
      html.push(obj.name);
      html.push('</div><div class="col">');
      html.push(obj.phone);
      html.push('</div><div class="col">');
      html.push(actions.join(''));

      html.push('</div></div>\n');
   });
   $("#textHistory").html(html.join(''));
}

function updateQueue(q) {
   html = []
   q.forEach(function(name) {
      url = "javascript:deleteName('" + name + "')";
      html.push('<div class="row">');
      html.push('<div class="col">');
      html.push(name);
      html.push('</div><div class="col"><a href="');
      html.push(url)
      html.push('">Remove</a></div>');
      html.push('</div>\n');
   });
   $("#queue").html(html.join(''));
   $("#queueSize").text(q.length);
   console.log(q.length);
}

function refreshData() {
   var jqxhr = $.getJSON( "/queueData", function() {
     console.log( "Scheduled" );
   }).done(function(data) {
     console.log( data );
     updateQueue(data.queue);
     updateHistory(data.history);
   }).fail(function() {
      alert('Error');
      console.log( "error" );
  }).always(function() {
      console.log( "complete - Always" );
  });
 
}
