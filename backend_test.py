import requests
import sys
import json
from datetime import datetime
from urllib.parse import quote

class GlobalRadioAPITester:
    def __init__(self, base_url="https://worldwave-radio-44.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.station_sample = None

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, list) and len(response_data) > 0:
                        print(f"   Response: List with {len(response_data)} items")
                        if endpoint == "api/stations":
                            # Store first station for streaming test
                            self.station_sample = response_data[0]
                            print(f"   Sample station: {response_data[0].get('name', 'Unknown')}")
                    elif isinstance(response_data, dict):
                        print(f"   Response keys: {list(response_data.keys())}")
                    return True, response_data
                except:
                    print(f"   Response: Non-JSON content (length: {len(response.content)})")
                    return True, response.content
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text[:200]}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout after {timeout}s")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root endpoint"""
        return self.run_test("Root Endpoint", "GET", "", 200)

    def test_health_check(self):
        """Test health check endpoint"""
        return self.run_test("Health Check", "GET", "api/health", 200)

    def test_get_stations(self):
        """Test fetching radio stations"""
        success, response = self.run_test("Get Radio Stations", "GET", "api/stations", 200, timeout=15)
        
        if success and isinstance(response, list):
            print(f"   ✅ Received {len(response)} stations")
            if len(response) > 0:
                station = response[0]
                required_fields = ['uuid', 'name', 'url', 'country']
                missing_fields = [field for field in required_fields if not station.get(field)]
                if missing_fields:
                    print(f"   ⚠️  Missing required fields: {missing_fields}")
                else:
                    print(f"   ✅ Station data structure is valid")
                    print(f"   Sample: {station['name']} from {station['country']}")
        
        return success, response

    def test_search_stations(self):
        """Test station search functionality"""
        # Test search by name
        success1, _ = self.run_test("Search Stations by Name", "GET", "api/stations/search?query=BBC", 200)
        
        # Test search by country
        success2, _ = self.run_test("Search Stations by Country", "GET", "api/stations/search?country=Germany", 200)
        
        # Test default search (no params)
        success3, _ = self.run_test("Search Stations Default", "GET", "api/stations/search", 200)
        
        return success1 and success2 and success3

    def test_stream_proxy(self):
        """Test streaming proxy endpoint"""
        if not self.station_sample:
            print("❌ No station sample available for streaming test")
            return False
            
        station_url = self.station_sample.get('url')
        if not station_url:
            print("❌ No station URL available for streaming test")
            return False
            
        # Encode the station URL for the proxy
        encoded_url = quote(station_url, safe='')
        
        print(f"   Testing stream proxy with: {station_url}")
        
        # Test with shorter timeout and expect streaming response
        success, response = self.run_test(
            "Stream Proxy", 
            "GET", 
            f"api/stream/{encoded_url}", 
            200, 
            timeout=10
        )
        
        return success

    def test_cors_headers(self):
        """Test CORS headers are present"""
        try:
            response = requests.options(f"{self.base_url}/api/stations")
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
            }
            
            print(f"\n🔍 Testing CORS Headers...")
            print(f"   CORS Headers: {cors_headers}")
            
            if cors_headers['Access-Control-Allow-Origin']:
                print("✅ CORS headers are configured")
                self.tests_passed += 1
            else:
                print("❌ CORS headers missing")
            
            self.tests_run += 1
            return bool(cors_headers['Access-Control-Allow-Origin'])
            
        except Exception as e:
            print(f"❌ CORS test failed: {e}")
            self.tests_run += 1
            return False

def main():
    print("🎵 Global Radio API Testing Suite")
    print("=" * 50)
    
    tester = GlobalRadioAPITester()
    
    # Run all tests
    print("\n📡 Testing Backend API Endpoints...")
    
    # Basic endpoints
    tester.test_root_endpoint()
    tester.test_health_check()
    
    # Core functionality
    tester.test_get_stations()
    tester.test_search_stations()
    
    # Streaming (depends on stations being available)
    tester.test_stream_proxy()
    
    # CORS configuration
    tester.test_cors_headers()
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed! Backend API is working correctly.")
        return 0
    else:
        failed_tests = tester.tests_run - tester.tests_passed
        print(f"⚠️  {failed_tests} test(s) failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())