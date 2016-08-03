def build_message_from_exception_chain(e: Exception):
    exception = e
    message = str(exception)
    while (exception.__cause__):
        exception = exception.__cause__
        message = message + " | " + str(exception)
    return message


def throw_exception():
    raise Exception("Hallo :-)")


def throw_second_exception():
    try:
        throw_exception()

    except Exception as e:
        raise Exception("Second") from e
        print('Exception: %s' % e)
        print('%s' % str(e))


try:
    throw_second_exception()
    print('finished')
except Exception as e:
    print(build_message_from_exception_chain(e))
