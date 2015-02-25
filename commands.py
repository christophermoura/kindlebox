from app import db
from app.kindleboxer import kindlebox
from app.kindleboxer import resend_books
from app.models import User
from app.models import Book

from flask.ext.script import Command
from flask.ext.script import Option


class CeleryTasksCommand(Command):
    """
    Sets off the `kindlebox` celery task for all active users and the
    `resend_books` celery task for all unsent books.
    """
    def run(self):
        # Kindleboxing active users.
        active_users = User.query.filter_by(active=True).all()
        for user in active_users:
            kindlebox.delay(user.dropbox_id)

        # Resending any unsent books.
        unsent_books = Book.query.filter_by(unsent=True).all()
        unsent_dropbox_ids = set(book.user.dropbox_id for book in unsent_books)
        for dropbox_id in unsent_dropbox_ids:
            resend_books.delay(dropbox_id)


class ResetUserCommand(Command):
    """
    Resets a user's Dropbox delta cursor to nothing and deletes all the books
    that they already own. Should be used if user has just signed up but
    doesn't receive any books that they added.
    """
    option_list = (
            Option('--user-id', '-u', dest='user_id'),
            )

    def run(self, user_id):
        user = User.query.filter_by(id=user_id).first()
        if user is None:
            print "User doesn't exist"
            return
        user.cursor = None
        user.books.delete()
        db.session.commit()