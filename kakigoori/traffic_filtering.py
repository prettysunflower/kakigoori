import json
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from django.http import HttpRequest, HttpResponseForbidden


class TrafficRuleAction(Enum):
    DENY = "DENY"
    ALLOW = "ALLOW"
    NO_ACTION = "NO_ACTION"


@dataclass
class TrafficRule:
    name: str
    user_agent_regex: re.Pattern
    action: TrafficRuleAction

    def test_rule(self, request: HttpRequest):
        user_agent = request.META.get("HTTP_USER_AGENT") or None
        if user_agent is None:
            return TrafficRuleAction.DENY

        print(user_agent)

        if self.user_agent_regex.search(user_agent) is not None:
            print("FOUND, RETURNING ACTINO")
            return self.action

        return TrafficRuleAction.NO_ACTION


class TrafficFiltering:
    traffic_rules = []

    def __init__(self, get_response):
        self.get_response = get_response

        with open(
            os.path.join(Path(__file__).resolve().parent, "traffic_rules.json")
        ) as f:
            traffic_rules_json = json.load(f)

        for rule in traffic_rules_json["rules"]:
            # noinspection PyTypeChecker
            self.traffic_rules.append(
                TrafficRule(
                    rule["name"],
                    re.compile(rule["user_agent_regex"]),
                    TrafficRuleAction[rule["action"]],
                )
            )

    def __call__(self, request: HttpRequest):
        for traffic_rule in self.traffic_rules:
            print(f"Checking for {traffic_rule.name}")
            action = traffic_rule.test_rule(request)
            print(action)
            match action:
                case TrafficRuleAction.DENY:
                    return HttpResponseForbidden()
                case TrafficRuleAction.ALLOW:
                    break
                case TrafficRuleAction.NO_ACTION:
                    continue

        response = self.get_response(request)
        return response
