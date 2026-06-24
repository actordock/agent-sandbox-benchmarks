# Copyright 2026 The Actordock Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from prometheus_client import start_http_server
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from locust import events
import logging

logger = logging.getLogger(__name__)

_initialized = False
request_counter = None
request_latency = None
locust_users = None


def init_metrics():
    global _initialized, request_counter, request_latency, locust_users
    if _initialized:
        return

    try:
        start_http_server(8000)
    except Exception as e:
        logger.warning("metrics server: %s", e)

    _reader = PrometheusMetricReader()
    _provider = MeterProvider(metric_readers=[_reader])
    metrics.set_meter_provider(_provider)
    meter = metrics.get_meter("locust_common")

    request_counter = meter.create_counter(
        name="locust_requests_total",
        description="Total number of requests",
    )
    request_latency = meter.create_histogram(
        name="locust_request_duration_milliseconds",
        description="Request latency in milliseconds",
    )
    locust_users = meter.create_up_down_counter(
        name="locust_users",
        description="Number of active locust users",
    )
    _initialized = True


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context=None, **kwargs):
    if not _initialized:
        return
    if context is None:
        context = kwargs.get("context", {})
    user_class = kwargs.get("user_class", context.get("user_class", "unknown"))
    attributes = {
        "method": request_type,
        "name": name,
        "status": "success" if exception is None else "failure",
        "user_class": user_class,
    }
    request_counter.add(1, attributes)
    request_latency.record((response_time or 0), attributes)


def update_user_count(delta, user_class):
    if locust_users is not None:
        locust_users.add(delta, {"user_class": user_class})
