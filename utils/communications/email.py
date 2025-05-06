from django.template.loader import render_to_string
from django.utils import html
from django.utils.html import strip_tags
from django.core.mail import send_mail
import logging

class HTML:
    pass


class EmailAddress:
    pass


class ListOfEmailAddress:
    pass


class EmailMessage:
    def __init__(
        self, 
        template: HTML, 
        sender: EmailAddress,
        receivers: ListOfEmailAddress,
        subject: str,
        context: dict
        ) -> None:
        
        self.template = template
        self.sender = sender
        self.receivers = receivers
        self.subject = subject
        self.context = context

    def send(self):
        html_message = render_to_string(self.template, self.context)
        plain_message = strip_tags(html_message)
        send_mail(
            self.subject,
            plain_message,
            self.sender,
            self.receivers,
            html_message=html_message
        )