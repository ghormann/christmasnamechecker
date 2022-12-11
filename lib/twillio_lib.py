
from twilio.rest import Client

def create_twillo_clients(config):
    rc = {}
    for t in config["allAccounts"]:
        client = Client(t["account_sid"], t["auth_token"])
        rc[t["fromPhone"]] = client
        if t["isPrimary"]:
            rc["primary"] = client
    return rc

def findAccount(config, clientId="primary"):
    primary = None
    for t in config["allAccounts"]:
        client = Client(t["account_sid"], t["auth_token"])
        if t["isPrimary"]:
            primary = t
        if t["fromPhone"] == clientId:
            return t
    return primary
