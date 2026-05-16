# rewildingCities 🌱

*Help us facilitate collective science for climate-resilient futures!*

Authors of science fiction interpret our realities to imagine and project our shared histories, futures, global maps, and economies. Together, we want to explore speculative realities of climate resilience on Earth.

rewildingCities is an open-source platform for collective imagination through *actual* science—where research on urban ecosystems meets world-building, and data becomes a lens for innovating our climate-resilient futures. We create accessible, rigorous analytical tools for communities who are ready to ask: *What flourishes when we make room for the wild? What transformations must take place for us to enjoy a safe, healthy future? Are we ready to redesign ourselves, through infrastructure and institution, to embrace the flow of our natural environment: to be collaborative, adaptive, and regenerative?*

**Our first investigation: surviving rising temperatures.** We're going to need to understand how heat travels throughout our cities. Nature did it best with green infrastructure, and we want to look at how we can design a *literal* rewilding of the city to combat our deadliest, most frequent natural disasters: heat waves. We've built an accessible pipeline for citizens to conduct their own geospatial analyses with community-specific datasets.

Currently, our platform supports thermal analysis of urban green infrastructure — measuring how parks cool their surroundings using satellite imagery and spatial statistics. We invite researchers, organizers, and learners to build with us—creating pipelines using this infrastructure to investigate the questions that matter to your community, and contribute to the development of economies of resilience.

---

## Who is this for?

- **Researchers and analysts** imploring data science like science fiction;
- **Advocates and planners** exploring methods for making climate-resilient futures;
- **Designers and systems thinkers** practicing biomimicry with civic literacy;
- **Leaders** developing technical literacy through meaningful work.

---

## Our codebase is a garden:

The codebase is organized symbolically to support a living system where patterns emerge from interdependence:

| Directory | Purpose | Metaphor |
|-----------|---------|----------|
| `canopy/` | Orchestration, providers, resolution, CLI | The visible canopy — how the system thinks |
| `soil/` | Validation, repair, transformation, filtering | Preparing the ground |
| `roots/` | Analytical primitives (buffers, PCI, Gi*, regression) | Hidden analytical foundation |
| `seeds/` | Schemas, crosswalks, profiles, templates | Preserved patterns |
| `garden/` | Curiosity space, methods, experiments | Where questions grow |
| `plots/` | City-specific data, manifests, envelopes | Each community is a plot of land |
| `compost/` | Logs, archives, feedback | Transformation through reflection |

---

## How is this shaped?

**Manifests** declare what data each city has — where it came from, how to get more, and what it means. The system checks its own consistency and acquires missing data automatically when possible.

**Experiments** compose analytical workflows from atomic primitives. Each step produces an **envelope** — a provenance record documenting inputs, outputs, timing, warnings, and the full data lineage. Every output knows where it came from.

**The Resolution Engine** reads what an experiment needs, checks what's available, attempts to acquire what's missing, traces the dependency graph to identify what breaks, and advises on uncertainty. It tells you what you can and can't do with the data you have.

**Providers** handle data acquisition through a uniform interface — Socrata, ArcGIS REST, Planetary Computer STAC, ESA WorldCover S3, and Google Earth Engine. One command can acquire all the data a city needs.

**Profiles** let you subset for context: `dev` for fast iteration, `full` for production, `neighborhood` for local analysis.

**Crosswalks** translate between classification systems, because every city names its world differently.

---

## Running an experiment

```bash
# validate your experiment
python -m canopy.cli.experiment plots/nyc/experiments/nyc_park_cooling_pedestrian.yml --dry-run

# check data availability and acquire what's missing
python -m canopy.cli.experiment plots/nyc/experiments/nyc_park_cooling_pedestrian.yml --resolve-only

# run with dev profile (fast iteration)
python -m canopy.cli.experiment plots/nyc/experiments/nyc_park_cooling_pedestrian.yml --profile dev

# full run
python -m canopy.cli.experiment plots/nyc/experiments/nyc_park_cooling_pedestrian.yml --profile full
```

---

## Our guiding principles:

1. **Honest outputs** — Document limitations. Tell people what they're actually getting.
2. **Data pluralism** — Help communities work with what they have.
3. **Composable primitives** — Atomic operations for learning or production.
4. **Transparent provenance** — Every output knows where it came from.
5. **Local-first, cloud-ready** — Works on a laptop. Scales when needed.
6. **Pedagogical design** — Design is instructional.

---

## The vision:

rewildingCities is a project of **Rewilding Intelligence**, a research initiative facilitating collaborative data science for climate-resilient futures. Infrastructure for investigating urban ecosystems. Tools that meet communities where they are. Research that learns from the patterns our natural environment has made clear.

---

## Inspiring research/resources:

- Xiao, Y. et al. (2023). "Using buffer analysis to determine urban park cooling intensity." *Science of the Total Environment*
- brown, a.m. (2017). *Emergent Strategy.* — Fractal governance, iterative development
- Hamann, K. et al. *The Psychology of Collective Climate Action* — Movement theory, social change roles
- Practices from reproducible research, biomimicry, and participatory design

---

## Get started

**clone the repo:**

```bash
git clone https://github.com/kalliannhale/rewildingCities.git
cd rewildingCities
```

**set up python (choose one):**

with conda/mamba:
```bash
conda env create -f environment.yml
conda activate rewilding
```

with pip:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**set up R:**

```bash
Rscript -e "install.packages(c('sf', 'terra', 'lwgeom'), repos='https://cloud.r-project.org')"
R CMD INSTALL seeds/packages/rewildr
```

**verify everything works:**

```bash
python -m canopy.cli.experiment plots/nyc/experiments/nyc_park_cooling_pedestrian.yml --dry-run
```

See the [contributor worksheet](CONTRIBUTING.md) for the full setup guide.

---