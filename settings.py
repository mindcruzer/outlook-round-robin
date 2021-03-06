
# The token provider endpoint for your Azure AD tenant.
#
TOKEN_PROVIDER_ENDPOINT = 'https://login.windows.net/00000000-0000-0000-0000-000000000000/oauth2/token'

# The application ID from Azure.
#
CLIENT_ID = 'app_id'

# The application secret from Azure.
#
CLIENT_SECRET = 'app_secret'

# The Azure AD user who's mailbox to watch.
#
MAILBOX_USER = 'mailbox@planetexpress.com'

# The folder to watch for messages to forward.
#
WATCH_FOLDER = 'Inbox'

# Who to forward messages to. This will be round-robin, so the first message 
# loaded from `WATCH_FOLDER` is forwarded to the first person in the list, second 
# message to the second person in the list, etc.
#
FORWARD_TO = [
    ('Bender Bending Rodriguez', 'bender@planetexpress.com'),
    ('Zoidberg', 'zoidberg@planetexpress.com'),
]

# Enable auto-reply to messages.
#
AUTO_REPLY = True

# Sender email addresses that will not be sent an auto-reply. You might want to use this 
# if someone you reply to will also auto reply, and you end up in an infinite loop.
#
AUTO_REPLY_EXCLUSIONS = []

# Subject of auto-reply message.
#
AUTO_REPLY_SUBJECT = 'Your message has been received.'

# Content of auto-reply message.
#
AUTO_REPLY_BODY =\
"""
Hello,

Thank you for your email,
Planet Express Crew

### This is an automated reply ###
"""

# How many unread messages to load from `WATCH_FOLDER` each time it is checked. Set this 
# to something reasonably high so that no messages are skipped.
# 
# ex. `LOAD_MESSAGE_COUNT = 5` would load the 5 newest messages from `WATCH_FOLDER`.
#
LOAD_MESSAGE_COUNT = 250

# How often (in minutes) do you want to check `WATCH_FOLDER` for messages?
# Set this to something reasonable. Ideally >= 1 min.
#
POLL_INTERVAL = 5

# This file stores who should receive the next message from `WATCH_FOLDER`. This allows
# messages to be evenly distributed across `FORWARD_TO`, even in the event of a restart.
#
INDEX_FILE_PATH = 'index.dat'

# The path to the log file. Set this to None to print logs to stdout.
# 
LOG_FILE_PATH = None

# For how many days should logs be kept?
#
LOG_BACKUPS = 14

LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s %(levelname)s %(message)s'
LOG_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
