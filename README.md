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
under the `Register the application in Azure Active Directory` section. 

Once that's done, rename `settings.py.example` to `settings.py` and add the following values from your 
application registration to `settings.py`:
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
That being said, this script doesn't do anything descructive, so don't be too paranoid.

## Deployment

Ok so now your script works but how do you deploy it? That's mostly up to you. What *I* did was fire up a `t2.nano` on AWS and set the script 
up as a systemd service. Here is a sample systemd service file that you might use to run this script in the background. It will automatically 
start the script at boot, and restart it if the process crashes. 

```
[Unit]
Description=Outlook Round-Robin
After=network.target

[Service]
User=ubuntu
Group=ubuntu
Type=idle
Restart=always
WorkingDirectory=/home/ubuntu
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

I also integrated the log files with CloudWatch to notify me of errors, but I'm too lazy to write about it. I'm sure you can figure it out.

## Notes

You probably don't run more than one instance of this script on a mailbox folder.

## License
