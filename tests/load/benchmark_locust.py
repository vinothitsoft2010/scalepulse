from locust import between, task
from locust.contrib.fasthttp import FastHttpUser


class ScalePulseLoadTest(FastHttpUser):
    wait_time = between(0.001, 0.005)

    @task(9)
    def resource(self) -> None:
        self.client.get("/api/v1/resource")

    @task(1)
    def health(self) -> None:
        self.client.get("/health")
