# BNBU bird–glass collision: interpretable risk and intervention decision system

Version: 0.1.0  
Status: executable prototype; not yet calibrated to BNBU.

## 1. What is being built

The project is not a single collision classifier and it is not a single
interpretable risk score. It is a modular decision-support system with four
separate outputs:

1. **Exposure and approach:** which bird groups are present, when they are
   active, and whether they actually approach a particular pane.
2. **Glass hazard:** whether the complete glass assembly creates a reflected
   habitat image, a false transparent passage, or another optical cue problem.
3. **Vegetation and site context:** which vegetation scales contribute to
   habitat availability, approach routes, reflected scenes, or obstruction.
4. **Intervention choice:** which glass treatment, lighting action, or
   habitat adjustment is best supported for the observed mechanism, and what
   evidence is still missing.

The model returns a pathway profile, ranked conditional actions, provenance,
and data gaps. It deliberately does **not** collapse all inputs into one
opaque number. It does not return an absolute collision probability from
incident reports or vegetation percentages alone.

## 2. Causal decomposition

For pane p, species/guild s and time t, the target process is:

```text
regional bird availability
        |
        v
local bird activity ---- habitat resources / season / weather
        |
        v
approach flow to pane <---- flight routes / canopy structure / water
        |
        v
optical hazard at pane <--- reflectance / transmission / reflected habitat
        |
        v
avoidance or contact <----- species vision / contrast / motion / lighting
        |
        v
glass contact / opaque contact / no contact / censored event
        |
        v
injury severity (separate model; currently not estimated)
```

A useful future estimand is:

```
expected glass contacts per pane-hour
  = at-risk approaches per pane-hour
    × P(glass contact | at-risk approach)
```

The first term needs an effort-corrected approach denominator. The second
needs continuous observation of approaches and independently verified
outcomes. Injury probability is a further, separate endpoint.

The observation process is another layer:

```
reported collision
  = true collision
    × carcass persistence
    × search/detection probability
    × reporting probability
```

The existing observation/persistence modules remain separate from the
biological encounter model.

## 3. Glass classification: measure the complete assembly

The code distinguishes:

- clear/transparent glass: possible false-passage pathway;
- highly reflective glass: possible reflected-sky/reflected-habitat pathway;
- reflective and transparent glass: both pathways;
- tinted or low-emissivity assemblies: **unclassified until measured**;
- fritted/patterned glass: evaluate pattern coverage, gap, marker width,
  exterior surface and contrast; the product label alone is insufficient;
- opaque spandrel: not a glass pane, but it remains an opaque obstacle in
  whole-structure contact accounting.

Required glass fields, where available:

- pane area and dimensions;
- exterior visible-light reflectance (VLR) and visible-light transmittance
  (VLT) for the full insulating-glass unit;
- coating and layer order;
- marker surface (first/exterior vs interior);
- marker width, maximum clear gaps in both axes, full-pane coverage and
  contrast;
- reflected and transmitted habitat fractions from plausible bird approach
  views;
- façade orientation and time-varying solar/view geometry.

**Important threshold discipline:** the American Bird Conservancy (ABC) 2025
prescriptive rating procedure uses 15% exterior VLR as a condition for some
patterns located behind the exterior surface. This is a rating-procedure
boundary, not a universal biological collision threshold. Site-specific
reflection varies with product, insulating-glass construction, angle,
illumination and background.

### Pattern status implemented

- **2x2:** full-pane exterior pattern, high contrast, marker elements at least
  5 mm wide, maximum clear gaps no greater than 5 cm in either axis.
- **2x4:** the ABC prescriptive category permits up to 10 cm horizontal and
  5 cm vertical clear gaps. It is less conservative than 2x2.
- **Not guideline verified:** interior-only, partial coverage, insufficient
  contrast, unknown dimensions, undersized markers, or larger gaps.

