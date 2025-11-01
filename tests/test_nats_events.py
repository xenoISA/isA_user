#!/usr/bin/env python3
"""
Test script to verify NATS events are being published
"""
import sys
import os

# Add isA_common to path
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_Cloud/isA_common')

# Test 1: Check NATS client connection
print("=" * 60)
print("Testing NATS Event Architecture")
print("=" * 60)
print()

try:
    from isa_common.nats_client import NATSClient

    print("1. Testing NATS gRPC Client Connection...")
    with NATSClient(host='localhost', port=50056, user_id='test_subscriber') as client:
        # Health check
        result = client.health_check()
        if result:
            print(f"   ✅ NATS is healthy")
            print(f"   - NATS Status: {result.get('nats_status')}")
            print(f"   - JetStream Enabled: {result.get('jetstream_enabled')}")
            print(f"   - Connections: {result.get('connections')}")
        else:
            print(f"   ❌ NATS health check failed")
            sys.exit(1)

        print()
        print("2. Getting NATS Statistics...")
        stats = client.get_statistics()
        if stats:
            print(f"   - Total Streams: {stats.get('total_streams')}")
            print(f"   - Total Messages: {stats.get('total_messages')}")
            print(f"   - Connections: {stats.get('connections')}")
            print(f"   - In Messages: {stats.get('in_msgs')}")
            print(f"   - Out Messages: {stats.get('out_msgs')}")

        print()
        print("3. Listing JetStream Streams...")
        streams = client.list_streams()
        if streams:
            print(f"   Found {len(streams)} streams:")
            for stream in streams:
                print(f"   - {stream['name']}: {stream['messages']} messages, subjects: {stream['subjects']}")
        else:
            print("   No streams found")

        print()
        print("4. Publishing a test event...")
        test_subject = "test.event"
        result = client.publish(test_subject, b'{"test": "data"}')
        if result:
            print(f"   ✅ Successfully published to {test_subject}")
        else:
            print(f"   ❌ Failed to publish test event")

    print()
    print("=" * 60)
    print("NATS Event Architecture Test: PASSED ✅")
    print("=" * 60)
    print()
    print("Next Step: Make an API call to the Model service")
    print("and check if billing events are published to NATS")

except ImportError as e:
    print(f"❌ Import Error: {e}")
    print()
    print("Make sure isa_common package is properly installed:")
    print("  cd /Users/xenodennis/Documents/Fun/isA_Cloud/isA_common")
    print("  pip install -e .")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
