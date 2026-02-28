#!/usr/bin/env python
"""
SMTP Email Test Script for GigRoute
Verifies email configuration and sends a test email.

Usage:
    python scripts/test_email_smtp.py [recipient_email]

Environment variables required:
    MAIL_SERVER     - SMTP server (default: smtp.gmail.com)
    MAIL_PORT       - SMTP port (default: 587)
    MAIL_USE_TLS    - Use TLS (default: true)
    MAIL_USERNAME   - SMTP username
    MAIL_PASSWORD   - SMTP password or app password
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


class Colors:
    GREEN = chr(27) + "[92m"
    RED = chr(27) + "[91m"
    YELLOW = chr(27) + "[93m"
    BLUE = chr(27) + "[94m"
    RESET = chr(27) + "[0m"
    BOLD = chr(27) + "[1m"


def print_header():
    print(f"{Colors.BOLD}{chr(61)*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  GIGROUTE - TEST EMAIL SMTP{Colors.RESET}")
    print(f"{Colors.BOLD}{chr(61)*60}{Colors.RESET}")


def print_success(msg):
    print(f"{Colors.GREEN}[OK]{Colors.RESET} {msg}")


def print_error(msg):
    print(f"{Colors.RED}[ERREUR]{Colors.RESET} {msg}")


def print_warning(msg):
    print(f"{Colors.YELLOW}[ATTENTION]{Colors.RESET} {msg}")


def print_step(step, msg):
    print(f"{Colors.BLUE}[{step}]{Colors.RESET} {msg}")


def get_config():
    return {
        "server": os.environ.get("MAIL_SERVER", "smtp.gmail.com"),
        "port": int(os.environ.get("MAIL_PORT", 587)),
        "use_tls": os.environ.get("MAIL_USE_TLS", "true").lower() == "true",
        "username": os.environ.get("MAIL_USERNAME"),
        "password": os.environ.get("MAIL_PASSWORD"),
        "sender": os.environ.get("MAIL_DEFAULT_SENDER", "noreply@gigroute.app"),
    }


def test_smtp_connection(config):
    print_step("1", f"Test connexion SMTP: {config[chr(39)+'server'+chr(39)]}:{config[chr(39)+'port'+chr(39)]}")
    try:
        server = smtplib.SMTP(config["server"], config["port"], timeout=10)
        server.ehlo()
        if config["use_tls"]:
            print_step("2", "Activation TLS...")
            server.starttls()
            server.ehlo()
            print_success("TLS active")
        if config["username"] and config["password"]:
            print_step("3", f"Authentification ({config[chr(39)+'username'+chr(39)]})...")
            server.login(config["username"], config["password"])
            print_success("Authentification reussie")
        server.quit()
        print_success("Connexion SMTP OK")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print_error(f"Echec authentification: {e}")
        print_warning("Pour Gmail, utilisez un App Password")
        return False
    except Exception as e:
        print_error(f"Erreur: {e}")
        return False


def send_test_email(config, recipient):
    print_step("4", f"Envoi email de test a: {recipient}")
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[TEST] GigRoute - Email Test ({datetime.now().strftime(chr(39)+'%H:%M:%S'+chr(39))})")
        msg["From"] = config["sender"]
        msg["To"] = recipient
        
        text = f"""
GIGROUTE - TEST EMAIL

Cet email confirme que votre configuration SMTP fonctionne.

Serveur: {config["server"]}
Port: {config["port"]}
TLS: {"Oui" if config["use_tls"] else "Non"}
Expediteur: {config["sender"]}
Date: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
"""
        msg.attach(MIMEText(text, "plain"))
        
        server = smtplib.SMTP(config["server"], config["port"], timeout=10)
        server.ehlo()
        if config["use_tls"]:
            server.starttls()
            server.ehlo()
        if config["username"] and config["password"]:
            server.login(config["username"], config["password"])
        server.sendmail(config["sender"], recipient, msg.as_string())
        server.quit()
        
        print_success(f"Email envoye a {recipient}")
        return True
    except Exception as e:
        print_error(f"Echec envoi: {e}")
        return False


def main():
    print_header()
    recipient = sys.argv[1] if len(sys.argv) > 1 else input("Email destinataire: ").strip()
    if not recipient:
        print_error("Aucun destinataire")
        sys.exit(1)
    
    config = get_config()
    print(f"
Configuration:")
    print(f"  Serveur: {config[chr(39)+'server'+chr(39)]}")
    print(f"  Port: {config[chr(39)+'port'+chr(39)]}")
    print(f"  Username: {config[chr(39)+'username'+chr(39)] or chr(39)+'(non defini)'+chr(39)}")
    print()
    
    if not config["username"] or not config["password"]:
        print_warning("MAIL_USERNAME/MAIL_PASSWORD non definis")
        sys.exit(1)
    
    if not test_smtp_connection(config):
        sys.exit(1)
    
    print()
    if send_test_email(config, recipient):
        print(f"
{Colors.GREEN}TEST REUSSI{Colors.RESET}")
    else:
        print(f"
{Colors.RED}TEST ECHOUE{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
