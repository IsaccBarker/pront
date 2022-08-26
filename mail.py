import validate
import email
from email.mime.text import MIMEText
import imaplib
import smtplib
import logging
import os

# Ha! Take that robots!
model_checker_email = "milo bonks at rowlandOhall dot olrg" \
    .replace("bonks", "banks") \
    .replace("at", "@") \
    .replace("Ohall", "hall") \
    .replace("dot", ".") \
    .replace("olrg", "org") \
    .replace(" ", "")

logger = logging.getLogger('pront')
# Emails already received.
received = []
# Models in the process of being verified.
queue = {}

# Create an IMAP connection.
def create_imap_connection(server, email, password):
    # Operate over SSL.
    imap = imaplib.IMAP4_SSL(server)
    # Login.
    imap.login(email, password)
    # Check out the inbox.
    imap.select('inbox')

    return imap

def create_smtp_connection(server, email, password):
    # Operate over SSL.
    smtp = smtplib.SMTP_SSL(server, 465)
    # Login.
    smtp.login(email, password)

    return smtp

# con: Connection to the IMAP server.
def fetch_imap_mail(imap, smtp, subject_filter):
    imap.check()
    status, data = imap.search(None, 'ALL')
    mail_ids = []
    ret = []

    for block in data:
        mail_ids += block.split()

    # Too lazy to document this mess START
    for i in mail_ids:
        status, data = imap.fetch(i, '(RFC822)')
        for response_part in data:
            if isinstance(response_part, tuple):
                message = email.message_from_bytes(response_part[1])
                mail_from = message['from']
                mail_subject = message['subject']

                if not mail_subject == subject_filter:
                    continue

                if message.is_multipart():
                    mail_content = ''
                    for part in message.get_payload():
                        if part.get_content_type() == 'text/plain':
                            mail_content += part.get_payload()
                else:
                    mail_content = message.get_payload()

                # To lazy to document this mess END

                # Create the hash we use for checking shit.
                the_hash = str(hash(mail_content + mail_from + mail_subject))

                # Don't keep adding to the received array if it's already in it, thus
                # avoiding duplicate entries.
                logger.debug("Checking for " + the_hash + " in " + str(received) + ", and if response is appropriate.")
                if the_hash in received:
                    continue

                # Handle the email so that it can be handed off for verification.
                logger.debug("Adding hash " + the_hash + " to received.")
                ret.append({"email": mail_from, "subject": mail_subject, "content": mail_content.replace("\r\n", "")})
                received.append(the_hash)
                # send_return_mail(mail_from, "PRONT", "Your model was successfully submitted! You will receive an email once aproved.\n\nOtherwise, radio silence.", smtp)

    return ret

# Send a verification email.
def send_request_mails(from_address, mails, smtp):
    for mail in mails:
        send_return_mail(from_address, model_checker_email, "PRONT VERIFICATION REQUEST", "A submission was posted not long ago!" +

"\n\nEmail: " + mail['email'] +
"\nDescription: " + mail['desc'] +
"\nName: " + mail['name'] +
"\nURL of model: " + mail['url'] +
"\nVerification Code: " + str(hash(mail['url'])) +

"\n\nReply with the verification code posted above. Ensure the title is 'Re: PRONT VERIFICATION REQUEST'. If you are using GMail, this should already be done.", smtp)

        # Add it to the queue so we can check if verification passed in the future.
        queue[str(hash(mail['url']))] = mail

# Send a generic email as a response.
def send_return_mail(from_address, to_address, subject, content, smtp):
    message = MIMEText(content)
    message['subject'] = subject
    message['from'] = from_address
    message['to'] = to_address

    logger.debug("Sending return mail:\n" + message.as_string())
    smtp.sendmail(from_address, to_address, message.as_string())

