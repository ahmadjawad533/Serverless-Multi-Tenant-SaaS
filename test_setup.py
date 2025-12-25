#!/usr/bin/env python3
"""
Quick setup validation for SaaS Backend
Tests basic imports and structure
"""

import sys
import os

def test_project_structure():
    """Test that all required files exist"""
    
    required_files = [
        'infrastructure/app.py',
        'infrastructure/stack.py',
        'services/tasks/create_task.py',
        'services/tasks/list_tasks.py',
        'services/tasks/update_task.py',
        'services/tasks/delete_task.py',
        'services/auth/authorizer.py',
        'events/task_created_handler.py',
        'requirements.txt',
        'cdk.json'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files present")
    return True


def test_basic_imports():
    """Test basic Python imports"""
    
    try:
        import json
        import uuid
        import boto3
        print("✅ Basic imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def main():
    """Run all tests"""
    
    print("🧪 Testing SaaS Backend Setup...")
    print("=" * 40)
    
    tests = [
        test_project_structure,
        test_basic_imports
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Setup validation successful!")
        print("\n📝 Next steps:")
        print("1. Install AWS CLI and configure credentials")
        print("2. Install AWS CDK: npm install -g aws-cdk")
        print("3. Install Python dependencies: pip install -r requirements.txt")
        print("4. Deploy: cdk deploy")
        return True
    else:
        print("❌ Setup validation failed!")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)