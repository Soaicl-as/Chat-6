from instagrapi import Client

class InstagramBot:
    def __init__(self):
        self.client = Client()
        self.username = None
        self.password = None
        self._ready = False

    def try_login(self, username, password):
        self.username = username
        self.password = password
        try:
            self.client.login(username, password)
            self._ready = True
            return "LOGIN_SUCCESS"
        except Exception as e:
            if "two-factor authentication required" in str(e).lower():
                return "2FA_REQUIRED"
            return str(e)

    def continue_login(self):
        try:
            self.client = Client()
            self.client.login(self.username, self.password)
            self._ready = True
            return "LOGIN_SUCCESS"
        except Exception as e:
            return "2FA_REQUIRED"

    def get_followers(self, username, amount):
        return self.client.user_followers(self.client.user_id_from_username(username), amount)

    def get_following(self, username, amount):
        return self.client.user_following(self.client.user_id_from_username(username), amount)

    def send_dm(self, user, message):
        self.client.direct_send(message, [user.pk])
