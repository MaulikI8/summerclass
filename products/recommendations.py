from collections import defaultdict
import numpy as np
from django.db.models import Sum, Avg
from django.utils import timezone
from datetime import timedelta

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from .models import Product, SearchHistory, ProductView, Review
from .models import OrderItem


class HybridRecommender:
    """
    Hybrid AI Recommendation Engine (TF-IDF + Behavioral + Category Preference + Ratings + Popularity)
    Implementation based on Islington Marketplace Hybrid Recommender specification.
    """
    def __init__(self, request):
        self.request = request
        self.user = request.user if request.user.is_authenticated else None
        if not request.session.session_key:
            request.session.create()
        self.session_key = request.session.session_key

        # 1. Candidate Product Set: active, approved, in-stock items
        qs = Product.objects.filter(status=True, is_approved=True, stock__gt=0).select_related("category")
        if self.user:
            qs = qs.exclude(user=self.user)
        self.products = list(qs)
        self.product_ids = [p.id for p in self.products]
        self.product_index = {p.id: idx for idx, p in enumerate(self.products)}

        self.documents = []
        for p in self.products:
            cat_name = p.category.name if p.category else ""
            self.documents.append(f"{p.name} {p.description or ''} {cat_name}")

        self.vectorizer = None
        self.product_matrix = None

        if HAS_SKLEARN and self.documents:
            try:
                self.vectorizer = TfidfVectorizer(stop_words="english")
                self.product_matrix = self.vectorizer.fit_transform(self.documents)
            except Exception:
                self.vectorizer = None
                self.product_matrix = None

    def search_scores(self):
        scores = defaultdict(float)
        if not self.vectorizer or self.product_matrix is None:
            return scores

        if self.user:
            searches = SearchHistory.objects.filter(user=self.user).order_by("-created_at")[:20]
        else:
            searches = SearchHistory.objects.filter(user__isnull=True, session_key=self.session_key).order_by("-created_at")[:20]

        queries = list(searches.values_list("query", flat=True))
        if not queries:
            return scores

        # Recency weighting: newest queries get repeated to increase influence
        weighted_queries = []
        for idx, q in enumerate(queries):
            weight = 4 if idx < 3 else (2 if idx < 7 else 1)
            weighted_queries.extend([q] * weight)

        search_text = " ".join(weighted_queries)
        try:
            search_vector = self.vectorizer.transform([search_text])
            similarities = cosine_similarity(search_vector, self.product_matrix)[0]
            for idx, p in enumerate(self.products):
                scores[p.id] = float(similarities[idx])
        except Exception:
            pass

        return scores

    def view_scores(self, current_product=None):
        scores = defaultdict(float)
        if self.product_matrix is None:
            return scores

        if self.user:
            views = ProductView.objects.filter(user=self.user).order_by("-created_at")[:15]
        else:
            views = ProductView.objects.filter(user__isnull=True, session_key=self.session_key).order_by("-created_at")[:15]

        viewed_pids = []
        for pid in views.values_list("product_id", flat=True):
            if current_product and pid == current_product.id:
                continue
            if pid not in viewed_pids:
                viewed_pids.append(pid)

        indexes = [self.product_index[pid] for pid in viewed_pids if pid in self.product_index]
        if not indexes:
            return scores

        try:
            interest_vector = self.product_matrix[indexes].mean(axis=0)
            interest_vector = np.asarray(interest_vector)
            similarities = cosine_similarity(interest_vector, self.product_matrix)[0]
            for idx, p in enumerate(self.products):
                scores[p.id] = float(similarities[idx])
        except Exception:
            pass

        return scores

    def similar_product_scores(self, current_product=None):
        scores = defaultdict(float)
        if not current_product or self.product_matrix is None or current_product.id not in self.product_index:
            return scores

        try:
            cur_idx = self.product_index[current_product.id]
            similarities = cosine_similarity(self.product_matrix[cur_idx], self.product_matrix)[0]
            for idx, p in enumerate(self.products):
                if p.id == current_product.id:
                    continue
                scores[p.id] = float(similarities[idx])
        except Exception:
            pass

        return scores

    def purchase_scores(self):
        scores = defaultdict(float)
        if not self.user:
            return scores

        purchases = OrderItem.objects.filter(order__user=self.user).select_related("product__category")
        if not purchases.exists():
            return scores

        cat_interest = defaultdict(float)
        for item in purchases:
            if item.product and item.product.category_id:
                cat_interest[item.product.category_id] += item.quantity

        if not cat_interest:
            return scores

        max_val = max(cat_interest.values())
        for p in self.products:
            c_score = cat_interest.get(p.category_id, 0)
            if c_score and max_val > 0:
                scores[p.id] = float(c_score / max_val)

        return scores

    def popularity_scores(self):
        scores = defaultdict(float)
        if not self.product_ids:
            return scores

        data = list(OrderItem.objects.filter(product_id__in=self.product_ids).values("product_id").annotate(total_qty=Sum("quantity")))
        if not data:
            return scores

        max_qty = max(row["total_qty"] for row in data if row["total_qty"])
        if not max_qty:
            return scores

        for row in data:
            scores[row["product_id"]] = float(row["total_qty"] / max_qty)

        return scores

    def rating_scores(self):
        scores = defaultdict(float)
        if not self.product_ids:
            return scores

        ratings = Review.objects.filter(product_id__in=self.product_ids, status=True).values("product_id").annotate(avg_rating=Avg("rating"))
        for row in ratings:
            scores[row["product_id"]] = min(float(row["avg_rating"] / 5.0), 1.0)

        return scores

    def recommend(self, current_product=None, limit=4):
        if not self.products:
            return []

        search = self.search_scores()
        views = self.view_scores(current_product=current_product)
        similarity = self.similar_product_scores(current_product=current_product)
        purchases = self.purchase_scores()
        popularity = self.popularity_scores()
        ratings = self.rating_scores()

        purchased_pids = set()
        if self.user:
            purchased_pids = set(OrderItem.objects.filter(order__user=self.user).values_list("product_id", flat=True))

        recs = []
        for p in self.products:
            if current_product and p.id == current_product.id:
                continue
            if p.id in purchased_pids:
                continue

            s_score = search.get(p.id, 0.0)
            v_score = views.get(p.id, 0.0)
            sim_score = similarity.get(p.id, 0.0)
            pur_score = purchases.get(p.id, 0.0)
            pop_score = popularity.get(p.id, 0.0)
            rat_score = ratings.get(p.id, 0.0)

            final_score = (
                s_score * 0.30 +
                v_score * 0.25 +
                sim_score * 0.20 +
                pur_score * 0.15 +
                pop_score * 0.05 +
                rat_score * 0.05
            )

            # Determine best human-readable reason
            weighted_reasons = {
                "Based on your recent searches": s_score * 0.30,
                "Based on products you viewed": v_score * 0.25,
                "Similar to this product": sim_score * 0.20,
                "Based on your previous purchases": pur_score * 0.15,
                "Popular with students": pop_score * 0.05,
                "Highly rated by peers": rat_score * 0.05,
            }

            best_reason_key = max(weighted_reasons, key=weighted_reasons.get)
            reason = best_reason_key if weighted_reasons[best_reason_key] > 0 else "Recommended for you"

            recs.append({
                "product": p,
                "score": round(final_score, 4),
                "reason": reason
            })

        recs.sort(key=lambda item: item["score"], reverse=True)
        return recs[:limit]

    @staticmethod
    def track_view(request, product):
        """30-minute deduplication tracking of product views"""
        if not product or not product.pk:
            return
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        user = request.user if request.user.is_authenticated else None

        thirty_mins_ago = timezone.now() - timedelta(minutes=30)
        recent_exists = ProductView.objects.filter(
            product=product,
            session_key=session_key,
            created_at__gte=thirty_mins_ago
        ).exists()

        if not recent_exists:
            ProductView.objects.create(
                user=user,
                session_key=session_key,
                product=product
            )

    @staticmethod
    def merge_guest_history_on_login(request, user):
        """Attaches guest SearchHistory and ProductView rows to authenticated user account"""
        old_session_key = request.session.session_key
        if old_session_key and user and user.is_authenticated:
            SearchHistory.objects.filter(session_key=old_session_key, user__isnull=True).update(user=user)
            ProductView.objects.filter(session_key=old_session_key, user__isnull=True).update(user=user)
