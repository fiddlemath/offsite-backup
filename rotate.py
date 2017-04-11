"""Handle a backup-rotation policy.

Example Usage:

    config = {'days': 
    r = Rotator(config)
"""

# This could clearly be generalized: days, weeks, months, years is easy to say,
# but all you really need is a 'rounding function', and a count per rounding function.
# Those rounding functions could be _really arbitrary_, and possibly even taken
# as arbitrary configuration.
# e.g. "Save every 20th day, save every 3 hours, save every 1000000 seconds."

from schema import Schema, Or, Optional
from datetime import datetime, timedelta

class Rotation:
    _schema = Schema({
        'days': Or(int, 'all'),
        'months': Or(int, 'all'),
        'weeks': Or(int, 'all'),
        'years': Or(int, 'all'),
        Optional('format', default='%Y-%m-%d'): '%Y-%m-%d'
        # format is a strptime() format.
        # No interesting values will work right now, because 
        # sorting in filter().
        # I won't fix this unless I need it for something, at which point
        # I'm likely to be mildly cross.
    })
    "The schema for configs for this class."

    @classmethod
    def validate(cls, config):
        return cls._schema.validate(config)

    def __init__(self, config):
        config = self.validate(config)

        self.max_days = config['days']
        self.max_weeks = config['weeks']
        self.max_months = config['months']
        self.max_years = config['years']
        self.date_format = config['format']
        
    def filter(self, filenames):
        """Return the tuple (keep, drop, invalid), partitioning `dates`,
        into the list of dates to be kept (`keep`),
        the list of dates to be dropped (`drop`),
        and the list of unmatched strings (`invalid`).

        This does not guarantee a stable ordering.
        """
        _filenames = list(filenames)

        # TODO: This is just going to be incorrect for most custom formats.
        _filenames.sort(reverse=True)

        days, weeks, months, years = 0, 0, 0, 0
        first_day, first_week, first_month, first_year = \
          None, None, None, None
        keep, drop, invalid = [], [], []
        
        for filename in _filenames:
            try:
                date_part = filename.split('.', 2)[0]
                d = datetime.strptime(date_part, self.date_format)
            except ValueError:
                invalid.append(filename)
                continue

            keep_this_one = False
            if (self.max_days == 'all' or days < self.max_days) \
              and (first_day == None or d < first_day):
                keep_this_one = True
                days += 1
                first_day = round_day(d)

            if (self.max_weeks == 'all' or weeks < self.max_weeks) \
              and (first_week == None or round_week(d) < first_week):
                keep_this_one = True
                weeks += 1
                first_week = round_week(d)

            elif (self.max_months == 'all' or months < self.max_months) \
              and (first_month == None or round_month(d) < first_month):
                keep_this_one = True
                months += 1
                first_month = round_month(d)

            elif (self.max_years == 'all' or years < self.max_years) \
              and (first_year == None or round_year(d) < first_year):
                keep_this_one = True
                years += 1
                first_year = round_year(d)

            if keep_this_one:
                keep.append(filename)
            else:
                drop.append(filename)

        return (keep, drop, invalid)
    
# "Rounding" functions. Make equivalent all dates of the given equivalence class.
def round_year(d):
    return d.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

def round_month(d):
    return d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

def round_week(d):
    time_since_monday = timedelta(days=d.weekday())
    new_day = d - time_since_monday
    return new_day.replace(hour=0, minute=0, second=0, microsecond=0)

def round_day(d):
    return d.replace(hour=0, minute=0, second=0, microsecond=0)

