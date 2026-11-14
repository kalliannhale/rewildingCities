import logging
import os
from urllib.parse import quote

from locust import HttpUser, task, between

# From the repository root:
# locust -f canopy\api\locustfile.py --host http://127.0.0.1:8000
# To poll an existing run, set LOCUST_RUN_ID and optionally LOCUST_RUN_PLOT.
# Indicator previews and receipts require the corresponding data on the server.

logger = logging.getLogger(__name__)

class ApiUser(HttpUser):
    wait_time = between(0.5, 2) # secs

    def on_start(self):
        self.run_id = os.environ.get("LOCUST_RUN_ID")
        self.run_plot = os.environ.get("LOCUST_RUN_PLOT", "nyc")
        if not self.run_id:
            logger.warning("LOCUST_RUN_ID is not set; run status requests are disabled")

    @task(3) # task(n): n= weight of this task relative to others 
    def health(self):
        self.client.get("/health")

    @task(2)
    def plots(self):
        self.client.get("/plots")

    @task(2)
    def reading(self):
        self.client.get("/plots/nyc/reading", name="/plots/{plot}/reading")

    @task(1)
    def holdings(self):
        self.client.get("/plots/nyc/holdings", name="/plots/{plot}/holdings")

    @task(1)
    def methods(self):
        self.client.get("/methods")
        
    @task(1)
    def curiosity(self):
        self.client.get("/curiosities")

    @task(1)
    def plot_curiosities(self):
        self.client.get("/plots/nyc/curiosities", name="/plots/{plot}/curiosities")

    @task(1)
    def acquire(self):
        self.client.get(
            "/plots/nyc/acquire",
            params={"method": "garden/methods/thermal/thermal_gradient_analysis.yml"},
            name="/plots/{plot}/acquire",
        )

    @task(1)
    def receipts(self):
        self.client.get("/plots/nyc/receipts", name="/plots/{plot}/receipts")

    @task(1)
    def trace(self):
        self.client.get("/plots/nyc/trace", name="/plots/{plot}/trace")

    @task(1)
    def run_status(self):
        if self.run_id:
            plot = quote(self.run_plot, safe="")
            run_id = quote(self.run_id, safe="")
            self.client.get(
                f"/plots/{plot}/runs/{run_id}",
                name="/plots/{plot}/runs/{run_id}",
            )

    @task(1)
    def indicators(self):
        self.client.get("/indicators")

    @task(1)
    def indicator(self):
        self.client.get("/indicators/cii_broadband", name="/indicators/{indicator_id}")

    @task(1)
    def plot_indicators(self):
        self.client.get("/plots/maine/indicators", name="/plots/{plot}/indicators")

    @task(1)
    def plot_indicator_values(self):
        self.client.get(
            "/plots/maine/indicators/cii_broadband",
            params={"unit_authority": "us_census_geoid", "dataset": "acs_county_2024"},
            name="/plots/{plot}/indicators/{indicator_id}",
        )
