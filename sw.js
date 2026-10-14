/* Elkhorn Ranch Walking Guide service worker: app shell offline + USGS topo tiles for the ranch area */
var VERSION = 'v3';
var SHELL = 'elkhorn-shell-' + VERSION;
var FULL = 'elkhorn-full-' + VERSION;
var TILES = 'elkhorn-tiles-' + VERSION;

var CORE = [
  './', 'index.html', 'app.css', 'app.js', 'data/stops.json', 'manifest.webmanifest',
  'vendor/leaflet/leaflet.js', 'vendor/leaflet/leaflet.css',
  'icons/icon-192.png', 'icons/icon-512.png', 'icons/icon-180.png'
];
var MEDIA = [
  'map/naip.jpg', 'img/stop8.jpg',
  'img/s1-gifford.jpg',
  'img/s1-brands.jpg',
  'img/s2-buckskin.jpg',
  'img/s3-furs.jpg',
  'img/s3-sewall.jpg',
  'img/s3-dow.jpg',
  'img/s3-maine.jpg',
  'img/s4-house.jpg',
  'img/s4-stables.jpg',
  'img/s4-bottom.jpg',
  'img/s5-roundup.jpg',
  'img/s5-tr-roundup.jpg',
  'img/s5-cowpunchers.jpg',
  'img/s5-cutting.jpg',
  'img/s6-river.jpg',
  'img/s6-above.jpg',
  'img/s6-winter.jpg',
  'img/s7-women.jpg',
  'img/s7-dugout.jpg',
  'img/s7-guarding.jpg',
  'img/s7-handsup.jpg',
  'img/s7-dickinson.jpg',
  'img/s8-piazza.jpg',
  'img/s8-site1919.jpg',
  'img/s8-today.jpg',
  'img/s8-drifting.jpg',
  'img/s8-then.jpg',
  'img/s8-now.jpg'
];
var FONTS = [
  'https://www.trlibrary.com/themes/custom/trpl/css/dharma_type-dharmagothice-bold.woff2',
  'https://www.trlibrary.com/themes/custom/trpl/css/clearfacestd-regular.woff2',
  'https://www.trlibrary.com/themes/custom/trpl/css/frutigerltstd-regular.woff2',
  'https://www.trlibrary.com/themes/custom/trpl/css/frutigerltstd-bold.woff2'
];
var TILE_URL = 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/';

function tileXY(lat, lon, z) {
  var n = Math.pow(2, z);
  var x = Math.floor((lon + 180) / 360 * n);
  var r = lat * Math.PI / 180;
  var y = Math.floor((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * n);
  return [x, y];
}
function tilesFor(s, w, n, e, zmin, zmax) {
  var out = [];
  for (var z = zmin; z <= zmax; z++) {
    var a = tileXY(n, w, z), b = tileXY(s, e, z);
    for (var x = a[0]; x <= b[0]; x++) for (var y = a[1]; y <= b[1]; y++) out.push(TILE_URL + z + '/' + y + '/' + x);
  }
  return out;
}
// The trail and river bottom in detail; the drive from I-94 at lower zoom.
var OFFLINE_TILES = tilesFor(47.226, -103.645, 47.252, -103.600, 13, 16)
  .concat(tilesFor(46.88, -103.90, 47.27, -103.50, 10, 12));

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(SHELL).then(function (c) { return c.addAll(CORE); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k.indexOf(VERSION) < 0; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('message', function (e) {
  if (!e.data || e.data.type !== 'save-offline') return;
  var port = e.ports[0];
  e.waitUntil(saveAll().then(function (ok) { port && port.postMessage({ ok: ok }); }));
});
function saveAll() {
  return caches.open(FULL).then(function (c) {
    var local = CORE.concat(MEDIA).map(function (u) { return c.add(u).then(function () { return true; }, function () { return false; }); });
    var fonts = FONTS.map(function (u) {
      return fetch(u, { mode: 'cors' }).then(function (r) { return r.ok ? c.put(u, r).then(function () { return true; }) : true; }, function () { return true; });
    });
    return Promise.all(local.concat(fonts));
  }).then(function (res) {
    return caches.open(TILES).then(function (c) {
      return Promise.all(OFFLINE_TILES.map(function (u) {
        return c.match(u).then(function (hit) {
          if (hit) return true;
          return fetch(u, { mode: 'cors' }).then(function (r) { return r.ok ? c.put(u, r).then(function () { return true; }) : true; }, function () { return true; });
        });
      }));
    }).then(function () { return res.every(Boolean); });
  }).catch(function () { return false; });
}

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = req.url;
  // Map tiles and fonts: cache first, then network (and keep a copy).
  if (url.indexOf(TILE_URL) === 0 || url.indexOf('/themes/custom/trpl/css/') > -1) {
    e.respondWith(caches.match(req).then(function (hit) {
      return hit || fetch(req).then(function (r) {
        if (r.ok) { var copy = r.clone(); caches.open(TILES).then(function (c) { c.put(req, copy); }); }
        return r;
      });
    }));
    return;
  }
  if (new URL(url).origin !== self.location.origin) return;
  // Same-origin: network first for the app files so updates arrive, cache when offline.
  e.respondWith(fetch(req).then(function (r) {
    if (r.ok && /\.(html|css|js|json|webmanifest)$|\/$/.test(new URL(url).pathname)) {
      var copy = r.clone(); caches.open(SHELL).then(function (c) { c.put(req, copy); });
    }
    return r;
  }).catch(function () {
    return caches.match(req, { ignoreSearch: true }).then(function (hit) { return hit || caches.match('index.html'); });
  }));
});
