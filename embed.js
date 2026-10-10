/* Elkhorn Ranch Walking Guide embed
   <div id="trpl-elkhorn-guide"></div>
   <script src="https://elkhornguide.labs.trlibrary.com/embed.js" defer></script>
   Optional: data-target="#some-id" on the script tag, data-height="720". */
(function () {
  var script = document.currentScript || document.querySelector('script[src*="elkhornguide"][src$="embed.js"]');
  var base = script ? script.src.replace(/embed\.js(\?.*)?$/, '') : 'https://elkhornguide.labs.trlibrary.com/';
  var sel = (script && script.dataset.target) || '#trpl-elkhorn-guide';
  var host = document.querySelector(sel);
  if (!host) { host = document.createElement('div'); script.parentNode.insertBefore(host, script); }
  var h = parseInt((script && script.dataset.height) || '0', 10);

  var wrap = document.createElement('div');
  wrap.style.cssText = 'position:relative;width:100%;max-width:960px;margin:0 auto;border:1px solid #D1CCBD;border-radius:8px;overflow:hidden;background:#F4F2EC';
  var frame = document.createElement('iframe');
  frame.src = base + '?embed=1';
  frame.title = 'Elkhorn Ranch Walking Guide: map, compass and stop-by-stop stories';
  frame.loading = 'lazy';
  frame.setAttribute('allow', 'geolocation; fullscreen; accelerometer; gyroscope; magnetometer; screen-wake-lock');
  frame.setAttribute('allowfullscreen', '');
  function size() {
    var vh = window.innerHeight || 800;
    frame.style.height = (h || Math.max(560, Math.min(760, Math.round(vh * 0.82)))) + 'px';
  }
  frame.style.cssText = 'display:block;width:100%;border:0';
  size(); window.addEventListener('resize', size);

  var bar = document.createElement('div');
  bar.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;padding:10px 12px;background:#fff;border-top:1px solid #D1CCBD;font:14px/1.4 Frutiger,"Helvetica Neue",Helvetica,Arial,sans-serif;color:#25282A';
  bar.innerHTML = '<span>Best on your phone at the ranch. Save it for offline before you lose signal.</span>' +
    '<a href="' + base + '" target="_blank" rel="noopener" style="display:inline-block;padding:10px 16px;background:#E7805D;color:#25282A;font-weight:700;text-decoration:none;border-radius:6px">Open the guide full screen</a>';

  wrap.appendChild(frame); wrap.appendChild(bar);
  host.appendChild(wrap);
})();
