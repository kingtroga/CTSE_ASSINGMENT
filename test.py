#!/usr/bin/env python3
"""
Simple Airtable API Test
Just run: python test_airtable.py
"""

import requests
import json

# Your credentials (from your .env)
BASE_ID = 'appLt31NqOLXcv3V1'
ACCESS_TOKEN = 'patRWURHXsrBYtayJ.0715b57665e5e586019b4c2b820243ecfb73ca041126b2c7d774521f9d6b9d41'

def test_airtable_connection():
    """Test basic connection to Airtable"""
    print("🔍 Testing Airtable connection...")
    
    # Headers for API request
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Test 1: Check if we can access the base
        print(f"📡 Connecting to base: {BASE_ID}")
        
        # Try to get base metadata (list of tables)
        url = f"https://api.airtable.com/v0/meta/bases/{BASE_ID}/tables"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            print("✅ Connection successful!")
            
            # Show available tables
            data = response.json()
            tables = data.get('tables', [])
            
            print(f"\n📋 Found {len(tables)} tables in your base:")
            for table in tables:
                print(f"   - {table['name']} (ID: {table['id']})")
            
            return True, tables
            
        elif response.status_code == 401:
            print("❌ Authentication failed - check your token")
            return False, None
            
        elif response.status_code == 403:
            print("❌ Permission denied - token needs schema.bases:read scope")
            return False, None
            
        elif response.status_code == 404:
            print("❌ Base not found - check your BASE_ID")
            return False, None
            
        else:
            print(f"❌ Unexpected error: {response.status_code}")
            print(f"Response: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"💥 Connection error: {e}")
        return False, None

def test_table_access(table_name="Table 1"):
    """Test reading from a specific table"""
    print(f"\n🔍 Testing table access: {table_name}")
    
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Try to read first few records from table
        url = f"https://api.airtable.com/v0/{BASE_ID}/{table_name}?maxRecords=3"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            records = data.get('records', [])
            
            print(f"✅ Successfully read {len(records)} records from '{table_name}'")
            
            if records:
                print("\n📄 Sample record structure:")
                first_record = records[0]
                fields = first_record.get('fields', {})
                for field_name, value in fields.items():
                    print(f"   - {field_name}: {type(value).__name__}")
            
            return True
            
        elif response.status_code == 404:
            print(f"❌ Table '{table_name}' not found")
            return False
            
        else:
            print(f"❌ Error accessing table: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"💥 Table access error: {e}")
        return False

def test_create_record(table_name="Table 1"):
    """Test creating a simple record"""
    print(f"\n🔍 Testing record creation in: {table_name}")
    
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Simple test record
    test_data = {
        "fields": {
            "sku": "Test Record - Django Sync",
            "status": "ACTIVE"
        }
    }
    
    try:
        url = f"https://api.airtable.com/v0/{BASE_ID}/{table_name}"
        response = requests.post(url, headers=headers, json=test_data)
        
        if response.status_code == 200:
            data = response.json()
            record_id = data.get('id')
            print(f"✅ Successfully created test record: {record_id}")
            
            # Clean up - delete the test record
            delete_url = f"{url}/{record_id}"
            delete_response = requests.delete(delete_url, headers=headers)
            
            if delete_response.status_code == 200:
                print("🧹 Test record cleaned up")
            
            return True
            
        elif response.status_code == 422:
            print("❌ Validation error - check field names match your table")
            print(f"Response: {response.text}")
            return False
            
        else:
            print(f"❌ Create error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"💥 Create record error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Airtable API Test Suite")
    print("=" * 40)
    
    # Test 1: Basic connection
    success, tables = test_airtable_connection()
    
    if not success:
        print("\n❌ Basic connection failed. Fix this first!")
        return
    
    # Test 2: Try to access first table if any exist
    if tables:
        first_table = tables[0]['name']
        test_table_access(first_table)
        test_create_record(first_table)
    
    print("\n" + "=" * 40)
    print("🎉 Test complete!")
    print("\nNext steps:")
    print("1. If all tests passed - your connection works!")
    print("2. Create your tables: SKU_Mappings, Inventory, Combo_Products")
    print("3. Run the Django sync command")
    print("\n😴 Now go watch your film and sleep! This is working.")

if __name__ == "__main__":
    main()