"""Smoke test for the filter logic. No network, no Telegram, no env needed.

Run:
    python tests/test_filters.py

Rule under test: a posting is kept only if it is (a) located in India,
(b) technical / product-management, (c) not HR / admin / sales / support,
and (d) an internship.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filters import (passes, label_for, is_india_location,          # noqa: E402
                     is_bengaluru_location, is_hyderabad_location,
                     is_ncr_location, is_mumbai_location,
                     is_pune_location, is_chennai_location)


def main() -> int:
    now = datetime.now(timezone.utc)
    cases = [
        # (title, location, dept, expected, reason)
        # --- kept: internship + tech + India ---
        ('Software Engineer Intern',             'Bengaluru, Karnataka, India', 'Engineering', True,  'intern + India'),
        ('Senior Software Engineer Intern',      'Hyderabad, Telangana',        'Engineering', True,  'intern (modifier ignored)'),
        ('SDE Intern',                           'Gurugram, Haryana',           'Engineering', True,  'NCR intern'),
        ('Machine Learning Intern',              'Pune, Maharashtra',           'ML',          True,  'MLE intern'),
        ('Data Science Intern',                  'Noida, Uttar Pradesh',        'Data',        True,  'DS intern'),
        ('Product Management - Intern',          'Noida, Uttar Pradesh',        'Product',     True,  'PM intern allowed'),
        ('Industrial Trainee - Embedded Systems','Chennai, Tamil Nadu',         'Engineering', True,  'India-specific intern label'),
        ('Software Engineering Intern',          'Remote - India',              'Engineering', True,  'remote India'),
        ('Backend Engineer Intern',              'Pan India',                   'Engineering', True,  'pan-India phrasing'),
        ('Firmware Intern',                      'Kochi, Kerala',               'Engineering', True,  'tier-2 city'),
        ('Research Intern - Computer Vision',    'Bhubaneswar, Odisha',         'Research',    True,  'east India'),

        # --- dropped: right role, wrong country ---
        ('Software Engineer Intern',             'San Francisco, CA',           'Engineering', False, 'US'),
        ('Software Engineer Intern',             'London, UK',                  'Engineering', False, 'UK'),
        ('Software Engineer Intern',             'Helsinki, Finland',           'Engineering', False, 'EU'),
        ('Software Engineer Intern',             'Singapore',                   'Engineering', False, 'APAC but not India'),
        ('Software Engineer Intern',             'Hyderabad, Sindh, Pakistan',  'Engineering', False, 'name collision, Pakistan'),
        ('Software Engineer Intern',             'Salem, OR, United States',    'Engineering', False, 'name collision, Oregon'),
        ('Software Engineer Intern',             'Indianapolis, Indiana, USA',  'Engineering', False, '"India" not inside "Indiana"'),
        ('Software Engineer Intern',             'Remote - Europe',             'Engineering', False, 'EU remote'),

        # --- dropped: right country, not an internship ---
        ('Software Engineer',                    'Bengaluru, India',            'Engineering', False, 'full-time IC'),
        ('Junior Software Engineer',             'Pune, India',                 'Engineering', False, 'junior FT'),
        ('Software Engineer, New Grad',          'Chennai, India',              'Engineering', False, 'new grad FT'),
        ('Senior Software Engineer',             'Bengaluru, India',            'Engineering', False, 'senior FT'),
        ('Graduate Engineer Trainee',            'Pune, India',                 'Engineering', False, 'Indian GET is full-time, not an internship'),
        ('Management Trainee',                   'Mumbai, India',               'Operations',  False, 'MT is full-time'),

        # --- dropped: right country + internship, wrong function ---
        ('HR Intern',                            'Bengaluru, India',            'People',      False, 'HR vetoed'),
        ('Talent Acquisition Intern',            'Gurugram, India',             'People',      False, 'recruiting vetoed'),
        ('Finance Intern',                       'Mumbai, India',               'Finance',     False, 'finance vetoed'),
        ('Sales Development Intern',             'Delhi, India',                'Sales',       False, 'sales vetoed'),
        ('Content Writing Intern',               'Bengaluru, India',            'Marketing',   False, 'marketing vetoed'),
        ('International Tax Advisor',            'Mumbai, India',               'Finance',     False, 'finance, has "intern" substring'),
        ('Stage Manager',                        'Mumbai, India',               'Production',  False, '"stage" false-positive guard'),
        ('Engineering Manager Intern',           'Bengaluru, India',            'Engineering', False, 'IC-only, "manager" vetoed'),
    ]

    ok = bad = 0
    for title, loc, dept, expected, reason in cases:
        job = {"title": title, "location": loc, "department": dept, "posted_at": now}
        got = passes(job)
        mark = "OK" if got == expected else "FAIL"
        if got == expected:
            ok += 1
        else:
            bad += 1
        print(f"{mark:4}  expect={int(expected)} got={int(got)}  "
              f"{title:40} | {loc:30} | {reason}")

    # --- label_for() ---
    label_cases = [
        ("Software Engineer Intern",          "Internship"),
        ("SDE Intern",                        "Internship"),
        ("Industrial Trainee - VLSI",         "Internship"),
        ("Graduate Software Engineer",        "New grad"),
        ("Software Engineer, New Grad",       "New grad"),
        ("Junior Software Engineer",          "Junior"),
        ("Associate Software Engineer",       "Junior"),
        ("SDE 1, Payments",                   "Junior"),
        ("Software Engineer III",             "Regular"),
        ("Software Engineer",                 "Regular"),
    ]
    print("\n--- label_for() ---")
    for title, expected in label_cases:
        got = label_for({"title": title})
        mark = "OK" if got == expected else "FAIL"
        if got == expected:
            ok += 1
        else:
            bad += 1
        print(f"{mark:4}  expect={expected:11}  got={got:11}  {title}")

    # --- is_india_location() ---
    geo_cases = [
        ("Bengaluru, Karnataka, India", True),
        ("Bangalore", True),
        ("Hyderabad, Telangana", True),
        ("Gurugram", True),
        ("Sector 62, Noida", True),
        ("Navi Mumbai", True),
        ("Hinjewadi, Pune", True),
        ("Guwahati, Assam", True),
        ("Thiruvananthapuram", True),
        ("Bengaluru / Gurgaon", True),
        ("IND-Bengaluru", True),
        ("Remote (India)", True),
        ("Hyderabad, Sindh, Pakistan", False),
        ("Lahore, Punjab, Pakistan", False),
        ("Salem, OR, United States", False),
        ("Indianapolis, Indiana, USA", False),
        ("Dhaka, Bangladesh", False),
        ("Helsinki, Finland", False),
        ("Remote in EMEA", False),
        ("", False),
    ]
    print("\n--- is_india_location() ---")
    for loc, expected in geo_cases:
        got = is_india_location(loc)
        mark = "OK" if got == expected else "FAIL"
        if got == expected:
            ok += 1
        else:
            bad += 1
        print(f"{mark:4}  expect={int(expected)} got={int(got)}  {loc!r}")

    # --- digest metro buckets ---
    metro_cases = [
        ("Whitefield, Bengaluru", is_bengaluru_location, True),
        ("Gachibowli, Hyderabad", is_hyderabad_location, True),
        ("Sector 62, Noida",      is_ncr_location,       True),
        ("Powai, Mumbai",         is_mumbai_location,    True),
        ("Kharadi, Pune",         is_pune_location,      True),
        ("Guindy, Chennai",       is_chennai_location,   True),
        ("Jaipur, Rajasthan",     is_bengaluru_location, False),
        ("Jaipur, Rajasthan",     is_ncr_location,       False),
    ]
    print("\n--- metro buckets ---")
    for loc, fn, expected in metro_cases:
        got = fn(loc)
        mark = "OK" if got == expected else "FAIL"
        if got == expected:
            ok += 1
        else:
            bad += 1
        print(f"{mark:4}  expect={int(expected)} got={int(got)}  "
              f"{fn.__name__}({loc!r})")

    print(f"\n{ok}/{ok + bad} passed")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
