import datetime


def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
