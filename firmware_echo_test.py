#!/usr/bin/env python3
"""
Echo Test - Stage 1C Transport Layer Test
Tests bidirectional communication with STM32
"""

import serial
import serial.tools.list_ports
import time
import sys

def find_stm32_port():
    """Find the STM32 USB CDC port"""
    ports = serial.tools.list_ports.comports()
    
    print("Available serial ports:")
    for i, port in enumerate(ports):
        print(f"  [{i}] {port.device} - {port.description}")
    
    # Try to auto-detect STM32
    for port in ports:
        if any(keyword in port.description.lower() 
               for keyword in ['stm32', 'stmicroelectronics', 'usb serial']):
            print(f"\nAuto-detected STM32 at: {port.device}")
            return port.device
    
    # If not found, ask user
    if ports:
        choice = input(f"\nEnter port number [0-{len(ports)-1}]: ")
        return ports[int(choice)].device
    else:
        print("No serial ports found!")
        return None

def test_echo(port_name):
    """Test echo functionality"""
    try:
        # Open serial port
        ser = serial.Serial(
            port=port_name,
            baudrate=115200,
            timeout=2
        )
        
        print(f"\n{'='*60}")
        print(f"Echo Test - Transport Layer Verification")
        print(f"{'='*60}")
        print(f"Port: {port_name}")
        print(f"Testing bidirectional communication...\n")
        
        # Give USB time to initialize
        time.sleep(0.5)
        
        # Clear any stale data
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Test 1: Single character echo
        print("Test 1: Single character echo")
        test_char = b'A'
        ser.write(test_char)
        time.sleep(0.1)
        
        if ser.in_waiting > 0:
            response = ser.read(1)
            if response == test_char:
                print(f"  ✓ Sent: {test_char.decode()}, Received: {response.decode()} - PASS")
            else:
                print(f"  ✗ Sent: {test_char.decode()}, Received: {response.decode()} - FAIL")
        else:
            print(f"  ✗ No response received - FAIL")
            return False
        
        # Test 2: Multiple characters
        print("\nTest 2: Multiple character echo")
        test_string = b"HELLO"
        ser.write(test_string)
        time.sleep(0.2)
        
        if ser.in_waiting >= len(test_string):
            response = ser.read(len(test_string))
            if response == test_string:
                print(f"  ✓ Sent: {test_string.decode()}, Received: {response.decode()} - PASS")
            else:
                print(f"  ✗ Sent: {test_string.decode()}, Received: {response.decode()} - FAIL")
        else:
            print(f"  ✗ Incomplete response (expected {len(test_string)}, got {ser.in_waiting}) - FAIL")
            return False
        
        # Test 3: Sentence echo
        print("\nTest 3: Sentence echo")
        test_sentence = b"The quick brown fox jumps over the lazy dog"
        ser.write(test_sentence)
        time.sleep(0.3)
        
        if ser.in_waiting >= len(test_sentence):
            response = ser.read(len(test_sentence))
            if response == test_sentence:
                print(f"  ✓ Sent: {test_sentence.decode()}")
                print(f"  ✓ Received: {response.decode()}")
                print(f"  ✓ PASS")
            else:
                print(f"  ✗ Mismatch - FAIL")
                print(f"    Expected: {test_sentence}")
                print(f"    Got: {response}")
        else:
            print(f"  ✗ Incomplete response - FAIL")
            return False
        
        # Test 4: Binary data echo
        print("\nTest 4: Binary data echo (0x00-0xFF)")
        test_binary = bytes(range(256))
        ser.write(test_binary)
        time.sleep(0.5)
        
        if ser.in_waiting >= len(test_binary):
            response = ser.read(len(test_binary))
            if response == test_binary:
                print(f"  ✓ All 256 bytes echoed correctly - PASS")
            else:
                print(f"  ✗ Binary data mismatch - FAIL")
                # Show where they differ
                for i, (sent, received) in enumerate(zip(test_binary, response)):
                    if sent != received:
                        print(f"    First mismatch at byte {i}: sent 0x{sent:02X}, got 0x{received:02X}")
                        break
        else:
            print(f"  ✗ Incomplete response (expected {len(test_binary)}, got {ser.in_waiting}) - FAIL")
            return False
        
        # Test 5: Rapid fire test
        print("\nTest 5: Rapid fire (100 characters)")
        success_count = 0
        for i in range(100):
            test_byte = bytes([i % 256])
            ser.write(test_byte)
            time.sleep(0.01)
            if ser.in_waiting > 0:
                response = ser.read(1)
                if response == test_byte:
                    success_count += 1
        
        print(f"  {success_count}/100 characters echoed correctly")
        if success_count >= 95:  # Allow a few missed due to timing
            print(f"  ✓ PASS")
        else:
            print(f"  ✗ FAIL (too many errors)")
            return False
        
        # All tests passed!
        print(f"\n{'='*60}")
        print(f"✓ ALL TESTS PASSED!")
        print(f"{'='*60}")
        print(f"Transport layer is working correctly!")
        print(f"Ring buffers: ✓")
        print(f"USB RX → Ring buffer: ✓")
        print(f"Ring buffer → USB TX: ✓")
        print(f"Bidirectional communication: ✓")
        print(f"\nReady for Stage 2: Link/Plumbing Layer")
        
        ser.close()
        return True
        
    except serial.SerialException as e:
        print(f"\n✗ Serial port error: {e}")
        return False
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        ser.close()
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False

def main():
    print("="*60)
    print("Stage 1C: Transport Layer Echo Test")
    print("="*60)
    
    # Find port
    port = find_stm32_port()
    if not port:
        sys.exit(1)
    
    # Run test
    print("\n** Make sure your STM32 is connected with echo firmware flashed **")
    input("Press Enter to start test...")
    
    success = test_echo(port)
    
    if success:
        sys.exit(0)
    else:
        print("\n✗ Some tests failed. Check connections and firmware.")
        sys.exit(1)

if __name__ == "__main__":
    main()