"""Optional personality replies. These never validate answers or move a gate."""

import re
from collections import OrderedDict

KEY_SHARING_WARNING = 'dont put that in a public channel'
REPEAT_REPLY = 'sending it twice doesnt make it more correct'


class SupportChatter:
    def __init__(self):
        self.recent = OrderedDict()

    def reply(self, user_id, conversation, message, *, remember=True, allow_repeat=True):
        """Conversation identity resets repeats; undelivered answers aren't saved."""
        text = ' '.join(message.strip().casefold().split())
        previous = self.recent.get(user_id)
        repeated = (
            remember
            and previous is not None
            and previous[0] is conversation
            and previous[1] == text
        )
        if remember:
            self.recent[user_id] = (conversation, text)
            self.recent.move_to_end(user_id)
            if len(self.recent) > 1024:
                self.recent.popitem(last=False)
        if text and repeated and allow_repeat:
            return REPEAT_REPLY
        if re.fullmatch(r'are you (?:really )?(?:a |an )?(?:bot|robot|ai)[?!.]*', text):
            return 'no, bots get paid more than me'
        return None


def casual_reply(chatter, user_id, message):
    """Top-level DMs have no verification context and never consume an answer."""
    reply = chatter.reply(user_id, chatter, message)
    if reply:
        return reply
    if mentions_technology(message):
        return 'thats a work in progress. file a ticket and ill check it later'
    return 'what did you need a hand with?'


def mentions_technology(message):
    # The caller strips email addresses so a backup address is never an aside.
    return bool(
        re.search(
            r'\b(?:internal (?:hosts?|network)|vpn|authentik|idp|identity provider|'
            r'oidc|oauth2?|grafana|postgres(?:ql)?|proxmox|dns|ssrf|'
            r'docker|nginx|redis|mysql|ssh|ci|registry|kubernetes|'
            r'build (?:server|runner)|printer|print queue|minecraft)\b',
            message,
            re.I,
        )
    )
