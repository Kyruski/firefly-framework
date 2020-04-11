#  Copyright (c) 2019 JD Williams
#
#  This file is part of Firefly, a Python SOA framework built by JD Williams. Firefly is free software; you can
#  redistribute it and/or modify it under the terms of the GNU General Public License as published by the
#  Free Software Foundation; either version 3 of the License, or (at your option) any later version.
#
#  Firefly is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
#  implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#  Public License for more details. You should have received a copy of the GNU Lesser General Public
#  License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#  You should have received a copy of the GNU General Public License along with Firefly. If not, see
#  <http://www.gnu.org/licenses/>.

from __future__ import annotations

import atexit
import errno
import importlib.util
import json
import os
import shlex
import signal
import subprocess
import sys
from time import sleep
from typing import Optional

import firefly.domain as ffd
import firefly.infrastructure as ffi


class DefaultAgent(ffd.Agent, ffd.LoggerAware):
    _web_server: ffi.WebServer = None
    _config: ffd.Configuration = None

    def __init__(self):
        self._deployment: Optional[ffd.Deployment] = None

    def handle(self, deployment: ffd.Deployment, start_server: bool = True, start_web_app: bool = True, **kwargs):
        self._deployment = deployment
        self._web_server.add_extension(self._register_gateways)

        if start_web_app:
            self.info('Starting web app')
            self._start_web_app()

        if start_server:
            self.info('Starting web server')
            self._web_server.run()

    def _register_gateways(self, web_server: ffi.WebServer):
        for api_gateway in self._deployment.api_gateways:
            for endpoint in api_gateway.endpoints:
                web_server.add_endpoint(endpoint.method, endpoint.route, endpoint.message)

    def _start_web_app(self):
        self._compile_web_app()
        cmd = 'webpack-dev-server -w --mode development --env local'
        webpack = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, bufsize=0
        )

        def stop_webpack(a=None, b=None):
            try:
                os.killpg(webpack.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

        atexit.register(stop_webpack)
        signal.signal(signal.SIGTERM, stop_webpack)
        signal.signal(signal.SIGINT, stop_webpack)

        while True:
            output = webpack.stdout.readline()
            if output:
                print(output.decode().rstrip())
                if 'Compiled successfully' in output.decode() or 'Compiled with warnings' in output.decode():
                    break
            if webpack.poll() is not None:
                break
            sys.stdout.flush()

    def _compile_web_app(self):
        modules = []
        for name, context in self._config.contexts.items():
            module_name = f'{name}_web.admin'
            if importlib.util.find_spec(module_name) is not None:
                modules.append(module_name)
            module_name = f'{name}_web.app'
            if importlib.util.find_spec(module_name) is not None:
                modules.append(module_name)

        self._create_build_files(modules)
        self._transpile('build.entry')

    @staticmethod
    def _create_build_files(modules: list):
        try:
            os.mkdir('build')
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        with open('build/app.py', 'w') as fp:
            for module in modules:
                if '_web.app' in module:
                    fp.write(f'import {module}\n')

        with open('build/admin.py', 'w') as fp:
            fp.write('import firefly_web.app\n')
            for module in modules:
                if '_web.admin' in module:
                    fp.write(f'import {module}\n')

        with open('build/entry.py', 'w') as fp:
            fp.write('import build.app\n')
            fp.write('import build.admin\n')

    def _transpile(self, module_name: str):
        cmd = f'. ./venv/bin/activate && ' \
              f'./venv/bin/python3 -m transcrypt --nomin --map --fcall --verbose "{module_name}"'
        self.info(os.system(cmd))