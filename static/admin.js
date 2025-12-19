song_count = 0;
warning_count = 0;

function adminInit() {
  refreshData();
  setInterval(refreshData, 2000);
}

function approve(name, phone) {
  $("#nameField").val(name);
  $("#notifyField").val(phone);
  $("input[name=pos][value='normal']").prop("checked", true);
}

function deleteName(name) {
  $("#nameField").val(name);
  $("input[name=pos][value='remove']").prop("checked", true);
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
    msg = " (" + diff + " sec)";
  } else {
    diff = Math.round(diff / 60);
    msg = " (" + diff + " min)";
  }

  return msg;
}

function updateOutHistory(q) {
  html = [];
  q.forEach(function (obj) {
    html.push('<div class="row">');
    html.push('<div class="col">');
    html.push(obj.message);
    html.push('</div><div class="col">');
    html.push(obj.phone);
    html.push(secondsPast(obj.ts));
    html.push("</div></div>");
  });
  $("#outHistory").html(html.join(""));
}

function updateBlocked(q) {
  html = [];
  q.forEach(function (obj) {
    url = "/removeBlock?phone=" + encodeURIComponent(obj.phone);
    html.push('<div class="row">');
    html.push('<div class="col">');
    html.push(obj.phone);
    html.push(' <a href="');
    html.push(url);
    html.push('">del</a>');
    html.push('</div><div class="col">');
    html.push(secondsPast(obj.ts));
    html.push("/");
    html.push(obj.length);
    html.push(" min</div></div>");
  });
  $("#blockHistory").html(html.join(""));
}

function updateHistory(q) {
  html = [];
  q.forEach(function (obj) {
    actions = [];
    html.push('<div class="row">');
    html.push('<div class="col');
    if (obj.blocked) {
      html.push(" blockedName");
    }
    if (!obj.valid) {
      html.push(" invalidName");
      actions.push("<a href=\"javascript:approve('");
      actions.push(encodeURIComponent(obj.name.replace("'", "").replace(" []", "")));
      actions.push("', '");
      actions.push(encodeURIComponent(obj.phone));
      actions.push("')\">Add</a>");
    }
    html.push('">');
    html.push(obj.name);
    html.push('</div><div class="col"><a href="javascript:selectPhone(\'');
    html.push(obj.phone);
    html.push("')\">");
    html.push(obj.phone);
    html.push('</a>')
    html.push('</div><div class="col">');
    html.push(actions.join(""));
    html.push(' ');
    html.push(obj.recent);
    html.push(' ');
    html.push(secondsPast(obj.ts));

    html.push("</div></div>\n");
  });
  $("#textHistory").html(html.join(""));
}

function formatName(html, nameObj, className) {
  var name = nameObj.name;
  var url = "javascript:deleteName('" + encodeURIComponent(name) + "')";
  html.push('<div class="row">');
  html.push('<div class="col-6">');
  html.push('<span class="');
  html.push(className);
  html.push('">');
  html.push(name);
  html.push("</span> ");
  html.push('</div><div class="col-4">');
  html.push(secondsPast(nameObj.ts));
  html.push('</div><div class="col-2"><a href="');
  html.push(url);
  html.push('">DEL</a></div>');
  html.push("</div>\n");
}

function updateQueue(ready, q, qLow) {
  var html = [];
  ready.forEach(function (nameObj) {
    formatName(html, nameObj, "gjh-ready");
  });
  q.forEach(function (nameObj) {
    formatName(html, nameObj, '""');
  });
  qLow.forEach(function (nameObj) {
    formatName(html, nameObj, "lowPriority");
  });
  $("#queue").html(html.join(""));
  $("#queueSize").text(ready.length + ", " + q.length + ", " + qLow.length);

}

function refreshSong(data) {
  if (data.status === "idle") {
    $("#current-song").html("Idle");
    return;
  }
  var html = [];
  html.push(data.title);
  html.push(": ");
  html.push(data.secondsRemaining);
  html.push(" / ");
  html.push(data.secondsTotal);
  $("#current-song").html(html.join(""));
}

function updateWarnings(warnings) {
  html = "<li>OK</li>"
  warning_count = warnings.length;
  if (warning_count > 0) {
    html = "";
    for (w of warnings) {
      html += "<li>"
      html += w
      html +='</li>'
    }
  }
  $("#fppd_warnings").html(html);
}

