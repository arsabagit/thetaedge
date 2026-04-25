import pyotp
import logging
import os
from .NorenApi import NorenApi

# Load .env if python-dotenv is installed (recommended)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("ShoonyaAuth")

class ShoonyaAuth:
    def __init__(self):
        self.api = NorenApi()
        
    def login(self):
        """
        Authenticate with Shoonya using environment variables only.
        """
        # STEP 1: Read environment credentials
        creds = {
            'user_id': os.getenv('SHOONYA_USER_ID'),
            'password': os.getenv('SHOONYA_PASSWORD'),
            'totp_secret': os.getenv('SHOONYA_TOTP_SECRET'),
            'api_secret': os.getenv('SHOONYA_API_KEY'),
            'imei': os.getenv('SHOONYA_IMEI'),
            'vendor_code': os.getenv('SHOONYA_VENDOR_CODE')
        }

        # STEP 2: Validate we have all credentials
        if not all(creds.values()):
            missing_keys = [k for k, v in creds.items() if not v]
            logger.error(f"Incomplete credentials. Missing: {missing_keys}")
            logger.error("Please check .env file and set all required SHOONYA_* variables")
            return None

        # STEP 3: Try Session Resumption (if token file exists)
        token_file = "shoonyakey.txt"
        if os.path.exists(token_file):
            try:
                with open(token_file, 'r') as f:
                    token = f.read().strip()
                if token:
                    logger.info("Attempting session resumption...")
                    self.api.set_session(creds['user_id'], creds['password'], token)
                    # Test if session is still valid
                    test_quote = self.api.get_quotes('NSE', '26009')
                    if test_quote and test_quote.get('stat') == 'Ok':
                        logger.info("✅ Session resumed successfully (no fresh login needed)")
                        return self.api
                    else:
                        logger.warning("Session token expired. Proceeding with fresh login.")
            except Exception as e:
                logger.debug(f"Session resumption failed: {e}")

        # STEP 4: Fresh Login (web platform endpoint — no API key needed)
        web_login_error = None
        try:
            logger.info("Performing fresh login (web endpoint, no API key)...")
            totp_val = pyotp.TOTP(creds['totp_secret']).now()
            ret = self.api.web_login(
                userid=creds['user_id'],
                password=creds['password'],
                twoFA=totp_val,
            )

            if ret and ret.get('stat') == 'Ok':
                logger.info(f"✅ Login Successful (web endpoint). User: {creds['user_id']}")
                return self.api
            else:
                web_login_error = ret
                logger.warning(f"Web login failed: {ret}")
        except Exception as e:
            web_login_error = str(e)
            logger.warning(f"Web login exception: {e}")

        # STEP 5: Fallback — direct QuickAuth (requires valid personal API key)
        direct_login_error = None
        try:
            logger.info("Attempting fallback login (QuickAuth with personal API key)...")
            totp_val = pyotp.TOTP(creds['totp_secret']).now()
            ret = self.api.login(
                userid=creds['user_id'],
                password=creds['password'],
                twoFA=totp_val,
                vendor_code=creds['vendor_code'],
                api_secret=creds['api_secret'],
                imei=creds['imei']
            )
            
            if ret and ret.get('stat') == 'Ok':
                logger.info(f"✅ Login Successful (QuickAuth). User: {creds['user_id']}")
                return self.api
            else:
                direct_login_error = ret
                logger.warning(f"QuickAuth failed: {ret}")
                
        except Exception as e:
            direct_login_error = str(e)
            logger.warning(f"QuickAuth exception: {e}")

        # All methods exhausted
        logger.error("ALL login methods failed. Web: %s | QuickAuth: %s",
                      web_login_error, direct_login_error)
        return None

