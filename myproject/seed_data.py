"""
Seed data script: Imports all data from backup.sql into Supabase.
Run with: python manage.py shell < seed_data.py
  OR:     python seed_data.py  (if DJANGO_SETTINGS_MODULE is set)
"""

import os
import sys
import django
import uuid

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User
from Canteen_backend.models import Canteen, Product, Menu, Cart, CartItem, Order, OrderItem

print("=" * 60)
print("Seeding Supabase database from backup.sql data...")
print("=" * 60)

# ─── 1. USERS ─────────────────────────────────────────────────
print("\n[1/5] Inserting Users...")
users_data = [
    dict(id=7,  username='Hari',    email='harisenthil13@outlook.com', password='pbkdf2_sha256$1000000$Bs4W6CKFQ5hjssd4satC2Z$6vX1T/W0qH9xnbn6bsCg/etNaLAtwlKUGOjiGqPIVqE=', is_superuser=False, is_staff=False, is_active=True, date_joined='2025-09-21 06:22:56.270884'),
    dict(id=8,  username='deepak',  email='deepak@gmail.com',          password='pbkdf2_sha256$1000000$jCENgsnFcLz3LgPRKiNaje$x5qhYtFK9rJ/Z5ebTR6LOdfi5XuiYsBh/brjU1NfRYY=', is_superuser=False, is_staff=False, is_active=True, date_joined='2025-09-21 06:28:45.301180'),
    dict(id=9,  username='Sandeep', email='sandeep@gmail.com',         password='pbkdf2_sha256$1000000$IPZpkOp4x917tpTipRIlA9$Pw38pbd2tK71iibUDFcIMQtVVYzKPuX2XBjqPLgA6YY=', is_superuser=False, is_staff=False, is_active=True, date_joined='2025-09-22 05:36:58.082707'),
    dict(id=10, username='Abishek', email='abishek@gmail.com',         password='pbkdf2_sha256$1000000$wzWOT9IyY22WmcS1PKCsIh$uzvPummg2o8obFaaAGwF44GI7G6wrX13zku/Hi1el8A=', is_superuser=False, is_staff=False, is_active=True, date_joined='2025-09-22 06:23:24.513652'),
    dict(id=11, username='sriram',  email='sriram@gmail.com',          password='pbkdf2_sha256$1000000$A9RopdChdAqR0BkjS0kDnT$Ft95CoCHPWCvekZAW6IJRfdvI5vs/Ih+vu7BBJ3c3D4=', is_superuser=False, is_staff=False, is_active=True, date_joined='2025-09-22 06:27:06.930246'),
    dict(id=12, username='logesh',  email='logesh@gmail.com',          password='pbkdf2_sha256$1000000$Boc1PMxQGkigq4yR9na8gK$Vi+YFJBcD1V8kppSntqYW5W3ltnfoF0QqAhEzBkCwa0=', is_superuser=False, is_staff=False, is_active=True, date_joined='2025-09-22 06:33:40.710880'),
    dict(id=13, username='sri',     email='sri@gmail.com',             password='pbkdf2_sha256$1000000$f8VHYEXsbmONgMhg5Q1tYz$bmMQ/UAkcC7Y0UBs18t4d7gRgZnHN+airKekUOpXUvM=', is_superuser=False, is_staff=False, is_active=True, date_joined='2025-09-22 06:36:18.174939'),
    dict(id=14, username='admin',   email='admin@gmail.com',           password='pbkdf2_sha256$1000000$xb6cN18osKDUwEdcQOX6ox$Hmf4JB4wt7Wwh67EPdLvM5GuUXBJXa8dY7pP8X09pTM=', is_superuser=False, is_staff=False, is_active=True, date_joined='2025-09-22 06:37:58.103893'),
    dict(id=15, username='guest',   email='guest@gmail.com',           password='pbkdf2_sha256$1000000$yL26rhTB1wsrTFVLjStCwv$FwKwzr9prkreaYxIRnBSjFEeneJOdY7DlL3Kq8QR7EI=', is_superuser=False, is_staff=False, is_active=True, date_joined='2025-09-22 06:45:00.718979'),
    dict(id=16, username='krish',   email='krish@gmail.com',           password='pbkdf2_sha256$1000000$JHhH6EjUemRWjcfD61yv6F$aHBm6X917w5cktZciieomNlaZfacr70kb3vCzoR2+Rc=', is_superuser=False, is_staff=False, is_active=True, date_joined='2025-09-22 06:45:48.394939'),
    dict(id=17, username='yogesh',  email='yogesh@gmail.com',          password='pbkdf2_sha256$1000000$GArjFheK8vEBNjPUmQH1Ct$w3dxng9w9sU5xv0kKwFolKaVFylwN2mcCEwGa6lCg64=', is_superuser=False, is_staff=False, is_active=True, date_joined='2025-09-22 07:24:51.862504'),
    dict(id=18, username='janarth', email='janarth@gmail.com',         password='pbkdf2_sha256$1000000$xMbt4s9jGjWyNSiK8S75Wz$QN1FCOBJYP1OD1fqc1fTxJzH1a8BWFWBdc0xew8zzgk=', is_superuser=False, is_staff=False, is_active=True, date_joined='2025-09-22 09:10:50.079316'),
]

for u in users_data:
    obj, created = User.objects.get_or_create(id=u['id'], defaults={
        'username': u['username'],
        'email': u['email'],
        'password': u['password'],
        'is_superuser': u['is_superuser'],
        'is_staff': u['is_staff'],
        'is_active': u['is_active'],
    })
    status = "CREATED" if created else "SKIPPED (exists)"
    print(f"  User [{u['id']}] {u['username']}: {status}")