function refreshDebug(data) {
  var last_name = Math.round(
    (Date.now() - new Date(data.model.health.lastnamePlay)) / 60000
  );
  $("#current-api-status").html(data.model.health.status + " (" + warning_count + ")");
  //console.log(data.model)
  if (data.model.health.status == "ALL_OK" && warning_count == 0) {
    $("#current-api-status").removeClass("gjh-warning");
  } else {
    $("#current-api-status").addClass("gjh-warning");
  }

  var html = [];
  html.push("<table><tr><th>Status</th><td>");
  html.push(data.model.health.status);
  html.push("</td></tr><tr><th>Name Status</th><td>");
  html.push(data.model.current.nameStatus);
  html.push("</td></tr><tr><th>Last name</th><td>");
  html.push(last_name);
  html.push(' mins. <a href="/setNameGen" ');
  html.push('" onclick="return confirm(\'Are you sure?\');">Gen name</a>');
  html.push(" </td></tr>");

  html.push("<tr><th>Show Enabled</th><td>");
  html.push(data.model.current.enabled);
  html.push(' <a href="/setEnabled?enabled=');
  html.push(!data.model.current.enabled);
  html.push('" onclick="return confirm(\'Are you sure?\');">Toggle</a>');

  html.push("</td></tr><tr><th>Show Skip Time:</th><td>");
  html.push(data.model.current.debug);
  html.push(' <a href="/setDebug?debug=');
  html.push(!data.model.current.debug);
  html.push('" onclick="return confirm(\'Are you sure?\');">Toggle</a>');

  html.push("</td></tr><tr><th>Short Show:</th><td>");
  html.push(data.model.current.isShortList);
  html.push(' <a href="/setShortShow?short=');
  html.push(!data.model.current.isShortList);
  html.push('" onclick="return confirm(\'Are you sure?\');">Toggle</a>');

  html.push("</td></tr></table>");
  $("#debug").html(html.join(""));
}

function refreshClockDebug(data, popcorn) {
  var html = [];
  html.push("<table>");
  html.push("<tr><th>Debug:</th><td>");
  html.push(data.debug);
  html.push(' <a href="/setClockDebug?debug=');
  html.push(!data.debug);
  html.push('" onclick="return confirm(\'Are you sure?\');">Toggle</a>');

   html.push("<tr><th>Popcorn:</th><td>");
  html.push(popcorn);
  html.push(' <a href="/setPopcorn?popcorn=');
  html.push(!popcorn);
  html.push('" onclick="return confirm(\'Are you sure?\');">Toggle</a>');

  html.push("</td></tr><tr><th>Timecheck:</th><td>");
  html.push(data.skipTime);
  html.push(' <a href="/setClockSkip?skip=');
  html.push(!data.skipTime);
  html.push('" onclick="return confirm(\'Are you sure?\');">Toggle</a>');

  html.push("</td></tr></table>");
  $("#clockdebug").html(html.join(""));
}

function updateInternal(songList, admin_song) {
  if (songList.length != song_count) {
    html = [];
    for (const song of songList) {
      html.push('<OPTION value="');
      html.push(song);
      html.push('">');
      html.push(song);
      html.push("</option>");
      $("#nextSong").html(html.join(""));
      song_count = songList.length;
    }
  }

  if (!admin_song) {
    admin_song = "No Song Scheduled";
  } else {
    admin_song = "Next Scheduled: " + admin_song;
  }
  $("#nextAdminSong").text(admin_song);
}

function refreshData() {
  //console.log('Refresh');
  var jqxhr = $.getJSON("/queueData", function () {
    //console.log( "Scheduled" );
  })
    .done(function (data) {
      //console.log(data);
      $("#lastRefresh").html(new Date().toLocaleString());
      updateQueue(data.ready, data.queue, data.queueLow);
      updateHistory(data.history);
      updateBlocked(data.blocked);
      updateOutHistory(data.outPhone);
      refreshClockDebug(data.timeinfo, data.popcorn);
      updateInternal(data.internal_songs, data.admin_song);
      updateWarnings(data.fppdWarnings);
    })
    .fail(function () {
      $("#current-api-status").html("Last query to queueData failed");
      $("#current-api-status").addClass("gjh-warning");
      console.log("Error quering server");
    })
    .always(function () {
      //console.log( "complete - Always" );
    });

  var jqxhr = $.getJSON("https://vote-now.org/api/model", function () {
    //console.log( "Scheduled" );
  })
    .done(function (data) {
      refreshDebug(data);
      refreshSong(data.model.current);
    })
    .fail(function () {
      $("#current-api-status").html("Last query to vote-now failed");
      $("#current-api-status").addClass("gjh-warning");
      $("#debug").html("Error");
      console.log("Error quering vote-now");
    })
    .always(function () {
      //console.log( "complete - Always" );
    });
}
