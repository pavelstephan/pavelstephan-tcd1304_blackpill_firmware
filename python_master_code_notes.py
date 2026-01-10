'''
 git repository: https://github.com/Ur-Namma/tcd1304_firmware.git

 echo "# tcd1304_firmware" >> README.md
git init
git add README.md
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/Ur-Namma/tcd1304_firmware.git
git push -u origin main

git remote add origin https://github.com/Ur-Namma/tcd1304_firmware.git
git branch -M main
git push -u origin main



Changes to firmware

Transport layer architecture (all binary, ascii is only at the control layer interfacing with 
python)

Python/Mac
    ↕ (USB)
Ring Buffers (RX: 256 bytes, TX: 512 bytes)
    ↕
USB CDC HAL
    ↕
STM32 Hardware

ring buffer will be used for:

Receiving commands from Python (USB → ring buffer)
Sending responses to Python (ring buffer → USB)
Buffering data between interrupts and main loop

Changes in firmware
- added ring_buffer and USB transport
- In main.c:

Added interrupt-safe ring buffers
- Created a USB transport abstraction layer
- Integrated it with existing USB callbacks
- Modified 4 different files correctly

 #include "usb_transport.h" in USER CODE BEGIN Includes
 usb_transport_init(); in USER CODE BEGIN 2
 usb_transport_process(); in USER CODE BEGIN 3

In usbd_cdc_if.c:

 #include "usbd_cdc_if.h" in USER CODE BEGIN INCLUDE ← You already have this
 #include "usb_transport.h" in USER CODE BEGIN INCLUDE ← Add this
 usb_transport_rx_callback(Buf, *Len); in CDC_Receive_FS function
 usb_transport_tx_complete_callback(); in CDC_TransmitCplt_FS function