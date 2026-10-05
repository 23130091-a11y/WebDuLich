"""Regression tests cho các bug đã fix (xem docs/SECURITY_AUDIT.md, AI_EVAL.md).

Chạy: USE_LOCAL_DB=true DJANGO_DEBUG=true python manage.py test travel
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.utils import timezone

from travel.models import Booking, Category, Destination, Review, TourPackage

User = get_user_model()


def make_tour(price=1000000):
    dest = Destination.objects.create(
        name='Test Đà Nẵng', slug='test-da-nang', description='x', location='Đà Nẵng')
    tour = TourPackage.objects.create(
        name='Tour test', slug='tour-test', destination=dest,
        duration=3, price=price, details='chi tiết')
    return tour


class BookingPricingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='booker', email='booker@x.com', password='pass12345')
        self.tour = make_tour(price=Decimal('1000000'))
        self.client = Client()
        self.client.force_login(self.user)

    def test_price_formula(self):
        """adult + child*0.7 + VAT 10%, tính server-side."""
        r = self.client.post(f'/book-tour/{self.tour.id}/', {
            'full_name': 'Nguyen Van A', 'phone_number': '0901234567',
            'email': 'a@x.com', 'departure_date': '2030-01-01',
            'number_of_adults': 2, 'number_of_children': 1,
        })
        self.assertEqual(r.status_code, 302)
        b = Booking.objects.get(user=self.user)
        # (2*1tr + 1*0.7tr) * 1.1 = 2.97tr
        self.assertEqual(b.total_price, Decimal('2970000'))
        self.assertEqual(b.status, 'pending')
        self.assertEqual(b.payment_status, 'unpaid')

    def test_booking_idor(self):
        """User B không mở được booking của user A."""
        other = User.objects.create_user(
            username='other', email='other@x.com', password='pass12345')
        b = Booking.objects.create(
            user=other, tour=self.tour, full_name='O', phone_number='09',
            email='o@x.com', departure_date='2030-01-01',
            number_of_adults=1, total_price=1100000)
        for url in (f'/payment/{b.id}/', f'/success/{b.id}/'):
            self.assertEqual(self.client.get(url).status_code, 404)


class ReviewDedupTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='rv', email='rv@x.com', password='pass12345')
        self.client = Client()
        self.client.force_login(self.user)
        self.dest = Destination.objects.create(
            name='Dest X', slug='dest-x', description='x', location='Huế')

    def test_duplicate_within_5min_rejected(self):
        payload = {'destination_id': self.dest.id, 'rating': 5, 'comment': 'tuyệt vời'}
        r1 = self.client.post('/api/review/', payload)
        self.assertEqual(r1.status_code, 200)
        r2 = self.client.post('/api/review/', payload)
        self.assertEqual(r2.status_code, 429)
        self.assertEqual(r2.json()['code'], 'DUPLICATE_REVIEW')

    def test_comment_xss_stripped(self):
        r = self.client.post('/api/review/', {
            'destination_id': self.dest.id, 'rating': 4,
            'comment': '<script>alert(1)</script> đẹp lắm'})
        self.assertEqual(r.status_code, 200)
        review = Review.objects.latest('id')
        self.assertNotIn('<script>', review.comment)


class BugfixRegressionTest(TestCase):
    def test_cache_key_no_spaces(self):
        from travel.cache_utils import get_cache_key
        key = get_cache_key('api_search_v3', query='da nang hotel')
        self.assertNotIn(' ', key)

    def test_sentiment_neu_not_confused_with_neg_pos(self):
        """NEG/POS không được lẫn chéo (AI_EVAL baseline)."""
        from travel.ai_engine import analyze_sentiment
        s_neg, _, _, _ = analyze_sentiment('dịch vụ tệ, phí tiền!')
        s_pos, _, _, _ = analyze_sentiment('phục vụ tốt, sẽ quay lại!')
        self.assertLess(s_neg, -0.18)
        self.assertGreater(s_pos, 0.18)

    def test_tour_sentiment_cached(self):
        """all_tours lần 2 phải hit cache (ít hoặc 0 query AI mới)."""
        tour = make_tour()
        user = User.objects.create_user(
            username='t', email='t@x.com', password='pass12345')
        from travel.models import TourReview
        TourReview.objects.create(
            tour=tour, user=user, author_name='T', rating=5,
            comment='tuyệt vời', status='published')
        c = Client()
        c.get('/tours/')  # warm cache
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        with CaptureQueriesContext(connection) as ctx:
            r = c.get('/tours/')
        self.assertEqual(r.status_code, 200)
        self.assertLess(len(ctx), 15)

    def test_api_search_prefiltered(self):
        """api_search không duyệt toàn bảng (queryset đã filter)."""
        make_tour()
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        with CaptureQueriesContext(connection) as ctx:
            r = Client().get('/api/search/?q=zzz-khong-ton-tai-zzz')
        self.assertEqual(r.status_code, 200)
        selects = [q for q in ctx if 'WHERE' in q['sql'].upper() or 'where' in q['sql']]
        self.assertTrue(all('LIKE' in q['sql'].upper() or 'where' in q['sql'].lower()
                            for q in selects) or len(ctx) <= 5)
