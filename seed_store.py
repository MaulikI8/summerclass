import os, django, random, urllib.request
from datetime import timedelta
from django.utils import timezone
from django.core.files.base import ContentFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()

from django.contrib.auth.models import User
from products.models import Category, Product, Auction, Bid, ItemRequest
from sitesetting.models import Banner, SiteSetting
from blog.models import Post as BlogPost, Category as BlogCategory

def fetch_img_file(url):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=4, context=ctx) as resp:
            return ContentFile(resp.read())
    except Exception:
        return None

def seed_database():
    print("Starting Store Seeding for Islington Marketplace...")

    # 1. Standardize Categories
    categories_data = [
        ("Books & Textbooks", "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=500&auto=format&fit=crop"),
        ("Electronics & Tech", "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=500&auto=format&fit=crop"),
        ("Accessories & Audio", "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&auto=format&fit=crop"),
        ("Clothing & Fashion", "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=500&auto=format&fit=crop"),
        ("Stationery & Lab Gear", "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=500&auto=format&fit=crop"),
        ("Others & Study Gear", "https://images.unsplash.com/photo-1517842645767-c639042777db?w=500&auto=format&fit=crop"),
    ]

    cat_objs = {}
    for name, img_url in categories_data:
        cat, created = Category.objects.get_or_create(name=name)
        if not cat.category_image:
            cf = fetch_img_file(img_url)
            if cf:
                cat.category_image.save(f"cat_{cat.id}.jpg", cf, save=True)
        cat_objs[name] = cat
        print(f"  Category: {cat.name}")

    # Remove old placeholder categories
    Category.objects.filter(name__in=['electronic', 'Test Category']).delete()

    # 2. Student Accounts
    students_data = [
        ("aayush_islington", "Aayush", "Shrestha", "aayush.s@islington.edu.np"),
        ("smarika_comp", "Smarika", "Karki", "smarika.k@islington.edu.np"),
        ("rohan_net", "Rohan", "Thapa", "rohan.t@islington.edu.np"),
        ("prashant_tech", "Prashant", "Gurung", "prashant.g@islington.edu.np"),
        ("neha_it", "Neha", "Adhikari", "neha.a@islington.edu.np"),
    ]

    user_objs = []
    for uname, fname, lname, email in students_data:
        usr, _ = User.objects.get_or_create(username=uname, defaults={
            'first_name': fname, 'last_name': lname, 'email': email, 'is_active': True
        })
        usr.set_password("StudentPass123!")
        usr.is_active = True
        usr.save()
        user_objs.append(usr)
        print(f"  Student Account: {usr.username}")

    admin_user = User.objects.filter(is_superuser=True).first() or user_objs[0]

    # 3. Product Listings
    products_data = [
        {
            "name": "PlayStation 5 Console (Disc Edition + 2 Controllers)",
            "category": "Electronics & Tech",
            "price": 68500.00,
            "stock": 1,
            "description": "Sony PlayStation 5 in pristine condition. Includes 2 original DualSense controllers and HDMI 2.1 cable. Barely used during semester break.",
            "user": user_objs[0],
            "img": "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?w=600&auto=format&fit=crop"
        },
        {
            "name": "MacBook Pro 14-inch M2 Pro (16GB RAM / 512GB SSD)",
            "category": "Electronics & Tech",
            "price": 235000.00,
            "stock": 1,
            "description": "Apple M2 Pro chip with 10-core CPU and 16-core GPU. Perfect for Mobile App Dev & AI assignments. Battery cycle count only 42.",
            "user": user_objs[1],
            "img": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop"
        },
        {
            "name": "BSc (Hons) Computing Year 2 Complete Textbook Set",
            "category": "Books & Textbooks",
            "price": 3200.00,
            "stock": 2,
            "description": "Includes Java Software Solutions (9th Ed), Data Structures & Algorithms, and Computer Networking Top-Down Approach. Clean pages with highlighted notes.",
            "user": user_objs[2],
            "img": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop"
        },
        {
            "name": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
            "category": "Accessories & Audio",
            "price": 36000.00,
            "stock": 1,
            "description": "Industry leading noise cancellation headphones. Great for studying in quiet library blocks. Includes original carrying case and 3.5mm jack.",
            "user": user_objs[3],
            "img": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop"
        },
        {
            "name": "Logitech MX Master 3S Wireless Performance Mouse",
            "category": "Accessories & Audio",
            "price": 12800.00,
            "stock": 3,
            "description": "Ultra-quiet clicks, 8K DPI sensor on glass tracking. Ergonomic design ideal for long coding sessions and UI design assignments.",
            "user": user_objs[4],
            "img": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop"
        },
        {
            "name": "Arduino Uno R3 Ultimate Project Starter Electronics Kit",
            "category": "Stationery & Lab Gear",
            "price": 3400.00,
            "stock": 4,
            "description": "Complete IoT & Embedded Systems lab kit. Includes breadboard, jumper wires, sensors, LCD screen, step motors, and resistors.",
            "user": user_objs[0],
            "img": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop"
        },
        {
            "name": "Meditations by Marcus Aurelius (Penguin Classics Hardcover)",
            "category": "Books & Textbooks",
            "price": 550.00,
            "stock": 5,
            "description": "Classic stoic philosophy book translated by Gregory Hays. Excellent read for personal development and critical thinking.",
            "user": user_objs[1],
            "img": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=600&auto=format&fit=crop"
        },
        {
            "name": "Oversized Islington Campus Tech Club Hoodie (Black / Large)",
            "category": "Clothing & Fashion",
            "price": 2400.00,
            "stock": 2,
            "description": "Heavyweight 380 GSM fleece cotton hoodie. Soft inner lining with minimal futuristic tech typography print.",
            "user": user_objs[2],
            "img": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=600&auto=format&fit=crop"
        },
        {
            "name": "IKEA Minimalist Study Desk & Ergonomic Mesh Chair Combo",
            "category": "Others & Study Gear",
            "price": 16500.00,
            "stock": 1,
            "description": "Clean white computer table (120x60cm) + height-adjustable lumbar mesh office chair. Perfect student room setup for hostel/apartment.",
            "user": user_objs[3],
            "img": "https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?w=600&auto=format&fit=crop"
        },
        {
            "name": "Casio FX-991EX ClassWiz Non-Programmable Scientific Calculator",
            "category": "Stationery & Lab Gear",
            "price": 1950.00,
            "stock": 3,
            "description": "High-resolution natural textbook display calculator. Allowed in all Islington university examinations.",
            "user": user_objs[4],
            "img": "https://images.unsplash.com/photo-1594980596870-8aa52a78d8cd?w=600&auto=format&fit=crop"
        },
        {
            "name": "Anker PowerCore 20,000mAh 22.5W Fast Charging Power Bank",
            "category": "Accessories & Audio",
            "price": 4500.00,
            "stock": 2,
            "description": "Dual USB-A and Type-C PowerIQ fast charger. Charges smartphones 4-5 times over during long lectures.",
            "user": user_objs[0],
            "img": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop"
        },
        {
            "name": "Dell UltraSharp 27-inch 4K USB-C Monitor (U2723QE)",
            "category": "Electronics & Tech",
            "price": 48000.00,
            "stock": 1,
            "description": "IPS Black technology with 2000:1 contrast ratio and 90W USB-C power delivery for laptops. Zero backlight bleed.",
            "user": user_objs[1],
            "img": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&auto=format&fit=crop"
        }
    ]

    prod_objs = []
    for item in products_data:
        cat = cat_objs[item["category"]]
        p, created = Product.objects.get_or_create(
            name=item["name"],
            defaults={
                'category': cat,
                'user': item["user"],
                'price': item["price"],
                'stock': item["stock"],
                'description': item["description"],
                'status': True,
                'is_approved': True
            }
        )
        # Update fields if exists
        p.price = item["price"]
        p.stock = item["stock"]
        p.description = item["description"]
        p.status = True
        p.is_approved = True
        if not p.product_image:
            cf = fetch_img_file(item["img"])
            if cf:
                p.product_image.save(f"prod_{p.id}.jpg", cf, save=False)
        p.save()
        prod_objs.append(p)
        print(f"  Product: {p.name} (Rs. {p.price})")

    # 4. Live 24-Hour Auctions
    auctions_data = [
        (prod_objs[0], "PlayStation 5 Console — 24h Live Student Auction", 55000.0, 62000.0),
        (prod_objs[3], "Sony WH-1000XM5 Headphones — Campus Bid Hub", 28000.0, 31000.0),
        (prod_objs[5], "Arduino Uno R3 Electronics Starter Kit Auction", 2200.0, 2800.0),
    ]

    for prod, title, start_bid, cur_bid in auctions_data:
        auc, _ = Auction.objects.get_or_create(
            product=prod,
            defaults={
                'title': title,
                'starting_bid': start_bid,
                'current_bid': cur_bid,
                'highest_bidder': user_objs[2],
                'end_time': timezone.now() + timedelta(hours=18),
                'is_active': True
            }
        )
        auc.title = title
        auc.current_bid = cur_bid
        auc.highest_bidder = user_objs[2]
        auc.end_time = timezone.now() + timedelta(hours=18)
        auc.is_active = True
        auc.save()

        Bid.objects.get_or_create(auction=auc, user=user_objs[2], defaults={'amount': cur_bid})
        print(f"  Auction: {auc.title}")

    # 5. Campus Wanted Requests
    requests_data = [
        ("Java Programming 9th Edition Book Needed", 800.0, "today", "Kumari Hall", "Need clean copy for lab reference test today."),
        ("USB-C to HDMI DisplayPort Dongle Adapter", 750.0, "today", "Skill Block", "For presentation in Skill Block Room 302."),
        ("Breadboard & Jumper Wires Set for IoT Assignment", 500.0, "week", "Nepal Block", "Flexible on condition as long as connections work."),
    ]

    for req_title, budget, urgency, loc, desc in requests_data:
        ItemRequest.objects.get_or_create(
            title=req_title,
            defaults={
                'user': user_objs[3],
                'budget': budget,
                'urgency': urgency,
                'preferred_location': loc,
                'description': desc,
                'is_fulfilled': False
            }
        )
        print(f"  Wanted Request: {req_title}")

    # 6. Hero Banners
    Banner.objects.all().delete()
    Banner.objects.create(
        featured_product=prod_objs[0],
        title="PlayStation 5 Console",
        subtitle="Sony PS5 Disc Edition + 2 Wireless Controllers. Instant campus pickup available.",
        badge_text="FEATURED • RS. 68,500.00",
        badge_icon="fa-star",
        theme_color="slide-blue",
        primary_btn_text="View Listing",
        primary_btn_url=f"/products/{prod_objs[0].id}/",
        secondary_btn_text="Explore Store",
        secondary_btn_url="/products/",
        order=1,
        is_active=True
    )
    Banner.objects.create(
        featured_product=prod_objs[1],
        title="MacBook Pro 14-inch M2 Pro",
        subtitle="16GB RAM / 512GB SSD. Pristine condition with only 42 battery cycle counts.",
        badge_text="STUDENT DEAL • RS. 235,000.00",
        badge_icon="fa-laptop",
        theme_color="slide-purple",
        primary_btn_text="View Listing",
        primary_btn_url=f"/products/{prod_objs[1].id}/",
        secondary_btn_text="Browse Laptops",
        secondary_btn_url="/products/?category=Electronics%20%26%20Tech",
        order=2,
        is_active=True
    )
    Banner.objects.create(
        featured_product=prod_objs[3],
        title="Sony WH-1000XM5 Headphones",
        subtitle="Active Noise Cancellation headphones. Ideal for study sessions in quiet campus blocks.",
        badge_text="LIVE AUCTION • CURRENT RS. 31,000",
        badge_icon="fa-headphones",
        theme_color="slide-green",
        primary_btn_text="Place Bid",
        primary_btn_url=f"/products/{prod_objs[3].id}/",
        secondary_btn_text="All Auctions",
        secondary_btn_url="/#liveBiddingSection",
        order=3,
        is_active=True
    )

    # 7. Campus Blogs & Guides
    bcat, _ = BlogCategory.objects.get_or_create(name="Campus Life & Advice")
    blog_data = [
        ("Top 5 Textbooks Every Islington Computing Student Needs in Year 2", "Navigating your second year in BSc (Hons) Computing can feel challenging without the right reference books. Here is our curated list of essential textbooks for Data Structures, Mobile Apps, and Computer Systems.", "Guide"),
        ("How to Prepare Your Tech Gear for Embedded Systems Lab Assignments", "From setting up your Arduino Uno drivers on macOS and Windows to organizing jumper wires and breadboards — here is the ultimate checklist before heading to Skill Block labs.", "Guide"),
        ("Islington Peer Trade Guide: Buying & Selling Used Laptops Safely", "Trading student items peer-to-peer on campus is safe, convenient, and wallet-friendly. Learn how to verify battery health cycles, check physical ports, and agree on meetup points like Kumari Hall.", "Guide")
    ]
    for btitle, bcontent, btag in blog_data:
        BlogPost.objects.get_or_create(
            title=btitle,
            defaults={
                'author': user_objs[0],
                'category': bcat,
                'content': bcontent,
                'tag': btag,
                'status': True
            }
        )
        print(f"  Blog Article: {btitle}")

    print("\n[SUCCESS] Store Seeding Completed Successfully! All categories, products, auctions, blogs, and banners are live!")

if __name__ == "__main__":
    seed_database()
