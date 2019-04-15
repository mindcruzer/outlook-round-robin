import os
import json
import re
from unittest.mock import patch, call
from datetime import datetime, timedelta

import httpretty

import settings
from outlook_round_robin import (
    API_ENDPOINT,
    load_index,
    store_index,
    get_access_token,
    mark_message_as_read,
    forward_message,
    load_messages,
    check_messages
)


MESSAGES_RESPONSE = {'value': [
    {'id': '1', 'subject': 'What\'s the matter? Ya scared?!', 'from': {'emailAddress': {'address': 'roberto@planetexpress.com'}}},
    {'id': '2', 'subject': 'What if... That thing I said', 'from':{'emailAddress': {'address': 'fry@planetexpress.com'}}},
    {'id': '3', 'subject': 'Good news everyone!', 'from': {'emailAddress': {'address': 'professor@planetexpress.com'}}},
]}


def test_load_store_index():
    """
    Index should be persisted and recoverable.
    """
    assert load_index() == 0
    store_index(4)
    assert load_index() == 4
    os.remove(settings.INDEX_FILE_PATH)


@httpretty.activate
def test_get_access_token():
    """
    Access token and renew time should be returned when getting access token succeeds.
    """
    # Arrange
    httpretty.register_uri(
        httpretty.POST, 
        settings.TOKEN_PROVIDER_ENDPOINT, 
        body='{"access_token": "access_token", "expires_in": 3600}', 
        context_type="application/json", 
        status=200
    )

    # Act
    got_token, access_token, renew_token_at = get_access_token()

    # Assert
    assert got_token is True
    assert access_token == "access_token"
    assert timedelta(minutes=50) < (renew_token_at - datetime.now()) < timedelta(minutes=60)


@httpretty.activate
def test_get_access_token_error():
    """
    Error code should be returned when getting an access token fails.
    """
    # Arrange
    httpretty.register_uri(
        httpretty.POST, 
        settings.TOKEN_PROVIDER_ENDPOINT, 
        body='{"error_description": "We\'re boned."}', 
        context_type="application/json", 
        status=400
    )

    # Act
    got_token, _, _ = get_access_token()

    # Assert
    assert got_token is False


@httpretty.activate
def test_mark_message_as_read():
    """
    Success code should be returned when message is successfully marked as read.
    """
    # Arrange
    httpretty.register_uri(
        httpretty.PATCH, 
        API_ENDPOINT + '/users/{}/messages/message_id'.format(settings.MAILBOX_USER), 
        body='', 
        context_type="application/json", 
        status=200
    )

    # Act
    success = mark_message_as_read('message_id', 'access_token')

    # Assert
    assert httpretty.last_request().headers['Authorization'] == 'Bearer access_token'
    assert success is True


@httpretty.activate
def test_mark_message_as_read_error():
    """
    Error code should be returned when there is an error marking a message as read.
    """
    # Arrange
    httpretty.register_uri(
        httpretty.PATCH, 
        API_ENDPOINT + '/users/{}/messages/message_id'.format(settings.MAILBOX_USER), 
        body='{"error": {"message": "We\'re boned."}}', 
        context_type="application/json", 
        status=400
    )

    # Act
    success = mark_message_as_read('message_id', 'access_token')
    
    # Assert
    assert success is False


@httpretty.activate
def test_forward_message():
    """
    Success code should be returned when forwarding a message succeeds.
    """
    # Arrange
    httpretty.register_uri(
        httpretty.POST, 
        API_ENDPOINT + '/users/{}/messages/message_id/forward'.format(settings.MAILBOX_USER), 
        body='', 
        context_type="application/json", 
        status=202
    )

    # Act
    success = forward_message('message_id', 'Zoidberg', 'zoidberg@planetexpress.com', 'access_token')

    # Assert
    assert httpretty.last_request().headers['Authorization'] == 'Bearer access_token'
    assert success is True


@httpretty.activate
def test_forward_message_error():
    """
    Error code should be returned when forwarding a message fails.
    """
    # Arrange
    httpretty.register_uri(
        httpretty.POST, 
        API_ENDPOINT + '/users/{}/messages/message_id/forward'.format(settings.MAILBOX_USER), 
        body='{"error": {"message": "We\'re boned."}}', 
        context_type="application/json", 
        status=400
    )

    # Act
    success = forward_message('message_id', 'Zoidberg', 'zoidberg@planetexpress.com', 'access_token')

    # Assert
    assert success is False


@httpretty.activate
def test_load_messages():
    """
    Message list should be returned when loading messages succeeds.
    """
    # Arrange
    httpretty.register_uri(
        httpretty.GET, 
        API_ENDPOINT + '/users/{}/mailFolders/{}/messages'.format(settings.MAILBOX_USER, settings.WATCH_FOLDER), 
        body=json.dumps(MESSAGES_RESPONSE), 
        context_type="application/json", 
        status=200
    )

    # Act
    success, messages = load_messages('access_token')
    
    # Assert
    assert httpretty.last_request().headers['Authorization'] == 'Bearer access_token'
    assert success is True
    assert len(messages) == 3


