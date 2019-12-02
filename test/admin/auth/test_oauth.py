from unittest import TestCase

import werkzeug.wrappers

from logistik.admin.auth.oauth import OAuthService
from logistik.config import ConfigKeys
from test.base import MockEnv, MockResponse


class MockAuth:
    def handle_oauth2_response(self):
        return {
            'access_token': 'very-legit-token'
        }


class OauthTest(TestCase):
    def setUp(self) -> None:
        self.env = MockEnv()
        self.root_url = 'http://some-url.com'
        self.env.config.set(ConfigKeys.OAUTH_BASE, self.root_url, domain=ConfigKeys.WEB)
        self.env.config.set(ConfigKeys.OAUTH_PATH, '/some-path', domain=ConfigKeys.WEB)
        self.env.config.set(ConfigKeys.ROOT_URL, self.root_url, domain=ConfigKeys.WEB)
        self.oauth = OAuthService(self.env)
        self.oauth.service_id = '1'
        self.oauth._get_request_args = lambda key: key
        self.oauth._do_post_request = \
            lambda token: MockResponse(200, {'scopes': [{'name': 'foo=1,bar=2'},{'name': 'baz=3'}]})
        self.oauth.auth = MockAuth()

    def test_internal_url_for(self):
        url = self.oauth.internal_url_for('/asdf')
        self.assertEqual('{}/{}'.format(self.root_url, 'asdf'), url)

    def test_authorized(self):
        response = self.oauth.authorized()
        self.assertTrue(type(response) == werkzeug.wrappers.Response)
        self.assertEqual(response.status_code, 302)

    def test_not_authorized(self):
        def not_authed():
            return dict()

        self.oauth.auth.handle_oauth2_response = not_authed

        response = self.oauth.authorized()
        self.assertTrue(type(response) == str)
        self.assertTrue(response.startswith('Access denied'))

    def test_parse_services_empty(self):
        services = []
        parsed = self.oauth.parse_services(services)
        self.assertEqual(0, len(parsed))

    def test_parse_services(self):
        services = [
            {'name': 'foo=1,bar=2'},
            {'name': 'baz=3'}
        ]
        parsed = self.oauth.parse_services(services)
        self.assertTrue('1' in parsed)
        self.assertFalse('2' in parsed)
        self.assertTrue('3' in parsed)
        self.assertTrue(len(parsed), 2)

    def test_check(self):
        self.assertTrue(self.oauth.check('token'))

    def test_check_not_200(self):
        def fail_post(_):
            return MockResponse(403)

        self.oauth._do_post_request = fail_post
        self.assertFalse(self.oauth.check('token'))

    def test_check_wrong_service_id(self):
        self.oauth.service_id = 'something-else'
        self.assertFalse(self.oauth.check('token'))

    def test_check_parse_fails(self):
        def parse_raises(_):
            raise RuntimeError()

        self.oauth.parse_services = parse_raises
        self.assertFalse(self.oauth.check('token'))
