import os

from locust import between, task
from locust.contrib.fasthttp import FastHttpUser


class ScalePulseLoadTest(FastHttpUser):
    wait_time = between(0.001, 0.005)

    def on_start(self) -> None:
        api_key = os.getenv("SCALEPULSE_BENCH_API_KEY")
        if api_key:
            self.client.headers["X-API-Key"] = api_key

    @task(9)
    def resource(self) -> None:
        self.client.get("/api/v1/resource")

    @task(1)
    def health(self) -> None:
        self.client.get("/health")
