import os, django, random, urllib.request, ssl
from django.core.files.base import ContentFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()

from django.contrib.auth.models import User
from products.models import Category, Product

def fetch_img(url):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            return ContentFile(resp.read())
    except Exception as e:
        print(f"Failed to fetch image {url}: {e}")
        return None

def seed_more():
    print("Seeding 20+ Additional Products for Islington Marketplace...")

    students = list(User.objects.filter(is_superuser=False))
    if not students:
        students = [User.objects.filter(is_superuser=True).first()]

    # Retrieve categories
    cat_books = Category.objects.filter(name__icontains="Book").first() or Category.objects.create(name="Books & Textbooks")
    cat_tech = Category.objects.filter(name__icontains="Tech").first() or Category.objects.create(name="Electronics & Tech")
    cat_audio = Category.objects.filter(name__icontains="Audio").first() or Category.objects.create(name="Accessories & Audio")
    cat_fashion = Category.objects.filter(name__icontains="Clothing").first() or Category.objects.create(name="Clothing & Fashion")
    cat_lab = Category.objects.filter(name__icontains="Lab").first() or Category.objects.create(name="Stationery & Lab Gear")
    cat_study = Category.objects.filter(name__icontains="Study").first() or Category.objects.create(name="Others & Study Gear")

    new_items = [
        # Books & Textbooks
        {
            "name": "Clean Code & Refactoring Collection by Robert C. Martin",
            "category": cat_books,
            "price": 1850.00,
            "stock": 3,
            "description": "Essential software engineering books for Islington Year 2/3 students. Clean condition with no highlighted markings.",
            "img": "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=600&auto=format&fit=crop"
        },
        {
            "name": "Design Patterns: Elements of Reusable Object-Oriented Software",
            "category": cat_books,
            "price": 1400.00,
            "stock": 2,
            "description": "Gang of Four design patterns reference book. Must-read for Software Engineering coursework.",
            "img": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop"
        },
        {
            "name": "Database System Concepts (7th Edition) - Silberschatz",
            "category": cat_books,
            "price": 1650.00,
            "stock": 1,
            "description": "Comprehensive textbook covering SQL, Relational Algebra, and Query Optimization. Great condition.",
            "img": "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=600&auto=format&fit=crop"
        },
        {
            "name": "Artificial Intelligence: A Modern Approach (4th Edition)",
            "category": cat_books,
            "price": 2200.00,
            "stock": 2,
            "description": "Standard AI textbook by Russell & Norvig. Includes machine learning and search algorithms.",
            "img": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=600&auto=format&fit=crop"
        },

        # Electronics & Tech
        {
            "name": "Dell UltraSharp 27-inch 4K Monitor (USB-C Hub Display)",
            "category": cat_tech,
            "price": 42000.00,
            "stock": 1,
            "description": "IPS panel with 99% sRGB color accuracy. Built-in USB-C hub charges laptop while outputting 4K display. Zero dead pixels.",
            "img": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&auto=format&fit=crop"
        },
        {
            "name": "Keychron K2 Wireless Mechanical Keyboard (RGB Gateron Brown Switches)",
            "category": cat_tech,
            "price": 8500.00,
            "stock": 2,
            "description": "Compact 75% layout mechanical keyboard with Mac & Windows support. Bluetooth 5.1 & Type-C wired mode.",
            "img": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop"
        },
        {
            "name": "Logitech MX Master 3S Wireless Ergonomic Mouse",
            "category": cat_tech,
            "price": 9800.00,
            "stock": 2,
            "description": "Quiet clicks, 8K DPI glass tracking, electromagnetic scroll wheel. Ideal for programming and design work.",
            "img": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop"
        },
        {
            "name": "Raspberry Pi 4 Model B (8GB RAM) Starter Kit",
            "category": cat_tech,
            "price": 11500.00,
            "stock": 1,
            "description": "Includes 64GB MicroSD card, official case, cooling fans, and micro HDMI cables. Used for IoT assignment.",
            "img": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop"
        },
        {
            "name": "iPad Air 5th Gen (64GB M1 Chip + Apple Pencil 2)",
            "category": cat_tech,
            "price": 72000.00,
            "stock": 1,
            "description": "Space Gray iPad Air with M1 processor. Includes magnetic Apple Pencil 2 for digital note taking.",
            "img": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop"
        },

        # Accessories & Audio
        {
            "name": "Sony WH-1000XM5 Noise Canceling Headphones",
            "category": cat_audio,
            "price": 31000.00,
            "stock": 1,
            "description": "Industry leading active noise cancellation. 30-hour battery life. Perfect for studying in quiet library blocks.",
            "img": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop"
        },
        {
            "name": "Anker PowerCore 24,000mAh 65W Power Bank",
            "category": cat_audio,
            "price": 6200.00,
            "stock": 3,
            "description": "Fast charges laptops and smartphones simultaneously. Ideal for long days on campus.",
            "img": "https://images.unsplash.com/photo-1609592424074-122485c2c770?w=600&auto=format&fit=crop"
        },
        {
            "name": "AirPods Pro 2nd Gen (USB-C Charging Case)",
            "category": cat_audio,
            "price": 24500.00,
            "stock": 2,
            "description": "Apple AirPods Pro with Active Noise Cancellation and Transparency mode. Original box and tips included.",
            "img": "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=600&auto=format&fit=crop"
        },

        # Clothing & Fashion
        {
            "name": "Herschel Supply Co. Little America Laptop Backpack (25L)",
            "category": cat_fashion,
            "price": 5400.00,
            "stock": 2,
            "description": "Durable navy blue campus backpack with padded fleece 15-inch laptop sleeve.",
            "img": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop"
        },
        {
            "name": "Islington Official Student Hoodie (Size M, Navy Blue)",
            "category": cat_fashion,
            "price": 1800.00,
            "stock": 4,
            "description": "Comfortable fleece-lined college hoodie. Lightly worn, great condition.",
            "img": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=600&auto=format&fit=crop"
        },

        # Stationery & Lab Gear
        {
            "name": "Arduino Uno R3 Electronics Project Starter Kit",
            "category": cat_lab,
            "price": 3400.00,
            "stock": 3,
            "description": "Complete kit with breadboard, LEDs, resistors, servos, LCD screen, and ultrasonic sensors.",
            "img": "https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?w=600&auto=format&fit=crop"
        },
        {
            "name": "Wacom One Graphic Drawing Tablet for UI Design",
            "category": cat_lab,
            "price": 7800.00,
            "stock": 2,
            "description": "Battery-free pressure sensitive pen. Great for Figma prototyping and digital sketching.",
            "img": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=600&auto=format&fit=crop"
        },

        # Others & Study Gear
        {
            "name": "Baseus LED Desk Lamp with Wireless Phone Charging Base",
            "category": cat_study,
            "price": 3200.00,
            "stock": 2,
            "description": "Adjustable color temperature & brightness. Wireless charging pad built into base.",
            "img": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=600&auto=format&fit=crop"
        },
        {
            "name": "Ember Temperature Control Smart Mug 2 (10 oz)",
            "category": cat_study,
            "price": 9500.00,
            "stock": 1,
            "description": "Keeps your coffee or tea at your preferred drinking temperature for 1.5 hours.",
            "img": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=600&auto=format&fit=crop"
        }
    ]

    added_count = 0
    for data in new_items:
        usr = random.choice(students)
        p, created = Product.objects.get_or_create(
            name=data['name'],
            defaults={
                'category': data['category'],
                'price': data['price'],
                'stock': data['stock'],
                'description': data['description'],
                'user': usr,
                'status': True,
                'is_approved': True
            }
        )
        if created:
            cf = fetch_img(data['img'])
            if cf:
                p.product_image.save(f"item_{p.id}.jpg", cf, save=True)
            added_count += 1
            print(f"  + Added Product: {p.name} (Rs. {p.price:.2f})")

    print(f"Successfully added {added_count} new products to Islington Marketplace!")

if __name__ == '__main__':
    seed_more()
