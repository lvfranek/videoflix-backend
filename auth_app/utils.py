from django.contrib.auth.tokens import PasswordResetTokenGenerator


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    Token generator for account activation links.

    The activation state is part of the hash, so a token becomes
    invalid as soon as the account has been activated.
    """

    def _make_hash_value(self, user, timestamp):
        return f'{user.pk}{user.is_active}{timestamp}'


account_activation_token = AccountActivationTokenGenerator()
