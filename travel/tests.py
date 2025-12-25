"""
Unit Tests for Travel App
Covers: Models, Views, AI Engine, APIs
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from decimal import Decimal
import json

from .models import (
    Category, Destination, DestinationImage, 
    TourPackage, Review, RecommendationScore, SearchHistory
)
from .ai_engine import (
    analyze_sentiment, search_destinations, 
    get_similar_destinations, SentimentAnalyzer
)

User = get_user_model()


# ==================== MODEL TESTS ====================

class CategoryModelTest(TestCase):
    """Tests for Category model"""
    
    def test_create_category(self):
        """Test creating a category"""
        category = Category.objects.create(
            name="Biển đảo",
            description="Du lịch biển và đảo"
        )
        self.assertEqual(category.name, "Biển đảo")
        self.assertEqual(category.slug, "bien-dao")
    
    def test_category_str(self):
        """Test category string representation"""
        category = Category.objects.create(name="Núi")
        self.assertEqual(str(category), "Núi")
    
    def test_auto_slug_generation(self):
        """Test automatic slug generation"""
        category = Category.objects.create(name="Văn hóa lịch sử")
        self.assertIsNotNone(category.slug)


class DestinationModelTest(TestCase):
    """Tests for Destination model"""
    
    def setUp(self):
        self.category = Category.objects.create(name="Biển")
        self.destination = Destination.objects.create(
            name="Vịnh Hạ Long",
            travel_type="Biển đảo",
            location="Quảng Ninh",
            description="Di sản thiên nhiên thế giới",
            latitude=20.9101,
            longitude=107.1839,
            avg_price=Decimal('2000000')
        )
    
    def test_create_destination(self):
        """Test creating a destination"""
        self.assertEqual(self.destination.name, "Vịnh Hạ Long")
        self.assertEqual(self.destination.location, "Quảng Ninh")
    
    def test_destination_str(self):
        """Test destination string representation"""
        self.assertEqual(str(self.destination), "Vịnh Hạ Long")
    
    def test_destination_with_category(self):
        """Test destination with category relationship"""
        self.destination.category = self.category
        self.destination.save()
        self.assertEqual(self.destination.category.name, "Biển")
    
    def test_destination_coordinates(self):
        """Test destination coordinates"""
        self.assertAlmostEqual(self.destination.latitude, 20.9101, places=4)
        self.assertAlmostEqual(self.destination.longitude, 107.1839, places=4)


class ReviewModelTest(TestCase):
    """Tests for Review model"""
    
    def setUp(self):
        self.destination = Destination.objects.create(
            name="Phố cổ Hội An",
            travel_type="Văn hóa",
            location="Quảng Nam"
        )
    
    def test_create_review(self):
        """Test creating a review"""
        review = Review.objects.create(
            destination=self.destination,
            author_name="Nguyễn Văn A",
            rating=5,
            comment="Rất đẹp và yên bình!"
        )
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.destination, self.destination)
    
    def test_review_str(self):
        """Test review string representation"""
        review = Review.objects.create(
            destination=self.destination,
            author_name="Test User",
            rating=4,
            comment="Tốt"
        )
        self.assertIn("Test User", str(review))
        self.assertIn("4 sao", str(review))
    
    def test_review_rating_choices(self):
        """Test review rating must be 1-5"""
        review = Review.objects.create(
            destination=self.destination,
            author_name="User",
            rating=3,
            comment="Bình thường"
        )
        self.assertIn(review.rating, [1, 2, 3, 4, 5])


class RecommendationScoreModelTest(TestCase):
    """Tests for RecommendationScore model"""
    
    def setUp(self):
        self.destination = Destination.objects.create(
            name="Đà Lạt",
            travel_type="Núi",
            location="Lâm Đồng"
        )
    
    def test_create_recommendation_score(self):
        """Test creating recommendation score"""
        score = RecommendationScore.objects.create(
            destination=self.destination,
            overall_score=85.5,
            review_score=80.0,
            sentiment_score=90.0,
            popularity_score=75.0,
            total_reviews=50,
            avg_rating=4.2
        )
        self.assertEqual(score.overall_score, 85.5)
        self.assertEqual(score.destination, self.destination)
    
    def test_one_to_one_relationship(self):
        """Test one-to-one relationship with destination"""
        RecommendationScore.objects.create(
            destination=self.destination,
            overall_score=80.0
        )
        # Should raise error if trying to create another
        with self.assertRaises(Exception):
            RecommendationScore.objects.create(
                destination=self.destination,
                overall_score=90.0
            )


# ==================== AI ENGINE TESTS ====================

class SentimentAnalyzerTest(TestCase):
    """Tests for Sentiment Analyzer"""
    
    def test_positive_sentiment(self):
        """Test positive sentiment detection"""
        text = "Địa điểm rất đẹp, phong cảnh tuyệt vời, nhân viên thân thiện"
        score, pos_keywords, neg_keywords = analyze_sentiment(text)
        
        self.assertGreater(score, 0)
        self.assertGreater(len(pos_keywords), 0)
    
    def test_negative_sentiment(self):
        """Test negative sentiment detection"""
        text = "Dịch vụ tệ, giá đắt, chờ lâu, thất vọng"
        score, pos_keywords, neg_keywords = analyze_sentiment(text)
        
        self.assertLess(score, 0)
        self.assertGreater(len(neg_keywords), 0)
    
    def test_neutral_sentiment(self):
        """Test neutral sentiment"""
        text = "Tôi đã đến đây hôm qua"
        score, pos_keywords, neg_keywords = analyze_sentiment(text)
        
        # Neutral should be close to 0
        self.assertGreaterEqual(score, -0.5)
        self.assertLessEqual(score, 0.5)
    
    def test_negation_handling(self):
        """Test negation word handling"""
        text = "Không đẹp, không tốt"
        score, pos_keywords, neg_keywords = analyze_sentiment(text)
        
        # "không đẹp" should be negative
        self.assertLessEqual(score, 0)
    
    def test_empty_text(self):
        """Test empty text handling"""
        score, pos_keywords, neg_keywords = analyze_sentiment("")
        
        self.assertEqual(score, 0.0)
        self.assertEqual(pos_keywords, [])
        self.assertEqual(neg_keywords, [])
    
    def test_intensifier_handling(self):
        """Test intensifier words"""
        text1 = "Đẹp"
        text2 = "Rất đẹp"
        text3 = "Cực kỳ đẹp"
        
        score1, _, _ = analyze_sentiment(text1)
        score2, _, _ = analyze_sentiment(text2)
        score3, _, _ = analyze_sentiment(text3)
        
        # Intensifiers should increase score
        self.assertGreaterEqual(score2, score1)


class SearchDestinationsTest(TestCase):
    """Tests for destination search functionality"""
    
    def setUp(self):
        # Create test destinations
        self.dest1 = Destination.objects.create(
            name="Vịnh Hạ Long",
            travel_type="Biển đảo",
            location="Quảng Ninh",
            description="Di sản thiên nhiên"
        )
        self.dest2 = Destination.objects.create(
            name="Phố cổ Hà Nội",
            travel_type="Văn hóa",
            location="Hà Nội",
            description="Phố cổ 36 phố phường"
        )
        self.dest3 = Destination.objects.create(
            name="Bãi biển Mỹ Khê",
            travel_type="Biển",
            location="Đà Nẵng",
            avg_price=Decimal('500000')
        )
        
        # Create recommendation scores
        RecommendationScore.objects.create(
            destination=self.dest1,
            overall_score=90.0
        )
        RecommendationScore.objects.create(
            destination=self.dest2,
            overall_score=85.0
        )
    
    def test_search_by_name(self):
        """Test search by destination name"""
        results = search_destinations("Hạ Long", {})
        
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].name, "Vịnh Hạ Long")
    
    def test_search_by_location(self):
        """Test search by location"""
        results = search_destinations("Hà Nội", {})
        
        names = [d.name for d in results]
        self.assertIn("Phố cổ Hà Nội", names)
    
    def test_search_with_type_filter(self):
        """Test search with travel type filter"""
        results = search_destinations("", {"travel_type": "Biển"})
        
        for dest in results:
            self.assertIn("Biển", dest.travel_type)
    
    def test_search_with_price_filter(self):
        """Test search with max price filter"""
        results = search_destinations("", {"max_price": 600000})
        
        for dest in results:
            if dest.avg_price:
                self.assertLessEqual(dest.avg_price, 600000)
    
    def test_empty_search(self):
        """Test empty search returns all destinations"""
        results = search_destinations("", {})
        
        self.assertEqual(len(results), 3)


class SimilarDestinationsTest(TestCase):
    """Tests for similar destinations recommendation"""
    
    def setUp(self):
        # Create destinations with same type
        self.beach1 = Destination.objects.create(
            name="Nha Trang",
            travel_type="Biển",
            location="Khánh Hòa",
            avg_price=Decimal('1000000')
        )
        self.beach2 = Destination.objects.create(
            name="Phú Quốc",
            travel_type="Biển",
            location="Kiên Giang",
            avg_price=Decimal('1200000')
        )
        self.mountain = Destination.objects.create(
            name="Sa Pa",
            travel_type="Núi",
            location="Lào Cai"
        )
        
        # Create recommendation scores
        for dest in [self.beach1, self.beach2, self.mountain]:
            RecommendationScore.objects.create(
                destination=dest,
                overall_score=80.0
            )
    
    def test_similar_by_type(self):
        """Test finding similar destinations by type"""
        similar = get_similar_destinations(self.beach1, limit=4)
        
        # Should include beach2 (same type)
        similar_names = [d.name for d in similar]
        self.assertIn("Phú Quốc", similar_names)
    
    def test_exclude_current_destination(self):
        """Test current destination is excluded"""
        similar = get_similar_destinations(self.beach1, limit=4)
        
        similar_ids = [d.id for d in similar]
        self.assertNotIn(self.beach1.id, similar_ids)


# ==================== VIEW TESTS ====================

class HomeViewTest(TestCase):
    """Tests for home page view"""
    
    def setUp(self):
        self.client = Client()
        self.destination = Destination.objects.create(
            name="Test Destination",
            travel_type="Test",
            location="Test Location"
        )
        RecommendationScore.objects.create(
            destination=self.destination,
            overall_score=80.0
        )
    
    def test_home_page_status(self):
        """Test home page returns 200"""
        response = self.client.get(reverse('travel:home'))
        self.assertEqual(response.status_code, 200)
    
    def test_home_page_template(self):
        """Test home page uses correct template"""
        response = self.client.get(reverse('travel:home'))
        self.assertTemplateUsed(response, 'travel/index.html')
    
    def test_home_page_context(self):
        """Test home page context contains required data"""
        response = self.client.get(reverse('travel:home'))
        
        self.assertIn('results', response.context)
        self.assertIn('top_destinations', response.context)


class SearchViewTest(TestCase):
    """Tests for search view"""
    
    def setUp(self):
        self.client = Client()
        self.destination = Destination.objects.create(
            name="Đà Nẵng",
            travel_type="Biển",
            location="Đà Nẵng"
        )
    
    def test_search_page_status(self):
        """Test search page returns 200"""
        response = self.client.get(reverse('travel:search'))
        self.assertEqual(response.status_code, 200)
    
    def test_search_with_query(self):
        """Test search with query parameter"""
        response = self.client.get(reverse('travel:search'), {'q': 'Đà Nẵng'})
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('destinations', response.context)
    
    def test_search_creates_history(self):
        """Test search creates search history"""
        self.client.get(reverse('travel:search'), {'q': 'test query'})
        
        history = SearchHistory.objects.filter(query='test query')
        self.assertTrue(history.exists())


class DestinationDetailViewTest(TestCase):
    """Tests for destination detail view"""
    
    def setUp(self):
        self.client = Client()
        self.destination = Destination.objects.create(
            name="Hội An",
            travel_type="Văn hóa",
            location="Quảng Nam",
            latitude=15.8801,
            longitude=108.3380
        )
        RecommendationScore.objects.create(
            destination=self.destination,
            overall_score=85.0,
            avg_rating=4.5,
            total_reviews=100
        )
    
    def test_detail_page_status(self):
        """Test detail page returns 200"""
        response = self.client.get(
            reverse('travel:destination_detail', args=[self.destination.id])
        )
        self.assertEqual(response.status_code, 200)
    
    def test_detail_page_context(self):
        """Test detail page context"""
        response = self.client.get(
            reverse('travel:destination_detail', args=[self.destination.id])
        )
        
        self.assertEqual(response.context['destination'], self.destination)
        self.assertIn('reviews', response.context)
        self.assertIn('recommendation', response.context)
    
    def test_detail_page_404(self):
        """Test detail page returns 404 for invalid id"""
        response = self.client.get(
            reverse('travel:destination_detail', args=[99999])
        )
        self.assertEqual(response.status_code, 404)
    
    def test_viewed_history_session(self):
        """Test destination is added to viewed history"""
        self.client.get(
            reverse('travel:destination_detail', args=[self.destination.id])
        )
        
        session = self.client.session
        self.assertIn(self.destination.id, session.get('viewed_destinations', []))


# ==================== API TESTS ====================

class APISearchTest(TestCase):
    """Tests for search API endpoint"""
    
    def setUp(self):
        self.client = Client()
        self.destination = Destination.objects.create(
            name="Sapa",
            travel_type="Núi",
            location="Lào Cai"
        )
        RecommendationScore.objects.create(
            destination=self.destination,
            overall_score=80.0
        )
    
    def test_api_search_returns_json(self):
        """Test API returns JSON response"""
        response = self.client.get('/api/search/', {'q': 'Sapa'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_api_search_results(self):
        """Test API search returns results"""
        response = self.client.get('/api/search/', {'q': 'Sapa'})
        data = json.loads(response.content)
        
        self.assertIn('results', data)
        self.assertGreater(len(data['results']), 0)
    
    def test_api_search_empty_query(self):
        """Test API with empty query"""
        response = self.client.get('/api/search/', {'q': ''})
        data = json.loads(response.content)
        
        self.assertEqual(data['results'], [])


class APISubmitReviewTest(TestCase):
    """Tests for submit review API endpoint"""
    
    def setUp(self):
        self.client = Client()
        self.destination = Destination.objects.create(
            name="Test Place",
            travel_type="Test",
            location="Test"
        )
    
    def test_submit_review_success(self):
        """Test successful review submission"""
        response = self.client.post('/api/submit-review/', {
            'destination_id': self.destination.id,
            'author_name': 'Test User',
            'rating': 5,
            'comment': 'Rất tuyệt vời!'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
    
    def test_submit_review_creates_record(self):
        """Test review is created in database"""
        self.client.post('/api/submit-review/', {
            'destination_id': self.destination.id,
            'author_name': 'Reviewer',
            'rating': 4,
            'comment': 'Tốt lắm'
        })
        
        review = Review.objects.filter(
            destination=self.destination,
            author_name='Reviewer'
        )
        self.assertTrue(review.exists())
    
    def test_submit_review_invalid_rating(self):
        """Test review with invalid rating"""
        response = self.client.post('/api/submit-review/', {
            'destination_id': self.destination.id,
            'author_name': 'User',
            'rating': 10,  # Invalid
            'comment': 'Test'
        })
        
        self.assertEqual(response.status_code, 400)
    
    def test_submit_review_missing_data(self):
        """Test review with missing required data"""
        response = self.client.post('/api/submit-review/', {
            'destination_id': self.destination.id,
            # Missing rating
        })
        
        self.assertEqual(response.status_code, 400)
    
    def test_submit_review_updates_scores(self):
        """Test review submission updates recommendation scores"""
        # Create initial score
        RecommendationScore.objects.create(
            destination=self.destination,
            overall_score=50.0,
            total_reviews=0
        )
        
        self.client.post('/api/submit-review/', {
            'destination_id': self.destination.id,
            'author_name': 'User',
            'rating': 5,
            'comment': 'Excellent!'
        })
        
        # Refresh and check
        score = RecommendationScore.objects.get(destination=self.destination)
        self.assertEqual(score.total_reviews, 1)


class APINearbyPlacesTest(TestCase):
    """Tests for nearby places API"""
    
    def setUp(self):
        self.client = Client()
    
    def test_nearby_places_missing_coords(self):
        """Test API returns error without coordinates"""
        response = self.client.get('/api/nearby/')
        
        self.assertEqual(response.status_code, 400)
    
    def test_nearby_places_invalid_coords(self):
        """Test API with invalid coordinates"""
        response = self.client.get('/api/nearby/', {
            'lat': 'invalid',
            'lon': 'invalid'
        })
        
        self.assertEqual(response.status_code, 400)


# ==================== INTEGRATION TESTS ====================

class UserJourneyTest(TestCase):
    """Integration tests for typical user journeys"""
    
    def setUp(self):
        self.client = Client()
        
        # Create test data
        self.destination = Destination.objects.create(
            name="Đà Lạt",
            travel_type="Núi",
            location="Lâm Đồng",
            description="Thành phố ngàn hoa",
            latitude=11.9404,
            longitude=108.4583
        )
        RecommendationScore.objects.create(
            destination=self.destination,
            overall_score=88.0,
            avg_rating=4.4,
            total_reviews=200
        )
    
    def test_search_and_view_detail(self):
        """Test user searches and views destination detail"""
        # 1. User visits home
        response = self.client.get(reverse('travel:home'))
        self.assertEqual(response.status_code, 200)
        
        # 2. User searches
        response = self.client.get(reverse('travel:search'), {'q': 'Đà Lạt'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.destination, response.context['destinations'])
        
        # 3. User views detail
        response = self.client.get(
            reverse('travel:destination_detail', args=[self.destination.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['destination'].name, "Đà Lạt")
    
    def test_submit_review_flow(self):
        """Test user submits a review"""
        # 1. View destination
        self.client.get(
            reverse('travel:destination_detail', args=[self.destination.id])
        )
        
        # 2. Submit review
        response = self.client.post('/api/submit-review/', {
            'destination_id': self.destination.id,
            'author_name': 'Du khách',
            'rating': 5,
            'comment': 'Đà Lạt rất đẹp, thời tiết mát mẻ, đồ ăn ngon!'
        })
        
        self.assertEqual(response.status_code, 200)
        
        # 3. Verify review exists
        review = Review.objects.get(
            destination=self.destination,
            author_name='Du khách'
        )
        self.assertEqual(review.rating, 5)
        # Sentiment should be positive
        self.assertGreater(review.sentiment_score, 0)
