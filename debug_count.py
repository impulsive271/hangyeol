import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from services.analysis_service import AnalysisService

def test_count():
    service = AnalysisService()
    
    # Initialize DB (Singleton) if not ready
    if not service.data.is_ready:
        print("Initializing Database...")
        service.data.initialize(service.morph)
    
    if not service.data.is_ready:
        print(f"Database init failed: {service.data.error_msg}")
        return

    text = "사과가 신선하지 않다니 사과할 수밖에 없을 것 같아"
    print(f"Input: {text}")
    
    stats, data, log = service.get_sentence_grade(text)
    
    print(f"Stats: {stats}")
    print(f"Total Count (stats['전체']): {stats.get('전체')}")
    print("-" * 20)
    print("Detailed Items:")
    for i, item in enumerate(data):
        print(f"{i+1}. {item['form']} ({item['tag_name']}) - {item['level']}")

if __name__ == "__main__":
    test_count()
