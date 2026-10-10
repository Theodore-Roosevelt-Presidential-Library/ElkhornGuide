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
      if (err.code === 1) {
        $('status').textContent = 'Location is blocked for this page, so the map cannot show where you are.';
        $('btnStatusHelp').hidden = false;
      } else $('status').textContent = 'Waiting for a GPS fix. Open sky helps.';
    }, { enableHighAccuracy: true, maximumAge: 2000, timeout: 30000 });
  }
  function onPosition(p) {
    var c = p.coords;
    pos = { lat: c.latitude, lon: c.longitude, acc: c.accuracy || 20 };
    checkPrecision(pos.acc);
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
  function enableCompass(cb) {
    cb = cb || function () {};
    var go = function () {
      if ('ondeviceorientationabsolute' in window) window.addEventListener('deviceorientationabsolute', onOrient, true);
      window.addEventListener('deviceorientation', onOrient, true);
      compassOn = true; $('btnCompass').hidden = true; cb('on');
      setTimeout(function () { if (heading === null && window.matchMedia('(pointer: coarse)').matches) toast('No compass reading. The arrow will assume north is up.', 4500); }, 3000);
    };
    if (typeof DeviceOrientationEvent !== 'undefined' && typeof DeviceOrientationEvent.requestPermission === 'function') {
      DeviceOrientationEvent.requestPermission().then(function (r) {
        if (r === 'granted') go(); else { cb('denied'); toast('Compass permission was not granted. The arrow will assume north is up.', 4500); }
      }).catch(function () { cb('error'); toast('Compass is not available here. Open the guide full screen and try again.', 5000); });
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
      $('status').textContent = preciseWarned
        ? 'Your phone is sharing an approximate location, so stops will not open on their own. Tap Read this stop when you get there.'
        : (d < 60 ? 'Almost there.' : 'Follow the mowed path.') + accTxt;
      var arriveR = Math.min(30, Math.max(18, pos.acc * 0.8));
      // Only auto-open a stop on a reasonably precise fix.
      if (pos.acc <= 60 && d <= arriveR && arrivedFor !== t.i) {
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
        if (ev.data && ev.data.ok) {
          checkOffline();
          locPermission().then(function (st) {
            if (st === 'granted' && (!NEEDS_COMPASS_ASK || compassOn)) toast('Saved. The guide will work without signal.');
            else { toast('Saved. Now set up location and the compass while you can read the prompts.', 4500); openPerm('setup', st); }
          });
        }
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


  /* ---------- permissions: explain, ask, recover ---------- */
  var UA = navigator.userAgent;
  var IS_IOS = /iPad|iPhone|iPod/.test(UA) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var IS_ANDROID = /Android/.test(UA);
  var BROWSER = /CriOS/.test(UA) ? 'chrome-ios' : /FxiOS/.test(UA) ? 'firefox-ios' : /EdgiOS/.test(UA) ? 'edge-ios'
    : IS_IOS ? 'safari' : /SamsungBrowser/.test(UA) ? 'samsung' : /Firefox/.test(UA) ? 'firefox' : /Edg\//.test(UA) ? 'edge'
    : /Chrome/.test(UA) ? 'chrome' : /Safari/.test(UA) ? 'safari-mac' : 'other';
  var HAS_ORIENT = typeof DeviceOrientationEvent !== 'undefined';
  var NEEDS_COMPASS_ASK = HAS_ORIENT && typeof DeviceOrientationEvent.requestPermission === 'function';
  var permMode = 'start', helpTopic = 'blocked';

  function locPermission() {
    if (!navigator.permissions || !navigator.permissions.query) return Promise.resolve('unknown');
    return navigator.permissions.query({ name: 'geolocation' }).then(function (r) { return r.state; }, function () { return 'unknown'; });
  }
  function setStep(id, stateId, cls, msg) {
    $(id).classList.toggle('done', cls === 'ok');
    var s = $(stateId); s.textContent = msg || ''; s.classList.toggle('bad', cls === 'bad');
  }
  function openPerm(mode, locState) {
    permMode = mode;
    $('btnPermGo').textContent = mode === 'start' ? 'Continue to the guide' : 'Done';
    $('btnPermClose').hidden = mode !== 'start';
    if (locState === 'granted') { setStep('stepLoc', 'locState', 'ok', 'Location is on.'); $('btnAskLoc').hidden = true; }
    else if (locState === 'denied') { helpTopic = 'blocked'; setStep('stepLoc', 'locState', 'bad', 'Location is blocked for this page. Your phone will not ask again until you switch it back on.'); $('btnAskLoc').textContent = 'Show me how'; $('btnAskLoc').hidden = false; }
    else { setStep('stepLoc', 'locState', '', ''); $('btnAskLoc').textContent = 'Allow location'; $('btnAskLoc').hidden = false; }
    if (!HAS_ORIENT || !window.matchMedia('(pointer: coarse)').matches) {
      $('stepCompass').hidden = true;
    } else if (!NEEDS_COMPASS_ASK) {
      $('stepCompass').hidden = false;
      $('compassExplain').textContent = 'Your phone’s compass turns on by itself. If the arrow seems off, wave the phone in a figure eight to calibrate it.';
      $('btnAskCompass').hidden = true; setStep('stepCompass', 'compassState', 'ok', 'Ready.');
    } else {
      $('stepCompass').hidden = false;
      if (compassOn) { $('btnAskCompass').hidden = true; setStep('stepCompass', 'compassState', 'ok', 'Compass is on.'); }
      else { $('btnAskCompass').hidden = false; setStep('stepCompass', 'compassState', '', ''); }
    }
    $('preciseTip').hidden = !IS_IOS;
    $('perm').hidden = false; $('perm').scrollTop = 0;
  }
  function askLocation() {
    if ($('btnAskLoc').textContent === 'Show me how') { openHelp(helpTopic); return; }
    if (!('geolocation' in navigator)) { setStep('stepLoc', 'locState', 'bad', 'This browser cannot share location. You can still read every stop.'); return; }
    $('btnAskLoc').disabled = true; $('btnAskLoc').textContent = 'Waiting for your answer…';
    navigator.geolocation.getCurrentPosition(function (p) {
      $('btnAskLoc').disabled = false; $('btnAskLoc').hidden = true;
      if (p.coords.accuracy > 500) {
        setStep('stepLoc', 'locState', 'bad', 'Location is on, but your phone is sharing only an approximate location. Turn on Precise Location so the guide knows when you reach a stop.');
        $('btnAskLoc').hidden = false; $('btnAskLoc').textContent = 'Show me how'; helpTopic = 'precise';
      } else setStep('stepLoc', 'locState', 'ok', 'Location is on.');
    }, function (err) {
      $('btnAskLoc').disabled = false;
      if (err.code === 1) {
        setStep('stepLoc', 'locState', 'bad', IS_IOS && BROWSER === 'safari'
          ? 'Location was blocked. If you never saw a prompt, location may be off for Safari on this iPhone.'
          : 'Location was blocked.');
        $('btnAskLoc').textContent = 'Show me how'; helpTopic = 'blocked';
      } else {
        setStep('stepLoc', 'locState', 'ok', 'Location is allowed. Your phone is still finding a GPS fix; that is normal indoors.');
        $('btnAskLoc').hidden = true;
      }
    }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
  }
  function askCompass() {
    enableCompass(function (r) {
      if (r === 'on') { $('btnAskCompass').hidden = true; setStep('stepCompass', 'compassState', 'ok', 'Compass is on.'); }
      else setStep('stepCompass', 'compassState', 'bad', 'The compass was not allowed. The guide still works: the arrow will assume north is up. To try again, close this tab, reopen the guide and tap Allow.');
    });
  }

  // Step-by-step recovery, by phone and browser.
  var HELP = {
    'safari': { name: 'iPhone, Safari', steps: [
      'Tap the <strong>aA</strong> (or page-settings) button at the left of the address bar.',
      'Tap <strong>Website Settings</strong>.',
      'Set <strong>Location</strong> to <strong>Allow</strong>.',
      'Reload the page, then tap <strong>Start the walking guide</strong>.'],
      note: 'Never saw a prompt? Location may be off for Safari: open <strong>Settings › Privacy &amp; Security › Location Services › Safari Websites</strong> and choose <strong>While Using the App</strong>.' },
    'chrome-ios': { name: 'iPhone, Chrome', steps: [
      'Open the iPhone <strong>Settings</strong> app.',
      'Scroll down and tap <strong>Chrome</strong>, then <strong>Location</strong>.',
      'Choose <strong>While Using the App</strong> and turn on <strong>Precise Location</strong>.',
      'Return to Chrome and reload the guide.'] },
    'firefox-ios': { name: 'iPhone, Firefox', steps: [
      'Open the iPhone <strong>Settings</strong> app and tap <strong>Firefox</strong>, then <strong>Location</strong>.',
      'Choose <strong>While Using the App</strong> and turn on <strong>Precise Location</strong>.',
      'Return to Firefox and reload the guide.'] },
    'edge-ios': { name: 'iPhone, Edge', steps: [
      'Open the iPhone <strong>Settings</strong> app and tap <strong>Edge</strong>, then <strong>Location</strong>.',
      'Choose <strong>While Using the App</strong> and turn on <strong>Precise Location</strong>.',
      'Return to Edge and reload the guide.'] },
    'chrome': { name: 'Android, Chrome', steps: [
      'Tap the icon at the left of the address bar.',
      'Tap <strong>Permissions</strong> (or <strong>Site settings</strong>).',
      'Turn <strong>Location</strong> on.',
      'Reload the page, then tap <strong>Start the walking guide</strong>.'],
      note: 'Still nothing? Check that Location is on in your phone’s quick settings, and that Chrome is allowed to use it: <strong>Settings › Apps › Chrome › Permissions › Location</strong>.' },
    'samsung': { name: 'Android, Samsung Internet', steps: [
      'Tap the menu (three lines) at the bottom right, then <strong>Settings</strong>.',
      'Tap <strong>Sites and downloads › Site permissions › Location</strong>.',
      'Remove the block for <strong>elkhornguide.labs.trlibrary.com</strong>.',
      'Reload the guide.'] },
    'firefox': { name: 'Android, Firefox', steps: [
      'Tap the lock icon at the left of the address bar.',
      'Turn <strong>Location</strong> back on (or clear the block).',
      'Reload the guide.'] }
  };
  var PRECISE = {
    ios: { name: 'iPhone', steps: [
      'Open the iPhone <strong>Settings</strong> app.',
      'Tap <strong>Privacy &amp; Security › Location Services</strong>.',
      'Tap <strong>Safari Websites</strong> (or your browser’s name).',
      'Turn on <strong>Precise Location</strong>, then reload the guide.'] },
    android: { name: 'Android', steps: [
      'Tap the icon at the left of the address bar, then <strong>Permissions</strong>.',
      'Tap <strong>Location</strong> and choose <strong>Precise</strong>.',
      'If Location on the phone itself is set to approximate, open <strong>Settings › Location</strong> and turn on <strong>Google Location Accuracy</strong>.'] }
  };
  function stepsHTML(h) {
    return '<div class="help-steps"><h3>' + h.name + '</h3><ol>' + h.steps.map(function (s) { return '<li>' + s + '</li>'; }).join('') + '</ol>' + (h.note ? '<p>' + h.note + '</p>' : '') + '</div>';
  }
  function openHelp(topic) {
    helpTopic = topic || 'blocked';
    if (helpTopic === 'precise') {
      $('helpTitle').textContent = 'Turn on precise location';
      $('helpLede').textContent = 'Your phone is sharing only an approximate location, which can be off by hundreds of feet. The guide needs your exact spot to tell when you reach each stop.';
      var mine = IS_ANDROID ? PRECISE.android : PRECISE.ios;
      $('helpMine').innerHTML = stepsHTML(mine);
      $('helpOthers').innerHTML = stepsHTML(IS_ANDROID ? PRECISE.ios : PRECISE.android);
    } else {
      $('helpTitle').textContent = 'Turn location back on';
      $('helpLede').textContent = 'If you tapped Don’t Allow, your browser won’t ask again on its own. Here is how to switch it back on.';
      var key = HELP[BROWSER] ? BROWSER : (IS_IOS ? 'safari' : 'chrome');
      $('helpMine').innerHTML = stepsHTML(HELP[key]);
      $('helpOthers').innerHTML = Object.keys(HELP).filter(function (k) { return k !== key; }).map(function (k) { return stepsHTML(HELP[k]); }).join('');
    }
    $('help').hidden = false; $('help').scrollTop = 0;
  }

  // If fixes keep coming back very coarse, the phone is probably sharing approximate location.
  var coarseCount = 0, preciseWarned = false;
  function checkPrecision(acc) {
    if (SIM || preciseWarned) return;
    coarseCount = acc > 500 ? coarseCount + 1 : 0;
    if (coarseCount >= 3) {
      preciseWarned = true;
      $('btnStatusHelp').textContent = 'Turn on precise location'; $('btnStatusHelp').hidden = false;
      $('btnStatusHelp').dataset.topic = 'precise';
    }
  }

  $('btnAskLoc').addEventListener('click', askLocation);
  $('btnAskCompass').addEventListener('click', askCompass);
  $('btnPermGo').addEventListener('click', function () { $('perm').hidden = true; if (permMode === 'start') startNav(); });
  $('btnPermClose').addEventListener('click', function () { $('perm').hidden = true; });
  $('btnPermHelp').addEventListener('click', function () { openHelp(helpTopic); });
  $('btnSetup').addEventListener('click', function () { locPermission().then(function (st) { openPerm('setup', st); }); });
  $('btnStatusHelp').addEventListener('click', function () { openHelp(this.dataset.topic || 'blocked'); });
  $('btnCloseHelp').addEventListener('click', function () { $('help').hidden = true; });
  $('btnHelpRetry').addEventListener('click', function () { location.reload(); });

  /* ---------- wire up ---------- */
  function startNav() {
    initMap(); show('nav'); startGPS(); keepAwake(); update();
    if (!compassOn && !NEEDS_COMPASS_ASK && HAS_ORIENT) enableCompass();
  }
  // Start: explain the permissions first unless they are already settled.
  function begin() {
    if (SIM) { startNav(); return; }
    locPermission().then(function (st) {
      if (st === 'granted' && (!NEEDS_COMPASS_ASK || compassOn)) startNav();
      else openPerm('start', st);
    });
  }
  $('btnBegin').addEventListener('click', begin);
  $('btnOffline').addEventListener('click', saveOffline);
  $('btnPreview').addEventListener('click', function () { $('list').hidden = false; });
  $('btnList').addEventListener('click', function () { $('list').hidden = false; });
  $('btnCloseList').addEventListener('click', function () { $('list').hidden = true; });
  $('btnFull').addEventListener('click', fullScreen);
  $('btnCompass').addEventListener('click', function () { enableCompass(); });
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
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { if (!$('story').hidden) closeStory(); $('list').hidden = true; $('help').hidden = true; } });
  if (params.has('embed')) document.documentElement.classList.add('embedded');
  if (SIM) setTimeout(startNav, 400);
})();
