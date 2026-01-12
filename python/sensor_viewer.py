#!/usr/bin/env python3
"""
TCD1304 Sensor Viewer - Fixed Version
Properly sends START/STOP commands and handles responses
"""

import serial
import serial.tools.list_ports
import struct
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time
from collections import deque
import csv
from datetime import datetime

# Frame structure constants
FRAME_START_MARKER = b'FRME'
FRAME_END_MARKER = b'ENDF'
FRAME_HEADER_SIZE = 8
FRAME_FOOTER_SIZE = 6
PIXEL_COUNT = 3694
PIXEL_DATA_SIZE = PIXEL_COUNT * 2
TOTAL_FRAME_SIZE = FRAME_HEADER_SIZE + PIXEL_DATA_SIZE + FRAME_FOOTER_SIZE  # 7402 bytes


def crc16_ccitt(data):
    """Calculate CRC-16-CCITT checksum"""
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return crc


def find_stm32_port():
    """Find and return the STM32 USB CDC port"""
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
    
    # Manual selection
    if ports:
        choice = input(f"\nEnter port number [0-{len(ports)-1}]: ")
        return ports[int(choice)].device
    else:
        print("No serial ports found!")
        return None


def send_command(ser, command, wait_response=True, timeout=1.0):
    """
    Send a command and optionally wait for ASCII response
    Returns: response string or None
    """
    print(f"Sending command: {command.strip()}")
    ser.write(command.encode() if isinstance(command, str) else command)
    
    if wait_response:
        start_time = time.time()
        response = b''
        
        # Read until we get a newline or timeout
        while time.time() - start_time < timeout:
            if ser.in_waiting > 0:
                byte = ser.read(1)
                response += byte
                if byte == b'\n':
                    break
            time.sleep(0.001)
        
        response_str = response.decode('ascii', errors='ignore').strip()
        print(f"Response: {response_str}")
        return response_str
    
    return None


class FrameParser:
    """Parse TCD1304 frames from serial data stream"""
    
    def __init__(self):
        self.buffer = bytearray()
        self.frames_received = 0
        self.frames_valid = 0
        self.frames_crc_error = 0
        
    def add_data(self, data):
        """Add incoming data to buffer"""
        self.buffer.extend(data)
        
    def find_frame(self):
        """
        Search buffer for complete frame
        Returns: (frame_data, frame_counter, pixels) or (None, None, None)
        """
        # Look for start marker
        start_idx = self.buffer.find(FRAME_START_MARKER)
        
        if start_idx == -1:
            # No start marker found, keep last 10 bytes
            if len(self.buffer) > 10:
                self.buffer = self.buffer[-10:]
            return None, None, None
        
        # Remove any junk before start marker
        if start_idx > 0:
            self.buffer = self.buffer[start_idx:]
        
        # Check if we have enough data for a complete frame
        if len(self.buffer) < TOTAL_FRAME_SIZE:
            return None, None, None
        
        # Extract frame
        frame_data = bytes(self.buffer[:TOTAL_FRAME_SIZE])
        
        # Parse header
        start_marker = frame_data[0:4]
        frame_counter = struct.unpack('<H', frame_data[4:6])[0]
        pixel_count = struct.unpack('<H', frame_data[6:8])[0]
        
        # Verify header
        if start_marker != FRAME_START_MARKER or pixel_count != PIXEL_COUNT:
            self.buffer = self.buffer[4:]
            return None, None, None
        
        # Extract pixel data
        pixel_data_start = FRAME_HEADER_SIZE
        pixel_data_end = pixel_data_start + PIXEL_DATA_SIZE
        pixel_data_bytes = frame_data[pixel_data_start:pixel_data_end]
        
        # Parse pixels
        pixels = struct.unpack(f'<{PIXEL_COUNT}H', pixel_data_bytes)
        
        # Extract footer
        end_marker = frame_data[pixel_data_end:pixel_data_end+4]
        received_crc = struct.unpack('<H', frame_data[pixel_data_end+4:pixel_data_end+6])[0]
        
        # Verify end marker
        if end_marker != FRAME_END_MARKER:
            self.buffer = self.buffer[4:]
            return None, None, None
        
        # Verify CRC
        crc_data = frame_data[:pixel_data_end+4]
        calculated_crc = crc16_ccitt(crc_data)
        
        self.frames_received += 1
        
        if calculated_crc != received_crc:
            print(f"CRC mismatch! Calc: 0x{calculated_crc:04X}, Recv: 0x{received_crc:04X}")
            self.frames_crc_error += 1
            self.buffer = self.buffer[TOTAL_FRAME_SIZE:]
            return None, None, None
        
        # Valid frame!
        self.frames_valid += 1
        self.buffer = self.buffer[TOTAL_FRAME_SIZE:]
        
        return frame_data, frame_counter, pixels


