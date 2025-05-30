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
        self.challenge_required = False
        self.last_json = None

    def log(self, message):
        if self.logger:
            self.logger.log(message)
        else:
            print(message)

    def try_login(self, username, password):
        self.username = username
        self.password = password
        try:
            # Try a simple login first
            self.client.login(username, password)
            self._ready = True
            return "LOGIN_SUCCESS"
        except Exception as e:
            error_msg = str(e).lower()
            self.log(f"Login initial exception: {error_msg}")
            
            # Store last_json from client for challenge handling
            self.last_json = self.client.last_json
            
            # Handle challenge required scenario
            if "challenge_required" in error_msg or "two-factor" in error_msg or hasattr(self.client, 'challenge_code_handler'):
                self.challenge_required = True
                # Actually send the challenge here when detected
                result = self.challenge_send()
                if result:
                    return "2FA_REQUIRED"
                else:
                    return f"Failed to send verification: {str(e)}"
            
            return str(e)

    def challenge_send(self):
        """Trigger the sending of the challenge verification"""
        try:
            if self.challenge_required:
                self.log("Challenge required detected...")
                
                # Check if we have challenge data in last_json
                if self.client.last_json and 'challenge' in self.client.last_json:
                    challenge_url = self.client.last_json.get('challenge', {}).get('api_path')
                    if challenge_url:
                        self.log(f"Challenge URL found: {challenge_url}")
                        # Use the specific challenge handler from instagrapi
                        choice = 1  # Usually 1 for SMS, 0 for email
                        self.log(f"Requesting verification via choice {choice}...")
                        self.client.challenge_resolve(self.client.last_json, choice)
                        return True
                
                # If we don't have specific challenge data, try generic methods
                self.log("Attempting general challenge resolution...")
                if hasattr(self.client, 'challenge_code_handler'):
                    self.log("Using challenge_code_handler...")
                    self.client.challenge_code_handler = None  # Reset handler first
                    # This will trigger sending the code
                    self.client.login(self.username, self.password)
                    return True
                else:
                    # Legacy fallback method
                    self.log("Trying legacy challenge resolution...")
                    if hasattr(self.client, 'challenge_resolve'):
                        self.client.challenge_resolve(self.client.last_json)
                        return True
                    
            return False
        except Exception as e:
            self.log(f"Error sending challenge: {e}")
            # Sometimes the exception is actually expected in the challenge flow
            # We still want to continue to manual verification page
            return True  

    def continue_login(self):
        """Continue the login process after 2FA approval"""
        try:
            if self.challenge_required:
                self.log("Checking if login is approved...")
                # Try automatic verification (checking if user approved in app)
                if hasattr(self.client, 'challenge_auto_resolve'):
                    self.log("Using challenge_auto_resolve...")
                    self.client.challenge_auto_resolve()
                    time.sleep(3)  # Give Instagram more time
                
                # Try to complete login
                self.log("Attempting login after challenge...")
                self.client.login(self.username, self.password)
                self._ready = True
                return "LOGIN_SUCCESS"
            else:
                # If somehow we got here without challenge required, try normal login again
                self.client.login(self.username, self.password)
                self._ready = True
                return "LOGIN_SUCCESS"
        except Exception as e:
            error_msg = str(e).lower()
            self.log(f"Continue login error: {error_msg}")
            
            # If still in challenge, return appropriate message
            if "challenge_required" in error_msg or "two_factor" in error_msg:
                return "STILL_WAITING_APPROVAL"
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
        self.challenge_required = False

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
