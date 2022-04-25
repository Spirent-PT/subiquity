# Copyright 2021 Canonical, Ltd.
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

import aiohttp
import logging
import os

from subiquity.client.controller import SubiquityTuiController
from subiquity.ui.views.message import MessageView
from subiquitycore.tuicontroller import Skip
from subiquitycore.utils import run_command
from subiquity.common.types import (
    ApplicationState,
    ShutdownMode,
    )

log = logging.getLogger('subiquity.client.controllers.message')

class MessageController(SubiquityTuiController):
    def read_message_file(self, path = "/cdrom/nocloud/script/message.txt"):
        msg = "Default message text"
        if os.path.isfile(path):
            with open(path, "r") as f:
                msg = f.read()
        else:
            log.debug("MessageController.read_message_file failed to read: {}".format(path))
        return msg

    async def make_ui(self):
        msg = self.read_message_file()
        return MessageView(self, "Message Title", msg)

    def run_answers(self):
        if 'agree' in self.answers:
            if self.answers['agree']:
                self.ui.body.agree_btn.base_widget._emit('click')
            else:
                self.ui.body.cancel_btn.base_widget._emit('click')

    async def close(self):
        try:
            await self.app.client.shutdown.POST(mode=ShutdownMode.REBOOT)
        except aiohttp.ClientError as e:
            log.error("MessageController.close {}".format(e))
        self.app.exit()

    def done(self, done):
        log.debug("MessageController.done {}".format(done))
        self.app.next_screen()

    def cancel(self, done):
        # Can't go back from here!
        log.debug("MessageController.cancel {}".format(done))
        self.app.aio_loop.create_task(self.close())
        