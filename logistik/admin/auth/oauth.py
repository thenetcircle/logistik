import logging
import os
import sys
import traceback
from abc import ABC, abstractmethod

import requests
from flask import redirect
from flask import request
from flask_oauthlib.client import OAuth

from logistik.config import ConfigKeys
from logistik.environ import GNEnvironment


class OAuthBase(ABC):
    @abstractmethod
    def internal_url_for(self, url):
        """pass"""

    @abstractmethod
    def authorized(self):
        """pass"""

    @abstractmethod
    def parse_services(self, services: list) -> set:
        """pass"""

    @abstractmethod
    def check(self, token: str) -> bool:
        """pass"""


class OAuthService(OAuthBase):
    def __init__(self, env: GNEnvironment):
        if env.config.get(ConfigKeys.INSECURE, domain=ConfigKeys.WEB, default=False):
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"

        self.oauth_base = env.config.get(ConfigKeys.OAUTH_BASE, domain=ConfigKeys.WEB)
        self.oauth_path = env.config.get(ConfigKeys.OAUTH_PATH, domain=ConfigKeys.WEB)
        self.service_id = env.config.get(ConfigKeys.SERVICE_ID, domain=ConfigKeys.WEB)
        self.service_secret = env.config.get(
            ConfigKeys.SERVICE_SECRET, domain=ConfigKeys.WEB
        )
        self.authorize_url = env.config.get(ConfigKeys.AUTH_URL, domain=ConfigKeys.WEB)
        self.token_url = env.config.get(ConfigKeys.TOKEN_URL, domain=ConfigKeys.WEB)
        self.callback_url = env.config.get(
            ConfigKeys.CALLBACK_URL, domain=ConfigKeys.WEB
        )
        self.unauthorized_url = env.config.get(
            ConfigKeys.UNAUTH_URL, domain=ConfigKeys.WEB
        )
        self.root_url = env.config.get(ConfigKeys.ROOT_URL, domain=ConfigKeys.WEB)

        self.check_token_url = "{}/{}".format(
            self.oauth_base.rstrip("/"), self.oauth_path.lstrip("/")
        )

        self.logger = logging.getLogger(__name__)
        self.env = env
        self._create_auth_app()

    def internal_url_for(self, url):
        return self.root_url + url

    def authorized(self):
        resp = self.auth.handle_oauth2_response()
        if resp is None or resp.get("access_token") is None:
            return "Access denied: reason=%s error=%s resp=%s" % (
                self._get_request_args("error"),
                self._get_request_args("error_description"),
                resp,
            )
        response = redirect(self.internal_url_for("/index"))
        response.set_cookie("token", resp["access_token"])
        return response

    def parse_services(self, services: list) -> set:
        parsed = set()
        for service in services:
            parsed.add(service["name"].split(",")[0].split("=")[1])
        return parsed

    def check(self, token: str) -> bool:
        response = self._do_post_request(token)

        if response.status_code < 200 or response.status_code >= 400:
            logging.warning(
                "got status code {} response when checking token".format(
                    str(response.status_code)
                )
            )
            return False

        try:
            content = response.json()
            services = self.parse_services(content["scopes"])
            if self.service_id not in services:
                return False
        except Exception as e:
            self.logger.error("could not parse services: {}".format(str(e)))
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return False
        return True

    def _create_auth_app(self):
        """for mocking purposes"""

        self.oauth = OAuth(self.env.app)
        self.auth = self.oauth.remote_app(
            self.service_id,
            consumer_key=self.service_id,
            consumer_secret=self.service_secret,
            base_url=self.oauth_base,
            request_token_params={},
            request_token_url=None,
            access_token_method="POST",
            access_token_url=self.token_url,
            authorize_url=self.authorize_url,
        )

        @self.auth.tokengetter
        def get_sso_token():
            return request.cookies.get("token")

    def _get_request_args(self, key):
        """for mocking purposes"""
        return request.args[key]

    def _do_post_request(self, token: str):
        """for mocking purposes"""
        return requests.post(self.check_token_url % token)
