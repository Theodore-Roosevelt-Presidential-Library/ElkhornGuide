"""Add dataset/detectability metadata and key findings to candidates.json (run after 07)."""
import json, sys
p=sys.argv[1]+'/candidates.json'; J=json.load(open(p))
J['dataset']=dict(project='ND_SouthWest_2021_D21', work_unit='ND_SouthWest_1_D21', tile='13tfn040320',
  access_note='rockyweb.usgs.gov LAZ download was blocked (TLS reset) from this environment; the identical 3DEP points were read from the public EPT (s3 usgs-lidar-public/ND_SouthWest_1_D21, EPSG:3857) and reprojected to EPSG:26913; Z agrees with the earlier 0.5 m DEM export to median -0.1 cm.',
  acquisition='2021-11-06 ~20:40-21:10 UTC (GPS time), leaf-off; work unit collected 2021-10-29..2021-11-08; 2 flight lines over site (point source IDs 194, 197)',
  quality_level='QL2, linear-mode lidar, USGS Lidar Base Spec 2021 rev A; USGS summary report: produced to meet 9.8 cm absolute vertical accuracy at 95% confidence in non-vegetated open terrain (per-project NVA/VVA test values not found in the staged reports)',
  classes={'1 unclassified':248732,'2 ground':528408,'7 low noise':1716,'9 water':12271,'18 high noise':4,'20 ignored ground (breakline proximity)':884},
  density_all_pts_per_m2=6.85, density_first_returns_per_m2=5.38, density_ground_per_m2={'340 m box incl. river':4.57,'320 m DEM box':5.16,'20 m radius of house':4.95,'house footprint':5.0},
  ground_spacing_m=0.45, empty_1m_cells_within_20m_of_house_pct=1.0,
  ground_noise_sigma_m=round(J['noise_sigma_m'],3))
J['detectability']=('Ground returns ~5/m2 (mean spacing ~0.45 m), relative noise ~2.4 cm (std of ground points about a 1.5 m local plane on flat ground). '
  'Reliable detection needs >= ~15-20 ground points across a feature and >= ~8-10 cm relief: i.e. hollows/mounds ~2 m or more across and ~0.1 m or more deep/high. '
  'Linear berms/hollows ~1-1.5 m wide and >= 10 cm can show if they run > ~5 m. Individual foundation stones, post holes, sill logs and fence lines are NOT resolvable. '
  'Cottonwood canopy (leaf-off) did not degrade ground returns at the house (1% empty 1 m cells); grass thatch may lift the ground surface a few cm.')
J['background_rates']={'note':'Tier-A (compact, open, off-scarp) features per hectare of eligible ground','0-25 m':{'depressions':24.2,'mounds':18.2},'25-50 m':{'depressions':17.0,'mounds':17.0},'50-100 m':{'depressions':1.2,'mounds':3.7},'100-150 m':{'depressions':0.4,'mounds':0.8}}
J['ring_test']={'method':'scripts/08_ring_test.py: rim annulus >=3 cm above interior and outside in N of 12 sectors; exhaustive search house window (80x100 m) vs two equal background windows',
  'pit_with_spoil_R3-5m':{'house_window':'4 hits (best D2 = 10/12)','west_terrace_bg':'1 hit (8/12)','northwest_bg':'0'},
  'corral_ring_R7.5-12.5m':{'house_window':'2 weak hits (8/12) at +14E,+31N and -16E,+47N (not west of house)','backgrounds':'0'}}
J['east_scarp']=('House terrace ~649.0 m. Break of slope begins ~18-24 m E of house center; steepest face (max 21 deg, ~0.9 m drop over ~3 m) at ~33-37 m E; '
  'total drop ~2.0 m to a swale at ~646.9 m at 48 m E (possible abandoned channel), low ridge 647.6 m at 55-65 m, then gradual descent to the 2021 river '
  'edge ~140 m ESE (cut bank ~1 m, water 643.65 m). 647.8 m contour lies 29-45 m E of house center over +-60 m N-S with no re-entrant notch > 1.5 m (scripts/12_scarp_notch.py).')
json.dump(J,open(p,'w'),indent=1); print('ok')
