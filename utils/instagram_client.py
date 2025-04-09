from instagrapi import Client
import time
import random

class InstagramBot:
    def __init__(self, logger=None):
        self.client = Client()
        self.username = None
        self.password = None
        self._ready = False
        self.logger = logger
        self.two_factor_info = None

    def log(self, message):
        if self.logger:
            self.logger.log(message)
        else:
            print(message)

    def try_login(self, username, password):
        self.username = username
        self.password = password
        try:
            self.client.login(username, password)
            self._ready = True
            return "LOGIN_SUCCESS"
        except Exception as e:
            error_msg = str(e).lower()
            if "two-factor authentication required" in error_msg or "challenge_required" in error_msg:
                # Store the client instance which now has the challenge info
                self.two_factor_info = True
                return "2FA_REQUIRED"
            return str(e)

    def challenge_send(self):
        """Trigger the sending of the challenge verification"""
        try:
            if self.two_factor_info:
                # This will trigger the prompt on Instagram's side
                self.client.challenge_send_sms(self.username)
                return True
        except Exception as e:
            self.log(f"Error sending challenge: {e}")
            return False

    def continue_login(self):
        """Continue the login process after 2FA approval"""
        try:
            # Don't create a new client - use the existing one with challenge info
            if self.two_factor_info:
                # Try to trigger the challenge again
                self.challenge_send()
                time.sleep(2)  # Give Instagram some time
                
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

    def logout(self):
        """Properly logout from Instagram"""
        if self._ready:
            try:
                self.client.logout()
            except:
                pass
        self._ready = False
        self.username = None
        self.password = None
        self.two_factor_info = None

    def get_me(self):
        """Get information about logged in user"""
        if not self._ready:
            return None
        try:
            return self.client.user_info(self.client.user_id)
        except Exception as e:
            self.log(f"Error getting user info: {e}")
            return None

    def get_followers(self, username, amount):
        """Get followers of a user"""
        try:
            user_id = self.client.user_id_from_username(username)
            return self.client.user_followers(user_id, amount=amount)
        except Exception as e:
            self.log(f"Error getting followers: {e}")
            raise e

    def get_following(self, username, amount):
        """Get users that a user is following"""
        try:
            user_id = self.client.user_id_from_username(username)
            return self.client.user_following(user_id, amount=amount)
        except Exception as e:
            self.log(f"Error getting following: {e}")
            raise e

    def send_dm(self, user, message):
        """Send a direct message to a user"""
        if not self._ready:
            raise Exception("Not logged in")
            
        # Add slight randomization to the message to avoid spam detection
        if random.random() > 0.7:
            # Sometimes add a space at the end or slightly alter punctuation
            message = message.rstrip() + (" " if not message.endswith(" ") else "")
            
        result = self.client.direct_send(message, [user.pk])
        
        # Add a random delay between 0.5 and 2 seconds to seem more human-like
        jitter = random.uniform(0.5, 2.0)
        time.sleep(jitter)
        
        return result
        
    def get_user_info(self, username):
        """Get detailed information about a user"""
        try:
            user_id = self.client.user_id_from_username(username)
            return self.client.user_info(user_id)
        except Exception as e:
            self.log(f"Error getting user info: {e}")
            return None
