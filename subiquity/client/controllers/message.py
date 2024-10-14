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

import logging
import os
import json

from subiquity.client.controller import SubiquityTuiController
from subiquity.ui.views.message import MessageView

log = logging.getLogger('subiquity.client.controllers.message')

class MessageController(SubiquityTuiController):
    def read_message_file(self, path="/cdrom/nocloud/files/message.json"):
        msg_obj = json.loads(
            '{"title": "Message Title", "text": "Default message text"}')
        if os.path.isfile(path):
            with open(path, "r") as f:
                msg = f.read()
                if not msg is None:
                    if not msg == '':
                        msg_obj = json.loads(msg)
        else:
            log.debug("MessageController.read_message_file failed to read: %s",
                      format(path))
        return msg_obj

    async def make_ui(self):
        msg = self.read_message_file()
        return MessageView(self, msg['title'], msg['text'])

    def run_answers(self):
        if 'agree' in self.answers:
            if self.answers['agree']:
                self.ui.body.agree_btn.base_widget._emit('click')
            else:
                self.ui.body.cancel_btn.base_widget._emit('click')

    def done(self):
        log.debug("MessageController.done")
        self.app.next_screen()

    def cancel(self):
        # Can't go back from here!
        log.debug("MessageController.cancel")
        os.system('/usr/sbin/poweroff')
