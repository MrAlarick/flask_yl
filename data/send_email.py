import email
import ssl
from smtplib import SMTP

ADDRESS = "noreply@alarick.org"
SERVER = "mail.alarick.org"
PASSWORD = ""
URL = ""
DELETE_URL = "https://alarick.org/yl_host/delete_account/"
_DEFAULT_CIPHERS = (
'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:'
'!eNULL:!MD5')


def _send_email(address, subject, text):
    msg = email.message.EmailMessage()
    msg["Subject"] = subject
    msg["From"] = ADDRESS
    msg["To"] = address
    msg.set_content(text)
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3

    context.set_ciphers(_DEFAULT_CIPHERS)
    context.set_default_verify_paths()
    context.verify_mode = ssl.CERT_REQUIRED
    with SMTP(SERVER, port=587) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.ehlo()
        smtp.login(ADDRESS, PASSWORD)

        smtp.send_message(msg, from_addr=ADDRESS, to_addrs=[address])


def send_verification_email(address, token):
    _send_email(address, "Confirm registration", f"""To confirm registration on alarick.org open this link:
https://alarick.org/yl_host/register/{token}""")


def send_code_email(address, code):
    _send_email(address, "Verification code for alarick.org", f"""To log in to alarick.org enter the code below:
{code}""")


def send_deletion_email(address, token):
    _send_email(address, "Confirm account deletion", f"""To confirm the deletion of your account on alarick.org open this link:
https://alarick.org/yl_host/delete_account/{token}""")


def send_subreddit_deletion_email(address, token):
    _send_email(address, "Confirm subreddit deletion", f"""To confirm the deletion of your subreddit open this link:
https://alarick.org/yl_host/confirm_subreddit_deletion/{token}""")