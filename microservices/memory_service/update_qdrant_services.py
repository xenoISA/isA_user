#!/usr/bin/env python3
"""
Script to batch update remaining memory services with Qdrant integration
"""

services_to_update = [
    {
        'file': 'procedural_service.py',
        'collection': 'procedural_memories',
        'class_name': 'ProceduralMemoryService',
        'payload_fields': ['user_id', 'skill_name', 'step_count']
    },
    {
        'file': 'semantic_service.py',
        'collection': 'semantic_memories',
        'class_name': 'SemanticMemoryService',
        'payload_fields': ['user_id', 'concept', 'category']
    },
    {
        'file': 'session_service.py',
        'collection': 'session_memories',
        'class_name': 'SessionMemoryService',
        'payload_fields': ['user_id', 'session_id']
    },
    {
        'file': 'working_service.py',
        'collection': 'working_memories',
        'class_name': 'WorkingMemoryService',
        'payload_fields': ['user_id', 'priority']
    }
]

import_to_add = "from isa_common.qdrant_client import QdrantClient\n"

init_code_template = """
        # Initialize Qdrant client for vector storage
        self.qdrant = QdrantClient(
            host=os.getenv('QDRANT_HOST', 'isa-qdrant-grpc'),
            port=int(os.getenv('QDRANT_PORT', 50062)),
            user_id='memory_service'
        )
        self._ensure_collection()
"""

ensure_collection_template = """
    def _ensure_collection(self):
        \"\"\"Ensure Qdrant collection exists for {memory_type} memories\"\"\"
        collection_name = '{collection_name}'
        try:
            if not self.qdrant.collection_exists(collection_name):
                self.qdrant.create_collection(collection_name, vector_size=1536, distance='Cosine')
                logger.info(f"Created Qdrant collection: {{collection_name}}")
                self.qdrant.create_field_index(collection_name, 'user_id', 'keyword')
                logger.info(f"Created user_id index on {{collection_name}}")
        except Exception as e:
            logger.warning(f"Error ensuring Qdrant collection: {{e}}")
"""

print("Batch update instructions:")
print("=" * 80)
for service in services_to_update:
    print(f"\nService: {service['file']}")
    print(f"  Collection: {service['collection']}")
    print(f"  Payload fields: {service['payload_fields']}")
print("\n" + "=" * 80)
print("\nManual steps needed for each service:")
print("1. Add import: from isa_common.qdrant_client import QdrantClient")
print("2. Add Qdrant client init in __init__")
print("3. Add _ensure_collection method")
print("4. Remove 'embedding' from memory_data dict")
print("5. Add Qdrant upsert after PostgreSQL insert")
