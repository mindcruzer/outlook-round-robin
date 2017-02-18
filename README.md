# Outlook Round-Robin
Watches a folder in a user's mailbox for messages, which are 
forwarded to a list of recipients in a round-robin fashion.

## Requirements
- Python 3

## How it works
This script will check the configured mailbox folder for *unread* emails at whichever interval you choose. When it finds 
some, it forwards them, round-robin, to a list of recipients. Once it has forwarded a message, it marks the message 
as *read*. Take note of that last part. If you go into the mailbox and start clicking around new messages, effectively 
marking them as read, the script will not forward them. 

## Y tho?
Well, I have a client that uses a third-party service which reports customer orders to them via email, but the problem is all the 
orders go to one mailbox, and volume is fairly high. Rather than paying someone to distribute the emails among a set of `n` employees, 
or worse, having one person process all those orders, they explained their predicament to me and I made them this script. 

## Setup
This uses the Microsoft Graph REST API to access the contents of a user's mailbox. For authentication, the 
original Azure Active Directory authentication endpoint is used, which means this only works with work and 
school accounts, not personal accounts.

The first thing you need to do is register an application with Azure AD. You can find the details of that [here](https://graph.microsoft.io/en-us/docs/authorization/app_only) 
under the `Register the application in Azure Active Directory` section. For permissions, select the `Microsoft Graph` API, and choose the 
following *Application* permissions:
- Read mail in all mailboxes
- Read and write mail in all mailboxes
- Send mail as any user

Once that's done, add the following values from your application registration to `settings.py`:
- `TOKEN_PROVIDER_ENDPOINT = "[Your app's OAuth 2.0 token endpoint]"`
- `CLIENT_ID = "[Application ID]"`
- `CLIENT_SECRET = "[The secret you created for the application]"`

Some other settings you'll want to modify are `MAILBOX_USER` and `FORWARD_TO`.

*Theoretically* the script should now work if you run `$ python3 outlook_round_robin.py`, **but before 
you do this** I recommend you find these two lines in `outlook_round_robin.py`:

```
if forward_message(message['id'], forward_name, forward_email, access_token):
    mark_message_as_read(message['id'], access_token)
```

... and comment them out. Run the script, view the log output to make sure everything looks good, then uncomment and do it live. 
That being said, this script doesn't do anything destructive, so don't be too paranoid.

## Test
```
$ pip3 install -r test/requirements.txt
$ python3 -m pytest
```

## Deployment
This is mostly up to you. What *I* did was fire up a `t2.nano` on AWS and set the script up as a systemd service. Here is a sample systemd 
service file that you might use to run this script in the background. It will automatically start the script at boot, and restart it if the 
process crashes. 

```
[Unit]
Description=Outlook Round-Robin
After=network.target

[Service]
User=ubuntu
Group=ubuntu
Type=idle
Restart=always
WorkingDirectory=/home/ubuntu/outlook-round-robin
ExecStart=/usr/bin/python3 /home/ubuntu/outlook-round-robin/outlook_round_robin.py

[Install]
WantedBy=multi-user.target
```

For Ubuntu 16.10, you would put this in `/etc/systemd/system/outlook_round_robin.service`. Then run:

```
$ systemd enable outlook_round_robin.service
$ systemd daemon-reload
$ systemd restart outlook_round_robin.service
```

## Monitoring
Another thing you'll probably want to do is get notified when errors occur. One way you can do this is by adding a second [log handler that emails you](https://docs.python.org/3/library/logging.handlers.html#smtphandler) log messages at a configured log level. This has one caveat: if the network goes 
down for your server, you will never know (until someone realizes they're no longer receiving forwards).

If you're on AWS, a better (and dirt cheap) solution is to push the logs to [CloudWatch](http://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/QuickStartEC2Instance.html). You can configure a log metric, and an alarm for that metric. Note that you'll want two filters for your log metric: 
- One matching `" ERROR "`, and a value of `1`
- Another matching everything, and a value of `0`

If you only configure the first filter your alarm will never leave the `INSUFFICIENT_DATA` state. With that in place, you'll want two notifications set up on your alarm: 
- One for the `ALARM` state. If this state is reached, error(s) have been logged. 
- One for the `INSUFFICIENT_DATA` state. If this state is reached, logs are no longer reaching CloudWatch, so something is likely wrong with your server.

## Notes
- You do *not* want an unauthorized person getting access to `CLIENT_ID` and `CLIENT_SECERET`, so secure your server.
- Don't run more than one instance of this script on a mailbox folder.