def save_frame_to_csv(pixels, filename=None):
    """Save a frame to CSV with pixel labels"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"frame_{timestamp}.csv"
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Pixel_Label', 'ADC_Value'])
        
        # Write dummy pixels (D0-D45)
        for i in range(46):
            label = f"D{i}"
            writer.writerow([label, pixels[i]])
        
        # Write signal pixels (S0-S3647)
        for i in range(46, PIXEL_COUNT):
            label = f"S{i-46}"
            writer.writerow([label, pixels[i]])
    
    print(f"Frame saved to: {filename}")
    return filename


def plot_static_frame(pixels):
    """Create a static plot of one frame"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))
    
    # Full spectrum plot
    pixel_indices = np.arange(PIXEL_COUNT)
    ax1.plot(pixel_indices, pixels, linewidth=0.5, color='blue')
    ax1.set_xlabel('Pixel Index')
    ax1.set_ylabel('ADC Value (12-bit)')
    ax1.set_title('TCD1304 Full Spectrum')
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, PIXEL_COUNT)
    
    # Mark dummy pixel regions
    ax1.axvspan(0, 46, alpha=0.2, color='gray', label='Dummy pixels')
    ax1.legend()
    
    # Statistics
    stats_text = f"Min: {np.min(pixels)}\n"
    stats_text += f"Max: {np.max(pixels)}\n"
    stats_text += f"Mean: {np.mean(pixels):.1f}\n"
    stats_text += f"Std: {np.std(pixels):.1f}"
    ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Signal pixels only
    signal_pixels = pixels[46:]
    signal_indices = np.arange(len(signal_pixels))
    ax2.plot(signal_indices, signal_pixels, linewidth=0.5, color='green')
    ax2.set_xlabel('Signal Pixel (S0-S3647)')
    ax2.set_ylabel('ADC Value (12-bit)')
    ax2.set_title('Signal Pixels Only (Dummy pixels excluded)')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


def capture_single_frame(serial_port, timeout=5):
    """
    Capture a single frame from the sensor
    Sends START, captures one frame, then sends STOP
    """
    parser = FrameParser()
    
    print("\nCapturing single frame...")
    
    # Clear any stale data
    time.sleep(0.1)
    serial_port.reset_input_buffer()
    
    # Send START command
    response = send_command(serial_port, "START\n", wait_response=True, timeout=0.5)
    if not response or "OK" not in response:
        print("Warning: Unexpected START response")
    
    # Wait a bit for frames to start flowing
    time.sleep(0.2)
    
    # Try to capture a frame
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if serial_port.in_waiting > 0:
            data = serial_port.read(serial_port.in_waiting)
            parser.add_data(data)
            
            frame_data, frame_counter, pixels = parser.find_frame()
            
            if pixels is not None:
                print(f"Frame captured! Counter: {frame_counter}")
                
                # Send STOP command
                time.sleep(0.1)
                serial_port.reset_input_buffer()  # Clear binary data
                send_command(serial_port, "STOP\n", wait_response=True, timeout=0.5)
                
                return np.array(pixels), frame_counter
        
        time.sleep(0.01)
    
    # Timeout - still try to stop
    serial_port.reset_input_buffer()
    send_command(serial_port, "STOP\n", wait_response=True, timeout=0.5)
    
    print("Timeout waiting for frame")
    return None, None


