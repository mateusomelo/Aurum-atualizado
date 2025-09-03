from datetime import datetime, timezone, timedelta

def get_brazil_time():
    """
    Retorna o horário atual no timezone brasileiro (UTC-3).
    """
    brazil_timezone = timezone(timedelta(hours=-3))
    return datetime.now(brazil_timezone).replace(tzinfo=None)

def get_utc_time():
    """
    Retorna o horário atual em UTC.
    """
    return datetime.utcnow()