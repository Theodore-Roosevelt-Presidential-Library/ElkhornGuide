/* Elkhorn Ranch Walking Guide
   Theodore Roosevelt Presidential Library
   Map + GPS + compass guide to the eight NPS Elkhorn Ranch tour stops. Works offline. */
(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };
  var params = new URLSearchParams(location.search);
  var SIM = params.has('sim');                 // tap the map to fake a position (staff preview)
  var IN_FRAME = window.self !== window.top;
  var STORE = 'trpl-elkhorn-guide-v1';
  var NAIP_BOUNDS = [[47.2325, -103.6315], [47.2445, -103.6175]];
  var FAR_METERS = 2500;                       // beyond this, guide you to the trailhead first

  var data = null, map = null, meMarker = null, accCircle = null, stopMarkers = [];
  var pos = null, heading = null, headingSource = null, gpsHeading = null;
  var state = load();
  var watchId = null, wakeLock = null, storyIndex = null, compassOn = false;

  function load() {
    try { return Object.assign({ next: 0, visited: [] }, JSON.parse(localStorage.getItem(STORE) || '{}')); }
    catch (e) { return { next: 0, visited: [] }; }
  }
  function save() { try { localStorage.setItem(STORE, JSON.stringify(state)); } catch (e) {} }

  /* ---------- geometry ---------- */
  var R = 6371000, rad = Math.PI / 180;
  function dist(a, b) {
    var dLat = (b.lat - a.lat) * rad, dLon = (b.lon - a.lon) * rad;
    var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }
  function bearing(a, b) {
    var y = Math.sin((b.lon - a.lon) * rad) * Math.cos(b.lat * rad);
    var x = Math.cos(a.lat * rad) * Math.sin(b.lat * rad) -
      Math.sin(a.lat * rad) * Math.cos(b.lat * rad) * Math.cos((b.lon - a.lon) * rad);
    return (Math.atan2(y, x) / rad + 360) % 360;
  }
  function fmtDist(m) {
    var ft = m * 3.28084;
    if (ft < 30) return 'Here';
    if (ft < 1000) return Math.round(ft / 10) * 10 + ' ft';
    var mi = m / 1609.344;
    return (mi < 10 ? mi.toFixed(1) : Math.round(mi)) + ' mi';
  }
  var DIRS = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'];
  function compassWord(b) { return DIRS[Math.round(b / 45) % 8]; }

  /* ---------- toast ---------- */
  var toastTimer;
  function toast(msg, ms) {
    var t = $('toast'); t.textContent = msg; t.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { t.hidden = true; }, ms || 3200);
  }

  /* ---------- screens ---------- */
  function show(id) {
    ['start', 'nav'].forEach(function (s) { $(s).hidden = s !== id; });
    if (id === 'nav' && map) setTimeout(function () { map.invalidateSize(); fitToTarget(); }, 80);
  }

  /* ---------- data ---------- */
  fetch('data/stops.json').then(function (r) { return r.json(); }).then(function (d) {
    data = d;
    $('approachBody').innerHTML = d.approach.body;
    $('approachLink').href = d.approach.directionsUrl;
    $('credits').textContent = d.credits;
    buildList();
    checkOffline();
    if (params.has('stop')) { var n = parseInt(params.get('stop'), 10); if (n >= 1 && n <= 8) openStory(n - 1); }
  }).catch(function () { toast('The guide could not load. Check your connection and try again.', 6000); });

  /* ---------- map ---------- */
  function divIcon(cls, html, size) {
    return L.divIcon({ className: '', html: '<div class="' + cls + '">' + (html || '') + '</div>', iconSize: [size, size], iconAnchor: [size / 2, size / 2] });
  }
  function initMap() {
    if (map) return;
    map = L.map('map', { zoomControl: false, attributionControl: true, maxZoom: 19, minZoom: 9 });
    L.control.zoom({ position: 'bottomright' }).addTo(map);
    L.tileLayer('https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}', {
      maxNativeZoom: 16, maxZoom: 19, attribution: 'USGS The National Map'
    }).addTo(map);
    L.imageOverlay('map/naip.jpg', NAIP_BOUNDS, { attribution: 'Aerial: USGS NAIP' }).addTo(map);

    var line = [[data.parking.lat, data.parking.lon]].concat(data.stops.map(function (s) { return [s.lat, s.lon]; }));
    L.polyline(line, { color: '#ffffff', weight: 7, opacity: .85 }).addTo(map);
    L.polyline(line, { color: '#E7805D', weight: 4, dashArray: '2 8', lineCap: 'round' }).addTo(map);

    L.marker([data.parking.lat, data.parking.lon], { icon: divIcon('park-marker', 'P', 28), keyboard: false })
      .addTo(map).bindTooltip('Parking area and trailhead');
    data.stops.forEach(function (s, i) {
      var m = L.marker([s.lat, s.lon], { icon: divIcon('stop-marker', s.n, 30), title: 'Stop ' + s.n + ': ' + s.title })
        .addTo(map).on('click', function () { openStory(i); });
      stopMarkers.push(m);
    });
    map.fitBounds(L.latLngBounds(line).pad(0.15));
    if (SIM) {
      map.on('click', function (e) { onPosition({ coords: { latitude: e.latlng.lat, longitude: e.latlng.lng, accuracy: 5, heading: null, speed: 0 } }); });
      toast('Preview mode: tap the map to set your position.', 4000);
    }
    refreshMarkers();
  }
  function refreshMarkers() {
    stopMarkers.forEach(function (m, i) {
      var el = m.getElement() && m.getElement().firstChild; if (!el) return;
      el.className = 'stop-marker' + (state.visited.indexOf(i) > -1 ? ' done' : '') + (i === state.next ? ' next' : '');
    });
  }

  /* ---------- location ---------- */
  function startGPS() {
    if (SIM) { $('status').textContent = 'Preview mode: tap the map to move.'; return; }
    if (!('geolocation' in navigator)) { $('status').textContent = 'This device cannot share its location. Use the map and the stop list.'; return; }
    if (watchId !== null) return;
    watchId = navigator.geolocation.watchPosition(onPosition, function (err) {
      $('status').textContent = err.code === 1
        ? 'Location is turned off for this page. Allow location in your browser settings to use the compass and map.'
        : 'Waiting for a GPS fix. Open sky helps.';
    }, { enableHighAccuracy: true, maximumAge: 2000, timeout: 30000 });
  }
  function onPosition(p) {
    var c = p.coords;
    pos = { lat: c.latitude, lon: c.longitude, acc: c.accuracy || 20 };
    if (c.heading !== null && !isNaN(c.heading) && c.speed > 0.6) gpsHeading = c.heading;
    if (map) {
      var ll = [pos.lat, pos.lon];
      if (!meMarker) {
        meMarker = L.marker(ll, { icon: divIcon('me-marker', '', 20), interactive: false, zIndexOffset: 1000 }).addTo(map);
        accCircle = L.circle(ll, { radius: pos.acc, color: '#2a7de1', weight: 1, fillOpacity: .12, interactive: false }).addTo(map);
        update(); fitToTarget(); return;
      } else { meMarker.setLatLng(ll); accCircle.setLatLng(ll).setRadius(pos.acc); }
    }
    update();
  }
  // Frame you and the place you're heading.
  function fitToTarget() {
    if (!map || !pos) return;
    var t = target(); if (!t) return;
    var dest = t.kind === 'done' ? data.parking : t;
    map.fitBounds(L.latLngBounds([[pos.lat, pos.lon], [dest.lat, dest.lon]]), { padding: [60, 60], maxZoom: 18 });
  }

  /* ---------- compass ---------- */
  function enableCompass() {
    var go = function () {
      if ('ondeviceorientationabsolute' in window) window.addEventListener('deviceorientationabsolute', onOrient, true);
      window.addEventListener('deviceorientation', onOrient, true);
      compassOn = true; $('btnCompass').hidden = true;
      setTimeout(function () { if (heading === null && window.matchMedia('(pointer: coarse)').matches) toast('No compass reading. The arrow will assume north is up.', 4500); }, 3000);
    };
    if (typeof DeviceOrientationEvent !== 'undefined' && typeof DeviceOrientationEvent.requestPermission === 'function') {
      DeviceOrientationEvent.requestPermission().then(function (r) {
        if (r === 'granted') go(); else toast('Compass permission was not granted.');
      }).catch(function () { toast('Compass is not available here. Open the guide full screen and try again.', 5000); });
    } else go();
  }
  function screenAngle() {
    return (screen.orientation && typeof screen.orientation.angle === 'number') ? screen.orientation.angle : (window.orientation || 0);
  }
  function onOrient(e) {
    var h = null;
    if (typeof e.webkitCompassHeading === 'number' && !isNaN(e.webkitCompassHeading)) { h = e.webkitCompassHeading; headingSource = 'ios'; }
    else if (e.absolute && typeof e.alpha === 'number') { h = 360 - e.alpha; headingSource = 'abs'; }
    else if (headingSource) return;            // ignore relative readings once we have absolute ones
    if (h === null) return;
    h = (h + screenAngle() + 360) % 360;
    if (heading === null) heading = h;
    else { var d = ((h - heading + 540) % 360) - 180; heading = (heading + d * 0.25 + 360) % 360; }
    paintCompass();
  }

  /* ---------- guidance ---------- */
  var arrivedFor = -1, lastBearing = 0, lastDist = null;
  function target() {
    if (!data) return null;
    if (pos && dist(pos, data.parking) > FAR_METERS && state.next === 0) {
      return { kind: 'park', lat: data.parking.lat, lon: data.parking.lon, title: 'Elkhorn Ranch parking area' };
    }
    if (state.next >= data.stops.length) return { kind: 'done' };
    var s = data.stops[state.next];
    return { kind: 'stop', i: state.next, lat: s.lat, lon: s.lon, title: s.title, n: s.n };
  }
  function update() {
    var t = target(); if (!t) return;
    if (t.kind === 'done') {
      $('targetLabel').textContent = 'Walk complete';
      $('targetTitle').textContent = 'Head back to the trailhead';
      $('dist').textContent = pos ? fmtDist(dist(pos, data.parking)) : '';
      $('dir').textContent = '';
      $('btnRead').textContent = 'Read the last stop';
      $('btnSkip').hidden = true;
      if (pos) { lastBearing = bearing(pos, data.parking); lastDist = dist(pos, data.parking); }
      paintCompass(); return;
    }
    $('btnSkip').hidden = t.kind !== 'stop';
    if (t.kind === 'park') {
      $('targetLabel').textContent = 'First, drive to the trailhead';
      $('targetTitle').textContent = 'Elkhorn Ranch parking';
      $('btnRead').textContent = 'Driving directions';
    } else {
      $('targetLabel').textContent = 'Stop ' + t.n + ' of ' + data.stops.length;
      $('targetTitle').textContent = t.title;
      $('btnRead').textContent = 'Read this stop';
    }
    if (!pos) { $('dist').textContent = '—'; $('dir').textContent = ''; return; }
    var d = dist(pos, t), b = bearing(pos, t);
    lastBearing = b; lastDist = d;
    $('dist').textContent = fmtDist(d);
    $('dir').textContent = d * 3.28084 >= 30 ? compassWord(b) : '';
    var accTxt = pos.acc > 25 ? ' GPS accuracy is about ' + Math.round(pos.acc * 3.28084) + ' ft.' : '';
    if (t.kind === 'park') {
      $('status').textContent = 'Straight-line distance. The drive is about 46 miles from the Library, 30 of them on gravel.';
    } else {
      $('status').textContent = (d < 60 ? 'Almost there.' : 'Follow the mowed path.') + accTxt;
      var arriveR = Math.min(30, Math.max(18, pos.acc * 0.8));
      if (d <= arriveR && arrivedFor !== t.i) {
        arrivedFor = t.i;
        markVisited(t.i);
        if (navigator.vibrate) navigator.vibrate([120, 60, 120]);
        toast('You have reached Stop ' + t.n + ': ' + t.title);
        openStory(t.i);
      }
    }
    paintCompass();
  }
  function paintCompass() {
    var c = $('compass'), arrow = $('arrow'), dial = $('dial');
    var h = heading !== null ? heading : gpsHeading;
    c.classList.toggle('no-heading', h === null);
    c.classList.toggle('arrived', lastDist !== null && lastDist * 3.28084 < 30);
    var rot = h === null ? lastBearing : lastBearing - h;
    arrow.style.transform = 'rotate(' + rot + 'deg)';
    dial.style.transform = 'rotate(' + (h === null ? 0 : -h) + 'deg)';
  }
  function markVisited(i) {
    if (state.visited.indexOf(i) < 0) state.visited.push(i);
    save(); refreshMarkers(); buildList();
  }

  /* ---------- story ---------- */
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]; }); }
  function quoteHTML(q) { return q ? '<blockquote><p>“' + esc(q.text) + '”</p><cite>' + esc(q.cite) + '</cite></blockquote>' : ''; }
  function openStory(i) {
    if (!data) return;
    storyIndex = i;
    var s = data.stops[i];
    $('storyScroll').innerHTML =
      '<figure class="story-photo"><img src="' + s.image + '" alt="' + esc(s.imageAlt) + '"><figcaption>' + esc(s.imageCredit) + '</figcaption></figure>' +
      '<div class="story-inner">' +
      '<div class="story-num">Stop ' + s.n + ' of ' + data.stops.length + '</div>' +
      '<h2>' + esc(s.title) + '</h2>' +
      '<p class="lede">' + esc(s.lede) + '</p>' +
      s.body + quoteHTML(s.quote) + (s.after || '') + quoteHTML(s.quote2) + (s.closing || '') +
      (s.source ? '<p class="story-source">' + esc(s.source) + '</p>' : '') +
      '</div>';
    $('storyScroll').scrollTop = 0;
    $('btnPrev').disabled = i === 0;
    $('btnNext').textContent = i < data.stops.length - 1 ? 'Next stop →' : 'Finish';
    $('list').hidden = true;
    $('story').hidden = false;
    var u = new URL(location.href); u.searchParams.set('stop', s.n); history.replaceState(null, '', u);
  }
  function closeStory() {
    $('story').hidden = true; storyIndex = null;
    var u = new URL(location.href); u.searchParams.delete('stop'); history.replaceState(null, '', u);
  }
  function nextFromStory() {
    var i = storyIndex;
    markVisited(i);
    if (i >= state.next) { state.next = i + 1; save(); }
    closeStory();
    if (i >= data.stops.length - 1) {
      toast('That is the last stop. The trailhead is about 0.7 mile back the way you came.', 5000);
    }
    if (!$('nav').hidden) { refreshMarkers(); update(); fitToTarget(); }
    else if (i < data.stops.length - 1) openStory(i + 1);
  }

  /* ---------- list ---------- */
  function buildList() {
    if (!data) return;
    $('listItems').innerHTML = data.stops.map(function (s, i) {
      return '<li class="' + (state.visited.indexOf(i) > -1 ? 'done' : '') + '"><button data-i="' + i + '">' +
        '<img src="' + s.image + '" alt="" loading="lazy"><span><span class="ln">Stop ' + s.n + '</span>' +
        '<span class="lt">' + esc(s.title) + '</span><span class="ld">' + esc(s.lede) + '</span></span></button></li>';
    }).join('');
  }
  $('listItems').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-i]'); if (b) openStory(+b.dataset.i);
  });

  /* ---------- offline ---------- */
  function checkOffline() {
    if (!('caches' in window)) return;
    caches.keys().then(function (keys) {
      var ok = keys.some(function (k) { return k.indexOf('elkhorn-full') === 0; });
      $('offlinePill').hidden = !ok;
      if (ok) { $('btnOffline').textContent = 'Saved for offline ✓'; $('offlineNote').textContent = 'The map, photos and stories are saved on this device.'; }
    });
  }
  function saveOffline() {
    if (!('serviceWorker' in navigator)) { toast('This browser cannot save the guide for offline use.'); return; }
    $('btnOffline').disabled = true; $('btnOffline').textContent = 'Saving…';
    navigator.serviceWorker.ready.then(function (reg) {
      var ch = new MessageChannel();
      ch.port1.onmessage = function (ev) {
        $('btnOffline').disabled = false;
        if (ev.data && ev.data.ok) { toast('Saved. The guide will work without signal.'); checkOffline(); }
        else { $('btnOffline').textContent = 'Save for offline'; toast('Some files could not be saved. Try again with a stronger signal.', 5000); }
      };
      reg.active.postMessage({ type: 'save-offline' }, [ch.port2]);
    });
  }
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(function () {});
  }

  /* ---------- full screen + wake lock ---------- */
  function fullScreen() {
    var el = document.documentElement;
    if (document.fullscreenElement || document.webkitFullscreenElement) {
      (document.exitFullscreen || document.webkitExitFullscreen).call(document); return;
    }
    var req = el.requestFullscreen || el.webkitRequestFullscreen;
    if (req) { req.call(el).catch(function () { openStandalone(); }); }
    else if (IN_FRAME) openStandalone();
    else toast('For full screen on iPhone, tap Share, then Add to Home Screen.', 5000);
  }
  function openStandalone() { window.open(location.href.replace(/([?&])embed=1&?/, '$1'), '_blank', 'noopener'); }
  function keepAwake() {
    if (!('wakeLock' in navigator)) return;
    navigator.wakeLock.request('screen').then(function (l) { wakeLock = l; }).catch(function () {});
  }
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible' && !$('nav').hidden) keepAwake();
  });

  /* ---------- wire up ---------- */
  function begin() {
    initMap(); show('nav'); startGPS(); keepAwake(); update();
    if (typeof DeviceOrientationEvent !== 'undefined' && typeof DeviceOrientationEvent.requestPermission !== 'function') enableCompass();
  }
  $('btnBegin').addEventListener('click', begin);
  $('btnOffline').addEventListener('click', saveOffline);
  $('btnPreview').addEventListener('click', function () { $('list').hidden = false; });
  $('btnList').addEventListener('click', function () { $('list').hidden = false; });
  $('btnCloseList').addEventListener('click', function () { $('list').hidden = true; });
  $('btnFull').addEventListener('click', fullScreen);
  $('btnCompass').addEventListener('click', enableCompass);
  $('btnRecenter').addEventListener('click', function () { if (pos && map) map.setView([pos.lat, pos.lon], Math.max(map.getZoom(), 17)); else if (map) toast('Waiting for your location.'); });
  $('btnRead').addEventListener('click', function () {
    var t = target();
    if (t && t.kind === 'park') window.open(data.approach.directionsUrl, '_blank', 'noopener');
    else if (t && t.kind === 'stop') openStory(t.i);
    else openStory(data.stops.length - 1);
  });
  $('btnSkip').addEventListener('click', function () {
    if (state.next < data.stops.length) { state.next++; save(); refreshMarkers(); update(); fitToTarget(); }
  });
  $('btnPrev').addEventListener('click', function () { if (storyIndex > 0) openStory(storyIndex - 1); });
  $('btnNext').addEventListener('click', nextFromStory);
  $('btnMap').addEventListener('click', function () { closeStory(); if ($('nav').hidden) begin(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { if (!$('story').hidden) closeStory(); $('list').hidden = true; } });
  if (params.has('embed')) document.documentElement.classList.add('embedded');
  if (SIM) setTimeout(begin, 400);
})();
