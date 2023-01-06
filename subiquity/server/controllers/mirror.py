# Copyright 2018 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
import copy
import io
import logging
from typing import List, Optional

import attr

from subiquitycore.async_helpers import SingleInstanceTask
from subiquitycore.context import with_context

from subiquity.common.apidef import API
from subiquity.common.types import (
    MirrorCheckResponse,
    MirrorCheckStatus,
    )
from subiquity.server.apt import get_apt_configurer
from subiquity.server.controller import SubiquityController
from subiquity.server.types import InstallerChannels

log = logging.getLogger('subiquity.server.controllers.mirror')


class MirrorCheckNotStartedError(Exception):
    """ Exception to be raised when trying to cancel a mirror
    check that was not started. """


@attr.s(auto_attribs=True)
class MirrorCheck:
    task: asyncio.Task
    output: io.StringIO


class MirrorController(SubiquityController):

    endpoint = API.mirror

    autoinstall_key = "apt"
    autoinstall_schema = {  # This is obviously incomplete.
        'type': 'object',
        'properties': {
            'preserve_sources_list': {'type': 'boolean'},
            'primary': {'type': 'array'},
            'geoip':  {'type': 'boolean'},
            'sources': {'type': 'object'},
            'disable_components': {
                'type': 'array',
                'items': {
                    'type': 'string',
                    'enum': ['universe', 'multiverse', 'restricted',
                             'contrib', 'non-free']
                }
            },
            "preferences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "package": {
                            "type": "string",
                        },
                        "pin": {
                            "type": "string",
                        },
                        "pin-priority": {
                            "type": "integer",
                        },
                    },
                    "required": [
                        "package",
                        "pin",
                        "pin-priority",
                    ],
                }
            }
        }
    }
    model_name = "mirror"

    def __init__(self, app):
        super().__init__(app)
        self.geoip_enabled = True
        self.app.hub.subscribe(InstallerChannels.GEOIP, self.on_geoip)
        self.app.hub.subscribe(
            (InstallerChannels.CONFIGURED, 'source'), self.on_source)
        self.cc_event = asyncio.Event()
        self.configured_event = asyncio.Event()
        self.source_configured_event = asyncio.Event()
        self._apt_config_key = None
        self._apply_apt_config_task = SingleInstanceTask(
            self._promote_mirror)
        self.apt_configurer = None
        self.mirror_check: Optional[MirrorCheck] = None

    def load_autoinstall_data(self, data):
        if data is None:
            return
        geoip = data.pop('geoip', True)
        self.model.load_autoinstall_data(data)
        self.geoip_enabled = geoip and self.model.mirror_is_default()

    @with_context()
    async def apply_autoinstall_config(self, context):
        if not self.geoip_enabled:
            return
        try:
            with context.child('waiting'):
                await asyncio.wait_for(self.cc_event.wait(), 10)
        except asyncio.TimeoutError:
            pass

    def on_geoip(self):
        if self.geoip_enabled:
            self.model.set_country(self.app.geoip.countrycode)
        self.cc_event.set()

    def on_source(self):
        # FIXME disabled until we can sort out umount
        # if self.apt_configurer is not None:
        #     await self.apt_configurer.cleanup()
        self.apt_configurer = get_apt_configurer(
            self.app, self.app.controllers.Source.source_path)
        self._apply_apt_config_task.start_sync()
        self.source_configured_event.set()

    def serialize(self):
        return self.model.get_mirror()

    def deserialize(self, data):
        self.model.set_mirror(data)

    def make_autoinstall(self):
        r = copy.deepcopy(self.model.config)
        r['geoip'] = self.geoip_enabled
        return r

    async def configured(self):
        await super().configured()
        self._apply_apt_config_task.start_sync()
        self.configured_event.set()

    async def _promote_mirror(self):
        await asyncio.gather(self.source_configured_event.wait(),
                             self.configured_event.wait())
        await self.apt_configurer.apply_apt_config(self.context)

    async def run_mirror_testing(self, output: io.StringIO) -> None:
        await self.source_configured_event.wait()
        await self.apt_configurer.apply_apt_config(self.context)
        await self.apt_configurer.run_apt_config_check(output)

    async def wait_config(self):
        await self._apply_apt_config_task.wait()
        return self.apt_configurer

    async def GET(self) -> str:
        return self.model.get_mirror()

    async def POST(self, data: str):
        log.debug(data)
        self.model.set_mirror(data)
        await self.configured()

    async def candidate_POST(self, url: str) -> None:
        log.debug(url)
        self.model.set_mirror(url)

    async def disable_components_GET(self) -> List[str]:
        return sorted(self.model.disabled_components)

    async def disable_components_POST(self, data: List[str]):
        log.debug(data)
        self.model.disabled_components = set(data)

    async def check_mirror_start_POST(self) -> None:
        if self.mirror_check is not None and not self.mirror_check.task.done():
            # TODO
            assert False
        output = io.StringIO()
        self.mirror_check = MirrorCheck(
                task=asyncio.create_task(self.run_mirror_testing(output)),
                output=output)

    async def check_mirror_progress_GET(self) -> MirrorCheckResponse:
        if self.mirror_check is None:
            # TODO
            assert False
        if self.mirror_check.task.done():
            if self.mirror_check.task.exception():
                status = MirrorCheckStatus.FAILED
            else:
                status = MirrorCheckStatus.OK
        else:
            status = MirrorCheckStatus.RUNNING

        return MirrorCheckResponse(
                status=status,
                output=self.mirror_check.output.getvalue())

    async def check_mirror_abort_POST(self) -> None:
        if self.mirror_check is None:
            raise MirrorCheckNotStartedError
        self.mirror_check.task.cancel()
        self.mirror_check = None
