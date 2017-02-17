"""
Outlook Round-Robin
------------
Watches a folder in a user's mailbox for messages. Messages are 
forwarded to a list of recipients in a round-robin fashion.
"""
from datetime import datetime, timedelta
from time import sleep
import logging
import logging.handlers
import signal
import sys

import requests
import settings


API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
logger = logging.getLogger(__name__)


class MSGraphAuth(requests.auth.AuthBase):
    """
    Adds the Microsoft Graph access token to a request.
    """
    def __init__(self, access_token):
        self.access_token = access_token

    def __call__(self, request):
        request.headers['Authorization'] = "Bearer {}".format(self.access_token)
        return request


def store_index(index):
    """
    Stores an integer in the file at `DATA_FILE_PATH`.
    """
    try:
        with open(settings.DATA_FILE_PATH, 'w') as data_file:
            data_file.write('{}\n'.format(index))
    except:
        pass


def load_index():
    """
    Retrieves an integer from the file at `DATA_FILE_PATH`.

    Returns the value in the file, if the file is read successfully; 0 otherwise.
    """
    try:
        with open(settings.DATA_FILE_PATH, 'r') as data_file:
            return int(data_file.readline())
    except:
        return 0


def get_access_token():
    """
    Requests an access token from Azure AD.

    Returns (True, [access token]) on success; (False, "") otherwise.
    """
    response = requests.post(settings.TOKEN_PROVIDER_ENDPOINT, data={
        'client_id': settings.CLIENT_ID,
        'client_secret': settings.CLIENT_SECRET,
        'resource': 'https://graph.microsoft.com',
        'grant_type': 'client_credentials'
    })

    data = response.json()

    if response.status_code == 200:
        logger.info('Got access token.')
        expires_seconds = int(data['expires_in'])
        # set renewal time to 5 minutes before expiry, just to be safe
        return True, data['access_token'], datetime.now() + timedelta(seconds=expires_seconds - 300) 
    else:
        logger.error('Error getting access token: {}'.format(data['error_description']))
        return False, "", None


def mark_message_as_read(message_id, access_token):
    """
    Marks a message as read.

    Returns True on success; False otherwise.
    """
    logger.info('Marking message as read...')
    logger.debug('Message id: {}'.format(message_id))

    response = requests.patch(API_ENDPOINT + '/users/{}/messages/{}'.format(settings.MAILBOX_USER, message_id), json={
        'isRead': True
    }, auth=MSGraphAuth(access_token))

    if response.status_code == 200:
        logger.info('Message successfully updated.')
    else:
        data = response.json()
        logger.error('Error updating message: {}'.format(data['error']['message']))
        return False


def forward_message(message_id, recipient_name, recipient_email, access_token):
    """
    Forwards a message to a recipient.

    Returns True on success; False otherwise.
    """
    logger.info('Forwaring message to {}...'.format(recipient_email))
    logger.debug('Message id: {}'.format(message_id))

    response = requests.post(API_ENDPOINT + '/users/{}/messages/{}/forward'.format(settings.MAILBOX_USER, message_id), json={
        'comment': '',
        'toRecipients': [ 
            {
                'emailAddress': {
                    'address': recipient_email,
                    'name': recipient_name
                }
            }
        ]
    }, auth=MSGraphAuth(access_token))

    if response.status_code == 202:
        logger.info('Message successfully forwarded.')
        return True
    else:
        data = response.json()
        logger.error('Error forwarding message: {}'.format(data['error']['message']))
        return False


def load_messages(access_token):
    """
    Loads unread messages from the mailbox folder. Note that only the message `id` and 
    `subject` are retrieved.

    Returns (True, messages) on success; (False, []) otherwise.
    """
    logger.info('Getting {} newest messages from {}\'s {} folder...'.format(
        settings.LOAD_MESSAGE_COUNT,
        settings.MAILBOX_USER, 
        settings.WATCH_FOLDER
    ))

    endpoint = API_ENDPOINT + '/users/{}/mailFolders/{}/messages'.format(settings.MAILBOX_USER, settings.WATCH_FOLDER)
    response = requests.get(endpoint, params={
        '$filter': 'isRead eq false',
        '$top': settings.LOAD_MESSAGE_COUNT,
        '$select':  'id,subject'
    }, auth=MSGraphAuth(access_token)) 

    data = response.json()

    if response.status_code == 200:
        messages = data['value']
        logger.info('Loaded {} messages from inbox.'.format(len(messages)))
        return True, messages
    else:
        logger.error('Error getting messages: {}'.format(data['error']['message']))
        return False, []


def process_messages(start_index, access_token):
    """
    Forwards unread messages to the list of users in `FORWARD_TO`. Forwarded messages 
    are then marked as read. 

    Returns the next index in `FORWARD_TO` that should be used.
    """
    got_messages, messages = load_messages(access_token)
        
    if not got_messages:
        return start_index

    stop_index = start_index

    for message in messages:
        forward_name, forward_email = settings.FORWARD_TO[stop_index]
            
        logger.info('Processing message for {}: {}'.format(forward_email, message['subject']))

        if forward_message(message['id'], forward_name, forward_email, access_token):
            mark_message_as_read(message['id'], access_token)
        
        stop_index = (stop_index + 1) % len(settings.FORWARD_TO)
        sleep(0.25)

    return stop_index


if __name__ == "__main__":
    def exit_handler(signal, frame):
        print('Exiting...')
        exit(0)
    
    signal.signal(signal.SIGINT, exit_handler)
    
    if settings.LOG_FILE_PATH:
        log_handler = logging.handlers.TimedRotatingFileHandler(settings.LOG_FILE_PATH, 'midnight', 1, 
                                                                backupCount=settings.LOG_BACKUPS)
    else:
        log_handler = logging.StreamHandler(stream=sys.stdout)
        
    log_formatter = logging.Formatter(settings.LOG_FORMAT)
    log_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)
    logger.setLevel(logging.DEBUG)

    renew_token_at = datetime.now()

    while True:
        if renew_token_at <= datetime.now():
            logger.info('Renewing token...')
            got_token, access_token, renew_token_at = get_access_token()
            
            if not got_token: 
                exit()
        
        logger.info('Checking messages...')
        
        start_index = load_index()
        stop_index = process_messages(start_index, access_token)
        store_index(stop_index)

        sleep(settings.POLL_INTERVAL * 60)