# ─── 2. CANTEENS ───────────────────────────────────────────────
print("\n[2/5] Inserting Canteens...")
canteens_data = [
    dict(id='24c1a6a4-d9f9-426f-a0eb-8e30b7a86ce5', name='Main Canteen (SOPANAM)', location='Near AB1'),
    dict(id='6dedf492-3b41-43c1-b40e-e7d5cd4e7b97', name='IT Canteen',             location='Near AB3'),
    dict(id='bc65894a-1032-43c8-9b49-78fce23ac6e0', name='MBA Canteen',            location='Near Business School'),
]

for c in canteens_data:
    obj, created = Canteen.objects.get_or_create(id=uuid.UUID(c['id']), defaults={
        'name': c['name'],
        'location': c['location'],
    })
    status = "CREATED" if created else "SKIPPED (exists)"
    print(f"  Canteen: {c['name']}: {status}")

# ─── 3. PRODUCTS ───────────────────────────────────────────────
print("\n[3/5] Inserting Products...")
products_data = [
    dict(id=1, product_code='A001', name='Black Tea',    price=15.0, type='Beverages', url='https://images.pexels.com/photos/13032225/pexels-photo-13032225.jpeg'),
    dict(id=2, product_code='A002', name='Black Coffee', price=15.0, type='Beverages', url='https://images.pexels.com/photos/1627931/pexels-photo-1627931.jpeg'),
    dict(id=3, product_code='A003', name='Black Boost',  price=20.0, type='Beverages', url='https://m.media-amazon.com/images/I/51+cuHopFsL.jpg'),
    dict(id=4, product_code='A004', name='Veg Puffs',    price=20.0, type='Snacks',    url='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTLAGi1iKwDtgu-pTJJzutB0ZKUtO_O2hS_Sg&s'),
    dict(id=5, product_code='A005', name='Egg Puffs',    price=25.0, type='Snacks',    url='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT0efCCOAs0Pg5S7SbI3Z4ACvYE1krAhurfvg&s'),
    dict(id=6, product_code='A006', name='Plain Dosa',   price=30.0, type='Meals',     url='https://cdn3.foodviva.com/static-content/food-images/south-indian-recipes/dosa-recipe/dosa-recipe.jpg'),
    dict(id=7, product_code='A007', name='Masala Dosa',  price=40.0, type='Meals',     url='https://t4.ftcdn.net/jpg/16/27/96/47/360_F_1627964740_eShNRJesWQ9oaEfOXHYRjXLT7pATobDZ.jpg'),
]

for p in products_data:
    obj, created = Product.objects.get_or_create(id=p['id'], defaults={
        'product_code': p['product_code'],
        'name': p['name'],
        'price': p['price'],
        'type': p['type'],
        'url': p['url'],
        'canteen_id': uuid.UUID('24c1a6a4-d9f9-426f-a0eb-8e30b7a86ce5'),
    })
    status = "CREATED" if created else "SKIPPED (exists)"
    print(f"  Product [{p['id']}] {p['name']}: {status}")

# ─── 4. MENU ───────────────────────────────────────────────────
print("\n[4/5] Inserting Menu entries...")
menu_data = [
    dict(id=1, stock=50, canteen_id='24c1a6a4-d9f9-426f-a0eb-8e30b7a86ce5', product_id=1),
    dict(id=2, stock=30, canteen_id='24c1a6a4-d9f9-426f-a0eb-8e30b7a86ce5', product_id=2),
    dict(id=3, stock=20, canteen_id='6dedf492-3b41-43c1-b40e-e7d5cd4e7b97', product_id=4),
    dict(id=4, stock=25, canteen_id='6dedf492-3b41-43c1-b40e-e7d5cd4e7b97', product_id=5),
    dict(id=5, stock=15, canteen_id='bc65894a-1032-43c8-9b49-78fce23ac6e0', product_id=6),
    dict(id=6, stock=10, canteen_id='bc65894a-1032-43c8-9b49-78fce23ac6e0', product_id=7),
]

for m in menu_data:
    obj, created = Menu.objects.get_or_create(
        canteen_id=uuid.UUID(m['canteen_id']),
        product_id=m['product_id'],
        defaults={'stock': m['stock']}
    )
    status = "CREATED" if created else "SKIPPED (exists)"
    print(f"  Menu [canteen={m['canteen_id'][-12:]}, product={m['product_id']}]: {status}")

# ─── 5. SEQUENCE RESET (PostgreSQL) ───────────────────────────
print("\n[5/5] Resetting PostgreSQL sequences...")
from django.db import connection

with connection.cursor() as cursor:
    # Reset auth_user sequence so new users get IDs > 18
    cursor.execute("SELECT setval(pg_get_serial_sequence('auth_user', 'id'), MAX(id)) FROM auth_user;")
    # Reset product sequence
    cursor.execute("SELECT setval(pg_get_serial_sequence('\"Canteen_backend_product\"', 'id'), MAX(id)) FROM \"Canteen_backend_product\";")
    # Reset menu sequence
    cursor.execute("SELECT setval(pg_get_serial_sequence('\"Canteen_backend_menu\"', 'id'), MAX(id)) FROM \"Canteen_backend_menu\";")
    print("  Sequences reset successfully.")

print("\n" + "=" * 60)
print("✅ All data seeded successfully into Supabase!")
print("=" * 60)
