# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
from app.agent import (
    get_destination_details,
    check_travel_advisories,
    get_destination_weather,
    root_agent,
)


def test_agent_tools_registered():
    """Verify all expected tools are registered on root_agent."""
    tool_names = [tool.__name__ for tool in root_agent.tools]
    assert "check_travel_advisories" in tool_names
    assert "get_destination_details" in tool_names
    assert "search_destinations" in tool_names
    assert "get_destination_weather" in tool_names
    assert "generate_destination_image" in tool_names


def test_check_travel_advisories():
    """Verify travel advisory tool fetches and parses real data."""
    result = check_travel_advisories("Portugal")
    assert "country" in result
    assert "advisory_level" in result
    assert "is_safe" in result


def test_get_destination_weather():
    """Verify weather tool fetches live weather from Open-Meteo."""
    result = get_destination_weather("Lisbon")
    assert "destination" in result
    assert "country" in result
    assert "current_temperature_c" in result
    assert "current_temperature_f" in result
