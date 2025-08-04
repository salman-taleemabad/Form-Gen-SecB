#!/usr/bin/env python3
"""
Test script for the new single prompt approach (matching teammate's method)
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"

# Sample lesson plan for testing
SAMPLE_LESSON_PLAN = """
Understanding Fractions

Student Learning Objective
* Identify different types of fractions: proper, improper, and mixed numbers.
* Convert between improper fractions and mixed numbers.

Summary
Today's lesson focuses on understanding fractions through visual representations and hands-on activities.
Students will work with fraction circles and number lines to develop conceptual understanding.
Collaborative activities will reinforce learning through peer discussion and problem-solving.

Resources
Fraction circles, number lines, textbook pages 45-48, whiteboard.

Opening
Say: Good morning! Today we'll explore fractions that are all around us.
Ask: Can anyone give me an example of when we use fractions in daily life?
Expected answers: Cooking, sharing pizza, measuring ingredients.
Instruction: Show fraction circles and ask students to identify what they see.

Explanation
Say: A fraction represents parts of a whole. Let's look at different types.
Instruction: Using fraction circles, demonstrate proper fractions (1/2, 2/3, 3/4).
Say: These are proper fractions because the numerator is smaller than the denominator.
Instruction: Show improper fractions (5/3, 7/4) using multiple circles.
Ask: What do you notice about these fractions?
Expected answer: The numerator is larger than the denominator.

Guided Practice
Instruction: Work in pairs to sort fraction cards into proper and improper fractions.
Say: Discuss with your partner why you placed each fraction in its category.
Instruction: Walk around and provide guidance, asking probing questions.
Ask: How can you tell if 8/5 is proper or improper?

Independent Practice
Instruction: Complete worksheet on page 47, identifying and converting fractions.
Say: Remember to show your work and use the fraction circles if needed.
Instruction: Circulate and provide individual support as needed.

Conclusion
Ask: What's the difference between proper and improper fractions?
Say: Great work today! Remember that fractions help us describe parts of wholes.
Instruction: Assign homework problems 1-10 on page 48.
"""

def test_new_approach():
    """Test the new single prompt approach"""
    print("🚀 Testing New Single Prompt Approach")
    print("=" * 60)
    
    try:
        payload = {"lesson_plan": SAMPLE_LESSON_PLAN}
        print("📤 Sending request to API...")
        
        response = requests.post(
            f"{BASE_URL}/rubric-from-string",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Rubric generated successfully!")
            print(f"📊 Questions generated: {len(data.get('questions', []))}")
            print("\n" + "="*80)
            print("📋 FULL RUBRIC OUTPUT:")
            print("="*80)
            
            # Pretty print the entire rubric
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            print("\n" + "="*80)
            print("📝 RUBRIC SUMMARY:")
            print("="*80)
            
            # Print a summary of each question
            questions = data.get('questions', [])
            for i, question in enumerate(questions, 1):
                print(f"\n🔹 Question {i}:")
                print(f"   Prompt: {question.get('prompt', 'N/A')}")
                print(f"   Order: {question.get('order', 'N/A')}")
                print(f"   Options: {len(question.get('options', []))}")
                
                # Show options
                for j, option in enumerate(question.get('options', []), 1):
                    print(f"      Option {j} ({option.get('value', 'N/A')}): {option.get('label', 'N/A')[:60]}...")
            
            print(f"\n✅ Test completed successfully! Generated {len(questions)} questions.")
            
        else:
            print(f"❌ API request failed with status code: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

def test_health_check():
    """Test the health check endpoint"""
    print("\n🏥 Testing Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data.get('message', 'Unknown')}")
            print(f"Version: {data.get('version', 'Unknown')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")

def main():
    """Main test function"""
    print("🧪 Testing New Single Prompt Approach (Matching Teammate's Method)")
    print("=" * 80)
    
    # Test health check first
    test_health_check()
    
    # Test the new approach
    test_new_approach()
    
    print("\n" + "=" * 80)
    print("🏁 Testing completed!")

if __name__ == "__main__":
    main() 