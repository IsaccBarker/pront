import mail
import printer
import validate
import logging
import time
import argparse

# Colors!
class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    cyan = "\x1b[0;36m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: cyan + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Setup the logging, easy enough.
def setup_logging():
    global logger

    logger = logging.getLogger("pront")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(CustomFormatter())
    logger.addHandler(ch)

# Main
def pront():
    setup_logging()

    # Set up the CLI
    parser = argparse.ArgumentParser(description='Print validation server.')
    parser.add_argument('server', type=str,
                    help='the imap server to fetch validation requests from.')
    parser.add_argument('username', type=str,
                    help='the username to send to the imap server to fetch validation requests from.')
    parser.add_argument('password', type=str,
                    help='the password to send to the imap server to fetch validation requests from.')

    args = vars(parser.parse_args())

    # Set up the connection we will need, namely to email servers (IMAP and SMTP).
    logger.info("Starting PRONT server...")
    logger.debug("Creating IMAP connection...")
    imap = mail.create_imap_connection(args['server'], args['username'], args['password'])
    logger.debug("Creating SMTP connection...")
    smtp = mail.create_smtp_connection(args['server'], args['username'], args['password'])
    logger.info("Started PRONT server!")

    # The plumbing.
    while True:
        # Fetch new submission emails, and verify them.
        logger.debug("Fetching mail from IMAP server (submissions).")
        imap_mails = mail.fetch_imap_mail(imap, smtp, "PRONT PRINT SUBMISSION")
        logger.debug("Validating mail (submissins).")
        imap_mails = validate.validate_requests(imap_mails, smtp)

        # Fire off verification emails based on the submission emails.
        logging.debug("Firing off requests.")
        mail.send_request_mails(args['username'], imap_mails, smtp)

        # Fetch new validation emails, and verify them.
        logger.debug("Fetching mail from IMAP server (validations).")
        imap_mails = mail.fetch_imap_mail(imap, smtp, "Re: PRONT VERIFICATION REQUEST")
        logger.debug("Validating mail (validations)")
        verification_codes = validate.validate_verifications(imap_mails, smtp)

        # Look through to see if we have validation email responses.
        for code in verification_codes:
            # If we got one and the code is in the mail queue, we got a winner.
            if code in mail.queue:
                # Add the print job to the print queue.
                verified = mail.queue[code]
                logger.debug("Approved code " + code + " (" + str(verified) + ")")
                printer.queue.append(verified)

                # Send success email.
                mail.send_return_mail(verified['email'], verified['email'], "PRONT", "Your model was approved! An email will be sent to you when your model starts printing.", smtp)

                # Remove it from the email queue.
                del mail.queue[code]

        # Slice and start printing.
        printer.process_queue()

        # Grace period as to not fuck over the SMTP and IMAP servers.
        logger.debug("Gracing.")
        time.sleep(10)

    return

# Voodoo
if __name__ == "__main__":
    pront()

