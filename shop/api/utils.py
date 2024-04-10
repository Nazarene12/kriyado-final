
from shop.models import Customer , Company
import random

def generate_unique_number():
    return random.randint(1000000, 9999990)

def get_unique_number():
    value = generate_unique_number()
    while Customer.objects.filter(customer_id=value).exists():
        value = generate_unique_number()
    return value

def get_unique_number_vendor():
    value = generate_unique_number()
    while Company.objects.filter(vendor_id=value).exists():
        value = generate_unique_number()
    return value