@httpretty.activate
def test_load_messages_error():
    """
    Empty message list should be returned when loading messages fails.
    """
    # Arrange
    httpretty.register_uri(
        httpretty.GET, 
        API_ENDPOINT + '/users/{}/mailFolders/{}/messages'.format(settings.MAILBOX_USER, settings.WATCH_FOLDER), 
        body='{"error": {"message": "We\'re boned."}}', 
        context_type="application/json", 
        status=400
    )

    # Act
    success, messages = load_messages('access_token')

    # Assert
    assert success is False
    assert len(messages) == 0


@patch('outlook_round_robin.settings')
@patch('outlook_round_robin.send_reply')
@patch('outlook_round_robin.mark_message_as_read')
@patch('outlook_round_robin.forward_message')
@patch('outlook_round_robin.load_messages')
def test_check_messages(load_mock, forward_mock, mark_mock, reply_mock, settings_mock):
    """
    Messages should be forwarded evenly across recipients.
    """
    # Arrange
    messages = MESSAGES_RESPONSE['value']
    settings_mock.FORWARD_TO = [
        ('Bender', 'bender@planetexpress.com'),
        ('Zoidberg', 'zoidberg@planetexpress.com'),
    ]
    settings_mock.AUTO_REPLY = True
    load_mock.return_value = (True, messages)
    forward_mock.return_value = True
    mark_mock.return_value = True
    reply_mock.return_value = True

    # Act
    stop_index = check_messages(0, 'access_token')

    # Assert
    assert stop_index == 1
    forward_mock.assert_has_calls([
        call('1', 'Bender', 'bender@planetexpress.com', 'access_token'),
        call('2', 'Zoidberg', 'zoidberg@planetexpress.com', 'access_token'),
        call('3', 'Bender', 'bender@planetexpress.com', 'access_token'),
    ])
    mark_mock.assert_has_calls([
        call('1', 'access_token'),
        call('2', 'access_token'),
        call('3', 'access_token'),
    ])
    reply_mock.assert_has_calls([
        call('roberto@planetexpress.com', 'access_token'),
        call('fry@planetexpress.com', 'access_token'),
        call('professor@planetexpress.com', 'access_token'),
    ])


@patch('outlook_round_robin.settings')
@patch('outlook_round_robin.send_reply')
@patch('outlook_round_robin.mark_message_as_read')
@patch('outlook_round_robin.forward_message')
@patch('outlook_round_robin.load_messages')
def test_check_messages_error_loading_messages(load_mock, forward_mock, mark_mock, reply_mock, settings_mock):
    """
    Nothing should happen when loading the message list fails.
    """
    # Arrange
    settings_mock.FORWARD_TO = [
        ('Bender', 'bender@planetexpress.com'),
        ('Zoidberg', 'zoidberg@planetexpress.com'),
    ]
    load_mock.return_value = (False, [])
    forward_mock.return_value = True
    mark_mock.return_value = True
    reply_mock.return_value = True

    # Act
    stop_index = check_messages(0, 'access_token')

    # Assert
    assert stop_index == 0
    assert forward_mock.called is False
    assert mark_mock.called is False


@patch('outlook_round_robin.settings')
@patch('outlook_round_robin.send_reply')
@patch('outlook_round_robin.mark_message_as_read')
@patch('outlook_round_robin.forward_message')
@patch('outlook_round_robin.load_messages')
def test_check_messages_forward_error(load_mock, forward_mock, mark_mock, reply_mock, settings_mock):
    """
    If forwarding a message fails, it should not get marked as read.
    """
    # Arrange
    messages = MESSAGES_RESPONSE['value']
    settings_mock.FORWARD_TO = [
        ('Bender', 'bender@planetexpress.com'),
        ('Zoidberg', 'zoidberg@planetexpress.com'),
    ]
    load_mock.return_value = (True, messages)
    forward_mock.return_value = False
    mark_mock.return_value = True
    reply_mock.return_value = True

    # Act
    stop_index = check_messages(0, 'access_token')

    # Assert
    assert stop_index == 0
    forward_mock.assert_has_calls([
        call('1', 'Bender', 'bender@planetexpress.com', 'access_token'),
        call('2', 'Bender', 'bender@planetexpress.com', 'access_token'),
        call('3', 'Bender', 'bender@planetexpress.com', 'access_token'),
    ])
    assert mark_mock.called is False 


