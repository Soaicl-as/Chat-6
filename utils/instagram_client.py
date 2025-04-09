from instagrapi import Client
import time

class InstagramBot:
    def __init__(self, logger=None):
        self.client = Client()
        self.username = None
        self.password = None
        self._ready = False
        self.logger = logger
        self.two_factor_info = None  # Store 2FA challenge info

    def try_login(self, username, password):
        self.username = username
        self.password = password
        try:
            self.client.login(username, password)
            self._ready = True
            return "LOGIN_SUCCESS"
        except Exception as e:
            if "two-factor authentication required" in str(e).lower():
                # Store the client instance which now has the challenge info
                self.two_factor_info = True
                return "2FA_REQUIRED"
            return str(e)

    def continue_login(self):
        try:
            # Don't create a new client - use the existing one with challenge info
            if self.two_factor_info:
                # This will trigger the prompt on Instagram's side
                self.client.challenge_send_sms(self.username)
                time.sleep(2)  # Give Instagram some time to send the notification
                
                # Try to re-login, which should now check the device confirmation
                self.client.login(self.username, self.password)
                self._ready = True
                return "LOGIN_SUCCESS"
            else:
                # If somehow we got here without 2FA info, try normal login again
                self.client.login(self.username, self.password)
                self._ready = True
                return "LOGIN_SUCCESS"
        except Exception as e:
            return str(e)

    def get_followers(self, username, amount):
        user_id = self.client.user_id_from_username(username)
        return self.client.user_followers(user_id, amount=amount)

    def get_following(self, username, amount):
        user_id = self.client.user_id_from_username(username)
        return self.client.user_following(user_id, amount=amount)

    def send_dm(self, user, message):
        result = self.client.direct_send(message, [user.pk])
        time.sleep(1)  # Add a small delay between each API call
        return result
