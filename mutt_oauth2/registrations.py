from dataclasses import dataclass

__all__ = ('registrations',)


@dataclass
class Registration:
    authorize_endpoint: str
    device_code_endpoint: str
    token_endpoint: str
    redirect_uri: str
    imap_endpoint: str
    pop_endpoint: str
    smtp_endpoint: str
    sasl_method: str
    scope: str
    tenant: str | None = None


@dataclass
class Registrations:
    google: Registration
    microsoft: Registration


registrations = Registrations(
    google=Registration(authorize_endpoint='https://accounts.google.com/o/oauth2/auth',
                        device_code_endpoint='https://oauth2.googleapis.com/device/code',
                        imap_endpoint='imap.gmail.com',
                        pop_endpoint='pop.gmail.com',
                        redirect_uri='urn:ietf:wg:oauth:2.0:oob',
                        sasl_method='OAUTHBEARER',
                        scope='https://mail.google.com/',
                        smtp_endpoint='smtp.gmail.com',
                        token_endpoint='https://accounts.google.com/o/oauth2/token'),  # noqa: S106,
    microsoft=Registration(
        authorize_endpoint='https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
        device_code_endpoint='https://login.microsoftonline.com/common/oauth2/v2.0/devicecode',
        imap_endpoint='outlook.office365.com',
        pop_endpoint='outlook.office365.com',
        redirect_uri='https://login.microsoftonline.com/common/oauth2/nativeclient',
        smtp_endpoint='smtp.office365.com',
        sasl_method='XOAUTH2',
        scope=('offline_access https://outlook.office.com/IMAP.AccessAsUser.All '
               'https://outlook.office.com/POP.AccessAsUser.All '
               'https://outlook.office.com/SMTP.Send'),
        tenant='common',
        token_endpoint='https://login.microsoftonline.com/common/oauth2/v2.0/token'))  # noqa: S106