The current classifier is a screening check, not a product certification.
Canada.ca guidance calls for patterns over the entire pane, on the exterior,
with no gaps over 5 cm in either direction and elements at least 5 mm wide.
ABC's 2025 rating update notes that 2x2 spacing is increasingly recommended;
2x4 can still receive a bird-friendly rating but may be less protective for
the smallest birds.

## 4. Vegetation: five buffers and four pathways

The system stores vegetation cover separately at:

| Buffer | Primary interpretation |
|---|---|
| 0–5 m | immediate structure and near-pane scene |
| 5–25 m | local canopy and short approach context |
| 25–100 m | building-scale green structure |
| 100 m–1 km | neighborhood habitat context |
| 1–10 km | landscape-scale habitat context |

These are not five interchangeable copies of one variable. They feed four
different mechanisms:

1. **Attraction / availability:** vegetation resources may support bird
   abundance or activity, but cover alone is not bird abundance.
2. **Flight routing:** canopy height, crown distance, overlap with pane height,
   corridor gaps and obstruction can shape approach paths.
3. **Optical scene:** the fraction of vegetation actually reflected in the
   pane is a direct optical covariate and should be measured from plausible
   approach directions.
4. **Landscape context:** broader green cover can describe habitat availability
   and seasonal species composition, but does not directly identify pane-level
   approach rates.

### Why no universal vegetation threshold is hard-coded

The China national study surveyed 3,078 buildings during 2021–2023. It
reported positive associations between building collisions and vegetation
cover at broader scales (including 1 km and 10 km), while trees within 5 m
were associated with reduced collision occurrence, especially in fall.
The November 2026 Ottawa study found nearby vegetation and tree canopy among
the strongest collision drivers in its local façade sample. These findings
are not interchangeable: they differ in region, study design, spatial
definition and ecological context.

Therefore:
- preserve continuous cover percentages at every buffer;
- compute low/middle/high bands only relative to a stated local
  region/season/land-cover reference distribution;
- record canopy height, nearest-crown distance, pane-height overlap and
  reflected vegetation separately;
- never recommend blanket tree removal from canopy percentage alone.

## 5. Species and seasonal exposure

The species layer should combine:

- local BNBU observations with observation effort and confidence;
- regional occurrence data (e.g. GBIF) for candidate species and taxonomy;
- eBird Basic Dataset where access is approved, because it contains effort
  metadata; and
- seasonal abundance/occurrence products where available and licensed.

An occurrence record is not an abundance estimate. GBIF's eBird Observational
Dataset contains species, date and location but not sampling-event effort.
The eBird Basic Dataset is updated monthly and requires a data request by a
logged-in user; it is the more appropriate route when effort metadata are
needed. The eBird Status and Trends products require a separate access request
and should not be assumed to cover every focal species or region.

The Neotropical 4,103-event dataset is useful for reported victim/event
composition and taxonomy. It is not a Guangdong bird-abundance dataset and
must not be used as the local species prior.

## 6. Intervention decision logic

The system matches actions to mechanisms, then ranks them by mechanism fit,
evidence strength and local support. It does not assign invented efficacy
percentages.

### A. Exterior visual markers — default first retrofit candidate

For clear or reflective untreated panes, the first candidate is a
high-contrast, full-pane exterior pattern. Prefer a maximum clear gap of
5 × 5 cm and marker elements at least 5 mm wide. Verify that the pattern is
visible against the real reflected/transmitted scene from multiple approach
angles and times of day.

The 2026 Ottawa study documented 225 collisions involving 51 species. Its
guideline-compliant treatments were associated with a significant reduction
in collision risk, while non-compliant treatments were not significantly
different from untreated façades. Its model-derived reductions (96.0% for
compliant and 70.1% for non-compliant treatments) are study-specific and are
not BNBU predictions.

A 2026 Oklahoma State University field study used 5.1 × 5.1 cm exterior white
markers. Descriptive collision rates at six treated façades fell by 67.2–71.6%
after treatment, while untreated façades increased by 15.7%; however, the
formal BACI treatment-by-period interaction was not statistically significant,
with low replication of treated façades. This supports field testing, not a
guaranteed local effect.

### B. External screens or cords — alternative

