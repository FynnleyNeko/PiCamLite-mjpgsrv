from http.server import BaseHTTPRequestHandler,HTTPServer
from socketserver import ThreadingMixIn
from ctypes import windll, wintypes
from PIL import Image
from io import BytesIO
import threading, time, sys, signal
import win32gui, win32ui, win32con
import numpy as np

if ( len(sys.argv) < 4):
    sys.exit()
    
port = int(sys.argv[1])
framerate = int(sys.argv[2])
quality = int(sys.argv[3])
if ( len(sys.argv) == 4 ):
    irismode = False
else:
    irismode = bool(int(sys.argv[4]))
    if irismode:
        if (framerate > 30):
            framerate=30

class GracefulExit:
  exit_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self, signum, frame):
    self.exit_now = True

exiter = GracefulExit()

class WindowCapture:
    w = 0
    h = 0
    hwnd = None
    offset_x = 0
    offset_y = 0

    def __init__(self, window_name):
        windll.user32.SetThreadDpiAwarenessContext(wintypes.HANDLE(-2))
        self.hwnd = win32gui.FindWindow(None, window_name)
        if not self.hwnd:
            raise Exception()
        window_rect = win32gui.GetWindowRect(self.hwnd)
        self.h = window_rect[3] - window_rect[1]
        self.w = window_rect[2] - window_rect[0]
        if irismode:
            self.offset_x = round((self.w - 640) / 2)
            self.offset_y = self.h - 480 - self.offset_x + 1
            self.w = 640
            self.h = 480
        else:
            self.offset_x = round((self.w - 320) / 2)
            self.offset_y = self.h - 240 - self.offset_x + 1
            self.w = 320
            self.h = 240

    def get_frame(self):
        wDC = win32gui.GetWindowDC(self.hwnd)
        dcObj = win32ui.CreateDCFromHandle(wDC)
        cDC = dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, self.w, self.h)
        cDC.SelectObject(dataBitMap)
        cDC.BitBlt((0, 0), (self.w, self.h), dcObj, (self.offset_x, self.offset_y), win32con.SRCCOPY)
        signedIntsArray = dataBitMap.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype='uint8')
        img.shape = (self.h, self.w, 4)
        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())
        img = img[...,:3]
        img = np.ascontiguousarray(img)
        return img

class CamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith('/left'):
            leftcap = None
            # If we get requests before having ever initialized the capture we just send 404
            try:
                leftcap = WindowCapture('Left Eye')
            except:
                self.send_response(404)
                return
            self.send_response(200)
            self.send_header('Content-type','multipart/x-mixed-replace; boundary=--jpgboundary')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0')
            self.end_headers()
            while not exiter.exit_now:
                # Set timer to current time and set target time for next frame
                cur_time = int(time.time_ns())
                next_time = cur_time + round(1000000000 / framerate)
                
                # Try to get the frame and if it fails try to reinitialize capture
                try:
                    jpg = Image.fromarray(leftcap.get_frame())
                except:
                    leftcap = None
                    while not leftcap:
                        try:
                            leftcap = WindowCapture('Left Eye')
                        except:
                            time.sleep(1)
                            
                # Compress and send frame to client
                tmpFile = BytesIO()
                jpg.save(tmpFile,'JPEG',quality=quality,subsampling=0)
                self.wfile.write(b"\r\n--jpgboundary\r\n")
                self.send_header('Content-type','image/jpeg')
                self.send_header('Content-length',str(tmpFile.getbuffer().nbytes))
                self.end_headers()
                tmpFile.seek(0)
                self.wfile.write(tmpFile.read())
                
                # Get current time and wait until we need the next frame to keep at desired framerate
                cur_time = int(time.time_ns())
                if ( cur_time < next_time ):
                    time.sleep( (next_time - cur_time) / 1000000000.0)
            return
        elif self.path.endswith('/right'):
            rightcap = None
            # If we get requests before having ever initialized the capture we just send 404
            try:
                rightcap = WindowCapture('Right Eye')
            except:
                self.send_response(404)
                return
            self.send_response(200)
            self.send_header('Content-type','multipart/x-mixed-replace; boundary=--jpgboundary')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0')
            self.end_headers()
            while not exiter.exit_now:
                # Set timer to current time and set target time for next frame
                cur_time = int(time.time_ns())
                next_time = cur_time + round(1000000000 / framerate)
                
                # Try to get the frame and if it fails try to reinitialize capture
                try:
                    jpg = Image.fromarray(rightcap.get_frame())
                except:
                    rightcap = None
                    while not rightcap:
                        try:
                            rightcap = WindowCapture('Right Eye')
                        except:
                            time.sleep(1)
                            
                # Compress and send frame to client
                tmpFile = BytesIO()
                jpg.save(tmpFile,'JPEG',quality=quality,subsampling=0)
                self.wfile.write(b"\r\n--jpgboundary\r\n")
                self.send_header('Content-type','image/jpeg')
                self.send_header('Content-length',str(tmpFile.getbuffer().nbytes))
                self.end_headers()
                tmpFile.seek(0)
                self.wfile.write(tmpFile.read())
                
                # Get current time and wait until we need the next frame to keep at desired framerate
                cur_time = int(time.time_ns())
                if ( cur_time < next_time ):
                    time.sleep( (next_time - cur_time) / 1000000000.0)
            return
        else:
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            header = '<html><head><title>PiCamLite</title></head><body>'
            body1 = '<h1>PiCamLite is running!</h1>'
            body2 = '<a href="http://127.0.0.1:' + str(port) + '/left">Left Camera (/left)</a><br>'
            body3 = '<a href="http://127.0.0.1:' + str(port) + '/right">Right Camera (/right)</a>'
            end = '</body></html>'
            self.wfile.write(header.encode())
            self.wfile.write(body1.encode())
            self.wfile.write(body2.encode())
            self.wfile.write(body3.encode())
            self.wfile.write(end.encode())
            return
            
class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass
    
def main():
    server = ThreadingSimpleServer(('127.0.0.1', port), CamHandler)
    
    while not exiter.exit_now:
        server.handle_request()

if __name__ == '__main__':
    main()

