#!/usr/bin/env python3
"""
Debug version - shows raw bytes
"""

import serial
import serial.tools.list_ports
import time

def find_stm32_port():
    """Find the STM32 USB CDC port"""
    ports = serial.tools.list_ports.comports()
    
    print("Available serial ports:")
    for i, port in enumerate(ports):
        print(f"  [{i}] {port.device} - {port.description}")
    
    for port in ports:
        if any(keyword in port.description.lower() 
               for keyword in ['stm32', 'stmicroelectronics', 'usb serial']):
            print(f"\nAuto-detected STM32 at: {port.device}")
            return port.device
    
    if ports:
        choice = input(f"\nEnter port number [0-{len(ports)-1}]: ")
        return ports[int(choice)].device
    return None

def test_raw_echo(port_name):
    """Test with raw byte display"""
    try:
        ser = serial.Serial(port=port_name, baudrate=115200, timeout=2)
        
        print(f"\nPort: {port_name}")
        print("Waiting 1 second for USB to stabilize...")
        time.sleep(1)
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        print("Buffers cleared\n")
        
        # Test simple bytes
        for test_byte in [0x41, 0x42, 0x43, 0x44, 0x45]:  # A, B, C, D, E
            print(f"Sending: 0x{test_byte:02X} ({chr(test_byte)})")
            ser.write(bytes([test_byte]))
            
            time.sleep(0.2)  # Give it time
            
            if ser.in_waiting > 0:
                received = ser.read(ser.in_waiting)
                print(f"  Received {len(received)} byte(s):", end=" ")
                for b in received:
                    print(f"0x{b:02X}", end=" ")
                    if 32 <= b < 127:
                        print(f"('{chr(b)}')", end=" ")
                print()
                
                if len(received) == 1 and received[0] == test_byte:
                    print("  ✓ MATCH!")
                else:
                    print("  ✗ MISMATCH")
            else:
                print("  ✗ No response")
            
            print()
        
        ser.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    port = find_stm32_port()
    if port:
        input("Press Enter to start debug test...")
        test_raw_echo(port)