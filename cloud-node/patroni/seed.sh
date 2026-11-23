#!/bin/sh
# Lance une seule fois, par Patroni, a la creation du premier leader
psql -h 127.0.0.1 -U postgres -d postgres -f /etc/patroni/seed.sql
