"""
Management command để test query performance và phát hiện N+1 queries
"""
from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.test.utils import override_settings
import time

from travel.models import Destination, Review, RecommendationScore
from travel.ai_module import search_destinations


class Command(BaseCommand):
    help = 'Test query performance và phát hiện N+1 queries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show all SQL queries',
        )

    def handle(self, *args, **options):
        verbose = options['verbose']
        
        self.stdout.write(self.style.SUCCESS('=== QUERY PERFORMANCE TEST ===\n'))
        
        # Test 1: Load homepage destinations
        self.test_homepage_query(verbose)
        
        # Test 2: Search destinations
        self.test_search_query(verbose)
        
        # Test 3: Destination detail
        self.test_detail_query(verbose)
        
        # Test 4: Calculate scores
        self.test_calculate_scores(verbose)
        
        self.stdout.write(self.style.SUCCESS('\n=== TEST COMPLETED ==='))

    def test_homepage_query(self, verbose):
        """Test query cho homepage"""
        self.stdout.write('\n1. Testing Homepage Query...')
        
        reset_queries()
        start_time = time.time()
        
        # Simulate homepage query
        destinations = list(
            Destination.objects.select_related('recommendation')
            .prefetch_related('reviews')
            .order_by('-recommendation__overall_score')[:6]
        )
        
        # Access related data to trigger queries
        for dest in destinations:
            _ = dest.recommendation.overall_score if hasattr(dest, 'recommendation') else 0
            _ = dest.reviews.count()
        
        end_time = time.time()
        query_count = len(connection.queries)
        
        self.stdout.write(f'   Destinations loaded: {len(destinations)}')
        self.stdout.write(f'   Queries executed: {query_count}')
        self.stdout.write(f'   Time taken: {(end_time - start_time)*1000:.2f}ms')
        
        if query_count <= 3:
            self.stdout.write(self.style.SUCCESS('   [OK] OPTIMIZED (<=3 queries)'))
        elif query_count <= 10:
            self.stdout.write(self.style.WARNING(f'   [WARN] ACCEPTABLE ({query_count} queries)'))
        else:
            self.stdout.write(self.style.ERROR(f'   [ERROR] N+1 PROBLEM ({query_count} queries)'))
        
        if verbose:
            self.print_queries()

    def test_search_query(self, verbose):
        """Test query cho search"""
        self.stdout.write('\n2. Testing Search Query...')
        
        reset_queries()
        start_time = time.time()
        
        # Simulate search
        destinations = list(search_destinations('Hà Nội', {}))[:10]
        
        # Access related data
        for dest in destinations:
            _ = dest.recommendation.overall_score if hasattr(dest, 'recommendation') else 0
        
        end_time = time.time()
        query_count = len(connection.queries)
        
        self.stdout.write(f'   Results found: {len(destinations)}')
        self.stdout.write(f'   Queries executed: {query_count}')
        self.stdout.write(f'   Time taken: {(end_time - start_time)*1000:.2f}ms')
        
        if query_count <= 5:
            self.stdout.write(self.style.SUCCESS('   [OK] OPTIMIZED (<=5 queries)'))
        elif query_count <= 15:
            self.stdout.write(self.style.WARNING(f'   [WARN] ACCEPTABLE ({query_count} queries)'))
        else:
            self.stdout.write(self.style.ERROR(f'   [ERROR] N+1 PROBLEM ({query_count} queries)'))
        
        if verbose:
            self.print_queries()

    def test_detail_query(self, verbose):
        """Test query cho destination detail"""
        self.stdout.write('\n3. Testing Destination Detail Query...')
        
        # Get first destination
        dest = Destination.objects.first()
        if not dest:
            self.stdout.write(self.style.WARNING('   No destinations found'))
            return
        
        reset_queries()
        start_time = time.time()
        
        # Simulate detail view
        destination = Destination.objects.select_related('recommendation').get(id=dest.id)
        reviews = list(Review.objects.filter(destination=destination).order_by('-created_at')[:50])
        
        # Access data
        _ = destination.recommendation.overall_score if hasattr(destination, 'recommendation') else 0
        for review in reviews:
            _ = review.rating
            _ = review.comment
        
        end_time = time.time()
        query_count = len(connection.queries)
        
        self.stdout.write(f'   Reviews loaded: {len(reviews)}')
        self.stdout.write(f'   Queries executed: {query_count}')
        self.stdout.write(f'   Time taken: {(end_time - start_time)*1000:.2f}ms')
        
        if query_count <= 3:
            self.stdout.write(self.style.SUCCESS('   [OK] OPTIMIZED (<=3 queries)'))
        elif query_count <= 5:
            self.stdout.write(self.style.WARNING(f'   [WARN] ACCEPTABLE ({query_count} queries)'))
        else:
            self.stdout.write(self.style.ERROR(f'   [ERROR] N+1 PROBLEM ({query_count} queries)'))
        
        if verbose:
            self.print_queries()

    def test_calculate_scores(self, verbose):
        """Test query cho calculate scores"""
        self.stdout.write('\n4. Testing Calculate Scores Query...')
        
        # Get first 5 destinations
        destinations = list(Destination.objects.prefetch_related('reviews')[:5])
        
        if not destinations:
            self.stdout.write(self.style.WARNING('   No destinations found'))
            return
        
        reset_queries()
        start_time = time.time()
        
        # Calculate scores
        from travel.ai_module import calculate_destination_score
        for dest in destinations:
            calculate_destination_score(dest)
        
        end_time = time.time()
        query_count = len(connection.queries)
        
        self.stdout.write(f'   Destinations processed: {len(destinations)}')
        self.stdout.write(f'   Queries executed: {query_count}')
        self.stdout.write(f'   Time taken: {(end_time - start_time)*1000:.2f}ms')
        
        # Expected: ~4 queries per destination (check existing + update/create score)
        # This is acceptable because we need to save each score individually
        expected_max = len(destinations) * 5
        
        if query_count <= expected_max:
            self.stdout.write(self.style.SUCCESS(f'   [OK] ACCEPTABLE (<={expected_max} queries for {len(destinations)} destinations)'))
        else:
            self.stdout.write(self.style.ERROR(f'   [ERROR] TOO MANY QUERIES ({query_count} queries, expected <={expected_max})'))
        
        if verbose:
            self.print_queries()

    def print_queries(self):
        """Print all SQL queries"""
        self.stdout.write('\n   SQL Queries:')
        for i, query in enumerate(connection.queries, 1):
            sql = query['sql']
            time_ms = float(query['time']) * 1000
            self.stdout.write(f'   [{i}] ({time_ms:.2f}ms) {sql[:100]}...')
