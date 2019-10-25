
function adminInit() {
   refreshData();
   setInterval(refreshData, 2000);
}

function approve(name) {
   $("#nameField").val(name);
   $("input[name=pos][value='normal']").prop("checked",true);
}

function deleteName(name) {
   $("#nameField").val(name);
   $("input[name=pos][value='remove']").prop("checked",true);
}

function selectPhone(p) {
   $("#to").val(p);
}

function secondsPast(ts) {
   var d = new Date();
   var seconds = d.getTime() / 1000;

   var diff = Math.floor(seconds - ts);
   msg = "";
   if (diff < 90) {
      msg = " (" + diff + " sec.)";
   } else {
      diff = Math.round(diff/60);
      msg = " (" + diff + " min.)";
   }

   return msg;
}

function updateOutHistory(q) {
   html = []
   q.forEach(function(obj) {
      actions = [];
      html.push('<div class="row">');
      html.push('<div class="col">');
      html.push(obj.message);
      html.push('</div><div class="col">');
      html.push(obj.phone);
      html.push(secondsPast(obj.ts));
      html.push("</div></div>");
   });
   $("#outHistory").html(html.join(''));
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
      html.push('</div><div class="col"><a href="javascript:selectPhone(\'');
      html.push(obj.phone);
      html.push('\')">');
      html.push(obj.phone);
      html.push('</a></div><div class="col">');
      html.push(actions.join(''));
      html.push(secondsPast(obj.ts));

      html.push('</div></div>\n');
   });
   $("#textHistory").html(html.join(''));
}

function updateQueue(ready, q, qLow) {
   html = []
   ready.forEach(function(name) {
      url = "javascript:deleteName('" + name + "')";
      html.push('<div class="row">');
      html.push('<div class="col gjh-ready">');
      html.push(name);
      html.push('</div>');
      html.push('</div>\n');
   });
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
   qLow.forEach(function(name) {
      url = "javascript:deleteName('" + name + "')";
      html.push('<div class="row">');
      html.push('<div class="col lowPriority">');
      html.push(name);
      html.push('</div><div class="col"><a href="');
      html.push(url)
      html.push('">Remove</a></div>');
      html.push('</div>\n');
   });
   $("#queue").html(html.join(''));
   $("#queueSize").text(ready.length + ", " + q.length + ", " + qLow.length);
   //console.log(q.length);
}

function refreshDebug(data){
   var last_name = Math.round((Date.now() - new Date(data.model.health.lastnamePlay))/60000);
   var html = []
   html.push('<table><tr><th>Status</th><td>');
   html.push(data.model.health.status)
   html.push('</td></tr><tr><th>Last name</th><td>');
   html.push(last_name);
   html.push(' mins.</td></tr>');
   html.push('<tr><th>Enabled</th><td>');
   html.push(data.model.current.enabled);
   html.push(' <a href="/setEnabled?enabled=');
   html.push(! data.model.current.enabled);
   html.push('">Toggle</a>');
   html.push('</td></tr><tr><th>Debug:</th><td>')
   html.push(data.model.current.debug);
   html.push(' <a href="/setDebug?debug=');
   html.push(! data.model.current.debug);
   html.push('">Toggle</a>');
   html.push('</td></tr></table>');
   $("#debug").html(html.join(''));

}

function refreshData() {
   //console.log('Refresh');
   var jqxhr = $.getJSON( "/queueData", function() {
     //console.log( "Scheduled" );
   }).done(function(data) {
     //console.log( data );
     $("#lastRefresh").html(new Date().toLocaleString());
     updateQueue(data.ready, data.queue, data.queueLow);
     updateHistory(data.history);
     updateOutHistory(data.outPhone);
   }).fail(function() {
      alert('Error quering server');
      console.log( "Error quering server" );
  }).always(function() {
      //console.log( "complete - Always" );
  });

  var jqxhr = $.getJSON( "https://vote-now.org/api/queue", function() {
   //console.log( "Scheduled" );
 }).done(function(data) {
    refreshDebug(data);    
 }).fail(function() {
    alert('Error quering vote-now');
    $("#debug").html('Error');
    console.log( "Error quering vote-now" );
}).always(function() {
    //console.log( "complete - Always" );
});

 
}
