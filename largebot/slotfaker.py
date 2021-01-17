from faker import Faker
from strgen import StringGenerator as stringify
from faker.providers import BaseProvider

templates = {
    'account_number': ['[\d]{2}(-|[\d])[\d]{6:10}[\d\d\d\w-]{2}[\d\w]{1}'],
    'phone_model': [
        'iPhone ([4-9]|X|XS|XS Max|XR|11|12|12 Pro|12 Pro Max|12 mini|SE)',
        'Samsung Galaxy (A21s|A31|A51|A71|M31|S20 Ultra|Note20 Ultra|S20|S10 Lite|Note10 Lite)',
        'OnePlus (8|8 Pro)',
        'Google Pixel (4a|5)',
        'Motorola One'
    ],
    'device_type': [
        'tablet',
        'phone',
        'smart phone',
        'computer',
        'smart watch',
        'streaming device',
        'cable box',
        'television',
        'TV'
    ],
    'subscription_package_level': [
        'Bronze',
        'Silver',
        'Gold',
        'Platinum'
    ],
    'cable_internet_providers': [
        'AT&T Wireless',
        'Verizon Wireless'
        'Spectrum',
        'CenturyLink',
        'EarthLink',
        'Viasat',
        'WOW!',
        'Frontier',
        'HughesNet',
        'Google Fiber',
        'Xfinity',
        'T-Mobile Wireless',
        'Dish'
    ],
    'notification_destination': [
        'phone',
        'tablet',
        'computer',
        'mail'
    ],
    'notification_method': [
        'text',
        'SMS',
        'call',
        'email',
        'mail'
    ],
    'channel_genre': [
        'Sports',
        'Action',
        'History',
        'SitCom',
        'Documentary',
        'Soap',
        'Cartoon',
        'True Crime',
        'Sci Fi'
        'Travel',
        'Kids',
        'Family',
        'Drama',
        'Reality'
    ],
    'credit_card_network': [
        'American Express',
        'MasterCard',
        'Visa',
        'Discover'
    ],
    'payment_schedule': [
        'monthly',
        'semi-monthly',
        'bi-weekly',
        'weekly',
        'quarterly'
    ],
    'operating_system': [
        'iOS',
        'iPadOS',
        'macOS',
        'Windows',
        'Ubuntu Linux',
        'Red Hat Enterprise Linux',
        'Linux Fedora',
        'Chrome OS',
        'Android',
        'Bada',
        'Blackberry OS',
        'Windows OS',
        'Symbian OS',
        'Tizen'
    ],
    'resolution': [
        '720p',
        '1080p',
        'HD'
        '2k',
        'UHD',
        '4K',
        '8K'
    ],
    'device_purpose': [
        'Personal',
        'Business'
    ],
    'media_type': [
        'Application',
        'Music',
        'Video',
        'Document'
    ],
    'streaming_service_name': [
        'Netflix',
        'Hulu',
        'Peacock',
        'YouTube TV',
        'Amazon Prime Video',
        'Disney+',
        'HBO Max',
        'CBS All Access'
    ]
}

class SlotFaker:
    def __init__(self):
        self.fake = Faker()

    def first_name(self):
        return self.fake.name.split()[0]

    def last_name(self):
        return self.fake.name.split()[-1]