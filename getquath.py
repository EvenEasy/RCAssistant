import requests, config


def getQAuth():
    body = {
    'client_id': config.TWITCH_CLIENT_ID,
    'client_secret': config.TWITCH_SECRET_KEY,
    "grant_type": 'client_credentials'
}
    try:
        print(1)
        req = requests.post('https://id.twitch.tv/oauth2/token', body)
        print(1)
        print(req.json())
        jsondata = req.json()
        if 'access_token' in jsondata:
            return jsondata['access_token']
    except Exception as e:
         print(e)

getQAuth()