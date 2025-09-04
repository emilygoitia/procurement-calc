from datetime import date, timedelta, datetime

# ======================= Holiday helpers (multi-country + Easter) =======================
def easter_date(year):
    # Anonymous Gregorian algorithm
    a = year % 19
    b = year // 100; c = year % 100
    d = b // 4; e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19*a + b - d - g + 15) % 30
    i = c // 4; k = c % 4
    l = (32 + 2*e + 2*i - h - k) % 7
    m = (a + 11*h + 22*l) // 451
    month = (h + l - 7*m + 114) // 31
    day = ((h + l - 7*m + 114) % 31) + 1
    return date(year, month, day)

def holidays_us(year):
    # Observed US Federal holidays
    def nth_weekday_of_month(month, weekday, n):
        import calendar
        c = calendar.Calendar()
        days = [d for d in c.itermonthdates(year, month) if d.weekday() == weekday and d.month == month]
        return days[-1] if n == -1 else days[n-1]
    def observed(d):
        if d.weekday()==5: return {d, d - timedelta(days=1)}
        if d.weekday()==6: return {d, d + timedelta(days=1)}
        return {d}
    hs = set()
    hs |= observed(date(year,1,1))
    hs.add(nth_weekday_of_month(1,0,3))
    hs.add(nth_weekday_of_month(2,0,3))
    hs.add(nth_weekday_of_month(5,0,-1))
    hs |= observed(date(year,6,19))
    hs |= observed(date(year,7,4))
    hs.add(nth_weekday_of_month(9,0,1))
    hs.add(nth_weekday_of_month(10,0,2))
    hs |= observed(date(year,11,11))
    hs.add(nth_weekday_of_month(11,3,4))
    hs |= observed(date(year,12,25))
    return hs

def holidays_mexico(year):
    # Main federal holidays (Ley Federal del Trabajo)
    def nth_weekday_of_month(month, weekday, n):
        import calendar
        c = calendar.Calendar()
        days = [d for d in c.itermonthdates(year, month) if d.weekday() == weekday and d.month == month]
        return days[n-1]
    hs = set()
    hs.add(date(year,1,1))  # Año Nuevo
    hs.add(nth_weekday_of_month(2,0,1))  # Día de la Constitución (1st Monday Feb)
    hs.add(nth_weekday_of_month(3,0,3))  # Natalicio Benito Juárez (3rd Monday Mar)
    hs.add(date(year,5,1))  # Día del Trabajo
    hs.add(date(year,9,16)) # Independencia
    hs.add(nth_weekday_of_month(11,0,3)) # Revolución (3rd Monday Nov)
    hs.add(date(year,12,25)) # Navidad
    return hs

def holidays_uk(year):
    # England & Wales common bank holidays (approx.)
    import calendar
    def first_monday(month):
        for d in range(1,8):
            dt = date(year,month,d)
            if dt.weekday()==0: return dt
    def last_monday(month):
        last_day = calendar.monthrange(year,month)[1]
        for d in range(last_day, last_day-7, -1):
            dt = date(year,month,d)
            if dt.weekday()==0: return dt
    hs = set()
    # New Year (observed)
    ny = date(year,1,1)
    if ny.weekday()==5: hs |= {ny, ny - timedelta(days=1)}
    elif ny.weekday()==6: hs |= {ny, ny + timedelta(days=1)}
    else: hs.add(ny)
    # Good Friday & Easter Monday
    easter = easter_date(year)
    hs.add(easter - timedelta(days=2))
    hs.add(easter + timedelta(days=1))
    # Early May bank holiday (first Monday May)
    hs.add(first_monday(5))
    # Spring bank (last Monday May)
    hs.add(last_monday(5))
    # Summer bank (last Monday August)
    hs.add(last_monday(8))
    # Christmas & Boxing Day (observed)
    xmas = date(year,12,25); box = date(year,12,26)
    for d in (xmas, box):
        if d.weekday()==5: hs |= {d, d - timedelta(days=1)}
        elif d.weekday()==6: hs |= {d, d + timedelta(days=1)}
        else: hs.add(d)
    return hs

def holidays_italy(year):
    # National holidays (approx.; includes Easter Monday)
    hs = {
        date(year,1,1),   # New Year
        date(year,1,6),   # Epiphany
        date(year,4,25),  # Liberation Day
        date(year,5,1),   # Labour Day
        date(year,6,2),   # Republic Day
        date(year,8,15),  # Assumption
        date(year,11,1),  # All Saints
        date(year,12,8),  # Immaculate Conception
        date(year,12,25), # Christmas
        date(year,12,26), # St. Stephen
    }
    hs.add(easter_date(year) + timedelta(days=1))  # Easter Monday
    return hs

def holidays_spain(year):
    # National holidays (approx.; includes Good Friday)
    hs = {
        date(year,1,1),   # Año Nuevo
        date(year,1,6),   # Epifanía
        date(year,8,15),  # Asunción
        date(year,10,12), # Fiesta Nacional
        date(year,11,1),  # Todos los Santos
        date(year,12,6),  # Constitución
        date(year,12,8),  # Inmaculada
        date(year,12,25), # Navidad
    }
    hs.add(easter_date(year) - timedelta(days=2))  # Good Friday
    return hs

def expand_holidays(country: str, years):
    hs = set()
    for y in years:
        if country == "United States":
            hs |= holidays_us(y)
        elif country == "Mexico":
            hs |= holidays_mexico(y)
        elif country == "United Kingdom":
            hs |= holidays_uk(y)
        elif country == "Italy":
            hs |= holidays_italy(y)
        elif country == "Spain":
            hs |= holidays_spain(y)
        else:
            hs |= holidays_us(y)
    return hs

def add_workdays(start_date, duration_days, holidays, workdays_per_week=5):
    if start_date is None or duration_days == 0: return start_date
    d = start_date
    step = 1 if duration_days > 0 else -1
    remaining = abs(int(duration_days))
    while remaining > 0:
        d += timedelta(days=step)
        dow = d.weekday()
        is_weekend = (dow == 6) or (dow == 5 and workdays_per_week == 5)
        if is_weekend or d in holidays: continue
        remaining -= 1
    return d

def to_date(x):
    if not x: return None
    try: return pd.to_datetime(x).date()
    except: return None

def workdays_between(d1, d2, ww=5, holidays=set()):
    if d1 is None or d2 is None: return None
    days = 0
    step = 1 if d2 >= d1 else -1
    d = d1
    while d != d2:
        d += timedelta(days=step)
        dow = d.weekday()
        is_weekend = (dow == 6) or (dow == 5 and ww == 5)
        if not is_weekend and d not in holidays:
            days += 1 if step > 0 else -1
    return days

def clamp(d, lo, hi):
    if d is None: return None
    if lo and d < lo: d = lo
    if hi and d > hi: d = hi
    return d