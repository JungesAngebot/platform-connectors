import datetime
import pytz

print((datetime.datetime.now() + datetime.timedelta(days=150)).strftime('%s'))

print(datetime.datetime.now(pytz.utc).strftime('%Y-%m-%dT%H:%M:%S%z'))
print(datetime.datetime.now(pytz.utc).isoformat())
