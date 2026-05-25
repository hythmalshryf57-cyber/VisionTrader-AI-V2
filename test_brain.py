import os
import sys
from pathlib import Path
from pprint import pprint

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'backend'))

from database import engine, Base
import models
from services.internal_brain import InternalBrain

def run_test():
    print("1. Creating missing tables for GlobalMemoryEvent...")
    Base.metadata.create_all(bind=engine)
    
    print("\n2. Initializing InternalBrain...")
    brain = InternalBrain()
    
    print("\n3. Testing log_event_experience...")
    brain.log_event_experience(
        component="test_component",
        event_type="deployment_threshold",
        event_key="test_key",
        event_value=0.75,
        metadata={"info": "testing"},
        success=True
    )
    brain.log_event_experience(
        component="test_component",
        event_type="deployment_threshold",
        event_key="test_key_2",
        event_value=0.6,
        success=False
    )
    brain.log_event_experience(
        component="test_component",
        event_type="deployment_threshold",
        event_key="test_key_3",
        event_value=0.8,
        success=True
    )
    print("Logs written successfully.")
    
    print("\n4. Testing get_dynamic_threshold...")
    dyn_threshold = brain.get_dynamic_threshold("test_component", "deployment_threshold", 0.65)
    print(f"Base Threshold: 0.65 -> Dynamic Threshold: {dyn_threshold}")
    
    print("\n5. Testing get_agent_dynamic_weight...")
    # Add fake agent logs
    for i in range(5):
        brain.log_agent_accuracy("TestAgent", was_correct=True, confidence=0.9)
    weight = brain.get_agent_dynamic_weight("TestAgent", default_weight=1.0)
    print(f"TestAgent default weight: 1.0 -> Dynamic weight: {weight}")
    
    print("\n6. Testing get_daily_learning_summary...")
    summary = brain.get_daily_learning_summary()
    pprint(summary)
    
if __name__ == "__main__":
    run_test()
