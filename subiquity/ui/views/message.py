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

"""Message

Message display text from file to the user
"""

import logging

from urwid import Text, LineBox

from subiquitycore.ui.buttons import forward_btn, other_btn
from subiquitycore.ui.utils import rewrap, screen
from subiquitycore.view import BaseView

log = logging.getLogger("subiquity.ui.views.message")


class MessageView(BaseView):
    title = "Message Title"
    msg = "Default message text"

    def __init__(self, controller, title_text, message_text):
        self.controller = controller
        self.title = title_text
        self.msg = message_text
        super().__init__(self.make_msg())

    def make_msg(self):
        self.agree_btn = forward_btn(
                label="Agree",
                on_press=self.agree_mode)
        self.cancel_btn = other_btn(
                label="Do Not Agree",
                on_press=self.disagree_mode)
        btns = [self.agree_btn, self.cancel_btn]
        widgets = [
            Text(""),
            LineBox(Text(rewrap(self.msg))),
            Text(""),
        ]
        return screen(widgets, btns)

    def agree_mode(self, sender):
        self.controller.done(True)

    def disagree_mode(self, sender):
        self.controller.cancel(True)
