#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Data Cleaner Application
Tests all backend endpoints with realistic data scenarios
"""

import requests
import json
import pandas as pd
import io
import tempfile
import os
from pathlib import Path
import time

# Configuration
BASE_URL = "https://dbe28ff8-8b87-4f25-9604-e797b21bdc8b.preview.emergentagent.com/api"
TEST_DATA_DIR = Path("/tmp/test_data")
TEST_DATA_DIR.mkdir(exist_ok=True)

class DataCleanerAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.uploaded_files = []
        self.test_results = {
            "file_upload": {"status": "PENDING", "details": []},
            "data_cleaning": {"status": "PENDING", "details": []},
            "data_statistics": {"status": "PENDING", "details": []},
            "file_export": {"status": "PENDING", "details": []},
            "file_management": {"status": "PENDING", "details": []},
            "mongodb_integration": {"status": "PENDING", "details": []}
        }
    
    def create_test_files(self):
        """Create realistic test files with various data scenarios"""
        print("Creating test data files...")
        
        # CSV file with missing values and duplicates
        csv_data = {
            'employee_id': [1, 2, 3, 4, 5, 3, 6, 7],  # Duplicate ID 3
            'name': ['Alice Johnson', 'Bob Smith', 'Charlie Brown', None, 'Eva Davis', 'Charlie Brown', 'Frank Wilson', '  Grace Lee  '],  # Missing name, duplicate name, whitespace
            'department': ['Engineering', 'Marketing', 'Sales', 'Engineering', None, 'Sales', 'HR', 'Engineering'],  # Missing department
            'salary': [75000, 65000, 55000, 80000, 70000, 55000, 60000, 72000],
            'hire_date': ['2020-01-15', '2019-06-20', '2021-03-10', '2018-11-05', '2020-08-12', '2021-03-10', '2022-01-20', '2019-12-15']
        }
        csv_df = pd.DataFrame(csv_data)
        csv_path = TEST_DATA_DIR / "employees.csv"
        csv_df.to_csv(csv_path, index=False)
        
        # XLSX file with numeric data for statistics testing
        xlsx_data = {
            'product_id': ['P001', 'P002', 'P003', 'P004', 'P005'],
            'product_name': ['Laptop', 'Mouse', 'Keyboard', 'Monitor', 'Headphones'],
            'price': [999.99, 25.50, 75.00, 299.99, 150.00],
            'quantity': [50, 200, 100, 75, 120],
            'category': ['Electronics', 'Accessories', 'Accessories', 'Electronics', 'Accessories']
        }
        xlsx_df = pd.DataFrame(xlsx_data)
        xlsx_path = TEST_DATA_DIR / "products.xlsx"
        xlsx_df.to_excel(xlsx_path, index=False)
        
        # JSON file with mixed data types
        json_data = [
            {"customer_id": 1, "name": "John Doe", "age": 30, "city": "New York", "orders": 5},
            {"customer_id": 2, "name": "Jane Smith", "age": 25, "city": "Los Angeles", "orders": 3},
            {"customer_id": 3, "name": "Mike Johnson", "age": None, "city": "Chicago", "orders": 7},  # Missing age
            {"customer_id": 4, "name": "Sarah Wilson", "age": 35, "city": None, "orders": 2},  # Missing city
            {"customer_id": 5, "name": "Tom Brown", "age": 28, "city": "Houston", "orders": 4}
        ]
        json_path = TEST_DATA_DIR / "customers.json"
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        return {
            'csv': csv_path,
            'xlsx': xlsx_path,
            'json': json_path
        }
    
    def test_api_health(self):
        """Test if API is accessible"""
        try:
            response = self.session.get(f"{BASE_URL}/")
            if response.status_code == 200:
                print("✅ API is accessible")
                return True
            else:
                print(f"❌ API health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API connection failed: {e}")
            return False
    
    def test_file_upload(self, test_files):
        """Test file upload endpoint with different file types"""
        print("\n🔄 Testing File Upload Endpoint...")
        
        for file_type, file_path in test_files.items():
            try:
                print(f"  Testing {file_type.upper()} upload...")
                
                with open(file_path, 'rb') as f:
                    files = {'file': (file_path.name, f, self._get_content_type(file_type))}
                    response = self.session.post(f"{BASE_URL}/upload", files=files)
                
                if response.status_code == 200:
                    data = response.json()
                    file_id = data['file_info']['id']
                    self.uploaded_files.append({'id': file_id, 'type': file_type, 'filename': file_path.name})
                    
                    # Validate response structure
                    required_keys = ['file_info', 'preview_data', 'statistics', 'columns']
                    if all(key in data for key in required_keys):
                        print(f"    ✅ {file_type.upper()} upload successful - File ID: {file_id}")
                        self.test_results["file_upload"]["details"].append(f"✅ {file_type.upper()} upload successful")
                        
                        # Validate statistics structure
                        stats = data['statistics']
                        if 'rows' in stats and 'columns' in stats and 'missing_values' in stats:
                            print(f"    ✅ Statistics calculated: {stats['rows']} rows, {stats['columns']} columns")
                        else:
                            print(f"    ⚠️ Statistics structure incomplete")
                    else:
                        print(f"    ❌ {file_type.upper()} upload response missing required fields")
                        self.test_results["file_upload"]["details"].append(f"❌ {file_type.upper()} response incomplete")
                else:
                    print(f"    ❌ {file_type.upper()} upload failed: {response.status_code} - {response.text}")
                    self.test_results["file_upload"]["details"].append(f"❌ {file_type.upper()} upload failed: {response.status_code}")
                    
            except Exception as e:
                print(f"    ❌ {file_type.upper()} upload error: {e}")
                self.test_results["file_upload"]["details"].append(f"❌ {file_type.upper()} upload error: {str(e)}")
        
        # Set overall status
        if len(self.uploaded_files) == len(test_files):
            self.test_results["file_upload"]["status"] = "PASS"
        elif len(self.uploaded_files) > 0:
            self.test_results["file_upload"]["status"] = "PARTIAL"
        else:
            self.test_results["file_upload"]["status"] = "FAIL"
    
    def test_data_statistics(self):
        """Test data statistics calculation"""
        print("\n🔄 Testing Data Statistics Calculation...")
        
        if not self.uploaded_files:
            print("  ❌ No uploaded files to test statistics")
            self.test_results["data_statistics"]["status"] = "FAIL"
            return
        
        for file_info in self.uploaded_files:
            try:
                file_id = file_info['id']
                file_type = file_info['type']
                print(f"  Testing statistics for {file_type.upper()} file...")
                
                response = self.session.get(f"{BASE_URL}/file/{file_id}/data")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Validate response structure
                    required_keys = ['data', 'total_rows', 'columns']
                    if all(key in data for key in required_keys):
                        print(f"    ✅ Data retrieval successful - {data['total_rows']} rows, {len(data['columns'])} columns")
                        self.test_results["data_statistics"]["details"].append(f"✅ {file_type.upper()} data statistics working")
                        
                        # Test pagination
                        if data['total_rows'] > 50:
                            page_response = self.session.get(f"{BASE_URL}/file/{file_id}/data?page=1&page_size=10")
                            if page_response.status_code == 200:
                                print(f"    ✅ Pagination working")
                            else:
                                print(f"    ⚠️ Pagination issue: {page_response.status_code}")
                    else:
                        print(f"    ❌ Data response missing required fields")
                        self.test_results["data_statistics"]["details"].append(f"❌ {file_type.upper()} data response incomplete")
                else:
                    print(f"    ❌ Data retrieval failed: {response.status_code} - {response.text}")
                    self.test_results["data_statistics"]["details"].append(f"❌ {file_type.upper()} data retrieval failed")
                    
            except Exception as e:
                print(f"    ❌ Statistics test error: {e}")
                self.test_results["data_statistics"]["details"].append(f"❌ Statistics error: {str(e)}")
        
        # Set overall status
        success_count = len([d for d in self.test_results["data_statistics"]["details"] if "✅" in d])
        if success_count == len(self.uploaded_files):
            self.test_results["data_statistics"]["status"] = "PASS"
        elif success_count > 0:
            self.test_results["data_statistics"]["status"] = "PARTIAL"
        else:
            self.test_results["data_statistics"]["status"] = "FAIL"
    
    def test_data_cleaning(self):
        """Test data cleaning operations"""
        print("\n🔄 Testing Data Cleaning Operations...")
        
        if not self.uploaded_files:
            print("  ❌ No uploaded files to test cleaning")
            self.test_results["data_cleaning"]["status"] = "FAIL"
            return
        
        # Test with CSV file (first uploaded file)
        csv_file = next((f for f in self.uploaded_files if f['type'] == 'csv'), None)
        if not csv_file:
            print("  ❌ No CSV file available for cleaning test")
            self.test_results["data_cleaning"]["status"] = "FAIL"
            return
        
        file_id = csv_file['id']
        
        # Test different cleaning operations
        cleaning_tests = [
            {
                "name": "Remove Duplicates",
                "options": {
                    "remove_duplicates": True,
                    "handle_missing": "none"
                }
            },
            {
                "name": "Handle Missing Values - Drop",
                "options": {
                    "remove_duplicates": False,
                    "handle_missing": "drop"
                }
            },
            {
                "name": "Handle Missing Values - Fill",
                "options": {
                    "remove_duplicates": False,
                    "handle_missing": "fill",
                    "fill_value": "Unknown"
                }
            },
            {
                "name": "Column Rename",
                "options": {
                    "remove_duplicates": False,
                    "handle_missing": "none",
                    "column_renames": {"name": "employee_name", "department": "dept"}
                }
            },
            {
                "name": "Trim Whitespace",
                "options": {
                    "remove_duplicates": False,
                    "handle_missing": "none",
                    "trim_whitespace": True
                }
            }
        ]
        
        for test in cleaning_tests:
            try:
                print(f"  Testing: {test['name']}...")
                
                data = {
                    'file_id': file_id,
                    'options': json.dumps(test['options'])
                }
                
                response = self.session.post(f"{BASE_URL}/clean", data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Validate response structure
                    required_keys = ['cleaned_file_id', 'original_rows', 'cleaned_rows', 'preview_data', 'statistics']
                    if all(key in result for key in required_keys):
                        print(f"    ✅ {test['name']} successful - {result['original_rows']} → {result['cleaned_rows']} rows")
                        self.test_results["data_cleaning"]["details"].append(f"✅ {test['name']} working")
                        
                        # Store cleaned file ID for export testing
                        self.uploaded_files.append({
                            'id': result['cleaned_file_id'],
                            'type': 'cleaned_csv',
                            'filename': f"cleaned_{csv_file['filename']}"
                        })
                    else:
                        print(f"    ❌ {test['name']} response missing required fields")
                        self.test_results["data_cleaning"]["details"].append(f"❌ {test['name']} response incomplete")
                else:
                    print(f"    ❌ {test['name']} failed: {response.status_code} - {response.text}")
                    self.test_results["data_cleaning"]["details"].append(f"❌ {test['name']} failed: {response.status_code}")
                    
            except Exception as e:
                print(f"    ❌ {test['name']} error: {e}")
                self.test_results["data_cleaning"]["details"].append(f"❌ {test['name']} error: {str(e)}")
        
        # Set overall status
        success_count = len([d for d in self.test_results["data_cleaning"]["details"] if "✅" in d])
        if success_count >= 3:  # At least 3 cleaning operations should work
            self.test_results["data_cleaning"]["status"] = "PASS"
        elif success_count > 0:
            self.test_results["data_cleaning"]["status"] = "PARTIAL"
        else:
            self.test_results["data_cleaning"]["status"] = "FAIL"
    
    def test_file_export(self):
        """Test file export functionality"""
        print("\n🔄 Testing File Export Functionality...")
        
        if not self.uploaded_files:
            print("  ❌ No files available for export testing")
            self.test_results["file_export"]["status"] = "FAIL"
            return
        
        # Test export formats
        export_formats = ['csv', 'xlsx', 'json']
        test_file = self.uploaded_files[0]  # Use first uploaded file
        
        for format_type in export_formats:
            try:
                print(f"  Testing {format_type.upper()} export...")
                
                response = self.session.get(f"{BASE_URL}/download/{test_file['id']}?format={format_type}")
                
                if response.status_code == 200:
                    # Check content type
                    content_type = response.headers.get('content-type', '')
                    expected_types = {
                        'csv': 'text/csv',
                        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'json': 'application/json'
                    }
                    
                    if expected_types[format_type] in content_type:
                        print(f"    ✅ {format_type.upper()} export successful - Content-Type: {content_type}")
                        self.test_results["file_export"]["details"].append(f"✅ {format_type.upper()} export working")
                        
                        # Validate content length
                        if len(response.content) > 0:
                            print(f"    ✅ Export file size: {len(response.content)} bytes")
                        else:
                            print(f"    ⚠️ Export file is empty")
                    else:
                        print(f"    ⚠️ {format_type.upper()} export content type mismatch: {content_type}")
                        self.test_results["file_export"]["details"].append(f"⚠️ {format_type.upper()} content type issue")
                else:
                    print(f"    ❌ {format_type.upper()} export failed: {response.status_code} - {response.text}")
                    self.test_results["file_export"]["details"].append(f"❌ {format_type.upper()} export failed")
                    
            except Exception as e:
                print(f"    ❌ {format_type.upper()} export error: {e}")
                self.test_results["file_export"]["details"].append(f"❌ {format_type.upper()} export error: {str(e)}")
        
        # Set overall status
        success_count = len([d for d in self.test_results["file_export"]["details"] if "✅" in d])
        if success_count == len(export_formats):
            self.test_results["file_export"]["status"] = "PASS"
        elif success_count > 0:
            self.test_results["file_export"]["status"] = "PARTIAL"
        else:
            self.test_results["file_export"]["status"] = "FAIL"
    
    def test_file_management(self):
        """Test file listing and deletion"""
        print("\n🔄 Testing File Management...")
        
        # Test file listing
        try:
            print("  Testing file listing...")
            response = self.session.get(f"{BASE_URL}/files")
            
            if response.status_code == 200:
                files = response.json()
                if isinstance(files, list) and len(files) > 0:
                    print(f"    ✅ File listing successful - {len(files)} files found")
                    self.test_results["file_management"]["details"].append("✅ File listing working")
                else:
                    print(f"    ⚠️ File listing returned empty or invalid data")
                    self.test_results["file_management"]["details"].append("⚠️ File listing empty")
            else:
                print(f"    ❌ File listing failed: {response.status_code}")
                self.test_results["file_management"]["details"].append("❌ File listing failed")
                
        except Exception as e:
            print(f"    ❌ File listing error: {e}")
            self.test_results["file_management"]["details"].append(f"❌ File listing error: {str(e)}")
        
        # Test file deletion (delete one file to test)
        if self.uploaded_files:
            try:
                test_file = self.uploaded_files[-1]  # Delete last uploaded file
                print(f"  Testing file deletion for: {test_file['filename']}...")
                
                response = self.session.delete(f"{BASE_URL}/file/{test_file['id']}")
                
                if response.status_code == 200:
                    print(f"    ✅ File deletion successful")
                    self.test_results["file_management"]["details"].append("✅ File deletion working")
                    self.uploaded_files.remove(test_file)
                else:
                    print(f"    ❌ File deletion failed: {response.status_code}")
                    self.test_results["file_management"]["details"].append("❌ File deletion failed")
                    
            except Exception as e:
                print(f"    ❌ File deletion error: {e}")
                self.test_results["file_management"]["details"].append(f"❌ File deletion error: {str(e)}")
        
        # Set overall status
        success_count = len([d for d in self.test_results["file_management"]["details"] if "✅" in d])
        if success_count >= 1:
            self.test_results["file_management"]["status"] = "PASS"
        else:
            self.test_results["file_management"]["status"] = "FAIL"
    
    def test_mongodb_integration(self):
        """Test MongoDB integration by verifying data persistence"""
        print("\n🔄 Testing MongoDB Integration...")
        
        if not self.uploaded_files:
            print("  ❌ No files to verify MongoDB integration")
            self.test_results["mongodb_integration"]["status"] = "FAIL"
            return
        
        try:
            # Test that uploaded files are persisted in database
            response = self.session.get(f"{BASE_URL}/files")
            
            if response.status_code == 200:
                files = response.json()
                uploaded_ids = [f['id'] for f in self.uploaded_files]
                db_ids = [f['id'] for f in files if isinstance(f, dict) and 'id' in f]
                
                # Check if uploaded files exist in database
                found_files = [file_id for file_id in uploaded_ids if file_id in db_ids]
                
                if len(found_files) > 0:
                    print(f"    ✅ MongoDB integration working - {len(found_files)} files found in database")
                    self.test_results["mongodb_integration"]["details"].append("✅ File metadata persistence working")
                    self.test_results["mongodb_integration"]["status"] = "PASS"
                else:
                    print(f"    ❌ MongoDB integration issue - uploaded files not found in database")
                    self.test_results["mongodb_integration"]["details"].append("❌ File metadata not persisted")
                    self.test_results["mongodb_integration"]["status"] = "FAIL"
            else:
                print(f"    ❌ Cannot verify MongoDB integration - file listing failed")
                self.test_results["mongodb_integration"]["status"] = "FAIL"
                
        except Exception as e:
            print(f"    ❌ MongoDB integration test error: {e}")
            self.test_results["mongodb_integration"]["details"].append(f"❌ MongoDB test error: {str(e)}")
            self.test_results["mongodb_integration"]["status"] = "FAIL"
    
    def _get_content_type(self, file_type):
        """Get appropriate content type for file upload"""
        content_types = {
            'csv': 'text/csv',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'json': 'application/json'
        }
        return content_types.get(file_type, 'application/octet-stream')
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🔍 BACKEND API TEST SUMMARY")
        print("="*80)
        
        overall_status = "PASS"
        
        for test_name, result in self.test_results.items():
            status_icon = {
                "PASS": "✅",
                "PARTIAL": "⚠️",
                "FAIL": "❌",
                "PENDING": "⏳"
            }.get(result["status"], "❓")
            
            print(f"\n{status_icon} {test_name.replace('_', ' ').title()}: {result['status']}")
            
            for detail in result["details"]:
                print(f"  {detail}")
            
            if result["status"] in ["FAIL", "PARTIAL"]:
                overall_status = "PARTIAL" if overall_status == "PASS" else "FAIL"
        
        print(f"\n{'='*80}")
        print(f"🎯 OVERALL BACKEND STATUS: {overall_status}")
        print(f"📊 Files Uploaded: {len(self.uploaded_files)}")
        print(f"🔗 API Base URL: {BASE_URL}")
        print("="*80)
        
        return overall_status, self.test_results

def main():
    """Main testing function"""
    print("🚀 Starting Data Cleaner Backend API Tests...")
    print(f"🔗 Testing API at: {BASE_URL}")
    
    tester = DataCleanerAPITester()
    
    # Check API health first
    if not tester.test_api_health():
        print("❌ API is not accessible. Exiting tests.")
        return
    
    # Create test data files
    test_files = tester.create_test_files()
    print(f"📁 Created test files: {list(test_files.keys())}")
    
    # Run all tests in order
    tester.test_file_upload(test_files)
    tester.test_data_statistics()
    tester.test_data_cleaning()
    tester.test_file_export()
    tester.test_file_management()
    tester.test_mongodb_integration()
    
    # Print final summary
    overall_status, results = tester.print_summary()
    
    return overall_status, results

if __name__ == "__main__":
    main()