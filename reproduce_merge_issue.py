
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from services.grade_database import GradeDatabase
from services.grade_profiler import GradeProfiler
from kiwipiepy import Kiwi

def reproduce():
    print("Initializing components...")
    kiwi = Kiwi()
    db = GradeDatabase()
    
    class MockMorph:
        def get_analyzer(self): return kiwi
    
    db.initialize(MockMorph())
    profiler = GradeProfiler(db)
    
    # User Case: "책을 두고 자면" -> 자(VV) + 면(EC)
    # Expected: "자" (Sleep) and "면" (If) separate, OR at least not "자면" (Grammar pattern '...자면')
    sentence = "책을 두고 자면."
    
    print(f"\nAnalyzing sentence: '{sentence}'")
    tokens = kiwi.tokenize(sentence)
    # Debug tokens to ensure it is VV + EC
    print("Tokens:", tokens)
    
    for t in tokens:
        if t.form == '자':
            print(f"Token '자': Tag={t.tag}")
        if t.form == '면':
            print(f"Token '면': Tag={t.tag}")

    analysis, _, _ = profiler.profile(tokens, sentence)
    
    print("\n--- Analysis Result ---")
    found_jamyeon = False
    found_ja_separate = False
    
    for item in analysis:
        print(f"Form: {item['form']}, Tag: {item.get('tag_code')}, ID: {item.get('id')}, Desc: {item.get('desc')}")
        if item['form'] == '자면':
            found_jamyeon = True
        if item['form'] == '자' and '자다' in str(item.get('desc', '')):
            found_ja_separate = True
        if item['form'] == '자' and 'VV' in item.get('tag_code', ''):
             found_ja_separate = True

    if found_jamyeon:
        print("\nISSUE REPRODUCED: '자면' was found (merged result).")
    elif found_ja_separate:
        print("\nGOOD: '자' was found separately.")
    else:
        print("\nUNCERTAIN: Neither '자면' nor '자'(verb) clearly found.")

if __name__ == "__main__":
    reproduce()
