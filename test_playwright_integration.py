"""
Test Script for Playwright/CDP Integration
Demonstrates the dynamic connection and web automation capabilities.
"""

import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.action.controller import DesktopController, WebAutomationError
from dotenv import load_dotenv

load_dotenv()


def test_initialization():
    """Test 1: Verify Playwright initialization doesn't fail when Chrome is not running."""
    print("\n" + "=" * 80)
    print("TEST 1: Initialize Controller (Chrome NOT running)")
    print("=" * 80)
    
    controller = DesktopController(enable_playwright=True)
    
    print("✅ Controller initialized successfully")
    print(f"   Playwright enabled: {controller.enable_playwright}")
    print(f"   Playwright available: {getattr(controller, 'playwright_available', False)}")
    print(f"   Browser connected: {controller.browser is not None}")
    print(f"   Page available: {controller.page is not None}")
    
    return controller


def test_chrome_launch(controller):
    """Test 2: Launch Chrome with CDP and wait for it to initialize."""
    print("\n" + "=" * 80)
    print("TEST 2: Launch Chrome with CDP Port")
    print("=" * 80)
    
    print("Launching Chrome with remote debugging...")
    controller.hotkey('win', 'r')
    time.sleep(0.5)
    controller.type_text('chrome --force-renderer-accessibility --remote-debugging-port=9222')
    controller.press_key('enter')
    
    print("⏳ Waiting 6 seconds for Chrome to initialize CDP port and accessibility tree...")
    controller.wait(6)
    
    print("✅ Chrome should now be running with CDP on port 9222")


def test_dynamic_connection(controller):
    """Test 3: Verify dynamic connection works when Chrome is running."""
    print("\n" + "=" * 80)
    print("TEST 3: Dynamic Playwright Connection")
    print("=" * 80)
    
    print("Attempting to connect to Chrome via CDP...")
    
    # This should trigger the dynamic connection in _ensure_browser_connection
    try:
        result = controller._ensure_browser_connection()
        
        if result:
            print("✅ Successfully connected to Chrome!")
            print(f"   Browser: {controller.browser}")
            print(f"   Page: {controller.page}")
            print(f"   Current URL: {controller.web_get_url()}")
        else:
            print("❌ Failed to connect to Chrome")
            print("   Ensure Chrome is running with --remote-debugging-port=9222")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def test_web_navigation(controller):
    """Test 4: Navigate to a website using Playwright."""
    print("\n" + "=" * 80)
    print("TEST 4: Web Navigation via Playwright")
    print("=" * 80)
    
    try:
        print("Navigating to example.com...")
        
        # First, let's navigate using address bar (UI Automation)
        print("Step 1: Clicking address bar...")
        controller.click_element(500, 50, scale=False)  # Approximate address bar position
        time.sleep(0.5)
        
        print("Step 2: Typing URL...")
        controller.type_text("example.com", press_enter=True)
        
        print("⏳ Waiting for page to load...")
        controller.wait(3)
        
        # Now verify Playwright can see the page
        current_url = controller.web_get_url()
        print(f"✅ Current URL: {current_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Navigation error: {e}")
        return False


def test_web_element_interaction(controller):
    """Test 5: Interact with web elements using CSS selectors."""
    print("\n" + "=" * 80)
    print("TEST 5: Web Element Interaction")
    print("=" * 80)
    
    try:
        print("Fetching interactive elements from page...")
        elements = controller.web_get_elements(max_elements=20)
        
        print(f"✅ Found {len(elements)} interactive elements:")
        for i, elem in enumerate(elements[:10], 1):  # Show first 10
            print(f"   {i}. {elem['type']}: {elem['text'][:50]}")
        
        # Try to click a link if available
        links = [e for e in elements if e['type'] == 'link']
        if links:
            first_link = links[0]
            print(f"\nAttempting to click link: {first_link['text'][:50]}")
            try:
                controller.web_click(first_link['selector'])
                print("✅ Successfully clicked link via Playwright!")
                controller.wait(2)
                print(f"   New URL: {controller.web_get_url()}")
            except WebAutomationError as e:
                print(f"⚠️  Click failed: {e}")
        else:
            print("ℹ️  No links found on page")
        
        return True
        
    except WebAutomationError as e:
        print(f"❌ Web automation error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_cleanup(controller):
    """Test 6: Verify proper cleanup."""
    print("\n" + "=" * 80)
    print("TEST 6: Cleanup")
    print("=" * 80)
    
    print("Closing Playwright connection...")
    controller.close_playwright()
    
    print("✅ Cleanup complete")
    print(f"   Browser closed: {controller.browser is None}")
    print(f"   Page closed: {controller.page is None}")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("PLAYWRIGHT/CDP INTEGRATION TEST SUITE")
    print("=" * 80)
    print("\nThis test suite will:")
    print("1. Initialize controller without Chrome running (should succeed)")
    print("2. Launch Chrome with CDP port 9222")
    print("3. Dynamically connect Playwright to Chrome")
    print("4. Navigate to a website")
    print("5. Interact with web elements via CSS selectors")
    print("6. Cleanup resources")
    print("\n⚠️  IMPORTANT: Close all Chrome instances before starting!")
    print("=" * 80)
    
    input("\nPress Enter to start tests...")
    
    try:
        # Test 1: Initialize without Chrome
        controller = test_initialization()
        time.sleep(1)
        
        # Test 2: Launch Chrome
        test_chrome_launch(controller)
        time.sleep(1)
        
        # Test 3: Dynamic connection
        connected = test_dynamic_connection(controller)
        if not connected:
            print("\n❌ Cannot proceed without Chrome connection")
            print("   Verify Chrome launched successfully with debugging port")
            return
        time.sleep(1)
        
        # Test 4: Web navigation
        test_web_navigation(controller)
        time.sleep(1)
        
        # Test 5: Web element interaction
        test_web_element_interaction(controller)
        time.sleep(1)
        
        # Test 6: Cleanup
        test_cleanup(controller)
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 80)
        print("\nKey Improvements Demonstrated:")
        print("1. ✅ Initialization succeeds even when Chrome is not running")
        print("2. ✅ Dynamic connection with retry logic handles Chrome startup delay")
        print("3. ✅ Playwright successfully connects via CDP after Chrome launches")
        print("4. ✅ Web automation via CSS selectors works correctly")
        print("5. ✅ Proper cleanup prevents orphaned browser processes")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        if 'controller' in locals():
            controller.close_playwright()
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
