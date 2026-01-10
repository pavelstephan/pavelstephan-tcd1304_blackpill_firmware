#!/usr/bin/env python3
"""
Test script to examine CCD buffer data from STM32
Run this to see what's actually in your buffers
"""

import serial
import serial.tools.list_ports
import struct
import matplotlib.pyplot as plt
import numpy as np

def find_stm32_port():
    """
    Automatically find the STM32 USB CDC port
    """
    ports = serial.tools.list_ports.comports()
    
    print("Available serial ports:")
    for i, port in enumerate(ports):
        print(f"  [{i}] {port.device} - {port.description}")
    
    # Try to auto-detect STM32
    for port in ports:
        # STM32 often shows up with these identifiers
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

# Add this to your analysis
def find_pixel_pattern(frames):
    """
    TCD1304 has characteristic patterns:
    - First ~32 pixels: optical black (dark reference)
    - Next ~3662 pixels: active area
    - After that: ???
    """
    avg_frame = np.mean(frames, axis=0)
    
    # Look for transitions
    window = 50
    for i in range(0, len(avg_frame) - window, 10):
        current_mean = np.mean(avg_frame[i:i+window])
        next_mean = np.mean(avg_frame[i+window:i+2*window])
        if abs(current_mean - next_mean) > 50:  # Significant change
            print(f"Signal transition at pixel {i}")

def capture_frames(port_name, num_frames=5, bytes_per_frame=12000):
    """
    Capture multiple frames and analyze them
    """
    try:
        # Open serial port
        ser = serial.Serial(
            port=port_name,
            baudrate=115200,  # CDC ignores this, but pyserial requires it
            timeout=2
        )
        
        print(f"\nOpened {port_name}")
        print(f"Capturing {num_frames} frames ({bytes_per_frame} bytes each)...")
        
        frames = []
        
        for i in range(num_frames):
            # Read one frame worth of data
            raw_data = ser.read(bytes_per_frame)
            
            if len(raw_data) != bytes_per_frame:
                print(f"Warning: Frame {i} only got {len(raw_data)} bytes")
                continue
            
            # Unpack as 16-bit unsigned integers (little-endian)
            pixels = struct.unpack(f'<{bytes_per_frame//2}H', raw_data)
            frames.append(pixels)
            
            print(f"  Frame {i+1}/{num_frames} captured: "
                  f"min={min(pixels)}, max={max(pixels)}, "
                  f"mean={np.mean(pixels):.1f}")
        
        ser.close()
        return frames
        
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return None
    except KeyboardInterrupt:
        print("\nCapture interrupted by user")
        ser.close()
        return None

def analyze_frames(frames):
    """
    Analyze captured frames to find where valid data ends
    """
    if not frames:
        print("No frames to analyze")
        return
    
    print(f"\n{'='*60}")
    print("ANALYSIS")
    print(f"{'='*60}")
    
    # Convert to numpy array for easier analysis
    frames_array = np.array(frames)
    
    # Average across all frames
    avg_frame = np.mean(frames_array, axis=0)
    std_frame = np.std(frames_array, axis=0)
    
    print(f"Total samples per frame: {len(avg_frame)}")
    print(f"Overall min: {np.min(avg_frame):.1f}")
    print(f"Overall max: {np.max(avg_frame):.1f}")
    print(f"Overall mean: {np.mean(avg_frame):.1f}")
    
    # Try to find where data becomes constant (likely end of valid data)
    # Look for where variance drops significantly
    window_size = 100
    variance_threshold = 10  # Adjust if needed
    
    for i in range(0, len(avg_frame) - window_size, window_size):
        window_std = np.std(avg_frame[i:i+window_size])
        if window_std < variance_threshold and i > 3000:
            print(f"\nLikely end of valid data around pixel {i}")
            print(f"  (variance dropped below {variance_threshold})")
            break
    
    # Plot results
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    
    # Plot 1: First frame (full range)
    axes[0].plot(frames[0])
    axes[0].set_title('First Frame - Full Buffer')
    axes[0].set_xlabel('Pixel Index')
    axes[0].set_ylabel('ADC Value')
    axes[0].grid(True)
    axes[0].axvline(x=3694, color='r', linestyle='--', label='Expected pixel count (3694)')
    axes[0].legend()
    
    # Plot 2: Zoomed to expected range
    axes[1].plot(frames[0][:4000])
    axes[1].set_title('First Frame - Zoomed to Expected Range')
    axes[1].set_xlabel('Pixel Index')
    axes[1].set_ylabel('ADC Value')
    axes[1].grid(True)
    axes[1].axvline(x=3694, color='r', linestyle='--', label='Expected pixel count (3694)')
    axes[1].legend()
    
    # Plot 3: Standard deviation across frames
    axes[2].plot(std_frame)
    axes[2].set_title('Standard Deviation Across All Frames')
    axes[2].set_xlabel('Pixel Index')
    axes[2].set_ylabel('Std Dev')
    axes[2].grid(True)
    axes[2].axvline(x=3694, color='r', linestyle='--', label='Expected pixel count (3694)')
    axes[2].legend()
    
    plt.tight_layout()
    plt.savefig('ccd_buffer_analysis.png', dpi=150)
    print(f"\nPlot saved as 'ccd_buffer_analysis.png'")
    plt.show()

def main():
    print("="*60)
    print("CCD Buffer Analysis Tool")
    print("="*60)
    
    # Find the port
    port = find_stm32_port()
    if not port:
        return
    
    # Capture frames
    print("\n** Make sure your STM32 is connected and running **")
    input("Press Enter to start capture...")
    
    frames = capture_frames(
        port_name=port,
        num_frames=5,
        bytes_per_frame=12000  # Current buffer size
    )
    
    if frames:
        analyze_frames(frames)
        find_pixel_pattern(frames)  # Add this line
    
    print("\nDone!")

if __name__ == "__main__":
    main()