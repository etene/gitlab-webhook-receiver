#! /usr/bin/env python
# -*- coding: utf-8 -*-

""" Gitlab Webhook Receiver """
# Based on: https://github.com/schickling/docker-hook

import sys
import logging
import json
import subprocess

from string import Template
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

try:
    # For Python 3.0 and later
    from http.server import HTTPServer
    from http.server import BaseHTTPRequestHandler
except ImportError:
    # Fall back to Python 2
    from BaseHTTPServer import BaseHTTPRequestHandler
    from BaseHTTPServer import HTTPServer as HTTPServer

import yaml

CONFIG = None

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                    level=logging.DEBUG,
                    stream=sys.stdout)


class RequestHandler(BaseHTTPRequestHandler):
    """A POST request handler."""

    def do_POST(self):
        logging.info("Hook received")

        # get payload
        header_length = int(self.headers.getheader('content-length', "0"))
        json_payload = self.rfile.read(header_length)
        json_params = {}
        if json_payload:
            json_params = json.loads(json_payload)

        # get project configuration
        project = json_params['project']['homepage']
        try:
            project_config = CONFIG[project]
        except KeyError as ker:
            self.send_response(400, "Unknown project %r" % ker)
            self.end_headers()
            return

        # Fetch the project's gitlab token in configuration
        try:
            gitlab_token = project_config['gitlab_token']
        except KeyError as ker:
            self.send_response(500, "No gitlab token in project configuration")
            self.end_headers()
            return

        # Check it
        if gitlab_token != self.headers.getheader('X-Gitlab-Token'):
            self.send_response(401, "Invalid token")
            self.end_headers()
            return

        # A dict of values that can be substitued on the command line
        available_params = {
            "event": json_params.get("object_kind"),
            "sha": json_params.get("checkout_sha"),
            "user": json_params.get("user_username"),
            "ref": json_params.get("ref"),
            "project_name": json_params["project"]["name"],
            "project_owner": json_params["project"]["namespace"],
        }
        logging.debug("Available variable substitions: %s", available_params)

        # Get the command to call
        try:
            # Substitute $variable => available_params["variable"]
            command = [Template(i).substitute(**available_params)
                       for i in project_config.get("command", ())]
        except KeyError as err:
            self.send_response(500, "Invalid substitution %s in command" % err)
            self.end_headers()
            self.wfile.write("Available substitutions: %s\n"
                             % ", ".join(available_params))
            return
        if not command:
            self.send_response(500, "No command defined for project")
            self.end_headers()
            return

        logging.info("Calling %s", " ".join(command))
        try:
            subprocess.Popen(command)
        except OSError as ose:
            self.send_response(500, "Could not call command: %s" % ose)
            self.end_headers()
            return
        self.send_response(200, "Hook command called")
        self.end_headers()


def get_parser():
    """Get a command line parser."""
    parser = ArgumentParser(description=__doc__,
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument("--addr",
                        dest="addr",
                        default="0.0.0.0",
                        help="address where it listens")
    parser.add_argument("--port",
                        dest="port",
                        type=int,
                        default=8666,
                        help="port where it listens")
    parser.add_argument("--cfg",
                        dest="cfg",
                        default="config.yaml",
                        help="path to the config file")
    return parser


def main():
    global CONFIG  # FIXME XXX TODO YUCK
    parser = get_parser()

    args = parser.parse_args()

    # load config file
    try:
        with open(args.cfg, 'r') as stream:
            CONFIG = yaml.load(stream)
    except IOError as err:
        logging.error("Config file %s could not be loaded: %s", args.cfg, err)
        sys.exit(1)
    httpd = HTTPServer((args.addr, args.port), RequestHandler)
    httpd.serve_forever()


if __name__ == '__main__':
    main()
