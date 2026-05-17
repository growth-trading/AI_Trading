import ssl
import certifi
from django.core.mail.backends.smtp import EmailBackend


class CertifiSMTPBackend(EmailBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
