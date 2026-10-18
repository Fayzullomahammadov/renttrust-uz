import urllib.request

data = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
boundary = '----TestBoundary'

parts = [
    f'--{boundary}'.encode(),
    b'Content-Disposition: form-data; name="file"; filename="test_pic.gif"',
    b'Content-Type: image/gif',
    b'',
    data,
    f'--{boundary}--'.encode(),
    b''
]
body = b'\r\n'.join(parts)

req = urllib.request.Request(
    'http://127.0.0.1:5000/api/upload',
    data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
    method='POST'
)

with urllib.request.urlopen(req) as resp:
    print('STATUS:', resp.status)
    print('OUTPUT:', resp.read().decode())
