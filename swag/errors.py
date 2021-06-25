class NoAccountRegistered(Exception):
    """Raised when an account name is not present in the SwagBank"""

    def __init__(self, name):
        self.name = name
        message = f"{name} n'a pas de compte sur $wagBank"
        super().__init__(message)


class AccountAlreadyExist(Exception):
    """Raised when a someone who already have an account create a new account"""

    pass


class NotEnoughSwagInBalance(Exception):
    """Raised when a account should have a negative value of swag"""

    def __init__(self, name):
        self.name = name
        message = f"{name} n'a pas assez d'argent sur son compte"
        super().__init__(message)


class InvalidSwagValue(Exception):
    """Raised when an invalid amount of swag is asked i.e not integor or negative"""

    pass


class InvalidStyleValue(Exception):
    """Raised when an invalid amount of style is asked i.e negative"""

    pass


class AlreadyMineToday(Exception):
    """Raised when an account try to mine the same day"""

    pass


class StyleStillBlocked(Exception):
    """Raised when someone want to interact with his $tyle but it's still blocked"""

    pass


class NotEnoughStyleInBalance(Exception):
    """Raised when a account should have a negative value of $tyle"""

    pass
