import os
import hvac
from dotenv import load_dotenv

load_dotenv()

class VaultClient:

    def __init__(self):
        self.vault_addr     = os.getenv("VAULT_ADDR")
        self.vault_username = os.getenv("VAULT_USERNAME")
        self.vault_password = os.getenv("VAULT_PASSWORD")
        #self.secret_path    = os.getenv("VAULT_SECRET_PATH", "dev_env")
        raw_path = os.getenv("VAULT_SECRET_PATH", "dev_env")
        self.secret_path = raw_path.replace("secret/data/", "").strip("/")

        print(f"Using secret path: secret/data/{self.secret_path}")

        if not self.vault_addr:
            raise RuntimeError("VAULT_ADDR is not set in .env")

        if not self.vault_username or not self.vault_password:
            raise RuntimeError(
                "VAULT_USERNAME and VAULT_PASSWORD must be set in .env"
            )

        # Connect to Vault
        self.client = hvac.Client(url=self.vault_addr)

        # Login with username and password
        self.client.auth.userpass.login(
            username=self.vault_username,
            password=self.vault_password
        )

        if not self.client.is_authenticated():
            raise RuntimeError(
                f" Vault authentication failed at {self.vault_addr}. "
                "Check VAULT_USERNAME and VAULT_PASSWORD."
            )

        print(f" Connected to Vault at {self.vault_addr}")

    def get_gemini_key(self) -> str:
        """
        Fetches Gemini API key from:
        http://10.2.0.208:8200/secret/data/dev_env
        key: GOOGLE_API_KEY
        """
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=self.secret_path,   # dev_env
                mount_point="secret"     # secret/data/dev_env
            )
            key = response["data"]["data"].get("GOOGLE_API_KEY")

            if not key:
                raise RuntimeError(
                    f"gemini_api_key not found at "
                    f"secret/data/{self.secret_path} in Vault"
                )

            print(f"Gemini API key fetched from Vault "
                  f"(secret/data/{self.secret_path})")
            return key

        except Exception as e:
            raise RuntimeError(f"Failed to fetch key from Vault: {e}")