class LiveViewer:
    """Live viewer with real-time plot updates"""
    
    def __init__(self, serial_port):
        self.ser = serial_port
        self.parser = FrameParser()
        self.current_pixels = None
        self.frame_times = deque(maxlen=30)
        self.last_frame_counter = None
        self.running = True
        self.started = False
        
        # Set up plot
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(14, 8))
        self.line1, = self.ax1.plot([], [], linewidth=0.5, color='blue')
        self.line2, = self.ax2.plot([], [], linewidth=0.5, color='green')
        
        # Configure axes
        self.ax1.set_xlim(0, PIXEL_COUNT)
        self.ax1.set_ylim(0, 4095)
        self.ax1.set_xlabel('Pixel Index')
        self.ax1.set_ylabel('ADC Value')
        self.ax1.set_title('TCD1304 Live View - Full Spectrum')
        self.ax1.grid(True, alpha=0.3)
        self.ax1.axvspan(0, 46, alpha=0.2, color='gray')
        
        self.ax2.set_xlim(0, PIXEL_COUNT - 46)
        self.ax2.set_ylim(0, 4095)
        self.ax2.set_xlabel('Signal Pixel (S0-S3647)')
        self.ax2.set_ylabel('ADC Value')
        self.ax2.set_title('Signal Pixels Only')
        self.ax2.grid(True, alpha=0.3)
        
        # Status text
        self.status_text = self.ax1.text(0.02, 0.98, '', transform=self.ax1.transAxes,
                                         verticalalignment='top',
                                         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        
    def update_plot(self, frame):
        """Animation update function"""
        if not self.running:
            return self.line1, self.line2, self.status_text
        
        # Send START on first update
        if not self.started:
            print("Sending START command...")
            send_command(self.ser, "START\n", wait_response=False)
            self.started = True
            time.sleep(0.2)  # Give it time to start
        
        # Read available data
        if self.ser.in_waiting > 0:
            data = self.ser.read(self.ser.in_waiting)
            self.parser.add_data(data)
        
        # Try to parse a frame
        frame_data, frame_counter, pixels = self.parser.find_frame()
        
        if pixels is not None:
            self.current_pixels = np.array(pixels)
            self.frame_times.append(time.time())
            self.last_frame_counter = frame_counter
            
            # Update plots
            pixel_indices = np.arange(PIXEL_COUNT)
            self.line1.set_data(pixel_indices, self.current_pixels)
            
            signal_pixels = self.current_pixels[46:]
            signal_indices = np.arange(len(signal_pixels))
            self.line2.set_data(signal_indices, signal_pixels)
            
            # Auto-scale Y axis
            if len(self.current_pixels) > 0:
                y_min = max(0, np.min(self.current_pixels) - 100)
                y_max = min(4095, np.max(self.current_pixels) + 100)
                self.ax1.set_ylim(y_min, y_max)
                self.ax2.set_ylim(y_min, y_max)
            
            # Calculate FPS
            fps = 0
            if len(self.frame_times) > 1:
                time_span = self.frame_times[-1] - self.frame_times[0]
                if time_span > 0:
                    fps = len(self.frame_times) / time_span
            
            # Update status
            status = f"Frame: {frame_counter}\n"
            status += f"FPS: {fps:.1f}\n"
            status += f"Min: {np.min(self.current_pixels)}\n"
            status += f"Max: {np.max(self.current_pixels)}\n"
            status += f"Mean: {np.mean(self.current_pixels):.1f}\n"
            status += f"Valid: {self.parser.frames_valid}\n"
            status += f"CRC Errors: {self.parser.frames_crc_error}"
            self.status_text.set_text(status)
        
        return self.line1, self.line2, self.status_text
    
    def start(self):
        """Start live viewing"""
        ani = FuncAnimation(self.fig, self.update_plot, interval=50, blit=True)
        
        print("\n" + "="*60)
        print("LIVE VIEWER RUNNING")
        print("="*60)
        print("Close the plot window to exit")
        print("Press 's' in plot window to save current frame")
        
        # Key press handler
        def on_key(event):
            if event.key == 's' and self.current_pixels is not None:
                filename = save_frame_to_csv(self.current_pixels)
                print(f"Saved frame to {filename}")
        
        self.fig.canvas.mpl_connect('key_press_event', on_key)
        
        # Handle window close
        def on_close(event):
            self.running = False
            print("\nStopping acquisition...")
            self.ser.reset_input_buffer()
            send_command(self.ser, "STOP\n", wait_response=True, timeout=0.5)
        
        self.fig.canvas.mpl_connect('close_event', on_close)
        
        try:
            plt.show()
        finally:
            self.running = False
            # Make sure we send STOP
            time.sleep(0.1)
            self.ser.reset_input_buffer()
            send_command(self.ser, "STOP\n", wait_response=True, timeout=0.5)


def main():
    """Main entry point"""
    print("="*60)
    print("TCD1304 Sensor Viewer - Phase 1 (Fixed)")
    print("="*60)
    
    # Find port
    port = find_stm32_port()
    if not port:
        return
    
    # Open serial connection
    try:
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            timeout=1
        )
        print(f"\nConnected to {port}")
        time.sleep(1)  # Let USB stabilize
        
        # Check for ready message
        if ser.in_waiting > 0:
            ready_msg = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
            print(f"Device says: {ready_msg.strip()}")
        
        # Check status
        response = send_command(ser, "STATUS\n", wait_response=True, timeout=1.0)
        
    except serial.SerialException as e:
        print(f"Error opening port: {e}")
        return
    
    # Menu
    while True:
        print("\n" + "="*60)
        print("OPTIONS:")
        print("  [1] Capture and plot single frame")
        print("  [2] Live viewer (real-time plot)")
        print("  [3] Capture and save to CSV")
        print("  [4] Check status")
        print("  [5] Exit")
        print("="*60)
        
        choice = input("Select option: ").strip()
        
        if choice == '1':
            pixels, frame_counter = capture_single_frame(ser)
            if pixels is not None:
                print(f"\nFrame {frame_counter} statistics:")
                print(f"  Min: {np.min(pixels)}")
                print(f"  Max: {np.max(pixels)}")
                print(f"  Mean: {np.mean(pixels):.1f}")
                print(f"  Std: {np.std(pixels):.1f}")
                
                fig = plot_static_frame(pixels)
                plt.show()
        
        elif choice == '2':
            viewer = LiveViewer(ser)
            viewer.start()
        
        elif choice == '3':
            pixels, frame_counter = capture_single_frame(ser)
            if pixels is not None:
                filename = save_frame_to_csv(pixels)
                print(f"Frame {frame_counter} saved!")
        
        elif choice == '4':
            ser.reset_input_buffer()
            response = send_command(ser, "STATUS\n", wait_response=True, timeout=1.0)
        
        elif choice == '5':
            # Make sure we're stopped
            ser.reset_input_buffer()
            send_command(ser, "STOP\n", wait_response=True, timeout=0.5)
            print("Exiting...")
            break
        
        else:
            print("Invalid option")
    
    ser.close()
    print("Done!")


if __name__ == "__main__":
    main()