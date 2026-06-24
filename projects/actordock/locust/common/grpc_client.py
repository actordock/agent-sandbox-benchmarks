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

import grpc
from . import runtimeapi_pb2_grpc

API_HOST = "api.actordock-system.svc.cluster.local:443"
API_SNI = "api.actordock-system.svc"
CA_PATH = "/run/servicedns-ca/ca.crt"


def control_stub():
    with open(CA_PATH, "rb") as f:
        ca_cert = f.read()
    options = [("grpc.ssl_target_name_override", API_SNI)]
    channel = grpc.secure_channel(
        API_HOST,
        grpc.ssl_channel_credentials(root_certificates=ca_cert),
        options=options,
    )
    return channel, runtimeapi_pb2_grpc.ControlStub(channel)