Consider when a continuous marker film is infeasible or the façade needs a
physical interruption. Mesh/cord spacing, stand-off, entanglement, wind load,
fire safety, egress, maintenance and human safety must be checked. Do not
assume any net is automatically safe or effective.

### C. Lighting controls — nocturnal pathway only

Use seasonal switch-off schedules, downward shielding, timers and occupancy
controls when local nocturnal migrant activity and artificial light are both
supported by evidence. This is separate from daytime glass marking. The
China study found season-dependent ALAN associations; do not transfer a
single universal light coefficient to BNBU.

### D. Vegetation management — conditional, not default

Do not remove or heavily prune trees merely because a buffer has high canopy
cover. First determine whether vegetation is reflected in the pane, overlaps
the pane height, attracts birds to a risky approach corridor, or instead
provides a safe barrier. If the reflection pathway is present, treating the
glass is the first candidate. Any habitat modification needs ecological
review and a check for displaced risk at adjacent panes.

### E. UV-only treatments — conditional research candidate

A controlled study of two songbird species found UV-reflective film reduced
collisions by 75–90% in forced-choice tunnel tests, but by 30–50% in a more
ecologically relevant choice condition. This is not evidence of universal
performance in subtropical species, cloud, shade or low-light conditions.
Require spectral measurements, species-vision review and a non-injurious
local test before relying on UV alone.

### F. Weak options

One or a few decals do not treat the full pane. Interior-only markers may
leave the external reflection visible. Raptor silhouettes are not a substitute
for a full-pane, evidence-based pattern. These should not outrank a compliant
exterior treatment.

## 7. Data and calibration rules

### External evidence

- **Neotropical 2025:** 4,103 curated reports, 571 species, 11 countries,
  1946–2020. Event composition only.
- **China 2025:** 3,078 buildings, multi-scale vegetation and ALAN
  associations. Individual raw records are available on request; paper-level
  associations are not treatment effects.
- **Ottawa 2026:** 225 collisions, 51 species; treatment compliance and
  vegetation/glass-area associations.
- **Oklahoma 2026:** replicated before-after-control-impact field design for
  exterior markers, but only six treated façades and limited power.
- **Canada.ca / ABC 2025:** installation and rating guidance; not local
  efficacy measurements.
- **eBird / GBIF:** regional species and seasonal context with different
  effort metadata and access limitations.

### BNBU observations

The approximately 48–50 local records are opportunistic collision
observations. Use them for:
- local species names and possible guilds;
- season and location hypotheses;
- cross-checking whether external taxa are locally plausible;
- qualitative calibration of the reporting process.

Do not use them as 50 independent positive examples with invented negative
rows. They do not supply all approaches, pane-hours, search effort or
detection probability.

### Validation

- group validation by bird/individual, camera/trial, building/façade and date;
- keep continuous-video approaches distinct from motion-triggered collision
  clips;
- annotate glass contact, opaque contact, no contact and right-censoring
  independently from the geometry model;
- compare to simple baselines and report calibration/uncertainty;
- evaluate adjacent-pane risk transfer after every proposed treatment;
- use a paired or staggered local intervention design before estimating
  BNBU-specific treatment efficacy.

## 8. Executable interface

The new modules are:

- `birdglass/evidence.py`: provenance-aware numeric measurements;
- `birdglass/vegetation.py`: multiscale vegetation pathways;
- `birdglass/glazing.py`: glass appearance and marker-compliance screening;
- `birdglass/decision.py`: pathway assessment, conditional contact-rate
  identification and ranked interventions;
- `scripts/audit_neotropical_sampling.py`: reproducible source audit.

The decision engine can identify a conditional glass-contact rate only when
all at-risk approaches are sampled by continuous video, outcomes are
independently verified, and no approaches are right-censored. If hourly
approach flow is also measured, it can derive expected glass contacts per
pane-hour. It still does not estimate injury probability.

The JSON interface and tests are being added on this branch. No BNBU pane
measurements or local efficacy values have been fabricated.
