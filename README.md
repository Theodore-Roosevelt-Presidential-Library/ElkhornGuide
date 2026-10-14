# Elkhorn Ranch Walking Guide

A mobile walking guide to Theodore Roosevelt's Elkhorn Ranch in the Elkhorn Ranch Unit of Theodore Roosevelt National Park. A live map and compass lead visitors to each of the eight National Park Service tour stops along the 0.7-mile path, and each stop opens the story of the ranch in T.R.'s and Bill Sewall's own words. It works offline, because there is no cell service at the ranch.

Live: https://elkhornguide.labs.trlibrary.com
Embedded on: https://www.trlibrary.com/visit/national-park/elkhorn-ranch

## How it works

- **Map.** Leaflet with a USGS NAIP aerial image of the trail (`map/naip.jpg`, public domain) over USGS National Map topo tiles. The route line joins the parking area and the eight NPS stop coordinates; it approximates the mowed path.
- **Location and arrival.** `navigator.geolocation.watchPosition`. A stop counts as reached inside 18 to 30 m, depending on GPS accuracy; the phone vibrates and the stop's story opens.
- **Compass.** `deviceorientationabsolute` on Android, `webkitCompassHeading` on iPhone (needs a tap on *Turn on compass*). Without a compass the arrow assumes north is up, and GPS course is used while walking.
- **Far from the ranch.** More than 2.5 km from the parking area, the guide points to the trailhead first and offers driving directions.
- **Offline.** `sw.js` caches the app on first load. *Save for offline* also stores the photos, the aerial, the brand fonts and USGS topo tiles for the trail (z13 to 16) and the drive from I-94 (z10 to 12): about 5 MB plus roughly 170 tiles.
- **Full screen.** The full-screen button uses the Fullscreen API. iPhone Safari does not support it for pages, so iPhone users get a prompt to Add to Home Screen, which opens the guide full screen with its own icon (`manifest.webmanifest`).
- **Permissions, explained first.** *Start* opens a short screen that says what the phone is about to ask (location, and on iPhone the separate "motion and orientation" prompt for the compass) and what the Library does with it (nothing: it stays on the phone). The phone's own prompts appear only after the participant taps *Allow*. *Save for offline* opens the same screen afterward, so people grant both while they still have signal.
- **Recovery.** If location was blocked, the guide shows step-by-step instructions for the participant's phone and browser (iPhone Safari, Chrome, Firefox, Edge; Android Chrome, Samsung Internet, Firefox), with the others one tap away.
- **Approximate location.** If three fixes in a row are worse than 500 m, the phone is probably sharing approximate location. The guide says so, stops opening stories on its own, and links to instructions for turning on Precise Location.
- **Progress** is kept in `localStorage` per device.

## Content

`data/stops.json` holds every word of the guide. Each stop has:

- `gallery`: swipeable photos, each with `src`, `alt`, `caption` and `credit` (the first is also the list thumbnail);
- `blocks`: the story in order, as `{"p": html}`, `{"q": text, "cite": source}`, `{"h": subhead}` or `{"thenNow": {...}}`;
- `look`: the green "Look for" cue;
- `more`: extra blocks behind a "More at this stop" toggle;
- `source`: the source line.

`docs/fact-check.md` lists the source for every quotation, fact and photograph. When adding an image, add its path to `MEDIA` in `sw.js` and bump `VERSION` so offline copies update.

## House footprint (for the 3D model)

`docs/model/` holds a first estimate of the ranch-house footprint, solved from the Library's 360° panoramas of the site (elkhorn.labs.trlibrary.com): two parallel rows of foundation stones, long axis about 11.7° east of true north, fitted to the 60 × 30 ft house. Position relative to the stones is good; absolute position is only about ±12 m because of phone GPS. See `footprint.json`, `topdown.png` and the overlays. A site visit with a tape and GNSS should confirm it before the model is built on it.

## Embedding on trlibrary.com

Drupal Code (embed) block:

```html
<div id="trpl-elkhorn-guide"></div>
<script src="https://elkhornguide.labs.trlibrary.com/embed.js" defer></script>
```

The embed is an iframe with `allow="geolocation; fullscreen; accelerometer; gyroscope; magnetometer; screen-wake-lock"`, plus a button that opens the guide full screen in its own tab. On a phone at the ranch, the full-screen version is the better experience.

## Staff preview

Add `?sim=1` to the URL to walk the route from anywhere: tap the map to move your position. Add `?stop=3` to open a stop directly.

## Credits

Stop locations: National Park Service, Theodore Roosevelt National Park, Elkhorn Ranch Walking Tour (NPS Data API). Historic photographs and drawings: public-domain books (Hunting Trips of a Ranchman, 1885; Ranch Life and the Hunting-Trail, 1888; Bill Sewall's Story of T.R., 1919; Hagedorn, Roosevelt in the Bad Lands, 1921) via archive.org, and the Library of Congress. Modern photographs: NPS and the Library. Aerial imagery and topo maps: U.S. Geological Survey. Map library: Leaflet (BSD-2-Clause). Text: Theodore Roosevelt Presidential Library.
