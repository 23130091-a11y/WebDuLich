"""
Unified Diagnostics Command
Gộp tất cả testing và diagnostic commands thành 1 command duy nhất

Usage:
    python manage.py diagnostics --all
    python manage.py diagnostics --ai
    python manage.py diagnostics --performance
    python manage.py diagnostics --cache
    python manage.py diagnostics --system
"""

import time
from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.test.utils import override_settings
from django.core.cache import cache
from django.conf import settings

from travel.models import Destination, Review, RecommendationScore, SearchHistory
from travel.ai_engine import get_sentiment_analyzer, search_destinations, calculate_destination_score


class Command(BaseCommand):
    help = 'Run comprehensive diagnostics for WebDuLich system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all diagnostics'
        )
        parser.add_argument(
            '--ai',
            action='store_true',
            help='Test AI sentiment analysis'
        )
        parser.add_argument(
            '--performance',
            action='store_true',
            help='Test query performance'
        )
        parser.add_argument(
            '--cache',
            action='store_true',
            help='Test cache system'
        )
        parser.add_argument(
            '--system',
            action='store_true',
            help='Test overall system health'
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Auto-fix issues found'
        )

    def handle(self, *args, **options):
        self.print_header("WEBDULICH SYSTEM DIAGNOSTICS")
        
        run_all = options['all']
        fix_mode = options['fix']
        
        if run_all or options['system']:
            self.test_system_health(fix_mode)
        
        if run_all or options['ai']:
            self.test_ai_sentiment()
        
        if run_all or options['performance']:
            self.test_query_performance()
        
        if run_all or options['cache']:
            self.test_cache_system()
        
        self.print_header("DIAGNOSTICS COMPLETED")

    def print_header(self, title):
        self.stdout.write("\n" + "="*60)
        self.stdout.write(f"  {title}")
        self.stdout.write("="*60)

    def print_success(self, msg):
        self.stdout.write(self.style.SUCCESS(f"  ✅ {msg}"))

    def print_warning(self, msg):
        self.stdout.write(self.style.WARNING(f"  ⚠️ {msg}"))

    def print_error(self, msg):
        self.stdout.write(self.style.ERROR(f"  ❌ {msg}"))

    def print_info(self, msg):
        self.stdout.write(f"  ℹ️ {msg}")

    def test_system_health(self, fix_mode=False):
        """Test overall system health"""
        self.print_header("1. SYSTEM HEALTH CHECK")
        
        # Database stats
        total_destinations = Destination.objects.count()
        total_reviews = Review.objects.count()
        total_scores = RecommendationScore.objects.count()
        
        self.print_info(f"Destinations: {total_destinations}")
        self.print_info(f"Reviews: {total_reviews}")
        self.print_info(f"Recommendation Scores: {total_scores}")
        
        # Coverage check
        dest_with_reviews = Destination.objects.filter(reviews__isnull=False).distinct().count()
        coverage = (dest_with_reviews / total_destinations * 100) if total_destinations > 0 else 0
        
        self.print_info(f"Review Coverage: {dest_with_reviews}/{total_destinations} ({coverage:.1f}%)")
        
        if coverage >= 80:
            self.print_success("Excellent review coverage!")
        elif coverage >= 50:
            self.print_warning("Good review coverage")
        else:
            self.print_error(f"Low review coverage - only {coverage:.1f}%")
            if fix_mode:
                self.print_info("Auto-fix: Generating sample reviews...")
                self._generate_sample_reviews()
        
        # Check recommendation scores
        missing_scores = Destination.objects.filter(recommendation__isnull=True).count()
        if missing_scores > 0:
            self.print_warning(f"{missing_scores} destinations missing recommendation scores")
            if fix_mode:
                self.print_info("Auto-fix: Calculating missing scores...")
                self._calculate_missing_scores()
        else:
            self.print_success("All destinations have recommendation scores")

    def test_ai_sentiment(self):
        """Test AI sentiment analysis"""
        self.print_header("2. AI SENTIMENT ANALYSIS TEST")
        
        test_cases = [
            ("Cảnh đẹp, dịch vụ tốt, rất hài lòng!", "positive"),
            ("Tệ, bẩn, đắt, không nên đi", "negative"),
            ("Bình thường, không có gì đặc biệt", "neutral"),
            ("Không đẹp lắm nhưng cũng ok", "neutral"),
            ("Rất tuyệt vời! Recommend mọi người nên đi", "positive")
        ]
        
        analyzer = get_sentiment_analyzer()
        correct_predictions = 0
        
        for text, expected in test_cases:
            start_time = time.time()
            score, pos_keywords, neg_keywords = analyzer.analyze(text)
            elapsed = (time.time() - start_time) * 1000
            
            # Determine label from score
            if score > 0.3:
                label = "positive"
            elif score < -0.3:
                label = "negative"
            else:
                label = "neutral"
            
            self.print_info(f"Text: '{text[:40]}...'")
            self.print_info(f"  Score: {score:.3f}, Label: {label}, Time: {elapsed:.1f}ms")
            self.print_info(f"  Positive: {pos_keywords[:3]}")
            self.print_info(f"  Negative: {neg_keywords[:3]}")
            
            if label == expected:
                self.print_success("  Correct prediction!")
                correct_predictions += 1
            else:
                self.print_error(f"  Wrong! Expected {expected}, got {label}")
        
        accuracy = (correct_predictions / len(test_cases)) * 100
        self.print_info(f"Overall Accuracy: {accuracy:.1f}%")
        
        if accuracy >= 80:
            self.print_success("AI sentiment analysis working well!")
        elif accuracy >= 60:
            self.print_warning("AI sentiment analysis needs improvement")
        else:
            self.print_error("AI sentiment analysis not working properly")

    def test_query_performance(self):
        """Test database query performance"""
        self.print_header("3. QUERY PERFORMANCE TEST")
        
        with override_settings(DEBUG=True):
            # Test 1: Homepage query
            reset_queries()
            start_time = time.time()
            
            destinations = list(
                Destination.objects.select_related('recommendation')
                .prefetch_related('reviews')
                .order_by('-recommendation__overall_score')[:6]
            )
            
            elapsed = (time.time() - start_time) * 1000
            queries = len(connection.queries)
            
            self.print_info(f"Homepage Query: {queries} queries, {elapsed:.2f}ms")
            if queries <= 3:
                self.print_success("Homepage query optimized!")
            else:
                self.print_warning(f"Homepage query uses {queries} queries (should be ≤3)")
            
            # Test 2: Search query
            reset_queries()
            start_time = time.time()
            
            results = search_destinations("Hà Nội", {})[:10]
            
            elapsed = (time.time() - start_time) * 1000
            queries = len(connection.queries)
            
            self.print_info(f"Search Query: {queries} queries, {elapsed:.2f}ms")
            if queries <= 5:
                self.print_success("Search query optimized!")
            else:
                self.print_warning(f"Search query uses {queries} queries (should be ≤5)")
            
            # Test 3: Recommendation calculation
            if destinations:
                reset_queries()
                start_time = time.time()
                
                scores = calculate_destination_score(destinations[0])
                
                elapsed = (time.time() - start_time) * 1000
                queries = len(connection.queries)
                
                self.print_info(f"Score Calculation: {queries} queries, {elapsed:.2f}ms")
                self.print_info(f"  Overall Score: {scores['overall_score']}")

    def test_cache_system(self):
        """Test caching system"""
        self.print_header("4. CACHE SYSTEM TEST")
        
        # Test basic cache functionality
        test_key = 'diagnostics_test'
        test_value = 'test_value_123'
        
        # Clear and set
        cache.delete(test_key)
        cache.set(test_key, test_value, timeout=60)
        
        # Test retrieval
        cached_value = cache.get(test_key)
        if cached_value == test_value:
            self.print_success("Basic cache functionality working!")
        else:
            self.print_error("Cache not working properly!")
            return
        
        # Test cache performance
        call_count = [0]
        
        def expensive_function():
            call_count[0] += 1
            time.sleep(0.01)  # Simulate expensive operation
            return "expensive_result"
        
        # First call (cache miss)
        start_time = time.time()
        cache.get_or_set('expensive_key', expensive_function, timeout=60)
        miss_time = (time.time() - start_time) * 1000
        
        # Second call (cache hit)
        start_time = time.time()
        cache.get_or_set('expensive_key', expensive_function, timeout=60)
        hit_time = (time.time() - start_time) * 1000
        
        self.print_info(f"Cache Miss: {miss_time:.2f}ms, Cache Hit: {hit_time:.2f}ms")
        self.print_info(f"Function called {call_count[0]} times (should be 1)")
        
        if call_count[0] == 1 and hit_time < miss_time:
            self.print_success("Cache performance optimization working!")
        else:
            self.print_warning("Cache performance may need attention")
        
        # Cache statistics
        try:
            # Get cache stats if available
            cache_stats = cache._cache.get_stats()
            if cache_stats:
                for stat in cache_stats:
                    hits = stat[1].get('get_hits', 0)
                    misses = stat[1].get('get_misses', 0)
                    total = hits + misses
                    hit_rate = (hits / total * 100) if total > 0 else 0
                    self.print_info(f"Cache Hit Rate: {hit_rate:.1f}% ({hits}/{total})")
        except:
            self.print_info("Cache statistics not available")

    def _generate_sample_reviews(self):
        """Generate sample reviews for destinations without reviews"""
        destinations_without_reviews = Destination.objects.filter(reviews__isnull=True)[:10]
        
        sample_reviews = [
            ("Địa điểm rất đẹp, đáng để ghé thăm!", 4),
            ("Cảnh quan tuyệt vời, dịch vụ tốt", 5),
            ("Bình thường, không có gì đặc biệt", 3),
            ("Khá ok, sẽ quay lại lần sau", 4),
            ("Tạm được, giá hơi cao", 3)
        ]
        
        for dest in destinations_without_reviews:
            for i, (comment, rating) in enumerate(sample_reviews[:2]):  # 2 reviews per destination
                Review.objects.create(
                    destination=dest,
                    author_name=f"User_{dest.id}_{i}",
                    rating=rating,
                    comment=comment,
                    sentiment_score=0.5 if rating >= 4 else (-0.2 if rating <= 2 else 0.0)
                )
        
        self.print_success(f"Generated sample reviews for {len(destinations_without_reviews)} destinations")

    def _calculate_missing_scores(self):
        """Calculate recommendation scores for destinations that don't have them"""
        destinations_without_scores = Destination.objects.filter(recommendation__isnull=True)
        
        for dest in destinations_without_scores:
            scores = calculate_destination_score(dest)
            RecommendationScore.objects.update_or_create(
                destination=dest,
                defaults=scores
            )
        
        self.print_success(f"Calculated scores for {len(destinations_without_scores)} destinations")