@patch('outlook_round_robin.settings')
@patch('outlook_round_robin.send_reply')
@patch('outlook_round_robin.mark_message_as_read')
@patch('outlook_round_robin.forward_message')
@patch('outlook_round_robin.load_messages')
def test_check_messages__auto_reply_off(load_mock, forward_mock, mark_mock, reply_mock, settings_mock):
    """
    No auto-replies should be sent when AUTO_REPLY is False.
    """
    # Arrange
    messages = MESSAGES_RESPONSE['value']
    settings_mock.FORWARD_TO = [
        ('Bender', 'bender@planetexpress.com'),
        ('Zoidberg', 'zoidberg@planetexpress.com'),
    ]
    settings_mock.AUTO_REPLY = False
    load_mock.return_value = (True, messages)
    forward_mock.return_value = True
    mark_mock.return_value = True
    reply_mock.return_value = True

    # Act
    stop_index = check_messages(0, 'access_token')

    # Assert
    assert stop_index == 1
    forward_mock.assert_has_calls([
        call('1', 'Bender', 'bender@planetexpress.com', 'access_token'),
        call('2', 'Zoidberg', 'zoidberg@planetexpress.com', 'access_token'),
        call('3', 'Bender', 'bender@planetexpress.com', 'access_token'),
    ])
    mark_mock.assert_has_calls([
        call('1', 'access_token'),
        call('2', 'access_token'),
        call('3', 'access_token'),
    ])
    assert reply_mock.called is False


@patch('outlook_round_robin.settings')
@patch('outlook_round_robin.send_reply')
@patch('outlook_round_robin.mark_message_as_read')
@patch('outlook_round_robin.forward_message')
@patch('outlook_round_robin.load_messages')
def test_check_messages__auto_reply_exclusions(load_mock, forward_mock, mark_mock, reply_mock, settings_mock):
    """
    No auto-replies should be sent to senders who are in the AUTO_REPLY_EXCLUSIONS list.
    """
    # Arrange
    messages = MESSAGES_RESPONSE['value']
    settings_mock.FORWARD_TO = [
        ('Bender', 'bender@planetexpress.com'),
        ('Zoidberg', 'zoidberg@planetexpress.com'),
    ]
    settings_mock.AUTO_REPLY = True
    settings_mock.AUTO_REPLY_EXCLUSIONS = ['fry@planetexpress.com']
    load_mock.return_value = (True, messages)
    forward_mock.return_value = True
    mark_mock.return_value = True
    reply_mock.return_value = True

    # Act
    stop_index = check_messages(0, 'access_token')

    # Assert
    assert stop_index == 1
    forward_mock.assert_has_calls([
        call('1', 'Bender', 'bender@planetexpress.com', 'access_token'),
        call('2', 'Zoidberg', 'zoidberg@planetexpress.com', 'access_token'),
        call('3', 'Bender', 'bender@planetexpress.com', 'access_token'),
    ])
    mark_mock.assert_has_calls([
        call('1', 'access_token'),
        call('2', 'access_token'),
        call('3', 'access_token'),
    ])
    reply_mock.assert_has_calls([
        call('roberto@planetexpress.com', 'access_token'),
        call('professor@planetexpress.com', 'access_token'),
    ])


@patch('outlook_round_robin.settings')
@patch('outlook_round_robin.send_reply')
@patch('outlook_round_robin.mark_message_as_read')
@patch('outlook_round_robin.forward_message')
@patch('outlook_round_robin.load_messages')
def test_check_messages__auto_reply_error(load_mock, forward_mock, mark_mock, reply_mock, settings_mock):
    """
    Any errors encountered when sending auto-reply messages should be ignored.
    """
    # Arrange
    messages = MESSAGES_RESPONSE['value']
    settings_mock.FORWARD_TO = [
        ('Bender', 'bender@planetexpress.com'),
        ('Zoidberg', 'zoidberg@planetexpress.com'),
    ]
    settings_mock.AUTO_REPLY = True
    load_mock.return_value = (True, messages)
    forward_mock.return_value = True
    mark_mock.return_value = True
    reply_mock.return_value = True

    # Act
    stop_index = check_messages(0, 'access_token')

    # Assert
    assert stop_index == 1
    forward_mock.assert_has_calls([
        call('1', 'Bender', 'bender@planetexpress.com', 'access_token'),
        call('2', 'Zoidberg', 'zoidberg@planetexpress.com', 'access_token'),
        call('3', 'Bender', 'bender@planetexpress.com', 'access_token'),
    ])
    mark_mock.assert_has_calls([
        call('1', 'access_token'),
        call('2', 'access_token'),
        call('3', 'access_token'),
    ])
    reply_mock.assert_has_calls([
        call('roberto@planetexpress.com', 'access_token'),
        call('fry@planetexpress.com', 'access_token'),
        call('professor@planetexpress.com', 'access_token'),
    ])
