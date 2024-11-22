
# Why?

This fix is for ssl authentication of slack bot interface
Basically implementing:
'''
import ssl
import certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())
client = slack.WebClient(token=os.environ['SLACK_TOKEN'], ssl=ssl_context)
'''
from https://stackoverflow.com/questions/59808346/python-3-slack-client-ssl-sslcertverificationerror


# Enable Slack Bot

link: https://api.slack.com/authentication/basics

1. Create a new app
2. Go to OAuth & Permissions from Features, Scroll down to Scopes and add chat:write, chat:write.public permission to Bot Token Scopes and chat:write to User Token Scopes
(User Token Scopes might not be needed)
3. At the same page, Go to OAuth Tokens for Your Workspace, and click Install to Workspace
4. Copy OAuth Token and save it as an environmental variable (SLACK_BOT_TOKEN or TQDM_SLACK_TOKEN)
5. When using WebClient, you want to add
"""
ssl_context = ssl.create_default_context(cafile=certifi.where())
self.client = WebClient(token=token, ssl=ssl_context)
"""


