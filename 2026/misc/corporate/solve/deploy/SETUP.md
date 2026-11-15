# Deploy Corporate

```sh
cd challs/misc/corporate/solve/deploy
export SITE_ADDRESS=http://localhost:8080 HTTP_BIND=127.0.0.1:8080 HTTP_PORT=8080
export HTTPS_BIND=127.0.0.1:8443 AUTH_MODE=disabled
export REVIEW_SITE_ADDRESS=http://review.localhost:8080
export UPLOAD_SITE_ADDRESS=http://upload.localhost:8080
./stack.sh up
```
### Monitor

```sh
./stack.sh up                  # build/start and wait; safe to repeat
./stack.sh down                # stop
./stack.sh restart bot support # apply code/config changes to selected services
./stack.sh reset               # fresh chat; also use after a host reboot
./stack.sh logs bot
./stack.sh monitor             # live terminal dashboard; Python 3 required
python3 botdump.py             # writes bot-conversations.html; needs host Python 3
```