from unittest import TestCase  # not really unit tests though
import subprocess
from random import randint
from signal import SIGINT
import requests
from functools import partial
from time import sleep
import os

HERE = os.path.dirname(os.path.abspath(__file__))

get_test_config = partial(os.path.join, HERE, "configs")

# shamelessly copied from the gitlab docs
sample_hook_data = """
{
  "object_kind": "push",
  "before": "95790bf891e76fee5e1747ab589903a6a1f80f22",
  "after": "da1560886d4f094c3e6c9ef40349f7d38b5d27d7",
  "ref": "refs/heads/master",
  "checkout_sha": "da1560886d4f094c3e6c9ef40349f7d38b5d27d7",
  "user_id": 4,
  "user_name": "John Smith",
  "user_username": "jsmith",
  "user_email": "john@example.com",
  "user_avatar": "https://s.gravatar.com/avatar/nope",
  "project_id": 15,
  "project":{
    "id": 15,
    "name":"Diaspora",
    "description":"",
    "web_url":"http://example.com/mike/diaspora",
    "avatar_url":null,
    "git_ssh_url":"git@example.com:mike/diaspora.git",
    "git_http_url":"http://example.com/mike/diaspora.git",
    "namespace":"Mike",
    "visibility_level":0,
    "path_with_namespace":"mike/diaspora",
    "default_branch":"master",
    "homepage":"http://example.com/mike/diaspora",
    "url":"git@example.com:mike/diaspora.git",
    "ssh_url":"git@example.com:mike/diaspora.git",
    "http_url":"http://example.com/mike/diaspora.git"
  },
  "repository":{
    "name": "Diaspora",
    "url": "git@example.com:mike/diaspora.git",
    "description": "",
    "homepage": "http://example.com/mike/diaspora",
    "git_http_url":"http://example.com/mike/diaspora.git",
    "git_ssh_url":"git@example.com:mike/diaspora.git",
    "visibility_level":0
  },
  "commits": [
    {
      "id": "b6568db1bc1dcd7f8b4d5a946b0b91f9dacd7327",
      "message": "Update Catalan translation to e38cb41.",
      "timestamp": "2011-12-12T14:27:31+02:00",
      "url": "http://example.com/mike/diaspora/commit/b6568db",
      "author": {
        "name": "Jordi Mallach",
        "email": "jordi@softcatala.org"
      },
      "added": ["CHANGELOG"],
      "modified": ["app/controller/application.rb"],
      "removed": []
    },
    {
      "id": "da1560886d4f094c3e6c9ef40349f7d38b5d27d7",
      "message": "fixed readme",
      "timestamp": "2012-01-03T23:36:29+02:00",
      "url": "http://example.com/mike/diaspora/commit/da15608",
      "author": {
        "name": "GitLab dev user",
        "email": "gitlabdev@dv6700.(none)"
      },
      "added": ["CHANGELOG"],
      "modified": ["app/controller/application.rb"],
      "removed": []
    }
  ],
  "total_commits_count": 4
}"""


class ScriptTests(TestCase):

    def setUp(self):
        # Choose a random (local)host and port
        self.port = randint(32000, 34000)
        self.addr = "127." + ".".join(str(randint(2, 250)) for i in range(3))
        self.config_name = get_test_config("basic.yaml")
        self.proc = subprocess.Popen(("python",
                                      "./gitlab-webhook-receiver.py",
                                      "--cfg", self.config_name,
                                      "--addr", self.addr,
                                      "--port", str(self.port)))
        print("%s:%s (%s)" % (self.addr, self.port, self.config_name))
        # wait a bit for the process to bind
        sleep(1)

    @property
    def url(self):
        """The running server's url"""
        return "http://%s:%s/" % (self.addr, self.port)

    def test_no_token(self):
        """A request without a token must return 401"""
        res = requests.post(self.url, sample_hook_data)
        self.assertEqual(res.status_code, 401)

    def test_wrong_token(self):
        """A request with the wrong token must return 401"""
        res = requests.post(self.url, sample_hook_data,
                            headers={"X-Gitlab-Token": "lol"})
        self.assertEqual(res.status_code, 401)

    def test_right_token(self):
        """A request with the wrong token must return 200"""
        res = requests.post(self.url, sample_hook_data,
                            headers={"X-Gitlab-Token": "test_token"})
        self.assertEqual(res.status_code, 200, res.reason)

    def tearDown(self):
        self.proc.send_signal(SIGINT)
        self.proc.communicate()
