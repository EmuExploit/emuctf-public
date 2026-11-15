#!/bin/bash
# Run ./x.sh <ip> <port>
{ printf 'd1d0\nd0e0\ne0e8\n'; sleep 5; } | nc "$@"
