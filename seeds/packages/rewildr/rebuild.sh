#!/bin/bash
Rscript -e "devtools::document('seeds/packages/rewildr')"
Rscript -e "devtools::install('seeds/packages/rewildr')"
